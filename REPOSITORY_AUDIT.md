# Repository Audit

Scope: the repository's file-level state after this pass's checkpoint freeze, not the manuscript's prose (see `FINAL_MANUSAL_AUDIT.md` for that).

## Checkpoints on disk

| Checkpoint | Status | SHA-256 |
|---|---|---|
| `semantic_gate_v3` (base) | Preserved, untouched, never default in production config | — |
| `semantic_gate_v3_mixed_lora_merged` (pre-continuation) | Preserved, referenced only as an explicit historical comparison row in `tab:v25b` | `638ed0fa...` (per legacy `FINAL_REPRODUCIBILITY_REPORT.md`, not independently rehashed this pass — low priority, not currently load-bearing) |
| `semantic_gate_v3_mixed_lora_continued_merged` (Pass 1 final, superseded) | Preserved, all active references relabeled historical this pass | `bbae0512...` (re-verified fresh this pass) |
| `semantic_gate_v3_mixed_lora_hardmine_merged` (current final) | **Production**, `isce_config.yaml` points here | `d126cc3...` (computed fresh this pass) |

No checkpoint was deleted. Each supersession was additive (new directory), consistent with this project's standing "preserve, don't overwrite" convention.

## New files this pass

**Data/scripts**: `b3_eval/v25_finetune/data/hardmine_v1_raw.jsonl`, `hardmine_train_split.jsonl`, `hardmine_val_split.jsonl`, `hardmine_corpus_manifest.json`, `audit_hardmine_leakage.py`, `train_lora_hardmine.py`, `merge_hardmine_lora.py`, `calibrate_hardmine_checkpoint.py`, `eval_hardmine_v25b.py`, `run_v25b_full_ablation_hardmine.py`, `figures_generated/scripts/generate_v25b_hardmine_figures.py`.

**Figures**: `figures_generated/fig_confusion_v25b_hardmine.pdf`, `figures_generated/fig_roc_pr_v25b_hardmine.pdf`.

**Reports**: `HARDMINE_IMPROVEMENT_REPORT.md`, `FINAL_PAPER_CHANGELOG.md`, `FINAL_MANUSAL_AUDIT.md`, `FINAL_FREEZE_REPORT.md`, `PUBLICATION_CHECKLIST.md`, `SUBMISSION_READINESS.md`, this file.

**Result artifacts**: `b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/` (5 config CSVs + manifest), `b3_eval/v25_finetune/results/hardmine_checkpoint_calibration.json`, `hardmine_v25b_eval.json`.

## Files modified this pass (docstring/banner supersession labels, not logic changes)

`isce_config.yaml`, `run_v25b_full_ablation.py`, `rerun_ablation_configs45_final.py`, `eval_v25b_final.py`, `calibrate_final_checkpoint.py`, `calibrate_final_checkpoint_ensembled.py`, `FINAL_REPRODUCIBILITY_REPORT.md`, `FINAL_RESULTS.md`, `FINAL_CHANGELOG.md`, `FINAL_SUBMISSION_CHECKLIST.md`, `ARCHITECTURE_EXPANSION_REPORT.md`, `FINAL_FREEZE_AUDIT.md`, `FINAL_CONSISTENCY_AUDIT.md`, `stbv_paper.tex`.

## Known repository debt, not addressed this pass (disclosed)

- Multiple `FINAL_*.md` files with overlapping scope accumulated across many passes (`FINAL_RESULTS.md`, `FINAL_FREEZE_AUDIT.md`, `FINAL_REPRODUCIBILITY_REPORT.md`, `FINAL_CHANGELOG.md`, `FINAL_SUBMISSION_CHECKLIST.md`, plus this pass's own `FINAL_FREEZE_REPORT.md`/`FINAL_MANUSAL_AUDIT.md`/etc.). Each has been kept (not deleted, per project convention) and cross-referenced with supersession notices rather than consolidated into one canonical document. A genuine repository-hygiene pass to consolidate these into a single authoritative index would reduce confusion for a new reader, but was out of scope for a correctness-focused freeze and risks losing audit trail if done carelessly.
- `semantic_gate_v3_mixed_lora_merged`'s SHA-256 was not independently rehashed this pass (carried from an older report) — low risk, since that checkpoint is not currently load-bearing for any active claim, only a static historical comparison row.
- Scratch/investigative scripts (`scratch_get_correct_pmalicious_pipeline.py`, `scratch_get_pmalicious_v25b.py`, and similar) remain in the repository root rather than being moved into a `scratch/` subdirectory — functional, but not tidy.
