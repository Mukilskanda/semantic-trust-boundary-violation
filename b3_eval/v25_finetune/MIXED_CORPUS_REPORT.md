# Mixed-Corpus Training Data — Build Report

Built by `b3_eval/v25_finetune/build_mixed_corpus.py`. Goal: retrain B3's LoRA
adapter on a mixture of STBV-Bench v2.5 + STBV-Bench v1 (instead of v2.5
alone) to test whether broadening the training distribution fixes the
catastrophic-forgetting regression documented in `REGRESSION_REPORT.md`.

## Sources considered and the inclusion/exclusion decision

| Source | Rows available | Included in training? | Why |
|---|---|---|---|
| STBV-Bench v2.5 (`train_split_full.jsonl`) | 8,535 | Yes, as-is | Already template-disjoint from its own val/test (`make_splits.py`); this is the existing training set, unchanged. |
| STBV-Bench v1 (`data/stbv_bench/v1/stbv_bench.jsonl`) | 100,000 | Yes, rows `[10000:]` only (90,000-row pool) | Rows `[0:10000]` are the fixed region every prior v1 evaluation script (`rerun_paper_ablation.py` default `--limit 10000`, `recalibrate_v1_collect.py` `LIMIT = 10000`, `recalibrate_v1_test_rerun.py`) reads from. Using any of those 10,000 rows in training would leak directly into the v1 test benchmark this task re-evaluates on. |
| STBV-Bench v2 (`results/stbv_bench_v2/stbv_bench_v2_windows.jsonl`) | 150 windows | **No** | `rerun_stbv_v2.py` scores **all 150/150** windows as the v2 evaluation set (`n_windows=150` reproduces the full committed manifest). There is no unused portion — every window is eval data. Including any of it in training would contaminate the exact benchmark being reported. |
| External semantic corpus (`external_semantic_eval/external_corpus.json`) | 117 entries | **No** | `rerun_external_and_cp.py` / `evaluate_external.py` score **all 117/117** entries. Same reasoning as v2 — 100% eval, 0% held out for training. |

This is a direct consequence of how the prior tasks defined "the benchmark":
v1 reserved a fixed 10k-row eval slice out of 100k, so a 90k-row disjoint pool
remains available for training. v2 and the external corpus were built and
consumed as eval-only sets from the start (full-corpus evaluation, no
train/test split ever existed for them) — so they cannot contribute training
rows without invalidating themselves as held-out benchmarks. The mixed corpus
is therefore v2.5 + v1 only. This is disclosed up front rather than silently
using a smaller "mixed" corpus than the task described.

## Text construction

- v2.5 rows: used as-is (`text` field is already directly-authored natural
  language; label = `label` field).
- v1 rows: raw structured CAM-message dicts, not text. Rendered to text with
  `pipeline.synthesizer.synthesize_message([transformed_message], {}, context="urban", template=TemplateStyle.DEFAULT)`
  — the same deterministic, model-free synthesizer B3's production pipeline
  uses (production ensembles across 4 `TemplateStyle`s; training here uses a
  single canonical style, `DEFAULT`, matching how v2.5's own corpus was
  authored as a single canonical rendering per row — not the 4-way ensemble).
  Label: `is_attacker` field on the message, falling back to
  `attack_family != "benign_control"` — identical rule to
  `recalibrate_v1_collect.py`'s ground-truth convention.

## Balance

v1's 90,000-row pool dwarfs v2.5's 8,535-row train split. To avoid v1
drowning out v2.5 in the mixture (the stated goal is broadening the
distribution, not replacing it), v1 is capped to a comparable order of
magnitude: per-family stratified sampling, 405 rows/family × 21 families ≈
8,505 rows, seed 42.

## Final composition

| Split | v2.5 rows | v1 rows | Total |
|---|---|---|---|
| mixed_train_split.jsonl | 8,535 | 7,229 | 15,764 |
| mixed_val_split.jsonl | 1,898 | 1,276 | 3,174 |

v1's 8,505 selected rows were split 85/15 (row-level, seed 42) into
train/val. Row-level splitting (rather than template-group splitting) is
used for v1 because v1 has no `template_id`-equivalent skeleton field — each
row is an independently-sampled VeReMi scene/timestamp, so row-level
splitting does not reproduce the kind of near-duplicate skeleton leakage
`template_id`-grouping was designed to prevent for v2.5.

## Leakage audit

- **v1 pool vs. v1 eval region**: hard assertion in `build_mixed_corpus.py`
  — zero `sample_id` overlap between the training pool (`rows[10000:]`) and
  the eval-reserved region (`rows[:10000]`). PASS.
- **Exact text duplicates, mixed_train ∩ v2.5 test_split_full**: 0.
- **Exact text duplicates, mixed_val ∩ v2.5 test_split_full**: 0.
- **Exact text duplicates, mixed_train ∩ mixed_val**: 0.
- v2 and external corpus: excluded entirely (see table above), so no
  leakage risk against those benchmarks by construction.

## Reproducibility

`python b3_eval/v25_finetune/build_mixed_corpus.py`, seed 42 throughout
(family sampling, shuffling, train/val split). Outputs:
`data/mixed_train_split.jsonl`, `data/mixed_val_split.jsonl`,
`data/mixed_v1_train_full.jsonl`, `data/mixed_v1_val_full.jsonl` (full
fidelity, with `sample_id`/`attack_family`, for audit), and
`data/mixed_corpus_manifest.json`.
