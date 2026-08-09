# Figure Final Justification Report

Scientifically frozen pass: no experiment rerun, no metric changed, no value fabricated. This report justifies every figure remaining in the manuscript after this pass's two changes (removed: the structural-zero progressive F1 bar chart; added: a new conceptual schematic).

## Changes made this pass

1. **Removed** `fig_v25b_progressive` (F1 by configuration, three structural-zero bars) — per explicit instruction. Its one piece of real information (F1 jumps discontinuously once B3 is enabled) is already stated in prose and is fully recoverable from Table V; the bar chart added a visual of a mostly-empty plot, which is exactly the "metric figure repeating a table" pattern this pass asked to eliminate.
2. **Added** `fig_boundary_schematic` — a new, general, message-independent conceptual diagram (two lanes: Traditional pipeline's identity/behavior/corroboration checks all passing while content is "never asked," vs. STBV's identical checks plus a content stage that gets "asked") placed at the very start of the Trust Boundary Analysis section, before the concrete worked example. This is deliberately distinct from `fig_whyfail` (which uses one real message and real $T_{Decision}$ numbers) — the new figure teaches the *mechanism*, `fig_whyfail` proves it happened on a real input. Net figure count unchanged (one removed, one added).

## Every remaining figure, and why it earns its place

| Figure | What it teaches that text/tables don't | Category |
|---|---|---|
| `fig_boundary_schematic` (new) | The core mechanism, in one glance, before any numbers appear — a reader who looks at only this figure and nothing else understands the paper's central idea | **Explanatory** |
| `fig_architecture` | The full 8-stage pipeline as a single object, with existing-vs-added stages visually distinguished (fill/border) — no table conveys "structure," only tables of numbers | **Explanatory** |
| `fig_whyfail` (flagship contribution map) | Proves the schematic's claim on one real message with real trust scores (0.730 ACCEPT vs. 0.240 REJECT), now annotated with exactly where trust is validated | **Explanatory + evidentiary** |
| `fig_layer_responsibility` | Answers "why does each layer exist" directly, at a glance, across 4 attack categories x 5 layers — no single table in the paper presents this cross-cut view | **Explanatory** |
| `fig_ite_coverage` | The defense-in-depth pattern (each layer completing exactly one row) is visually instantaneous here; Table IV requires reading 9 cells and noticing the diagonal pattern yourself | **Explanatory, compact** |
| `fig_v25b_confusion_grid` | Shows the actual error distribution's shape (where mass concentrates: FN is negligible, FP is the entire cost) — Table V's single F1 number cannot convey this | **Metric, non-redundant** (distributional information a scalar cannot carry) |
| `fig_v25b_heatmap` | Per-family recall x configuration — no table in the paper reports this at the family level; Table V only has aggregate rows | **Metric, non-redundant** |
| `fig_v25b_roc` | The full precision/recall trade-off curve, not just the single operating point Table VI reports | **Metric, non-redundant** |
| `fig_v25b_score_dist` | The shape of class separation (unimodal vs. bimodal, overlap region) — invisible in any summary statistic | **Metric, non-redundant** |
| `fig_v25b_calibration` | Whether confidence is trustworthy as a number, bin by bin — the single ECE scalar in text cannot show *which* confidence range is miscalibrated | **Metric, non-redundant** |
| `fig_deployment_summary` | Three real-world engineering facts in one glance (temporal latency behavior, per-stage attribution, throughput headroom) that would otherwise require three separate figures or none at all | **Explanatory + metric, consolidated** |
| `fig_decision_dist` (v1, historical) | The sole visual evidence anywhere in the paper of fusion's escalation-only behavior on a fixed-sample-set benchmark — the equivalent v2.5b claim exists only as a McNemar statistic in prose, with no figure | **Explanatory, non-redundant** |
| `fig_ablation` (v1, historical, consolidated confusion+ROC/PR) | The explicit "before" half of the prior-checkpoint vs. current-checkpoint improvement story; removing it would leave the checkpoint-improvement narrative with only text, no visual | **Metric, historical, non-redundant given its comparative role** |
| `fig_family_heatmap` (ITE-Bench per-family) | The only figure showing per-family (not per-class) recall for B1/B2's real attacks — finer-grained than Table IV | **Metric, non-redundant** |

## Figures considered for removal and kept, with reason

- **`fig_v25b_confusion_grid`, `fig_v25b_roc`, `fig_v25b_score_dist`, `fig_v25b_calibration`** were reviewed against "does this merely repeat a table." None do: each conveys a *shape* (error distribution, trade-off curve, class-separation shape, per-bin calibration error) that the corresponding table's scalar summary (F1, ROC AUC, ECE) cannot represent. These are retained as legitimate metric figures, not because "metric figures are allowed" generically, but because each one specifically fails the "redundant with a table" test when checked individually.
- **`fig_ablation` and `fig_decision_dist`** (v1, historical) were reviewed against "does this teach something new." Both pass: they are currently the *only* visual evidence for their respective claims (checkpoint-improvement comparison; escalation-only fusion mechanism) — v2.5b's equivalents exist only as text/statistics, not figures, so removing the v1 figures would leave those two claims with zero visual support anywhere in the paper.

## Net effect

Figure count: unchanged (13 environments before this pass's edit → 12 after removal → 13 after the new schematic; `fig_whyfail`, a `figure*`, is additionally present and unaffected by the count, as before). Every remaining figure was checked individually against the "does it teach something a table doesn't" test in the table above — none survive by default; each has a stated, specific reason.
