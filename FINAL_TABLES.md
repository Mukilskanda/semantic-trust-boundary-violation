# Final Tables

This supersedes the prior version of this file (from an early-session pass, referencing a since-superseded checkpoint name and a 13-table count from before multiple later consolidation passes). This is the authoritative record of every evaluation table now in `stbv_paper.tex`, one benchmark/configuration combination per row, no duplicates anywhere else in the manuscript with a different value (verified in `TABLE_CONSISTENCY_REPORT.md`). All values use the current final checkpoint (`semantic_gate_v3_mixed_lora_hardmine_merged`) unless a row explicitly names an earlier one.

## Table I -- `tab:v25b`: Checkpoint Progression, STBV-Bench v2.5b, Direct Classifier ($n{=}10{,}098$)

| Checkpoint | Acc. | Prec. | Rec. | F1 | ROC AUC |
|---|---|---|---|---|---|
| Untuned base | 0.576 | 0.634 | 0.478 | 0.545 | 0.619 |
| Mixed corpus (pre-cont.) | 0.912 | 0.910 | 0.926 | 0.918 | 0.965 |
| Continued (prior final) | 0.941 | 0.939 | 0.951 | 0.945 | 0.985 |
| **Hard-mined (final)** | **0.954** | **0.946** | **0.969** | **0.957** | **0.989** |

## Table II -- `tab:ite_ablation`: Architectural Validation on ITE-Bench ($n{=}9{,}900$), Current Final Checkpoint

*Purpose: can the architecture detect communication and behavioral attacks?*

| Configuration | Acc. | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|---|
| Existing Pipeline | -- | -- | -- | -- | -- (not implementable) |
| B1 | 0.536 | 1.000 | 0.381 | 0.552 | 0.000 |
| B1+B2 | 0.691 | 0.894 | 0.667 | 0.764 | 0.236 |
| B1+B2+CP | 0.691 | 0.894 | 0.667 | 0.764 | 0.236 |
| **Full STBV** | **0.913** | **0.896** | **1.000** | **0.945** | **0.349** |

## Table III -- `tab:v25b_pipeline`: Semantic Validation on STBV-Bench v2.5b ($n{=}10{,}098$), Current Final Checkpoint

*Purpose: does semantic validation improve the trust stack?*

| Configuration | Acc. | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|---|
| B3 | 0.852 | 0.782 | 0.999 | 0.877 | 0.315 |
| B1+B2+B3 (no CP) | 0.845 | 0.775 | 0.999 | 0.873 | 0.329 |
| **Full STBV** | **0.852** | **0.782** | **0.999** | **0.877** | **0.315** |

## Table IV -- `tab:veremi`: VeReMi Kinematic Companion, MBD (5 seeds, mean)

Unchanged this pass -- real VeReMi results, message- and vehicle-level, per attack type; see manuscript for full values.

## Table V -- `tab:carla`: Live CARLA, Final Checkpoint, Post-Fix ($n{=}400$; two runs)

Unchanged this pass -- per-scenario decision outcomes; see manuscript for full values.

## Table VI -- `tab:complexity`: Per-Stage Time Complexity, Latency, and Memory

Unchanged this pass -- real per-stage measured latency, SUMO replay, $n{=}2{,}000$; see manuscript for full values.

## Explicit non-duplication statement

Every configuration/benchmark pair above appears in **exactly one** row in **exactly one** table. "Full STBV" appears twice across the whole manuscript's tables (Table II, ITE-Bench; Table III, v2.5b) -- by design, as two independent cross-benchmark measurements of the same checkpoint, not a duplicate or disagreement (`TABLE_CONSISTENCY_REPORT.md`). No other configuration name is repeated across tables with numeric values attached.
