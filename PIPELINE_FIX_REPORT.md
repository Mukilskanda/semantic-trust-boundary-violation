# Pipeline Fix Report

This report consolidates the pipeline-consistency investigation requested this pass. It intentionally does not duplicate content already written in full elsewhere — it summarizes and points to the source-of-truth documents.

## What was fixed, verified, and what was not

**Root cause of the standalone-vs-pipeline F1 gap (0.945 → 0.860) — fully diagnosed, not fixed:**
Two independent, fully-quantified mechanisms, with zero unexplained residual. Full trace, numbers, and the self-caught `confidence`-vs-`p_malicious` measurement bug: `PIPELINE_DIFFERENCE_REPORT.md`.
- Stage 1, text-synthesis distribution shift: −0.039 F1. B3 receives a synthesized scene report, not raw text. This is architectural (the synthesizer's job), not a bug — no fix attempted or warranted; it is disclosed as expected pipeline behavior.
- Stage 2, calibration/ensembling mismatch: −0.046 F1. Deployed temperature was fit on single-template scoring while production ensembles three templates.

**The calibration-methodology mismatch (Stage 2) was fixed, built, and verified this pass — not left as a proposal.** Full detail: `CALIBRATION_FIX_REPORT.md`. Summary: refitting temperature on the properly-ensembled path ($T{=}4.44$) genuinely improves ECE ($0.098\to0.070$) but, verified end-to-end on all 10,098 v2.5b samples, makes real decision metrics worse (F1 $0.860\to0.817$) due to an interaction with the fixed 0.85 confidence-aware-benign floor. **Reverted, not deployed** — the deployed system remains at $T{=}2.82$, and every previously-published metric is unchanged.

## Text synthesizer: investigated, not changed

The instruction also asked to investigate (not necessarily implement) whether the text synthesizer could be improved by removing redundant telemetry/formatting without changing benchmark or message semantics. Investigated: the synthesizer's preamble (station/context/sensor-status boilerplate before the actual peer-report text) is exactly what Stage 1 above measures as a real, disclosed −0.039 F1 cost. Trimming it would very likely narrow that gap — but doing so now, in direct response to having just measured its cost, would be indistinguishable from tuning implementation details to chase a metric on the exact benchmark used to evaluate it, which this project's standing rule prohibits. It is also a change to what the deployed pipeline actually does at inference time (not merely to how it's scored), so it isn't a scoring-methodology fix like the calibration refit was — it would change real production behavior. **Not attempted this pass**; noted here as a legitimate, disclosed candidate for future architectural work, not silently skipped.

## Consistency verification

Standalone → pipeline → Trust Decision Engine → final decision: internally consistent, in the sense that every stage's contribution to the score/decision is now traced to a specific, evidenced mechanism (synthesis, ensembling, calibration, the 0.85 floor, Dempster-Shafer/Yager fusion) with no remaining unexplained gap. `TRUST_ENGINE_AUDIT.md` traces every v2.5b false positive to its origin: 59.5% Stage-1 (B3 misclassification), 40.5% Stage-2 (floor interaction), 0% from fusion itself.

**Remaining, disclosed, open items** (not silently dropped, not fixed by assumption):
- Stage 2's mismatch is diagnosed and a fix was tested, but not adoptable without also redesigning the 0.85 floor jointly — scoped as legitimate future work in `CALIBRATION_FIX_REPORT.md`.
- The synthesizer's Stage-1 cost is diagnosed but not remediated, per the reasoning above.

## Deliverables produced this pass

- `CALIBRATION_FIX_REPORT.md` — the calibration fix, verification, and revert, in full.
- `PIPELINE_DIFFERENCE_REPORT.md` — updated to remove stale "not attempted" language.
- `FINAL_CONSISTENCY_AUDIT.md` — updated with a calibration-consistency section confirming $T{=}2.82$ everywhere.
- `stbv_paper.tex` — v2.5b paragraph (Section~\ref{sec:v25b}) updated to describe the tested-and-reverted finding instead of a stale "not yet attempted" placeholder. No numeric table values changed.
