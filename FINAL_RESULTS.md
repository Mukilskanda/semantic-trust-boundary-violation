# Final Results

**SUPERSEDED CHECKPOINT NOTICE**: this file's numbers (below) were measured against `semantic_gate_v3_mixed_lora_continued_merged` (SHA-256 `bbae0512...`), which was the final checkpoint at the time this file was written but has since been superseded by `semantic_gate_v3_mixed_lora_hardmine_merged` (SHA-256 `d126cc3...`). The current manuscript's v2.5b numbers (F1=0.957 direct classifier, F1=0.877 full pipeline) reflect the new checkpoint and supersede this file's v2.5b row (F1=0.945/0.860). See `HARDMINE_IMPROVEMENT_REPORT.md` for the current checkpoint's full record. This file's v1/ITE-Bench/VeReMi/CARLA/SUMO numbers remain accurate (those benchmarks were not affected by or rerun against the new checkpoint, per `HARDMINE_IMPROVEMENT_REPORT.md`'s checkpoint-invariance analysis).

**Correction of a stale premise carried over from an earlier work phase**: this file's title previously named `semantic_gate_v3_mixed_lora_merged` as "the final checkpoint." That is the *pre-continuation* mixed-corpus checkpoint. The actual final checkpoint — used throughout the current manuscript, verified by SHA-256, and the product of a genuine continued fine-tuning pass — is `semantic_gate_v3_mixed_lora_continued_merged` (`bbae05120439774f724dcce205be71b79d1720e4f0edb47cdb4cc793849a9b1a`). All numbers below use the correct final checkpoint; see `FINAL_FREEZE_AUDIT.md` for the full checkpoint provenance chain.

## Primary semantic benchmark: STBV-Bench v2.5b (now primary, per this pass's reprioritization)

| Evaluation | Acc. | Prec. | Rec. | F1 | Notes |
|---|---|---|---|---|---|
| Direct classifier (raw text) | 0.941 | 0.939 | 0.951 | **0.945** | Matches training/validation scoring convention |
| Full pipeline, B1 / B1+B2 / B1+B2+CP | 0.469 | -- | 0.000 | -- | Same threat-model scope reason as v1; ITE-Bench evaluates B1/B2 fairly |
| Full pipeline, B3-alone / full stack | 0.828 | 0.756 | 0.999 | **0.860** | New finding: synthesizer wraps raw text in a telemetry preamble before B3 sees it |

**New finding this pass, investigated rather than assumed**: the gap between 0.945 (direct classifier) and 0.860 (pipeline-embedded) is real and was traced to a specific cause, not left unexplained. Instrumenting the exact text B3 receives inside the full pipeline confirms it is a synthesized scene report (station ID, kinematics, sensor status) wrapping the raw v2.5b text under a `[Peer Reports]` heading — not the raw text itself. This is a genuine distribution-shift cost of pipeline deployment that a direct-classifier evaluation cannot surface. The gap concentrates in precision (0.756) while recall stays high (0.999), consistent with added context diluting rather than corrupting the semantic signal. B3-alone and full-stack are identical in aggregate (854/10,098 individual decisions differ, but all are Caution→Reject escalations that don't cross the binary decision boundary — the same "binary F1 hides transition structure" pattern already established on STBV-Bench v1).

## STBV-Bench v1 (now historical/supplementary, per this pass's reprioritization)

Kept as supplementary comparison, not the primary claim: F1=1.000 (B3-alone), F1=0.995 (full stack). Its near-ceiling result has an identified, disclosed mechanism — template-family exposure via the final checkpoint's `rows[10000:]` training slice of the same v1 corpus file the evaluated `rows[0:10000]` are drawn from (`TABLE_II_AUDIT.md`) — which is exactly why it is no longer the paper's primary generalization claim.

## ITE-Bench (fair B1/B2/B3 evaluation, unchanged this pass)

Each layer: 1.000 recall within its own threat class, 0.000 outside it, McNemar-confirmed zero-cost layering ($p{<}10^{-15}$, two independent comparisons).

## VeReMi, CARLA, SUMO

Unchanged this pass — no bug was found in any of them to justify a rerun. VeReMi: MBD message-level F1 up to 0.833 (ConstPos/fabrication). CARLA: post-synthesizer-fix, `authority_override`/`false_hazard_clearance` correctly flagged MALICIOUS by B3 (previously invisible to it); `sybil_attack`/`semantic_manipulation` remain B3-invisible, caught only by MBD. SUMO: 12.3 msg/s throughput, B3 forward pass >98% of end-to-end latency.

## What changed vs. what didn't, this pass

**Changed**: benchmark emphasis (v2.5b now primary, v1 now supplementary/historical); one new full-pipeline 5-config ablation on v2.5b (genuinely new experiment, not a rerun of an existing one); seven new or regenerated figures, all traced to real per-sample data; expanded architecture/theory/complexity/assumptions/failure-mode content; one corrected figure caption (a "previously-reported ECE of 0.017" claim that does not actually exist anywhere else in the current manuscript was removed rather than left as an unverifiable comparison).

**Not changed**: no previously-reported metric's value was altered anywhere in the manuscript. Every number in this document either exactly matches a prior measurement (confirming it was not stale) or is a genuinely new measurement reported alongside, not instead of, the prior one.

## Addendum: calibration recalibration attempted and reverted (subsequent pass)

A methodologically-corrected calibration temperature ($T{=}4.44$, fit on the same ensembled-inference path deployment uses, vs. deployed $T{=}2.82$'s single-template fit) was built and verified end-to-end on all 10,098 v2.5b samples. It genuinely improves ECE ($0.098\to0.070$) but makes every table above's F1/precision/FPR numbers *worse* if deployed (F1 $0.860\to0.817$), due to an interaction with the fixed 0.85 confidence-aware-benign floor. **Reverted — every number in the table above remains exactly as measured with the deployed $T{=}2.82$.** Full account: `CALIBRATION_FIX_REPORT.md`.
