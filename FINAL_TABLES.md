# FINAL_TABLES.md — every table in the submitted `stbv_paper.tex`

13 tables total (12 `table` + 1 `table*`), all now reflecting only the final
checkpoint `semantic_gate_v3_mixed_lora_merged` where checkpoint-dependent,
or explicitly marked checkpoint-invariant/not-rerun otherwise. Source for
every value: `REPRODUCIBILITY_MAP.md` (renamed/finalized as
`FINAL_REPRODUCIBILITY_REPORT.md`).

| Label | Title | Checkpoint status |
|---|---|---|
| `tab:related_work` | Positioning vs. related literature | N/A — qualitative, not B3-dependent |
| `tab:main_ablation` | Layer Contribution on STBV-Bench v1 | Rows 1–3 checkpoint-invariant (B3 disabled); rows "B3 alone"/"full stack" = final checkpoint, $n=10{,}000$ |
| `tab:coverage` | Threat-Class Coverage Summary | Semantic-side rows = final checkpoint (mixed-threat rerun); kinematic-side rows checkpoint-invariant (MBD-only) |
| `tab:external_eval` | External Semantic Evaluation | Final checkpoint, $n=117$ |
| `tab:adaptive` | Adaptive Attack Evaluation | Final checkpoint, $n=51$ seeds |
| `tab:cp_full` | CP's Marginal, Attributable Effect | Final checkpoint; verified byte-identical to the effect measured under the prior checkpoint |
| `tab:baselines` | Baseline Comparison | B3 row = final checkpoint (config 4); other rows checkpoint-invariant (never call B3) |
| `tab:deployment` | Deployment Feasibility: SUMO vs. CARLA | SUMO column = final checkpoint, fresh protocol-identical rerun; CARLA column = prior checkpoint, **not rerun** (disclosed, CARLA unavailable in this environment) |
| `tab:carla_scenarios` | Live CARLA per-scenario outcomes | Prior checkpoint, **not rerun** (disclosed) |
| `tab:safety` | Failure Modes Ranked by Safety Consequence | Risk ratings reassessed against final-checkpoint numbers this evaluation cycle (adaptive-evasion row downgraded HIGH→MEDIUM) |
| `tab:full_ablation` | Supplementary Full Five-Configuration Ablation | Same source/status as `tab:main_ablation` |
| `tab:external_sources` | External Corpus Composition by Source | Corpus-construction table, not checkpoint-dependent |
| `tab:external_family` | Per-Family Recall, External Corpus | Final checkpoint, $n=117$ |

## Headline final-checkpoint values (cross-referenced against raw artifacts)

| Metric | Value | Source artifact |
|---|---|---|
| STBV-Bench v1, full stack | Acc 0.993 / Prec 0.990 / Rec 1.000 / F1 0.995 / FPR 0.023 | `ablation_config_5.csv` |
| STBV-Bench v1, B3 alone | F1 0.9999, ROC-AUC 1.000, PR-AUC 0.9998 | `ablation_config_4.csv` |
| STBV-Bench v2 (windowed) | F1 0.521, Recall 1.000, FPR 0.693 | `stbv_bench_v2_per_message.csv` |
| External semantic corpus | Acc 0.880 / Prec 0.931 / Rec 0.910 / F1 0.920 / ROC-AUC 0.897 | `external_eval_results__mixed.json` |
| Adaptive-attack ASR | 21.6% (11/51) | `adaptive_attack_results__mixed.json` |
| Mixed-threat semantic recall / benign FPR | 1.000 / 0.673 | `mixed_threat_per_message.csv` |
| CP isolated effect | 33 decision changes, 11/21 attackers recovered | `cp_full_eval_results__mixed.json` |
| SUMO deployment (final ckpt) | mean 73.9~ms, $p_{99}=100.2$~ms, throughput 13.51~msg/s | `deployment_eval_results_mixed.json` |
| Live CARLA | not rerun this cycle — prior-checkpoint values retained, disclosed | (unchanged) |

## Addendum — presentation/structure phase

- `tab:hardood` moved from a main-Results table to a Limitations/Future-Work
  table (Section~\ref{sec:limitations}), reflecting the benchmark's role as
  an exploratory scope-boundary probe, not a core capability claim (Task 5
  of this phase). Its numbers were also updated to the final,
  audit-revised values already established in the prior phase (F1=0.345,
  not the pre-audit 0.446) — no new number, just correct positioning.
- New: the 11-family perturbation/robustness battery, previously disclosed
  as stale, was rerun against the final checkpoint and integrated as prose
  (not a new table) into the existing "Calibration, Robustness, and
  Latency" paragraph in main Results — 6/11 families improved, 4 unchanged,
  1 (`contradictory`) regressed to 100% over-defense; aggregate accuracy
  0.833→0.864, **not statistically significant** (McNemar exact binomial
  $p=0.727$, $n=66$ paired). Full detail: `ROBUSTNESS_EVAL_REPORT.md`.
- Table count: 14 total (13 `table` + 1 `table*`), unchanged from the prior
  phase — one table relocated, not added or removed net.

## Addendum 2 — independent in-scope benchmark (new primary Results table)

### New: `tab:indep` — Independent In-Scope Evaluation, Frozen B3 ($n=216$)

| Metric | Value |
|---|---|
| Accuracy | 0.472 [0.412, 0.542] |
| Precision | 0.969 |
| Recall | 0.215 |
| F1 | 0.352 [0.260, 0.440] |
| ROC AUC | 0.683 |
| PR AUC | 0.829 |
| ECE | 0.490 |
| Brier | 0.493 |

Source: `indep_bench/independent_metrics.json`. Integrated as a **primary
Results table** (Section~\ref{sec:indepbench}, inserted after the External
Semantic Evaluation subsection and before Adaptive Attack Evaluation) —
not appendix, not exploratory — because it passed this project's full
leakage/scope audit and its unexpectedly-low score was root-caused (no bug
found) before being reported, per this phase's explicit integration
criterion. Table count now 15 total (14 `table` + 1 `table*`).

## Addendum 3 — controlled surface-attribute-only confirmatory result

No new standalone table added (integrated as prose within `sec:indepbench`,
not a new `\begin{table}`, to avoid table proliferation for a confirmatory
result). Numbers, for reference:

| Metric | `indep_bench` (rich narrative, n=216) | `indom_bench` (surface-only, n=216) |
|---|---|---|
| F1 | 0.352 [0.260, 0.440] | 0.314 [0.224, 0.409] |
| Accuracy | 0.472 | 0.454 |
| Recall | 0.215 | 0.188 |
| Precision | 0.969 | 0.964 |
| ROC-AUC | 0.683 | 0.532 |

CIs overlap substantially — **not a meaningful difference**. This
confirms the generalization gap is not an artifact of the richer
benchmark's added narrative complexity: pure surface-attribute novelty,
at STBV-Bench's own calibrated message directness, reproduces the same
gap. Decision: **both corpora kept, neither replaces the other** — see
`INDOMAIN_BENCHMARK_RESULTS.md`'s "Manuscript integration decision" for
full reasoning. Table count remains 15 total (14 `table` + 1 `table*`).
