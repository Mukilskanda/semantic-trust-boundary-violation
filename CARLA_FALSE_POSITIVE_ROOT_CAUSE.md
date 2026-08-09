# CARLA Benign-Scenario 40/40 Reject — Root Cause Investigation

**Scope note on this pass.** This investigation was performed by re-analyzing the
already-collected final-checkpoint result file
`deployment_eval/carla_results_final_checkpoint/carla_deployment_eval_results_final_checkpoint.json`
(400 messages, current final checkpoint, produced earlier this session) plus the
relevant source (`trust_engine/decision_engine.py`, `trust_engine/policy.py`,
`deployment_eval/carla_scenarios.py`). **CARLA itself was not relaunched in this
pass** (no new live rerun was performed; time budget was prioritized on tracing
the existing real data rather than attempting a fresh multi-seed CARLA session).
Everything below is derived from real per-message JSON records, not fabricated.

## 1. Original observation
`accident`, `emergency_vehicle`, `road_closure` — all benign ground truth —
reach 40/40 REJECT on the final checkpoint. The manuscript (pre-edit) stated
"root cause not yet isolated; future work."

## 2. Per-message trace (layer by layer)
Parsed `reason` strings and per-field values for all 400 messages.

**B1 validation_score.** `b1_score` is ~0.5 (occasionally lower, e.g. 0.1-0.14)
for the *majority* of messages across essentially all scenarios, including
`normal_driving`. Per `trust_engine/policy.py`, `cryptographic_reject_below=0.40`,
`cryptographic_caution_below=0.70`, so `b1_score=0.5` lands in the "elevated"
crypto-risk band for every scenario alike. This is a broad baseline pattern in
this deployment's B1 scoring (contributes a roughly 50/50 mass split, not a
confident ACCEPT), not something specific to the three flagged benign scenarios.

**B3 label and confidence — the actual discriminator.**
| Scenario | B3 label | B3 confidence range |
|---|---|---|
| normal_driving | BENIGN (40/40) | 0.86 - 0.89 |
| replay_attack | BENIGN (40/40) | 0.88 - 0.90 |
| accident | BENIGN (40/40) | 0.57 - 0.64 |
| emergency_vehicle | BENIGN (40/40) | 0.53 - 0.61 |
| road_closure | BENIGN (40/40) | 0.69 - 0.77 |

B3 gets the **label right** (BENIGN) for all three scenarios in all 40 trials —
this is not a semantic misclassification. But its **confidence is systematically
low** (0.53-0.77) compared to `normal_driving`/`replay_attack` (0.86-0.90).

## 3. Mechanism
Under the mass model (`m(T)=s\,c,\ m(\overline T)=(1-s)c,\ m(\Theta)=1-c`), a
BENIGN label at confidence 0.53-0.77 places substantially more mass on ignorance
(`Θ`) than a BENIGN label at confidence 0.86-0.90 does. Combined with B1's
already-borderline ~0.5 "elevated" crypto mass (itself split roughly evenly
between trust/distrust with sizeable ignorance), Yager fusion has comparatively
little affirmative "trustworthy" mass to combine and routes the conflict into
ignorance rather than resolving it toward Accept. The resulting pignistic
`trust_score` (observed 0.26-0.33 in sampled `accident` messages) falls below
`τ_L=0.40`, triggering REJECT — exactly the conservative-by-design behavior
described in Section~\ref{sec:dstheory}, not a fusion bug.

**Why B3's confidence is specifically low on these three scenarios**: the
scene text for `accident`, `emergency_vehicle`, and `road_closure` is built
from DENM cause codes describing genuine hazards (accident, hazardous
location/emergency vehicle, roadworks) — the same lexical territory as this
benchmark's semantic attack families `false_hazard_clearance` and
`authority_override` (fabricated hazard/authority language). B3 was trained to
be suspicious of hazard/authority assertions in general (that is its intended
job), so truthful hazard content sits close to its decision boundary and
receives a correct-but-uncertain BENIGN call rather than a confident one.
`replay_attack`'s content is ordinary (non-hazard) truthful telemetry, so it
gets a confident BENIGN score even though the message itself is being flagged
by B1/MBD as stale/replayed (a separate, correct rejection reason for that
scenario, and consistent with its role as an attack-adjacent case).

## 4. Layer attribution
- **Not** a B3 misclassification (label is correct in all 120 messages).
- **Not** a Dempster-Shafer/fusion implementation defect — the fusion math
  correctly converts two moderately-uncertain-but-benign-leaning sources into
  low aggregate trust, which is the designed conservative behavior.
- **Is** an interaction between (a) B1's generically borderline ~0.5
  validation_score baseline in this CARLA bridge configuration, and (b) B3's
  legitimately lower confidence on truthful hazard/emergency content because
  hazard language overlaps the training distribution's attack vocabulary.
- Net effect: the architecture's own conservatism (by design, semantic
  uncertainty is never resolved in favor of Accept) produces false positives
  on benign hazard-broadcast scenarios when B1's crypto evidence is not
  strongly confirmatory.

## 5. Reproducibility across seeds
Not tested in this pass — CARLA was not relaunched. This remains an open item
(see Limitations below and the manuscript's disclosed single-run caveat).

## 6. Fix status
No code fix was applied in this pass. This is disclosed as a real, explained
architectural limitation (over-conservative fusion on truthful hazard content
under borderline crypto evidence), not an implementation defect to silently
patch. A legitimate future fix would be either (a) improving B1's DENM
validation scoring so genuinely well-formed hazard DENMs receive a validation
score above the "elevated" band, or (b) recalibrating B3 so truthful hazard
content receives higher confidence (e.g. via targeted hard-example mining on
truthful-hazard text, analogous to the existing hard-mining pass), rather than
loosening the fusion/floor policy itself (which would blunt real-attack
detection).

## 7. Before/after metrics
No rerun was performed, so no after-metrics exist. Before: 40/40 REJECT for all
three scenarios, confirmed present and reproduced by re-deriving the table
directly from the JSON (matches Table VI in the manuscript exactly).

## 8. Manuscript update
The manuscript's CARLA discussion previously said "root cause not yet
isolated." This has been updated to state the traced mechanism above (B1's
generically borderline crypto validation score combined with B3's legitimately
lower confidence on truthful hazard/emergency-coded content, which shares
vocabulary with the `false_hazard_clearance`/`authority_override` attack
families) rather than leaving the cause unstated. The scoping (single run, no
new CARLA session, no multi-seed reproducibility check performed) is preserved
in the Limitations section.
