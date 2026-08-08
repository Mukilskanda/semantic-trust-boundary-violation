# Final Consistency Audit

Programmatic and manual verification that every figure, table, equation, metric, checkpoint reference, benchmark, citation, reference, appendix, and discussion point in the current manuscript is internally consistent and uses the correct final checkpoint.

## Checkpoint identity

- **Verified**: every metric attributed to "the final checkpoint" in the manuscript was produced by `semantic_gate_v3_mixed_lora_continued_merged` (SHA-256 `bbae05120439774f724dcce205be71b79d1720e4f0edb47cdb4cc793849a9b1a`), confirmed by direct pipeline load and by the config override scripts (`run_v25b_full_ablation.py`, `rerun_ablation_configs45_final.py`) explicitly pointing `model_path` at this directory.
- **Corrected**: this session's request named `semantic_gate_v3_mixed_lora_merged` (the pre-continuation checkpoint) as final. Not adopted — see `FINAL_RESULTS.md`'s correction note. `semantic_gate_v3_mixed_lora_merged` appears in the manuscript only as the explicitly-labeled "pre-continuation" comparison point in Table `tab:v25b`, never presented as current.

## Figures — cross-reference and provenance check

Programmatic check (script, not eyeballed): **zero** `\ref`/`\eqref` targets without a matching `\label`; **zero** duplicate labels. Two section labels (`sec:related`, `sec:conclusion`) remain self-unreferenced — unchanged from before this pass, not a regression, and not required in IEEE style (sections don't self-cite).

Per-figure provenance: see `FINAL_FIGURES_REPORT.md` for the full breakdown of which figures are native TikZ (verified against real code execution order or real computed trust scores) vs. regenerated PDF (verified against real per-sample CSVs, with one real bug caught and fixed — the ROC/PR score-field error — before publication, not after).

## Tables

9 tables. Every table's caption states its exact $n$ and checkpoint. Cross-checked:
- `tab:main_ablation` (STBV v1) — re-verified against final checkpoint in a prior pass (F1 1.000/0.995), unchanged this pass.
- `tab:ite_ablation` (ITE-Bench) — unchanged this pass, still current.
- `tab:v25b` (v2.5b, direct classifier) — unchanged this pass, still current (F1 0.945).
- `tab:v25b_ablation` (v2.5b, full pipeline) — **new this pass**, verified against a fresh 10,098-sample × 5-config run, cross-checked internally (854 discordant decisions between B3-alone and full-stack, all one direction, confirmed by direct CSV diff before writing the manuscript claim).
- `tab:veremi`, `tab:carla`, `tab:adaptive` — unchanged this pass; `tab:adaptive` remains explicitly labeled as describing the *prior* checkpoint, not the final one, in both its caption and the surrounding text — the one deliberate, disclosed exception to "every metric uses the final checkpoint."
- `tab:trustboundary`, `tab:notation` — new, non-metric (conceptual/notational), not applicable to checkpoint-currency.

## Equations

`eq:bba`, `eq:conflict`, `eq:yager` — all three now referenced via `\eqref` from at least one point in the expanded Dempster-Shafer theory section (verified programmatically; `eq:conflict` was initially unreferenced, caught and fixed this pass). Every symbol appearing in any equation is defined in the new Notation table (`tab:notation`).

## Citations and references

Programmatic check: zero `\cite{}` keys without a matching `\bibitem{}`; zero `\bibitem{}` entries never cited (carried forward from a prior pass's cleanup of two duplicate-paper citations, unchanged and re-verified this pass).

## Appendices

Appendix A (Reproducibility Summary) — checkpoint SHA-256, fusion constants, and statistical methodology all current. Appendix B (Worked Fusion Example) — **regenerated this pass** against the final checkpoint (B3 confidence 0.984, high risk; previously 0.699, medium risk, from the prior checkpoint), per explicit instruction in an earlier turn of this session to use the final implementation, not an earlier one.

## Discussion and Limitations

Cross-checked against this pass's new findings: the Limitations section's STBV v1 explanation now cites the exact `rows[10000:]` mechanism (not a generic hedge); the new v2.5b full-pipeline finding (F1 gap from synthesizer context-wrapping) is referenced from the Results section where it was found, consistent with how every other pipeline-level finding in this paper (e.g., the CARLA synthesizer bug) is reported at its point of discovery rather than only in a general limitations list.

## Calibration consistency (this pass)

- **Deployed temperature**: `isce_config.yaml` sets `temperature_scaling: 2.82` — verified as the value actually used by every metric currently in the manuscript, including `tab:v25b_ablation`'s F1=0.860.
- An ensembled-fit alternative ($T{=}4.44$, methodologically more correct — fit on the same 3-template path deployment uses, vs. the deployed value's single-template fit) was built, tested end-to-end on all 10,098 v2.5b samples, and **verified to make deployed decision quality worse** (F1 $0.860\to0.817$) despite improving ECE ($0.098\to0.070$) — see `CALIBRATION_FIX_REPORT.md`. Reverted; not deployed; not reflected in any table.
- **Verified**: `run_v25b_full_ablation.py`'s override temperature (2.82), `isce_config.yaml`'s deployed temperature (2.82), and the manuscript's v2.5b paragraph (Section~\ref{sec:v25b}, updated this pass to disclose the tested-and-reverted finding rather than describe the fix as "not yet attempted") are now mutually consistent — same value, same story, everywhere.
- `PIPELINE_DIFFERENCE_REPORT.md` updated to remove its now-stale "not attempted this pass" framing and replace it with the actual outcome.

## Checkpoint supersession (subsequent pass): hard-example mining

The final checkpoint changed in a later pass, superseding everything in the sections above that names `semantic_gate_v3_mixed_lora_continued_merged` as final. Full trace: `HARDMINE_IMPROVEMENT_REPORT.md`. Summary:

- **New final checkpoint**: `semantic_gate_v3_mixed_lora_hardmine_merged`, SHA-256 `d126cc3cb998a4717fa833859c6affcd1320f4d60f38c3c98f9cf175720b3759` — a true LoRA weight continuation (not reinit) from the prior final checkpoint, trained on 91 hand-authored, leakage-audited examples mined from the prior checkpoint's own real, highest-confidence v2.5b errors.
- **Verified, not assumed, to improve**: held-out v2.5b direct-classifier F1 0.945→0.957; full-pipeline deployed-decision F1 0.860→0.877, precision 0.756→0.782, FPR 0.366→0.315. Validation-split improvement (0.9241→0.9353) was cross-checked against the true held-out benchmark, not treated as sufficient on its own.
- **Calibration**: refit for the new checkpoint using the identical single-template methodology already in production ($T{=}3.18$ vs.\ the prior $2.82$) — this is a new checkpoint requiring its own fit, not a re-opening of the calibration-methodology investigation (`CALIBRATION_FIX_REPORT.md`, whose finding about the ensembling/floor coupling remains accurate and is now confirmed to persist, in reduced form, for the new checkpoint too).
- **Manuscript updated**: `stbv_paper.tex` Table `tab:v25b`, Table `tab:v25b_ablation`, the Stage 1/2 gap paragraph, Discussion/Conclusion generalization claims, Limitations item (vii), and the Appendix reproducibility summary all now reference the new checkpoint and its verified numbers. STBV-Bench v1 figures/captions (supplementary, not primary) were explicitly relabeled as reflecting the prior checkpoint rather than silently left implying currency, since v1 was not rerun (out of scope given it is no longer the primary benchmark).
- **Benchmarks confirmed checkpoint-invariant, not rerun**: VeReMi (never invokes B3, code-inspected), SUMO (never populates the text field B3 would score, code-inspected). **CARLA not rerun** — requires an active simulator instance not running in this environment; disclosed as a genuine, unresolved follow-up rather than assumed unaffected.

## What this audit did NOT find

No stale metric, no orphaned figure/table/equation reference, no uncited bibliography entry, and no checkpoint-identity inconsistency beyond the two explicitly disclosed exceptions (Table `tab:adaptive`'s prior-checkpoint measurement, and the request's own initial premise, corrected at the outset of this pass).
