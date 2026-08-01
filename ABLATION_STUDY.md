# Layer Ablation Study — STBV-Bench (real, bug-fixed pipeline)

This document is the reproducible record of the layer-ablation study requested
after the n=10,000 STBV-Bench v1 baseline run (`PUBLICATION_PROGRESS.md`,
accuracy 0.688 / precision 0.983 / recall 0.565 / F1 0.718 / FPR 0.023).
Everything below was actually executed this session; nothing is projected or
estimated. Code references are to the state of the repo at the time this
study was run (commit `33b572be4` and the `enable_b3` addition committed
alongside this document).

---

## Step 1 — Audit of the existing ablation mechanism

### 1a. How does the pipeline currently disable a layer?

Read `pipeline/orchestrator.py` (`ISCEPipeline.__init__`/`run`) directly.

- **MBD** (`enable_mbd: bool = True`, `orchestrator.py:114`): a real,
  code-level skip. `run()` only calls `self._run_mbd(...)` inside
  `if self.enable_mbd:` (`orchestrator.py:430-433`); when disabled,
  `mbd_dict = None` and the MBD computation never executes at all — not
  computed-then-ignored.
- **CP** (`enable_cp: bool = True`, `orchestrator.py:115`): same pattern —
  `_run_cp(...)` only runs inside `if self.enable_cp:`
  (`orchestrator.py:453-460`); disabled means `cp_dict = None` and
  `cp_layer()` never runs.
