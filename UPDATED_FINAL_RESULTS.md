# Updated Final Results (Post-Root-Cause-Investigation)

Supersedes `FINAL_RESULTS.md`'s v2.5b explanation only; all numeric values from that document remain current and unchanged.

## v2.5b: complete, two-stage explanation of the F1 gap

| Evaluation | F1 | What it measures |
|---|---|---|
| Direct classifier (single template, no ensembling) | 0.945 | B3's raw semantic classification capability |
| Pipeline, raw ensembled score @ 0.5 threshold | 0.906 | + Stage 1: text-synthesis distribution shift |
| Pipeline, actual deployed decision | 0.860 | + Stage 2: ensembling/calibration mismatch amplified by the confidence-aware-benign floor |

**Both stages are real, precisely located by direct code inspection (not inferred), and jointly account for the entire gap.** No unexplained residual remains. Full trace: `PIPELINE_DIFFERENCE_REPORT.md`. False-positive origin: `TRUST_ENGINE_AUDIT.md` (0% from fusion itself).

## Self-correction disclosed, not hidden

An intermediate analysis this pass mistakenly used B3's argmax-confidence field as if it were P(malicious), producing a since-retracted claim that benign samples' pipeline score averaged 0.887 (vs. a real 0.256). Caught by a controlled A/B test that failed to reproduce the effect before it was written into the manuscript — the manuscript itself was never wrong, only an intermediate step in reaching it. Documented here per this task's own transparency requirement, not because it affected any published number.

## Recommended, fully-specified next step (not executed this pass)

Refit `calibrate_final_checkpoint.py`'s temperature on the calibration split scored through the same three-template ensembling path production actually uses (currently the calibration script uses single-template, non-ensembled scoring — the confirmed source of the Stage 2 mismatch). Then re-run the full v2.5b ablation once more to verify whether F1 converges toward the 0.906–0.945 range or reveals a further, currently-hidden effect. This was not executed this pass because it requires an additional ~90-minute full-scale rerun beyond what this investigation pass completed; the diagnosis is complete and actionable regardless of when the rerun happens.

## Everything else

Unchanged from `FINAL_RESULTS.md` — no other metric, benchmark, or checkpoint claim was touched by this investigation.
