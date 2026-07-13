# CHANGELOG

## CP evidence semantics: corroboration deficit → Θ mass, contradiction → ¬A mass

**Files changed:** `pipeline/orchestrator.py` (CP fold block only),
`tests/test_cp_uncertainty_semantics.py` (new).
**Not changed:** B1/B2/B3 scoring logic, all thresholds and weights, all
public interfaces (`ISCEPipeline.run`, `TrustDecisionEngine.decide`,
`cp_layer`, `TrustEvidence`), CP's own computation.

### What was wrong

The orchestrator folded CP into the decision inputs as
`validation_score := min(validation_score, cp_confidence)`. In the
downstream Dempster–Shafer construction
(`MassFunction.from_score_confidence`: `m_A = score·conf`,
`m_¬A = (1−score)·conf`, `m_Θ = 1−conf`), a lowered *score* commits mass to
**¬A (disbelief)**. But `cp_confidence` is low in two epistemically distinct
situations that the fold conflated:

1. **Contradiction** — reports about the same claimed event actively
   disagree (genuine negative evidence);
2. **Corroboration deficit** — few/low-diversity independent reports, or
   plain CAM traffic that is merely spatially spread out
   (`cp_layer.spatial_consistency` scores 0 for any honest spread beyond
   ~20 m std, and the pipeline always calls CP with `event_label=None`).

Routing (2) into disbelief violates the foundational D-S distinction between
*disbelief* and *ignorance*: absence of evidence for A is mass on Θ, not on
¬A (Shafer, *A Mathematical Theory of Evidence*, Princeton, 1976, ch. 1–2).
Measured consequence (evaluation framework, self-generated scenarios):
**FPR 0.37 on benign dense traffic and 0.93 on replay scenarios** — mass
rejection of honest, merely-uncorroborated messages.

### The fix

CP's already-computed component scores are routed to the two correct mass
axes, reusing CP's **existing** weights (0.35/0.25/0.20/0.20) and its
**existing** 0.7 pass threshold — no retuning:

- **Contradiction channel** (→ `validation_score`, i.e. the score axis →
  ¬A mass): `agreement = (0.35·spatial + 0.25·speed + 0.20·heading)/0.80`,
  applied **only when `event_label` is not None** — i.e. only when the fused
  reports actually claim to observe the same event, which is the only case
  in which their inconsistency constitutes contradiction under `cp_layer`'s
  own consistency semantics.
- **Corroboration channel** (→ `confidence_calibration`, i.e. the
  confidence axis → Θ mass, since `m_Θ = 1 − confidence`):
  `corroboration = diversity_score`, applied when `num_reports > 1`
  (a single-report window carries no corroboration signal either way).

Yager's rule (Yager, "On the Dempster–Shafer framework and new combination
rules," *Information Sciences* 41(2), 1987), already used by
`trust_engine/dempster_shafer.py`, propagates Θ mass through combination
rather than normalizing it away, so routed uncertainty survives fusion and
lands the decision in CAUTION via the pignistic transform
(Smets & Kennes, *Artificial Intelligence* 66, 1994:
`trust = m_A + ½·m_Θ`) instead of forcing REJECT.

### Measured behavioral change

| Measurement | Before | After |
|---|---|---|
| FPR, benign dense generated traffic (full stack) | 0.37 | **0.00** |
| FPR, replay generated scenarios (full stack) | 0.93 | **0.00** |
| Recall, replay generated scenarios | 0.857 (artifact: mostly CP-sparsity REJECTs coinciding with attackers; precision was 0.13) | 0.00 REJECT-recall; attackers land CAUTION (caution_rate 1.0). B1's genuine replay detection on the fixture suite is unchanged: `validation/run_ablation_table.py` still reports replay acc/F1 = 1.000/1.000. |
| Fixture-based suites (`tests/`, `test_system.py`, `manual_pipeline_test.py --regression`, `validation/run_*`) | pass | pass, unchanged |

The replay-recall drop on *generated* scenarios is a legitimate consequence
of removing the artifact, not a lost capability: the prior REJECTs were
issued at 0.93 FPR (i.e., the detector was rejecting nearly everything, so
it "caught" attackers the way a stopped clock is right twice a day). Honest
current picture: on generated multi-vehicle scenarios with fresh senders the
stack is uniformly conservative (CAUTION), and decisive REJECTs come from
genuine evidence — B1 fatals, shared-event contradiction, or (pending GPU
runs) B3 semantic verdicts.

### New tests (`tests/test_cp_uncertainty_semantics.py`)

1. Pure corroboration deficit (agreeing but sparse/low-diversity reports):
   Θ mass rises (`m_Θ > 0.5`), no disbelief manufactured (`m_¬A ≈ 0`),
   decision CAUTION — never REJECT, `attack_detected=False`.
2. Genuine shared-event contradiction (`event_label` set, low
   spatial/speed/heading agreement, high diversity): disbelief dominates,
   decision REJECT, `attack_detected=True`.
3. Spread-out plain CAM traffic (`event_label=None`, `spatial_score=0`):
   CP adds exactly zero disbelief relative to the CP-disabled baseline.
4. Single-report window: decision identical to CP-disabled pipeline.
5. Monotonicity: Θ mass decreases as corroboration increases.