- **B2** (`b2_explain.ExplainabilityEngine`): **always runs, unconditionally**
  (`orchestrator.py:435-448`, comment at 435: "Run B2 (Explainability) —
  ALWAYS runs, including on B1-fatal paths"). There is no flag to disable
  it. `TrustDecisionEngine.decide()` also hard-requires a non-`None`
  `explainability_report` (`decision_engine.py:112-113`,
  `MissingLayerInputError` otherwise) — B2 is not optional in the frozen
  fusion contract.
- **B3**: **no existing disable flag at all.** `synthesize_message(...)`
  and `classify_text(...)` are called unconditionally in the non-B1-fatal
  path (`orchestrator.py:520-525`, or the ensembling branch at 465-518 if
  `enable_b3_ensembling` is set — irrelevant here, that config is off by
  default per `isce_config.yaml`). The only way B3 doesn't run today is
  the B1-fatal short-circuit (`orchestrator.py:361-425`), which is a
  data-dependent property of a given message, not something an ablation
  config can select.
- **Fusion (Trust Decision Engine)**: `self.trust_engine.decide(b1_dict,
  b2_dict, b3_result)` is called unconditionally on every non-fatal
  message (`orchestrator.py:636`) and is the sole fusion point
  (`decision_engine.py`'s own module docstring: "the only component that
  fuses B1... B2... and B3... No B-layer imports another layer; this
  module is the sole composition point"). There is no existing flag to
  bypass it and use a single layer's raw output as the final decision.

**Conclusion:** MBD and CP ablation is already a real, verified skip of
computation. B3 ablation has no existing mechanism and required a new
code-level flag (added this session, see 1c). Fusion-bypass (config 4) has
no existing mechanism in `orchestrator.py`/`decision_engine.py` and, per
the frozen-architecture mandate, was **not** added there — instead it is
implemented as a separate, clearly-labeled scoring function in the ablation
harness itself (`stbv_bench/run_ablation.py`), which consumes the same
`b3_result` dict the real pipeline produces and reuses
`TrustPolicy.classify_semantic_risk()` (already-existing code) rather than
hand-rolling new risk logic. This does not touch or reinterpret
`decision_engine.decide()`; it is an alternative decision function computed
alongside it, never substituted into the frozen decide() path.

### 1b. Is each config a real code-level ablation, not post-hoc filtering?

| Config | Mechanism | Real skip or post-hoc filter? |
|---|---|---|
| 1. B1 only | `enable_mbd=False, enable_cp=False, enable_b3=False` | Real skip — MBD/CP/B3 computation genuinely does not execute (verified in 1a/1c). B2 still executes (see caveat below), but only ever sees B1's own `validation_assessment` (`b2.explain(b1_dict)`, `orchestrator.py:446`) — it adds no independent evidence source when MBD is off (see 1c note). |
| 2. B1+B2 | `enable_mbd=True, enable_cp=False, enable_b3=False` | Real skip. Turning MBD on is what makes "B1+B2" observably different from "B1 only": B2 now fuses `TrustEvidence.from_mbd_result(mbd_dict)` (`orchestrator.py:440-444`), i.e. MBD's behavioral/misbehavior signal is what B2 "adds." |
| 3. B1+B2+CP | `enable_mbd=True, enable_cp=True, enable_b3=False` | Real skip. CP genuinely runs and folds into `b2_dict` via the CP evidence fold (`orchestrator.py:554-629`); B3 genuinely does not run. |
| 4. B1+B2+CP+B3, no fusion | `enable_mbd=True, enable_cp=True, enable_b3=True` (full computation), decision **recomputed** from `res["b3"]` alone via `TrustPolicy.classify_semantic_risk()`, ignoring `res["decision"]` | B3 and every upstream layer genuinely execute and produce real output; only the **decision** is taken from B3's own risk band instead of `decide()`'s fused output. This is not filtering logged evidence after the fact — it's a legitimate second decision function over the same, honestly-computed evidence, and is reported as such (config 4's decision source is disjoint from config 5's). |
| 5. Full stack | Unmodified `ISCEPipeline().run(...)`, all flags default | Identical code path to the STBV-Bench v1 baseline. Re-run explicitly in this batch (not reused from the prior run) so all 5 configs share one harness invocation, one process, one fixed 10,000-sample slice. |

### 1c. Blocker found and the minimal fix applied

**Blocker:** no `enable_b3` flag existed. Minimal fix (committed alongside
this document): added `enable_b3: bool = True` to `ISCEPipeline.__init__`
(default `True` preserves all existing behavior for every non-ablation
caller — this is additive, not a change to the frozen architecture's
default operation, and follows the exact precedent already set by
`enable_mbd`/`enable_cp`). When `False`:
- `preload_classifier()` is not called at construction (skips the B3 model
  load entirely for that pipeline instance).
- In `run()`, the B3 synthesize+classify block is skipped and
  `b3_result` is set to `{"available": False, "label": None,
  "confidence": None, "risk_level": "unavailable", "status": "disabled
  (ablation: enable_b3=False)"}` — the same shape `decide()` already
  handles for the B1-fatal path, so no downstream code needed to change.
  `TrustPolicy.classify_semantic_risk()` reads `available: False` and
  returns `SemanticRisk.UNAVAILABLE` (`policy.py:112-113`), which
  `decision_engine.py`'s `_semantic_mass` maps to a **vacuous** mass
  function (`decision_engine.py:168-169`: `MassFunction.vacuous()`) — i.e.
  genuinely zero influence on the DS fusion, not a thumb on the scale in
  either direction.

**B2 caveat (reported plainly, not glossed over):** B2 cannot be disabled
by any config — it is a hard, unconditional dependency of
`TrustDecisionEngine.decide()`. "B1 only" therefore actually means "B1,
plus B2 acting as a pure passthrough of B1's own validation score/reasons
(no MBD evidence folded in)." This is stated explicitly here because it
changes what "config 1 vs config 2" is actually measuring: the marginal
value of **MBD**, not of "B2" as an independent detection source — B2 by
itself does not add new evidence, only recombines whatever upstream
evidence it's given (see `b2_explain`'s `explain()` vs `explain_evidence()`
split at `orchestrator.py:439-448`).

No config in the requested list was skipped. All five are implemented as
above; the code diff is `pipeline/orchestrator.py`'s `enable_b3` addition,
committed separately from this document per the "root-cause any bugs
found, don't just patch silently" standard.
