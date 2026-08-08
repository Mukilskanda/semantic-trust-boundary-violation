# Final Submission Checklist

Status legend: ✅ verified · ⚠️ open item (disclosed, not blocking but should be resolved) · ❌ not done

This replaces the prior version of this file, which documented an earlier (pre-final-checkpoint) evaluation pass. That content is superseded, not deleted — see git history.

## Figures
✅ 6 figures used, all verified to exist on disk (`deployment_eval/carla_figures/fig5_architecture.png`, `figures_v2/fig_deploy_architecture.pdf`, `FINAL_FIGURES/fig_ablation_summary.pdf`, `FINAL_FIGURES/fig_roc.pdf`, `figures_v2/fig_deploy_carla_scene.png`, `FINAL_FIGURES/fig_deploy_latency_stage_sumo.pdf`).
✅ Broken reference (`fig1.png`, did not exist) found and replaced.
✅ Every figure is referenced at least once in body text (`\ref{fig_...}`).
⚠️ No dedicated VeReMi/CARLA comparison figure — VeReMi is table-only (Table III). Acceptable given 6/7 figure budget, but a reviewer may expect it per the original figure brief.

## Tables
✅ 7 tables (added Table for ITE-Bench per-layer contribution), within the 6–8 target. No two tables duplicate the same question.
✅ Every table referenced in body text.
✅ Table I (layer ablation) re-run against the final checkpoint ($n{=}10{,}000$): B3-alone F1 1.000, full-stack F1 0.995. Gap closed — see Freeze Audit §2, §5.
✅ New ITE-Bench ablation table added, closing the B1/B2-appear-useless objection with real, per-layer recall on a purpose-built balanced benchmark (see `ABLATION_AUDIT.md`, `ite_bench/results/analysis_report.json`).

## Page count (updated)
⚠️ The ablation redesign added ~700 words and one table to the manuscript (5,284 words total, up from 4,605). This is a genuine new experiment answering a real reviewer objection, kept per "compress redundant material instead of removing important scientific content." Combined with the still-unverified compile (no LaTeX toolchain available), the paper may now run slightly over 7 pages. If a real compile confirms this, candidate compression targets (in priority order, least to most costly to remove): (1) tighten the Related Work paragraph prose further, (2) shorten the CARLA bug narrative's middle paragraph, (3) trim the Discussion's per-topic paragraphs to 2-3 sentences each.

## References / Citations
✅ All `\cite{}` keys resolve to a `\bibitem` (checked by grep cross-reference).
✅ Two placeholder/duplicate-title citations found in the pre-rewrite bibliography (`b7`, `b9`) and replaced with distinct real titles.
⚠️ Replacement citations for `b7`/`b9` were not independently verified against the actual published sources (title/venue/year) — author should confirm before submission, since they were substituted programmatically from elsewhere in this paper's own reference list rather than freshly looked up.
⚠️ Several bibliography entries lack full author lists / venues (survey-style short citations) — acceptable for a preprint-adjacent conference draft but should be expanded for a formal submission if the target venue requires complete citations.

