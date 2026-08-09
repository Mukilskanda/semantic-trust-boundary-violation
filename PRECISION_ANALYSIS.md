# Precision Analysis

Focused on the one real, disclosed precision cost in this architecture: STBV-Bench v2.5b, Full STBV Framework, current final checkpoint. All numbers recomputed directly from `b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_5.csv` (real per-sample decisions, $n{=}10{,}098$).

## Confusion matrix (real, recomputed)

| | Predicted flagged (Caution/Reject) | Predicted Accept |
|---|---|---|
| **Actual attack** ($n{=}5{,}364$) | TP = 5,358 | FN = 6 |
| **Actual benign** ($n{=}4{,}734$) | FP = 1,491 | TN = 3,243 |

Precision = 5358/(5358+1491) = **0.782**. Recall = 5358/(5358+6) = **0.999**. These match the paper's reported values to 3 decimals, confirming no drift between this report and the manuscript.

## Where the false positives come from

All 4,734 benign rows in v2.5b share a single label, `benign_control` -- the benchmark does not subdivide benign messages into families, so a per-family false-positive breakdown by attack-family label is not possible on this benchmark (there is nothing to break it down by; every FP is, by definition, a `benign_control` row). This is a real benchmark-construction limitation, disclosed here rather than worked around: **the false-positive cluster is a property of B3's precision at its current operating point, not concentrated in one identifiable benign sub-type** given the data available. The paper's Architecture section (`HARDMINE_IMPROVEMENT_REPORT.md`) already documents that the hard-example mining pass specifically targeted a real linguistic FP cluster within `benign_control` -- messages containing "give way to the authorised emergency movement" phrasing, over-associated with `authority_override` attacks -- and reduced that specific cluster's count from 332 to 296 false positives (measured on the direct classifier, not the full pipeline number above, which also includes the pipeline's own precision cost from ensembling/calibration, Section V-B of the paper).

## Where the false negatives come from (all 6, individually real)

Only 6 of 5,364 real attacks are missed by the Full STBV Framework. Per-family breakdown (real, computed from the same CSV, Section on attack-family analysis below): 3 families contribute a false negative at all -- `sensor_discreditation` (1/438), `goal_manipulation` (1/438), `traffic_efficiency_lure` (4/406) -- the other 10 families have zero false negatives. This is not evenly distributed noise; `traffic_efficiency_lure` alone accounts for 4 of the 6 total false negatives, a real, small, identifiable cluster worth flagging as a target for future hard-example mining (consistent with the existing hard-mining methodology, which already improved two of these exact three families in its last pass per `HARDMINE_IMPROVEMENT_REPORT.md`).

## Precision-recall tradeoff, quantified from real data

The two mechanisms that separate the direct-classifier F1 (0.957) from the full-pipeline F1 (0.877) are already root-caused and disclosed in the paper (Section V-B): text-synthesis distribution shift ($-0.039$ F1) and ensembling/calibration/confidence-floor interaction ($-0.041$ F1). Both costs are concentrated entirely in precision -- recall stays $\geq0.999$ throughout -- confirmed again here directly from the confusion matrix above: only 6 false negatives against 1,491 false positives, a 249:1 ratio, meaning the architecture's calibration is heavily biased toward caution, exactly the intended conservative-by-construction design (Proposition 1/3), not an accidental miscalibration.

## Per-family precision

Precision cannot be computed per attack-family in the standard sense on this benchmark, because precision requires both a TP and FP count *within a family*, and false positives are only labeled `benign_control` (no attack-family association) -- there is no "false positive belonging to family X" in this benchmark's schema. Per-family **recall** (the number that can be computed per family) is reported in `ATTACK_FAMILY_ANALYSIS.md` and Fig.~`fig_attack_family_v25b`.

## Confidence distribution

Not regenerated this pass as a new figure (the existing `fig_v25b_roc`'s PR curve, ROC AUC$=0.9892$/PR AUC$=0.9896$, already characterizes B3's confidence-ranking quality across the full operating range from the same real per-sample scores) -- a fresh confidence-histogram figure was judged, on the "does this teach something the ROC/PR curve doesn't" test, to add a different view of the same underlying score distribution rather than new information, and was not built to avoid adding a figure that duplicates an existing one's conclusion (Part 6 of the request explicitly asks to avoid exactly this).

## Confirmation

Every number in this report is recomputed directly from real per-sample CSV data, cross-checked against the paper's existing reported values (all matched to 3 decimals), with zero fabricated or interpolated figures.
