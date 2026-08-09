# Final Figure Selection

**Exactly 10 figures in the final manuscript.** No experimental result changed, no experiment rerun, no value fabricated — every number in every figure was already published in the manuscript's text or tables before this pass.

## The 10 retained figures, in document order, with one-sentence justification

| # | Figure | Why removing it would weaken the paper |
|---|---|---|
| 1 | `fig_architecture` | Without it, no reader gets the full 8-stage pipeline as one object; every subsequent claim about "which layer does what" depends on this map existing first. |
| 2 | `fig_boundary_schematic` (new) | The only figure that teaches the paper's central mechanism in the abstract, before any specific evidence — removing it forces every reader to reconstruct the idea from prose alone. |
| 3 | `fig_whyfail` (flagship contribution map, `figure*`) | The single strongest evidentiary figure in the paper — real trust scores (0.730 ACCEPT / 0.240 REJECT) on a real message; no other figure proves the mechanism actually happened. |
| 4 | `fig_layer_responsibility` | The only figure that directly answers "why does each layer exist" across all four threat categories in one glance; without it that question is answered only by scattered prose across four different subsections. |
| 5 | `fig_ite_coverage` | The only figure showing the complete defense-in-depth diagonal (each layer owning exactly one row) — the paper's clearest rebuttal to "B1/B2 look weak," visible without reading a table. |
| 6 | `fig_v25b_confusion_grid` | The paper's primary semantic-benchmark result, at the exact error-count level (FN=6 vs. FP=1,491) that Table V's aggregate F1/precision/recall cannot convey. |
| 7 | `fig_error_analysis` (new) | Makes the FN/FP asymmetry from Fig. 6 explicit as the paper's central deployment trade-off statement — without it, a reader could misread the confusion matrix as "31.5% of decisions are wrong" rather than "0.1% of attacks get through." |
| 8 | `fig_v25b_roc` | The only figure showing performance across the full decision threshold range, not just the one operating point every table reports. |
| 9 | `fig_sumo_stage` (now `fig_deployment_summary`) | The only deployment-realism evidence in figure form — latency timeline, per-stage attribution, and throughput headroom together, answering "does this actually work outside a benchmark." |
| 10 | `fig_architecture_glance` (new) | The paper's closing systems figure — threat class → layer → real evidence → decision, in one table-like diagram; without it, a figures-only skim ends on a latency chart rather than a summary of the contribution. |

## Removed completely

| Figure | Reason |
|---|---|
| `fig_decision_dist` (v1, before/after fusion bar chart) | Its one fact (fusion escalates, never relaxes) is now stated as real numbers in prose (Accept 2,993→2,924, Reject 6,855→6,972, Caution 152→104) and independently confirmed on the primary benchmark by the McNemar result already in Section VI-C — a bar chart of 3 categories x 2 conditions was a table in disguise. |
| `fig_v25b_score_dist` (v2.5b score histogram) | Class-separation shape is a real, distinct signal from a scalar, but with ROC/PR (Fig. 8) and the confusion matrix (Fig. 6) already conveying discriminative quality and error structure, a third view of the identical classifier's behavior was judged to not teach something new relative to what ten figures can afford. |
| `fig_v25b_calibration` (reliability diagram) | ECE=0.027 is now stated directly in text; per the explicit instruction to remove it "if ECE is already sufficiently reported in text," it is. |
| `fig_ablation` (v1 consolidated confusion+ROC/PR, historical) | Its real numbers (TN=2,924, FP=69, FN=0, TP=7,007; ROC AUC=1.000) are now reported as text in the "Why B1's and CP's contributions read as near-zero" paragraph; the historical-comparison role is preserved in prose, just not as a dedicated figure slot. |
| `fig_family_heatmap` (ITE-Bench per-family) | Redundant with `fig_ite_coverage`, which already shows the identical specialization pattern at the class level; the family-level version added granularity without changing the conclusion. |
| `fig_v25b_heatmap` (attack-family x config, v2.5b) | Per the explicit instruction: v2.5b's per-family recall is uniform (0.99–1.00 across all 13 families) — exactly the "figures where every plotted value is essentially identical" case flagged for removal. The confusion matrix (Fig. 6) already carries the one number (FN=6) that summarizes this. |
| `fig_v25b_progressive` (F1 by configuration, structural zeros) | Removed in the immediately preceding pass, per the same instruction repeated in this one; not revisited. |

## Merged

| Merge | Into | Reason |
|---|---|---|
| Standalone per-stage latency figure + prose-only throughput/timeline claims | `fig_deployment_summary` (3-panel) | Consolidated in a prior pass; unchanged this pass. No separate latency figure exists elsewhere in the manuscript. |

## New figures added

| Figure | Why it earns a slot |
|---|---|
| `fig_boundary_schematic` | General mechanism, taught once, abstractly, before the concrete evidence — fills the gap left by removing several narrower metric figures. |
| `fig_error_analysis` | Turns the confusion matrix's raw counts into the specific deployment-relevant claim ("errors are almost entirely FP, not FN") that a reviewer would otherwise have to compute themselves from Fig. 6. |
| `fig_architecture_glance` | The paper's one summary figure — did not exist before this pass in any form; closes the "figures-only skim" loop by giving the reader a final, complete recap. |

## Table removed

**Table III** (`tab:main_ablation`, the STBV-Bench v1 4-row progressive ablation) — removed per explicit instruction ("remove Table III if it only exists for STBV-Bench v1"). Its four numbers (B1 only: F1 undefined; B1+B2: F1=0.034; B3 alone: F1=1.000; full stack: F1=0.995) are preserved as inline prose in the same paragraph that previously introduced the table, so no information is lost, only the dedicated table environment. All five body-text references to the table (`Table~\ref{tab:main_ablation}`) were found and converted to "the STBV-Bench v1 ablation numbers above."

## Caption rewrite

Every retained figure's caption now opens with a bolded, one-sentence claim stating what conclusion the reader should draw (e.g., "The architecture almost never misses an attack, and its entire remaining cost is precision"), followed by the descriptive/provenance detail. This was applied to all 10 figures, not only the newly added ones.

## Confirmation

- **No numerical result changed**: every value now stated in prose (in place of a removed figure or table) is transcribed verbatim from the figure/table it replaces, not recomputed or approximated.
- **No experiment was rerun**: all removals, merges, and additions operate on data already generated in prior passes (`ablation_results/v25b_full_hardmine/`, ITE-Bench's existing per-class CSVs, `deployment_eval/results/`).
- **No value was fabricated**: the two new data-bearing figures (`fig_error_analysis`, and `fig_architecture_glance`'s "real evidence" cells) cite only counts and metrics already published elsewhere in the manuscript (Table V's TP/FP/FN/TN; Table IV, Table V, Table VII's recall/F1 values).

Final figure count, verified programmatically: **10** (9 `\begin{figure}` environments + 1 `figure*`, `fig_whyfail`).