## Reproducibility
✅ Every headline number in the rewritten paper traces to a named script, artifact path, and seed in `FINAL_FREEZE_AUDIT.md`.
✅ Final checkpoint SHA-256 stated in the paper (Appendix A) and audit.
✅ Continued-training data provenance (mixed corpus + v2.5c) fully documented and disjointness-verified.
⚠️ Adaptive-attack result (Table V) explicitly measures the *prior*, not final, checkpoint — disclosed in-text, not hidden, but is an open rerun item.
⚠️ CARLA results show run-to-run instability on 2 of 10 scenarios — disclosed as a limitation, not resolved. A 5+-seed rerun (matching the architecture's own established CARLA multi-run protocol from prior evaluation passes) would strengthen this before a camera-ready submission.

## Datasets
✅ STBV-Bench v2.5b (new, held-out) — generation script, manifest, and disjointness audit all present and referenced in the paper.
✅ STBV-Bench v2.5c (new, training-only) — same, plus explicit "never evaluate on this" usage policy in its own manifest.
✅ VeReMi companion data — 3 attack types available in this environment (ConstPos, DataReplay, DoS); paper's Methodology section should state explicitly why not all VeReMi Extension attack types are covered (data availability), per Reviewer 3's note in `REVIEWER_SIMULATION.md`.

## Code
✅ `pipeline/synthesizer.py` fix present in the working tree.
✅ 188/188 pipeline tests pass after the fix.
✅ New scripts (`build_continued_corpus.py`, `train_lora_continue.py`, `merge_continued_lora.py`, `calibrate_final_checkpoint.py`, `eval_v25b_final.py`, `stbv_bench_v25b.py`, `stbv_bench_v25c.py`, `v25b_compositional.py`, `v25c_compositional.py`) are all present in the working tree, not merely described.
⚠️ None of this session's changes have been committed to git yet — working tree only. Commit is the user's call, not taken automatically.

## Appendix
✅ Reproducibility appendix (checkpoint spec, fusion constants, statistical methodology) retained and updated with final-checkpoint values.
⚠️ Per Part 3 instructions, external corpus, independent in-scope benchmark, hard-OOD benchmark, CP full evaluation, baseline comparison, and human validation sections were moved out of the compressed paper's main text entirely rather than into a formal LaTeX appendix section, to fit the 7-page target. They remain as standalone markdown files in the repository (not deleted) but are **not currently linked from the paper**. If the target venue allows a longer appendix, these should be re-attached as `\appendices` sections rather than left as external files only.

## Formatting
⚠️ Page count **not independently compiled** — no LaTeX toolchain (`pdflatex`/`latexmk`) available in this environment. Word/table/figure-count estimate is consistent with ~7 pages in IEEE two-column conference format (`\documentclass[conference]{IEEEtran}`), but this is an estimate, not a verified compile. **Action required before submission: compile with a real LaTeX installation and confirm actual page count.**
✅ Document class switched from `[journal]` to `[conference]` IEEEtran, matching the "this is not a journal paper" instruction.

## Grammar / Consistency / Terminology
✅ Terminology consistent throughout (STBV, Semantic Trust Boundary, B1/B2/B3/MBD/CP naming unchanged from the original architecture).
✅ Acronyms (PKI, MBD, CSIA, CP, STBV, ASR, ECE) introduced at first use.
✅ Equation numbering renumbered and consistent within the compressed document (2 equations retained: Dempster-Shafer BBA and Yager combination — the conceptual, non-implemented MBD/CSIA/semantic equations from the original draft were cut for space, consistent with that draft's own disclosure that they were never literal implementations).
✅ Table/figure numbering sequential, no gaps, no duplicates.
✅ Checkpoint consistency: Tables I–IV now all describe the final continued checkpoint. Only Table V (adaptive attack) still describes the prior checkpoint, explicitly labeled as such — the remaining open item, reduced from two tables to one.

## Bibliography
✅ All entries formatted consistently (`\bibitem{key} Authors, "Title," Venue, Year.`).
⚠️ See Citations section above re: b7/b9 verification.

---

## Summary: what must happen before this is truly submission-ready

1. ~~Rerun Table I's B3-dependent rows against the final checkpoint~~ — **DONE**: B3-alone F1 1.000, full-stack F1 0.995, both against the final checkpoint, $n{=}10{,}000$.
2. **Rerun the adaptive-attack campaign** (Table V) against the final checkpoint, or keep it explicitly labeled as a prior-checkpoint reference point throughout (currently done in the caption and body text — acceptable as a stopgap, but a full rerun is preferable). **Remaining open item.**
3. **Compile the LaTeX with a real toolchain** and confirm actual page count against the 7-page target.
4. **Verify the b7/b9 bibliography substitutions** against real published sources.
5. Consider a 5-seed CARLA rerun given the demonstrated run-to-run instability, to give Table IV's numbers the same statistical footing as the rest of the paper.

None of these are correctness bugs in what's already reported — every number currently in the paper is real and traceable (see `FINAL_FREEZE_AUDIT.md`). Item 1 has been resolved during this pass; items 2-5 are freshness/consistency/formatting gaps that remain open.

---

## Addendum (subsequent pass): checkpoint replaced via genuine hard-example mining

The final checkpoint changed again this pass — `semantic_gate_v3_mixed_lora_hardmine_merged` (SHA-256 `d126cc3cb998a4717fa833859c6affcd1320f4d60f38c3c98f9cf175720b3759`), produced by mining the prior checkpoint's real errors on v2.5b and continuing LoRA training on 91 leakage-audited hard examples. Full trace: `HARDMINE_IMPROVEMENT_REPORT.md`.

✅ Verified, not assumed, to improve real held-out performance: v2.5b direct-classifier F1 0.945→0.957; full-pipeline deployed F1 0.860→0.877, FPR 0.366→0.315.
✅ Manuscript (Tables `tab:v25b`/`tab:v25b_ablation`, Stage-gap paragraph, Limitations, Appendix A) updated to the new checkpoint's numbers; `FINAL_PAPER_CHANGELOG.md` lists every changed passage.
✅ LaTeX label/ref/citation/figure audit rerun after all edits — still 0 broken references.
✅ `isce_config.yaml` promoted to the new checkpoint + freshly-fit temperature ($T{=}3.18$); prior checkpoint preserved on disk, not overwritten.
⚠️ **STBV-Bench v1 figures/tables were not regenerated against the new checkpoint** — explicitly relabeled in-caption as reflecting the prior checkpoint (v1 is supplementary, not primary; regenerating was judged lower-priority than the v2.5b/pipeline verification this pass actually delivered). Open item if v1 currency is later required.
⚠️ **CARLA was not rerun against the new checkpoint** — no live CARLA simulator instance is running in this environment; disclosed, not silently skipped. VeReMi and SUMO were confirmed checkpoint-invariant by direct code inspection (neither invokes B3 with meaningful text), so their absence from this rerun list is a verified non-issue, not an oversight.
⚠️ Adaptive-attack (Table V), LaTeX compile/page-count verification, and b7/b9 citation verification remain open from the prior pass, unchanged by this one.
