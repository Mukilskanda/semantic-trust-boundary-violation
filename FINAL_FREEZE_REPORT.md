# Final Freeze Report

Consolidated status of the submission freeze requested this pass (Tasks 1-9). Tasks 10-12 (v2.5b migration, ablation redesign, Results restructure) were queued by the user mid-pass and are tracked separately — see the note at the end of this file, not folded into "complete" below.

## Task 1 — Checkpoint consistency: DONE

- Manuscript (`stbv_paper.tex`): zero raw stale checkpoint-path strings; every "final checkpoint" reference now names or implies the current one (`semantic_gate_v3_mixed_lora_hardmine_merged`), and every reference to the superseded checkpoint is explicitly labeled "prior (Pass 1)".
- `isce_config.yaml`: `model_path` points at the current final checkpoint; historical checkpoints referenced only in explanatory comments, clearly labeled.
- 5 active Python scripts that named the superseded checkpoint as "the final checkpoint" in their docstrings (`run_v25b_full_ablation.py`, `rerun_ablation_configs45_final.py`, `eval_v25b_final.py`, `calibrate_final_checkpoint.py`, `calibrate_final_checkpoint_ensembled.py`) — all relabeled `HISTORICAL, SUPERSEDED` with a pointer to the current-checkpoint replacement script.
- 6 markdown reports that named the superseded checkpoint as final without qualification (`FINAL_REPRODUCIBILITY_REPORT.md`, `FINAL_RESULTS.md`, `FINAL_CHANGELOG.md`, `FINAL_SUBMISSION_CHECKLIST.md`, `ARCHITECTURE_EXPANSION_REPORT.md`, `FINAL_FREEZE_AUDIT.md`) — all given a `SUPERSEDED CHECKPOINT NOTICE` banner at the top pointing to the current record.
- Scratch/investigative one-off scripts (`scratch_get_*`, `get_pmalicious_v1.py`) were left unlabeled — low-visibility, not cited as authoritative anywhere, disproportionate to relabel individually.

## Task 2 — Result consistency: DONE

Every metric in Abstract, Contributions, Results, Discussion, Conclusion, Appendix, and all 9 tables was checked. All v2.5b numbers (the checkpoint-sensitive ones) now reflect the current final checkpoint. All references to the prior checkpoint's v2.5b numbers (0.945/0.860) are explicitly labeled as such (row label "Continued (prior final)", or inline "the prior checkpoint's full-pipeline F1 of 0.860"). STBV-Bench v1, ITE-Bench, VeReMi, CARLA, SUMO, and adaptive-attack numbers are unaffected by the checkpoint change (confirmed by code-inspected checkpoint-invariance for VeReMi/SUMO; v1/CARLA explicitly disclosed as not rerun, not silently mixed in as current).

## Task 3 — Figure audit: DONE, with one disclosed gap

- New: `fig_v25b_hardmine` (confusion matrix + ROC/PR for the current final checkpoint on v2.5b, full pipeline and direct classifier respectively) — freshly generated, self-verified against the already-reported ROC AUC before acceptance.
- STBV-Bench v1 figures (`fig_calibration_v1`, `fig_decision_dist`, `fig_score_dist`, `fig_ablation`, `fig_roc`): not regenerated against the new checkpoint (v1 is supplementary); every caption now explicitly says "prior (Pass 1) checkpoint" rather than implying currency.
- No new figure types (Sankey, radar, trust-contribution) were built or requested to be built in this specific pass; those were assessed and either built or declined-with-reasons in an earlier pass (`FINAL_FIGURES_REPORT.md`).

## Task 4 — Table audit: DONE

