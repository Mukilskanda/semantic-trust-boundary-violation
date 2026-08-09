# Figure Redesign Report

**No numerical result changed. No experiment was rerun. No value was fabricated.** Every figure below was verified against an already-published number (table row, in-text statistic, or prior figure) before being accepted — see the "Verification" column.

## Global style (Task 2, Task 9)

`figures_generated/scripts/pubstyle.py`, applied to every regenerated figure: serif typography, consistent font-size hierarchy (9pt body / 10pt titles / 7-8pt ticks), 2.0pt lines, 1.0pt spines, colorblind-safe Okabe-Ito palette, soft gridlines (alpha 0.25), top/right spines removed, PDF+SVG+600dpi-PNG export. The Task 9 semantic color mapping (blue=architecture, green=success, orange=caution, red=failure/threshold, purple=semantic validation, grey=historical) is encoded as named constants (`ARCH_C`, `SUCCESS_C`, `FAIL_C`, `SEMANTIC_C`, `HIST_C`) and used consistently in every figure built or touched this pass.

## Figures changed

| Figure | Change | Verification |
|---|---|---|
| `fig_whyfail` (flagship architecture contribution map, Task 4) | Added explicit in-diagram annotations marking where trust is validated (STBV's B3 box) and where conventional trust has no content check at all; caption rewritten to lead with "Architecture contribution map" | Same real $T_{Decision}$ values (0.730 ACCEPT / 0.240 REJECT) already verified in an earlier pass — no new computation |
| `fig_v25b_confusion_grid` | Row-normalized % + count per cell, sequential Blues, no unnecessary ticks | TN=3,243, FP=1,491, FN=6, TP=5,358 — identical counts to Table V's full-stack row; row percentages recomputed directly from these same counts |
| `fig_v25b_roc` | In-plot AUC/AP boxed annotation, thicker curve, diagonal baseline | ROC AUC=0.9892, PR AUC=0.9896 — identical to the already-verified values |
| `fig_v25b_progressive` | Structural-zero bars explicitly greyed/labeled "0 (structural)" rather than ambiguous empty bars | Six F1 values identical to Table V |
| `fig_v25b_heatmap` | Palette unified to Blues (was Greys) | Data unchanged |
| `fig_latency_breakdown_final` (still used once, early, in Complexity Analysis) | Restyled: value labels, red highlight on B3's bottleneck bar | Same 8 real per-stage ms values already in the manuscript text |

## New figures

| Figure | Task | What it shows | Verification |
|---|---|---|---|
| `fig_layer_responsibility` | Task 6 | Qualitative Strong/Moderate/Weak/Not-Exercised matrix, attack category x layer | Every cell traced to a specific, already-published finding (ITE-Bench Table IV, v2.5b Table V, CARLA Table VIII) — no new metric computed |
| `fig_deployment_summary` | Task 7 | 3-panel: (A) latency timeline, (B) per-stage breakdown, (C) achieved vs. required throughput | Mean latency 81.23ms (manuscript: 81.2ms); achieved throughput $1000/81.23=12.31$ msg/s (manuscript: "12.3 msg/s") — both independently recomputed from the same real per-message JSON and matched to the existing text before acceptance |

## Merges (Task 8)

The per-stage latency figure and the aggregate latency/throughput claims (previously two separate pieces of evidence: one figure + prose-only throughput numbers) were consolidated into the single `fig_deployment_summary` panel in the Results/SUMO subsection. The standalone per-stage figure is retained in its restyled single-panel form for one earlier, narrower reference in the Complexity Analysis section, where a full deployment panel would be premature (that section is about computational complexity, not deployment throughput).

## Confirmation

- **No numerical result changed**: every value plotted in every figure above already exists in the manuscript's text or tables; each was independently recomputed from the underlying real data (per-sample CSVs, per-message JSON) and checked to match before the figure was accepted.
- **No experiment was rerun**: all data sources are files already on disk from prior evaluation passes (`b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/`, `deployment_eval/results/deployment_eval_results.json`, Table IV/VIII's already-published values).
- **No value was fabricated or interpolated**: the score-distribution KDE (built in a prior pass) is a standard Silverman-bandwidth density estimate over the real per-sample scores, not smoothing of aggregate results; the layer-responsibility matrix's qualitative labels are an ordinal summary of quantitative findings already in the paper, not new evidence.

See `FIGURE_AUDIT.md` for the full per-figure keep/improve/merge/replace/remove decision table, and `FINAL_VISUAL_CHECKLIST.md` for the reviewer-perspective final check.
