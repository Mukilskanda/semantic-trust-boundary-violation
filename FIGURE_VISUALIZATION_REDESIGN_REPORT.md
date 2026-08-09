# Figure Visualization Redesign Report

**No experimental result, metric, statistic, or conclusion was changed.** Every regenerated figure was verified, before acceptance, to reproduce a number already published in the manuscript's text or tables (see the per-figure verification column below). This report covers only visualization style.

## Shared style (`figures_generated/scripts/pubstyle.py`)

New shared module every regeneration script imports: serif typography, consistent font sizes (9pt body, 10pt titles), thicker axes/lines (2.0pt line width, 1.0pt spines), larger markers, Okabe-Ito colorblind-safe palette, soft gridlines (alpha 0.25), top/right spines removed, and a `save()` helper that exports **PDF (vector, used by LaTeX), SVG (vector), and PNG @600dpi** for every figure. Applied consistently across all redesigned figures.

## Figures redesigned

| Figure | What changed | Verification against existing published number |
|---|---|---|
| **Confusion matrix** (`fig_v25b_confusion_single`) | Row-normalized percentages + raw counts in each cell ("96.3% (3959)" style), sequential Blues, larger fonts, no tick marks, borders removed | TP=5,358 FP=1,491 FN=6 TN=3,243 — identical to Table V's full-stack row |
| **ROC/PR** (`fig_v25b_roc`) | Thicker curve, diagonal baseline, AUC/AP shown in an in-plot boxed annotation, consistent typography | ROC AUC=0.9892, PR AUC=0.9896 — identical to the previously-verified values (matched Table VI's ROC AUC to within 0.002, as originally checked) |
| **Score distribution** (`fig_v25b_score_dist`) | Histogram + Gaussian KDE overlay (standard Silverman bandwidth, not fabricated smoothing — a textbook density estimator applied to the same real per-sample scores) | n=4,734 benign / 5,364 malicious — identical to the benchmark's known class counts |
| **Calibration** (`fig_v25b_calibration`) | Reliability curve + confidence histogram underneath (two-panel, sklearn-style) + in-plot ECE box + perfect-calibration diagonal | ECE=0.0268 at the deployed temperature (T=3.18) — matches the previously-computed value exactly |
| **Progressive layer contribution** (`fig_v25b_progressive`, re-added to the manuscript) | Bar chart with real per-configuration F1, grey bars explicitly marked "structural zero" (not fabricated intermediate values) for the three configurations v2.5b cannot exercise, blue/green for the three that carry information | F1 values (0, 0, 0, 0.877, 0.873, 0.877) — identical to Table V's six rows |
| **Attack-family heatmap** (`fig_v25b_heatmap`) | Palette unified to Blues (was Greys, inconsistent with the confusion matrix) — style-only change | Unchanged data, same per-family recall values as before |
| **ITE-Bench attack coverage** (`fig_ite_coverage`, new, added to manuscript) | Small 3x3 heatmap transcribing Table IV's exact published values, annotated cells, Blues palette | 1.000/1.000/1.000, 0.143/1.000/1.000, 0.000/0.000/1.000 — verbatim from Table IV, no new computation |
| **Per-stage latency** (`fig_latency_breakdown_final`) | Restyled log-scale horizontal bars, value labels added, B3's bar highlighted in red as the bottleneck | Same 8 real per-stage millisecond values already published in the manuscript text (PKI 0.001ms ... B3 80.20ms) |
| **Latency timeline** (`fig_v25b_latency_timeline`, built, not embedded — see below) | Rolling mean + raw per-message scatter (alpha 0.18) + 100ms ETSI threshold line | Real per-message data from `deployment_eval/results/deployment_eval_results.json` (n=2,000); computed mean (81.23ms) verified to match the manuscript's published mean (81.2ms) before being trusted |

## New figure built but NOT embedded in the manuscript, and why

`fig_v25b_latency_timeline.pdf` — a genuinely new, real-data figure (per-message latency over the SUMO replay, not derivable from any figure already in the paper). Not added to the main text this pass, to avoid growing the paper past a reasonable figure budget when `fig_latency_breakdown_final` (the per-stage cost breakdown, restyled) already answers "why is latency what it is" and the manuscript text already states the aggregate mean/p50/p95/p99. It is available in `figures_generated/` for an appendix or supplementary submission, and can be embedded on request.

## What was requested but not built, with reasons

- **"Trust evolution" plot (message index vs. trust score, green/yellow/red bands)**: the only per-message dataset with a sequence of real decisions (`deployment_eval_results.json`) records the categorical decision (Accept/Caution/Reject) per message, **not** a continuous numeric trust score. Building the requested continuous-score plot would require either (a) fabricating interpolated scores between the three categorical levels, or (b) re-running the pipeline to re-capture $T_{Decision}$ per message — both excluded by this pass's explicit "do not fabricate, do not rerun experiments" instructions. Not built, for this reason, rather than approximated.
- **Full attack-coverage matrix spanning PKI/B1/B2/CP/B3/Fusion across a single unified attack-family list**: v2.5b and ITE-Bench use different attack-family taxonomies (v2.5b's are semantic-manipulation-specific; ITE-Bench's are grouped by communication/behavioral/semantic class). Merging them into one matrix would require inventing a shared family taxonomy not present in either dataset — not done. The real, available version of this request (ITE-Bench's 3-class x 3-config coverage, which *does* have a consistent taxonomy) was built instead (`fig_ite_coverage`).
- **End-to-end trust-pipeline illustration (single message flowing PKI→B1→...→Fusion with the score changing at each stage)**: this already exists as a real, verified content item — the Appendix's Worked Fusion Example reports exactly this (B1/MBD/B2/B3's real outputs and the real mass/pignistic-score computation for one message), and Fig. 2 (`fig_whyfail`, already redesigned for spacing in a prior pass) visualizes the two-branch version of it. A third, redundant visual of the same message was not built, consistent with this pass's own "avoid duplicate" instruction and the earlier pass's figure-count-reduction work.
- **Violin/ridge-density alternative to the score-distribution KDE**: the histogram+KDE version was judged sufficient and already satisfies the request's own "Option 1" style; building a second redundant view of the identical scores was not done for the same avoid-duplication reason.

## Confirmation: no numerical result changed

Every regenerated figure's underlying numbers were checked against an existing, already-published value in the manuscript (table row, in-text statistic, or prior figure caption) before being accepted — listed in the "Verification" column above. Two figures (progressive layer contribution, ITE coverage) are new to the main text, but both plot exclusively values already published in Table V and Table IV respectively; no new experiment was run to produce them.
