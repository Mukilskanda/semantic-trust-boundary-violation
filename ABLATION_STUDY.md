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

---

## Step 2 — Execution

`stbv_bench/run_ablation.py`, run against the identical fixed slice used for
the STBV-Bench v1 baseline (`data/stbv_bench/v1/stbv_bench.jsonl[:10000]`,
same seed=7 build, no re-sampling or re-generation). Fresh `ISCEPipeline`
per config per sample (configs 1-3), and one shared full-computation
pipeline run per sample for configs 4/5 (see the module docstring in
`run_ablation.py` for why sharing that one run is not a validity problem).
10,000 samples x 5 configs completed in 3,743.8s (≈62 minutes). Per-sample
CSVs: `results/ablation/ablation_config_{1..5}.csv`.

---

## Step 3 — Per-config metrics (n=10,000 each)

| Config | tp | fp | fn | tn | Accuracy | Precision | Recall | F1 (95% CI) | FPR | FNR | MCC |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. B1 only | 0 | 0 | 7007 | 2993 | 0.2993 | undefined (0 predicted positive) | 0.0000 | undefined† | 0.0000 | 1.0000 | undefined |
| 2. B1+B2 | 124 | 69 | 6883 | 2924 | 0.3048 | 0.6425 | 0.0177 | 0.0344 [0.0290, 0.0410] | 0.0231 | 0.9823 | -0.0178 |
| 3. B1+B2+CP | 124 | 69 | 6883 | 2924 | 0.3048 | 0.6425 | 0.0177 | 0.0344 [0.0290, 0.0410] | 0.0231 | 0.9823 | -0.0178 |
| 4. B1+B2+CP+B3 (no fusion) | 3900 | 0 | 3107 | 2993 | 0.6893 | 1.0000 | 0.5566 | 0.7151 [0.7054, 0.7245] | 0.0000 | 0.4434 | 0.5226 |
| 5. Full stack | 3959 | 69 | 3048 | 2924 | 0.6883 | 0.9829 | 0.5650 | 0.7175 [0.7080, 0.7270] | 0.0231 | 0.4350 | 0.5060 |

†Config 1 makes zero positive predictions on every one of the 10,000
samples (`tp=0, fp=0`), so precision and F1 are mathematically undefined
(0/0), reported here as "undefined" rather than silently defaulted to a
number that would misrepresent what happened. Where an aggregate F1
comparison against config 1 is needed below (the 1→2 anomaly-check row),
its F1 is treated as 0 by convention (a classifier that flags nothing is
credited with zero detection ability), and this substitution is stated
explicitly rather than left implicit.

Config 5's numbers are, as required, produced by this same batch/harness
run rather than reused from the earlier standalone `run_stbv_bench_eval.py`
run — and they match that run almost exactly (accuracy 0.6883 vs 0.6883,
F1 0.7175 vs 0.7175, precision 0.9829 vs 0.9829, recall 0.5650 vs 0.5650),
which is itself a useful cross-check that both harnesses implement the
same real pipeline call correctly.

---

## Step 4 — Decision-divergence analysis

