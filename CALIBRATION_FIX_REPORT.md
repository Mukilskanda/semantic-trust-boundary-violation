# Calibration Fix Report

## Task

`PIPELINE_DIFFERENCE_REPORT.md` identified a genuine calibration-methodology mismatch: production inference averages B3's prediction across three template renderings (`enable_ensembling: true`), while the deployed temperature ($T{=}2.82$) was fit on single-template, non-ensembled scoring. This report documents fixing that mismatch, verifying the result, and — critically — **not assuming the fix helps**.

## The fix, built and verified

`b3_eval/v25_finetune/calibrate_final_checkpoint_ensembled.py`: refits temperature on the calibration split (n=85) scored through the *same* three-template ensembling path production actually uses (DEFAULT + NARRATIVE + STRUCTURED, real synthesizer output, averaged probability), rather than single-template scoring. Result: $T{=}4.44$ (vs. the old $2.82$), **ECE genuinely improves** on the ensembled scoring path: $0.098 \to 0.070$.

**On this narrow measure — calibration quality — the fix works exactly as intended.**

## Verification: full v2.5b re-evaluation, both temperatures

10,098-sample full-pipeline rerun with $T{=}4.44$ deployed, compared against the existing $T{=}2.82$ results:

| Metric | Old ($T{=}2.82$) | New ($T{=}4.44$) | Change |
|---|---|---|---|
| Accuracy | 0.828 | 0.761 | **worse** |
| Precision | 0.756 | 0.690 | **worse** |
| Recall | 0.999 | 1.000 | marginal (ceiling effect) |
| F1 | 0.860 | 0.817 | **worse** |
| FPR | 0.366 | 0.509 | **substantially worse** |
| ECE (ensembled scoring) | 0.098 | 0.070 | **better** |

**Verified, not assumed: the recalibration makes deployed decision quality worse while making the underlying probability estimates more honest.**

## Why this happens (the real, disclosed mechanism)

A higher, better-fit temperature flattens the probability distribution toward 0.5 — correct behavior for a model whose raw ensembled scores were overconfident, and exactly what a lower ECE reflects. But the deployed decision policy applies a **fixed** confidence floor (BENIGN accepted as safe only if confidence $\geq 0.85$, "confidence-aware-benign", Section IV of the manuscript). Flattening confidence pushes *more* correctly-benign predictions under this fixed floor, escalating them to Caution/Reject. The floor threshold was never explicitly tuned against either temperature — but the *old*, overconfident temperature happened to produce peakier confidence distributions that, empirically, cleared the fixed 0.85 floor more often for correct BENIGN calls. Fixing the temperature in isolation, without also revisiting the floor, moves the system to a worse operating point on the metrics that matter for deployment (F1, FPR), even though it improves the metric (ECE) that motivated the fix.

## Decision: reverted, not deployed

**The deployed configuration (`isce_config.yaml`) has been reverted to $T{=}2.82$.** This is a deliberate choice, explained in the config file itself, not a silent rollback:
- Deploying $T{=}4.44$ would satisfy the narrow "fix the calibration mismatch" instruction while making the system objectively worse at its actual job (correctly deciding Accept/Caution/Reject) — the exact outcome Task 3's own instruction ("verify improvement... if no improvement occurs, explain why") anticipates and requires disclosing.
- Jointly retuning the 0.85 confidence floor *together* with the new temperature might recover or exceed the old operating point, but doing so now, narrowly, in response to seeing the metric drop, would itself be indistinguishable from "tuning a threshold to chase a number" — the standing prohibition in every pass of this session's instructions. Not attempted for this reason.
- The $T{=}4.44$ ensembled-fit results are preserved, not deleted, at `b3_eval/v25_finetune/ablation_results/v25b_full_T4.44_REJECTED/`, for reproducibility and audit.

## What remains open

The Stage 2 mechanism identified in `PIPELINE_DIFFERENCE_REPORT.md` (calibration/ensembling mismatch contributing $-0.046$ F1 to the standalone-vs-pipeline gap) is **confirmed real** but **not resolved** by this pass's fix attempt — fixing it in isolation makes a different metric worse. A legitimate resolution would require jointly redesigning the temperature *and* the confidence-aware-benign floor together (e.g., refitting the floor threshold on the ensembled-and-recalibrated score distribution specifically, as a single coupled optimization, not two independent point-fixes) — scoped as concrete future work, not attempted here given the risk of it becoming exactly the prohibited threshold-chasing.

## No manuscript numbers changed as a result of this fix attempt

Because the fix was reverted, every previously-reported v2.5b metric (F1=0.860, etc.) remains the deployed system's actual, current behavior and is unchanged. What is new is the manuscript now discloses this recalibration attempt and its negative result directly, since a reviewer asking "did you try fixing the calibration mismatch you found?" deserves the honest answer: yes, verified, and reverted with a specific, evidenced reason — not silence.
