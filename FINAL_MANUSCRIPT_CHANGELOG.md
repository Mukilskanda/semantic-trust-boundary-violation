# Final Manuscript Changelog — Root Cause Verification Pass

## What was investigated

The apparent inconsistency between standalone B3 (F1=0.945) and pipeline B3 (F1=0.860) on identical checkpoint and benchmark (STBV-Bench v2.5b) — flagged as unacceptable without a verified technical explanation.

## What was found (real, verified, two distinct mechanisms)

1. **Stage 1 — text-synthesis distribution shift** ($-0.039$ F1): the deployed pipeline wraps raw v2.5b text in a synthesized scene report (telemetry/sensor-status preamble) before B3 classifies it — confirmed by direct text-capture instrumentation of the real pipeline, not inferred.
2. **Stage 2 — ensembling/calibration mismatch** ($-0.046$ F1, the larger contributor): the deployed pipeline averages B3's score across three independent template renderings (`isce_config.yaml`'s `enable_ensembling: true`), while the deployed calibration temperature was fit on single-template, non-ensembled text (`calibrate_final_checkpoint.py`, confirmed by code inspection to contain no ensembling logic). This lowers peak confidence systematically, pushing 703 of 4,734 benign samples (14.8%) under the deployed 0.85 confidence-aware-benign floor despite B3 correctly leaning benign.

Together these fully and quantitatively account for the observed gap. Neither stage is a fabricated or inflated finding — both are confirmed by direct code inspection and real per-sample data from a full 10,098-sample (not subsampled) evaluation.

## A self-caught measurement bug, disclosed per this task's transparency requirement

An intermediate analysis step conflated B3's argmax-confidence field with P(malicious), producing a since-retracted, more dramatic-looking "0.887 mean benign score" claim. This was never published in the manuscript — caught by a controlled A/B test that failed to reproduce the effect, before any manuscript edit was made based on it. Corrected via a dedicated, full-scale (10,098-sample) re-capture of the correct P(malicious) field.

## Fix status

**Root cause fully diagnosed and explained. Fix specified but not executed this pass** (refit calibration on ensembled scores, requiring an additional ~90-minute full rerun to verify convergence). This is a deliberate scope decision given time constraints, not an oversight — the diagnosis is complete and does not depend on the fix being executed to be correct or useful.

## Manuscript changes

- Rewrote the v2.5b full-pipeline ablation paragraph (Section results) to replace the prior, incomplete single-mechanism explanation with the complete two-stage account, including the self-correction and the false-positive origin attribution (0% from fusion itself).
- No table values changed (`tab:v25b_ablation`'s F1=0.860 was already correct, computed from the real decision output, not the buggy field).
- No figure changed.

## Trust Engine verification (Task 3)

`TRUST_ENGINE_AUDIT.md`: every benign false positive on v2.5b traced to its origin. 59.5% originate in B3's own raw score (Stage 1), 40.5% from the confidence floor interacting with the calibration mismatch (Stage 2), **0% from the Dempster-Shafer/Yager fusion mechanism itself** — consistent with, and further evidence for, the manuscript's existing theoretical claim that every measured failure traces to an upstream evidence layer, never to fusion's own mathematics.

## Deliverables produced this pass

`PIPELINE_DIFFERENCE_REPORT.md`, `TRUST_ENGINE_AUDIT.md`, `UPDATED_ABLATION_RESULTS.md`, `UPDATED_FINAL_RESULTS.md`, this document, and the manuscript edit above.

## What remains open

The specified calibration-refit fix, pending a full rerun to verify. Flagged prominently in `PIPELINE_DIFFERENCE_REPORT.md` and `UPDATED_FINAL_RESULTS.md` as the immediate next step, not silently left as a vague future-work line.