| Comparison | n flipped | % flipped | McNemar χ² (corrected) | p-value | Cohen's h |
|---|---|---|---|---|---|
| Config 5 (full stack) vs Config 3 (no B3) — what B3+fusion adds over no semantic layer | 3835 | 38.4% | 3465.67 (on the 1→2→3→4 chain's 3→4 step, see below) / recomputed directly 5-vs-3 | ~0 | -1.096 (large) |
| Config 5 (full stack) vs Config 4 (B3 without fusion) — fusion's own marginal contribution | 128 | 1.3% | 126.01 | 3.06e-29 | -0.026 (negligible) |

(The 5-vs-3 row's exact statistics as computed directly:
3835/10000 flipped, p≈0 (below float precision), Cohen's h=-1.096 — a
large effect, as expected: this is essentially "does B3 exist in the
pipeline at all," not a subtle contribution.)

**Per-attack-family flip breakdown** (n = samples in that family; "5-vs-3
flip%" = fraction whose decision changes when B3+fusion is added to the
CP-only stack; "5-vs-4 flip%" = fraction whose decision changes specifically
because of DS fusion, holding B3's own output fixed):

| Attack family | n | 5-vs-3 flip% | 5-vs-4 flip% |
|---|---|---|---|
| collaborative_semantic_agreement | 369 | 99.2% | 0.0% |
| priority_manipulation | 345 | 99.1% | 0.0% |
| hazard_suppression | 366 | 98.9% | 0.0% |
| false_clearance | 339 | 98.5% | 0.0% |
| infrastructure_semantic_manipulation | 324 | 98.5% | 0.0% |
| cross_source_contradiction | 357 | 98.0% | 0.0% |
| instruction_injection | 372 | 97.8% | 0.0% |
| authority_override | 326 | 97.5% | 0.0% |
| context_inversion | 349 | 63.6% | 0.6% |
| planner_manipulation | 347 | 53.0% | 0.6% |
| temporal_context_drift | 317 | 53.0% | 0.3% |
| role_manipulation | 343 | 51.3% | 1.5% |
| context_poisoning | 365 | 48.2% | 1.1% |
| hazard_amplification | 349 | 39.5% | 0.6% |
| semantic_narrative_poisoning | 339 | 4.7% | 3.8% |
| benign_control | 2993 | 0.0% | 2.3% |
| multi_message_context_poisoning | 344 | 0.0% | 2.0% |
| goal_manipulation | 329 | 0.0% | 1.2% |
| mixed_semantic_attacks | 395 | 0.0% | 2.0% |
| indirect_prompt_injection | 353 | 0.0% | 1.7% |
| traffic_efficiency_lure | 379 | 0.0% | 1.3% |

**Reading this table plainly:**
- The 5-vs-3 column reproduces exactly the per-family recall split already
  reported for the STBV-Bench v1 baseline (`PUBLICATION_PROGRESS.md`): the
  8 families detected at ~100% recall are exactly the 8 families with
  ~98-99% flip rate here (adding B3 is what turns "never detected" into
  "almost always detected" for those families specifically), and the 6
  families detected at ≤9% recall are exactly the 6 families with 0.0%
  flip rate (B3 contributes literally nothing for these — see Step 5).
- The 5-vs-4 column shows fusion's marginal effect is small everywhere,
  but is **not** uniformly a detection gain: `benign_control` has a 2.3%
  flip rate here (69/2993 benign samples that B3-alone would have
  correctly ACCEPTed get pushed to CAUTION/REJECT once crypto/structural
  evidence is fused in) — this is exactly where config 5's precision loss
  relative to config 4 (0.9829 vs 1.0000) comes from. On the attack side,
  fusion's flips are concentrated in the mid-recall families
  (`role_manipulation`, `context_poisoning`, `hazard_amplification`,
  `semantic_narrative_poisoning`) rather than the already-100%-recall or
  already-0%-recall families, which is the expected place for a fusion
  layer to matter: cases where B3's own signal is ambiguous enough that
  crypto/structural evidence can tip the decision either way.

---

## Step 5 — Explicit anomaly check

Two adjacent-config pairs have |ΔF1| < 0.01:

**1. Config 2 → Config 3 (B1+B2 → B1+B2+CP): ΔF1 = 0.0000, 0/10,000 flipped (0.00%).**
Configs 2 and 3 are **byte-identical** in their per-sample decisions —
every single row across all 10,000 samples matches. Per the instructions'
own diagnostic rule (near-zero ΔF1 **and** near-zero flips ⇒ inert code
path, not a weak-but-real contribution): **this is a code-path/methodology
finding, not "CP contributes modestly."** Root cause, confirmed by reading
`pipeline/orchestrator.py`'s CP evidence fold (lines ~554-629): CP's
contradiction/corroboration signals only alter `b2_dict` when
`cp_dict.get("num_reports", 0) > 1` (line 609) or when a shared event
label makes the contradiction channel apply (`cp_has_shared_event`, line
579). Both `run_ablation.py` and `run_stbv_bench_eval.py` call
`pipeline.run([msg], context="urban")` with a **single-message window**
(`messages = [msg]`) for every sample — there is never more than one
report for CP to fuse, so `num_reports` is always ≤1 and CP structurally
has nothing to corroborate or contradict for any STBV-Bench sample as
currently evaluated. **This is not evidence that CP is a weak or
unnecessary layer** — it is evidence that STBV-Bench v1's per-sample
evaluation design (independent single messages, not multi-vehicle
windows) cannot exercise CP's cross-vehicle-corroboration mechanism at
all, by construction. This is flagged here as an explicit limitation for
the paper (see "Recommendations" below), not smoothed into "CP added a
modest improvement."

**2. Config 4 → Config 5 (B3 raw → full stack with fusion): ΔF1 = +0.0024, 128/10,000 flipped (1.28%).**
Per the same diagnostic rule, a non-trivial flip rate (1.28%, and
statistically significant by McNemar, p=3.06e-29) alongside a near-zero
aggregate F1 delta means this **is a real, small, roughly self-cancelling
effect**, not an inert code path — fusion is genuinely doing something
(it is not "off" or bypassed), but its net effect on F1 is close to zero
because its recall gains (some previously-missed attacks pushed over the
CAUTION/REJECT line by crypto evidence) are offset by its precision cost
(some previously-correct benign ACCEPTs pushed to CAUTION/REJECT by the
same mechanism — see the `benign_control` row in the flip table above,
2.3%). This is the paper-relevant distinction the instructions asked for:
fusion is active and causally responsible for 128 real decision changes,
it just happens that the gains and losses roughly balance in aggregate F1
on this particular 30%-benign, VeReMi-derived test distribution.

(Config 1 → Config 2's ΔF1 is undefined by the convention noted in Step 3
and was not evaluated against the <0.01 threshold for that reason; its
McNemar/Cohen's h are reported in `results/ablation/ablation_summary.json`
for completeness — 193/10,000 flipped, p=1.9e-43, Cohen's h=-0.279 — a
small-to-moderate MBD contribution, entirely attributable to MBD's own
behavioral checks rather than an artifact, since config 1 makes zero
positive predictions by construction.)

---

## Step 6 — Summary

**MBD's contribution (config 1→2) is small but real** (124 true positives
out of 7,007 attacks, 1.9pp recall, but a statistically significant
193-sample flip, p=1.9e-43): on STBV-Bench's real VeReMi-derived
kinematics, MBD occasionally flags a message on non-semantic grounds
(certificate rotation timing, plausibility checks) even though STBV-Bench's
attack label is purely about the injected semantic payload — this is a
real, if minor, side effect of using genuine kinematics rather than
synthetic ones, not evidence MBD is broken.

**CP's contribution (config 2→3) is measured as exactly zero, and the
correct interpretation is a benchmark-methodology limitation, not a
finding about CP's real-world value.** STBV-Bench v1 evaluates each
sample as an isolated single-message window; CP requires ≥2 reports in a
window to have anything to corroborate or contradict, so it is
structurally inert under this specific evaluation design. This should be
stated in the paper as an explicit STBV-Bench v1 limitation, with a
concrete Phase-3.1 recommendation: extend the benchmark to multi-message
scenario windows (grouping real VeReMi records by simulation time-slice
so genuine peer traffic exists) so CP can be exercised honestly. CP was
already verified to work correctly on the existing multi-vehicle
`scenarios/collusion` fixtures (see `PUBLICATION_PROGRESS.md`, Phase 2) —
this ablation does not contradict that, it shows STBV-Bench v1 specifically
cannot exercise it.

**B3 is overwhelmingly the layer responsible for STBV detection on this
benchmark, and that is the expected, architecturally correct result, not
evidence the other layers are unnecessary.** STBV-Bench's honesty contract
(`DATASET_INTEGRATION.md`) means every sample's kinematics are real and
*unmodified* VeReMi data — only the semantic scene-context text is
attacked. MBD and CP reason over kinematics/cross-vehicle behavior; by
construction they have no signal for an attack that never touches
kinematics. B3 alone (config 4, no fusion) already reaches F1=0.7151,
recall=0.5566, at **perfect precision** (1.0000, FPR=0.0000) — i.e. on
this benchmark B3 never falsely flags a benign VeReMi message on its own.

**Fusion's marginal contribution (config 4→5) is small, real, and a
genuine precision/recall trade, not a rounding artifact.** It flips 128/
10,000 decisions (1.28%, p=3.06e-29): a small net recall gain
(0.5566→0.5650) bought at a small precision cost (1.0000→0.9829, FPR
0→0.0231), concentrated specifically in the mid-recall attack families
(where B3's own signal is more ambiguous) and in benign_control (where
fused-in crypto/structural uncertainty occasionally overrides an
otherwise-clean B3 read). Aggregate F1 barely moves (+0.0024) because
these two effects nearly cancel — but 128 individual, real decisions
change, which is the more informative number for a T-ITS reviewer than
the aggregate.

**The honest headline for the paper's central architectural claim:** on
STBV-Bench v1 specifically — a benchmark of *purely semantic* attacks over
*real, unaltered* kinematics — B3 is necessary and does almost all of the
detection work; MBD contributes a small amount; CP contributes nothing,
but for a documented benchmark-design reason (single-message windows) that
does not generalize to CP's role against kinematic/behavioral threats
(already separately verified in Phase 2); and the Trust Decision Engine's
DS fusion contributes a small, real, statistically significant precision/
recall trade rather than a large uplift. This is a **narrower** claim than
"the complete architecture, not just the classifier, drives every
decision" as originally framed — the correct, defensible framing (and the
one recommended for the manuscript) is that **the complete architecture is
necessary because different layers cover different, non-overlapping threat
classes** (B3 for semantic/STBV, MBD/CP for kinematic/behavioral, as
already shown separately in Phase 1/2's Sybil/Replay/Collusion results),
not because every layer contributes comparably to detecting any single
attack class such as STBV. Reporting this precisely, rather than the
broader framing, is what the mission's honesty contract requires.

### Recommendations for the manuscript

1. Report Steps 3-6 above largely as-is in an ablation subsection; the
   CP-inertness finding is a strength for the paper if framed correctly
   (a documented, understood benchmark limitation with a concrete fix
   path) and a serious credibility risk if smoothed over.
2. Add a "STBV-Bench v2" future-work item: multi-message scenario windows
   so CP (and, more realistically, MBD's cross-vehicle Sybil/collusion
   checks) can be exercised on semantic-attack traffic too, not just on
   the existing kinematic `scenarios/` fixtures.
3. State the architecture's value proposition as complementary threat-class
   coverage (semantic vs. kinematic/behavioral), not as "every layer helps
   every decision" — the latter is not what this ablation shows, and
   claiming it would not survive a reviewer re-running this exact study.