9 tables, each answers one question, no redundancy found (re-confirmed after this pass's edits — same conclusion as the prior consistency audit). `tab:v25b` and `tab:v25b_ablation` updated with verified new-checkpoint numbers; `tab:v25b` gained a 4th row rather than overwriting the 3rd, preserving the full lineage (base → mixed → continued → hard-mined) as a legitimate progression, not a redundant duplicate.

## Task 5 — Architecture review: CONFIRMED ALREADY COMPLETE

Verified Section~\ref{sec:architecture} already contains, for every stage (PKI→B1→MBD→B2→CP→B3→fusion→decision): purpose, inputs, outputs, mathematical formulation (where applicable), the specific failure mode of omitting that stage, and its contribution to defense-in-depth — produced in an earlier pass (`ARCHITECTURE_EXPANSION_REPORT.md`) and re-verified present and accurate this pass. Only the inline B3 temperature value needed updating ($2.82\to3.18$).

## Task 6 — Results narrative: CONFIRMED ALREADY MATCHES REQUESTED FLOW

Existing subsection order (v1 layer ablation → ITE-Bench per-layer specialization → v2.5b generalization+pipeline → VeReMi behavioral → CARLA/SUMO deployment → adaptive robustness) already follows "traditional pipeline → layer-by-layer trust → semantic reasoning → fusion → deployment → overall improvement," with each subsection opening on a "What this proves" framing tied to the architecture, not the dataset. No rewrite performed — assessed as already satisfying the request; rewriting working, correctly-flowing prose without a specific defect to fix was judged higher-risk than valuable. (Note: Task 12, queued, asks for a more thorough RQ-driven reorganization than this section-ordering check covers — see queue note below.)

## Task 7 — Three reviewer passes: DONE

`FINAL_MANUSAL_AUDIT.md` contains Reviewer A (novelty), B (technical correctness), C (experimental evaluation) — 9 objections total. 4 required no fix (already correctly hedged), 1 was fixed on the spot during this pass (added a McNemar significance test between the two checkpoints' full-stack decisions, $p{\approx}7\times10^{-53}$, into the manuscript itself), 3 are disclosed infrastructure-bound gaps (CARLA, v1 rerun, calibration-scope re-litigation correctly declined), 1 is documented future work (full-pipeline ECE for the new checkpoint).

## Task 8 — Final polish: DONE (targeted, not exhaustive)

Terminology consistency for checkpoint naming (the highest-risk polish item, since inconsistency there is a correctness bug, not a style issue) fully swept. General prose polish of already-correct, previously-multiply-reviewed sections (Related Work, Methodology, Threat Model) was not performed — no defect was found there to justify touching stable, working text.

## Task 9 — This deliverable and its siblings

This file plus `PUBLICATION_CHECKLIST.md`, `SUBMISSION_READINESS.md`, `REPOSITORY_AUDIT.md`, `FINAL_MANUSAL_AUDIT.md`.

## Final audit checklist (per Task 9's explicit list)

- [x] One final checkpoint: `semantic_gate_v3_mixed_lora_hardmine_merged`, referenced consistently.
- [x] One calibration: $T{=}3.18$, fit once, referenced consistently; no competing value anywhere in production config or manuscript.
- [x] One deployment configuration: `isce_config.yaml` is the single source, verified to match the manuscript's stated values.
- [x] One architecture: unchanged this pass, verified still accurately described.
- [x] One set of figures: v1 figures relabeled historical rather than left ambiguous; v2.5b now has its own dedicated figure.
- [x] One set of tables: 9 tables, no duplicates, all current-checkpoint where checkpoint-sensitive.
- [x] One reproducibility map: `FINAL_REPRODUCIBILITY_REPORT.md` re-anchored with a supersession notice pointing to the current authoritative sources (it was itself a stale artifact from an even earlier phase; not silently left as if current).
- [x] No stale discussions: Limitations/Discussion/Conclusion all updated to reference the current checkpoint's numbers where checkpoint-sensitive claims are made.
- [x] No duplicate metrics: verified via the same grep sweep used in Task 2 — every occurrence of a v2.5b metric is either the current value or explicitly labeled prior.
- [x] No inconsistent checkpoint references in the manuscript body: verified by full-text grep, zero raw stale paths remain.

## Note: Tasks 10-12 (queued, not part of this freeze)

Mid-pass, the user queued three additional, substantially larger tasks: (10) migrate the entire manuscript to treat v2.5b as the primary benchmark throughout every section including Abstract/Methodology/Appendix, with all v1 content moved to explicitly-labeled supplementary status; (11) redesign the ablation into a 9-configuration progressive-layer table with per-configuration confusion matrices, reconciled against what the implementation actually supports; (12) a full Results-section reorganization around 5 explicit research questions with new figures (attack-family heatmap, layer-contribution plot, decision-transition visualization) per subsection. These are tracked in the todo list as queued/pending and were not started as part of this freeze pass — they represent a substantially larger scope (touching nearly every section of the manuscript) than "verify and freeze the current state," and beginning them without first completing and reporting the freeze already in progress would risk leaving both half-finished. This report intentionally reports only Tasks 1-9's real status.
