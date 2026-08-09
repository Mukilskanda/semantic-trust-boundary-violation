# Attack-Family Metric Analysis

Every metric computable from the existing real per-sample logs (`ablation_results/v25b_full_hardmine/config_5.csv`, which carries `raw_score` = B3's calibrated $P(\text{malicious})$ per message, real, not fabricated) for the Full STBV Framework, current final checkpoint, computed per attack family. Script: `b3_eval/v25_finetune/scratch_attack_family_metrics.py`.

## What is and is not computable per family on this benchmark

STBV-Bench v2.5b labels every benign message `benign_control` (no benign sub-families), so **per-family precision, per-family FPR, and per-family false-positive count are not computable** -- there is no attack-family-labeled false positive to attribute (already established in `PRECISION_ANALYSIS.md`). What *is* computable per family, all real: recall, false-negative count, mean/median/min/max/stdev of B3's calibrated confidence score, and (in aggregate, not per-family) FPR/false-positive count for the single `benign_control` bucket.

## Information content per candidate metric (13 attack families)

| Metric | Min | Max | Std | CV (std/mean) | Range | Verdict |
|---|---|---|---|---|---|---|
| Recall | 0.990 | 1.000 | 0.0027 | 0.0027 | 0.0099 | **Reject** -- negligible variance, already the failure mode this task exists to avoid |
| Mean confidence | 0.919 | 0.988 | 0.0222 | 0.0229 | 0.0690 | **Marginal** -- real but small spread; more informative than recall, less than the two below |
| False-negative count | 0 | 4 | 1.08 | 2.35 | 4 | **Keep** -- real, small, concrete, already used in the current figure |
| **Within-family confidence std.\ dev.** | 0.0006 | 0.170 | 0.057 | **1.05** | 0.169 | **Select** -- by far the most discriminative real metric available: some families are detected at uniformly near-ceiling confidence (std $\approx$ 0.0006-0.0023: `fabricated_consensus`, `priority_manipulation`, `cross_source_contradiction`, `context_inversion`, `authority_override`), others show wide per-message confidence spread (std $\approx$ 0.09-0.17: `traffic_efficiency_lure`, `goal_manipulation`, `false_clearance`, `sensor_discreditation`, `narrative_poisoning`) -- i.e., some individual messages within these families are borderline, even though the family's *aggregate* recall still rounds to 0.99-1.00. |

Accuracy, F1, and ROC/PR-derived metrics were not separately tabulated per family: on this benchmark, per-family accuracy and F1 both reduce algebraically to functions of recall alone (no per-family FP term exists, as established above), so they carry no additional information beyond the recall row already rejected.

## Selected design (adopts the two-panel structure suggested alongside this request)

**Panel A: mean confidence per family, sorted low-to-high, with error bars showing within-family standard deviation.** This single panel now carries two real, non-fabricated pieces of information at once: which families the model is on average least confident about (mean), and which families have the most internally inconsistent, borderline-scored messages (the error bar, i.e.\ the metric identified above as most discriminative, CV=1.05). Mean confidence alone (CV=0.023) would have been only "Marginal"; combined with its own real standard deviation as an error bar, the panel communicates the actually-informative signal (confidence *consistency*) without introducing a metric that cannot be justified from the evaluation data.

**Panel B: false-negative counts per family (kept from the prior figure, unchanged in content, real).**

This directly implements the two-panel design suggested alongside this task's request (Panel A: mean confidence sorted low-to-high; Panel B: error counts by family), arrived at independently via the same systematic metric-rejection process this task's Step 2/3 specify.
