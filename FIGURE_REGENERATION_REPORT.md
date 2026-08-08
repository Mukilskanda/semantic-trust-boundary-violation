# Figure Regeneration Report

**Update: the user provided the actual compiled PDF this session**, which resolved the previous pass's biggest blocker (no LaTeX compiler available, so page/figure numbers were unverifiable). The compiled PDF showed 15 figures with real page positions; the fixes below act on the real, confirmed layout, not a guess. Real figure identity was confirmed by matching each old-PDF figure to its stable LaTeX `\label`, since the source had already been edited once (a prior pass's v1 confusion+ROC/PR merge) between when the PDF was compiled and now.

## Old PDF's figure numbers → real identity → what happened this session

| Old PDF # | Label | What it is | Action this session |
|---|---|---|---|
| 1 | `fig_architecture` | Conceptual architecture diagram (page 3) | **Fixed a real layout bug**: the "Proposed STBV Trust Framework" background label overlapped the B1 box (visible as garbled/merged text in the PDF extraction) because the fit-box's label had only 3mm clearance while B1 sat only 6mm below PKI. Increased node spacing (6mm→11mm between PKI and B1; 4mm and 8mm→7mm and 9mm elsewhere), widened label-column spacing (2mm→3mm), and gave the background fit-box asymmetric padding (`inner ysep=5mm`) plus a `yshift` on the label so it has genuine room. |
| 2 | `fig_whyfail` (comparison, page 8) | Two-column conventional-vs-STBV diagram | **Fixed a real layout bug**: 5-box left column vs. 9-box right column left a large block of empty space below the shorter (conventional) branch. Shrunk box/spacing dimensions (~10% smaller throughout) and vertically re-centered the shorter branch within the taller one's span (`below left=29mm` vs. the original `10mm`, computed from the height difference) so the whitespace is now distributed rather than dangling at the bottom. |
| 3 | `fig_pipeline` (deployment diagram) | Deployment/bridge integration diagram | **Removed.** On inspection, its content (PKI→B1→...→B3→TDE staged through a bridge) duplicates `fig_architecture`'s own pipeline diagram in a second visual form; its one genuinely new fact (a bridge converts live vehicle state to CAM/DENM) is now one sentence in prose instead of a full figure. |
| 4–8 | `fig_decision_dist`, `fig_score_dist`, `fig_calibration_v1`, `fig_ablation` (v1 confusion+ROC/PR, already merged in a prior pass) | STBV v1, prior checkpoint, supplementary | Unchanged this session — real data, already correctly labeled supplementary in captions |
| 9 | `fig_family_heatmap` | ITE-Bench, per-layer detection | Unchanged — unique information, not redundant with the v2.5b heatmap |
| 10 | `fig_v25b_confusion_grid` | v2.5b, current checkpoint, 6-panel confusion-matrix grid | **Reduced to a single panel** (Full STBV Framework only). Regenerated from the same real `config_5.csv` data. The other 5 configurations' exact numbers remain in Table V (`tab:v25b_ablation`); 3 of the 6 removed panels were visually identical (all-zero-recall), and the other 2 differed from the kept panel by <70 false positives out of 10,098 — indistinguishable at grid scale, so removing them costs no legible information. |
| 11 | `fig_v25b_progressive` | v2.5b, current checkpoint, line chart of the same 6 configurations | **Removed entirely.** It plotted exactly Table V's numbers with no added information, and a table gives exact values where a line chart gives an approximate visual read of the same six points. |
| 12 | `fig_v25b_heatmap` | v2.5b, attack-family × configuration recall heatmap | Unchanged — this already satisfies the per-family-visualization request (Task 4's own preferred "Option 1": heatmap, rows=families, columns=layers, color=recall) |
| 13 | `fig_v25b_roc` | v2.5b, direct-classifier ROC/PR | Unchanged |
| 14 | `fig_carla_scene` | Live CARLA screenshot | **Removed entirely.** Zero quantitative content — its only claim ("this is a real, running simulator") is already stated in the surrounding prose and evidenced by Table `tab:carla`'s per-scenario results. The image file remains in the repository, just not embedded in the main manuscript. |
| 15 | `fig_sumo_stage` | SUMO per-stage latency | Unchanged |

## Net result

**11 figure environments now** (down from 15 in the compiled PDF the user reviewed; down from 13 at the start of this session). Three figures removed entirely (`fig_pipeline`, `fig_v25b_progressive`, `fig_carla_scene`), one reduced from 6 panels to 1 (`fig_v25b_confusion_grid`), two TikZ diagrams had real, specific layout bugs fixed (not just re-styled) using the actual rendered output as ground truth.

## What was requested but genuinely could not be verified even with the PDF

The attached PDF was compiled from a version of the manuscript **before** a prior pass's v1-figure consolidation — so its "Figure 6/7/8" (three separate v1 figures) already don't exist as three separate figures in the current source (merged into one, `fig_ablation`, in an earlier pass). This was resolved by matching content and page context, not figure number, wherever the two versions diverged — e.g., "Figure 3," "Figure 10," "Figure 11," and "Figure 14" were identified by their stable content (deployment diagram; v2.5b confusion grid; v2.5b progressive curve; CARLA screenshot respectively), confirmed to be unambiguous matches, and acted on directly.

## Per-family visualization (Task 4) and Table V (Task 6): already satisfied, reconfirmed

`fig_v25b_heatmap` already implements the requested heatmap (attack families × configurations, colored by recall) from a prior pass. Table V (`tab:v25b_ablation`) already implements the requested 6-row architecture progression (Traditional/+B2/+CP/B3-only/B1+B2+B3-no-CP/Full STBV) with the PKI-inseparability explanation already in the surrounding prose. Both confirmed present and correct against the compiled PDF — no further change made.
