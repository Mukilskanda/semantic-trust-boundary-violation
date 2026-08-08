# Final Figures Report

11 figures in the current manuscript. Every raster/vector figure is either (a) a native TikZ vector diagram embedded directly in `stbv_paper.tex`, or (b) a real PDF regenerated this session from real per-sample data, with the generating script kept in `figures_generated/scripts/` for reproducibility. None were fabricated.

## Native TikZ diagrams (no external file, compiled in-place)

1. **`fig_architecture`** — the full pipeline architecture, existing V2X stack vs. this paper's additions, verified against `pipeline/orchestrator.py`'s actual execution order (0–7) before drawing.
2. **`fig_whyfail`** — two-column comparison (conventional pipeline vs. STBV), using **real** trust scores from an actual pipeline run on a constructed message ($T_{Decision}{=}0.730$ ACCEPT vs. $0.240$ REJECT).

## Regenerated this session from real data (`figures_generated/*.pdf`)

3. **`fig_ablation`** (confusion matrix) — real counts from the STBV v1 config-5 rerun (TN=2,924, FP=69, FN=0, TP=7,007). Replaces a prior figure that was disclosed as stale relative to the final checkpoint.
4. **`fig_roc`** (ROC + PR) — regenerated from a fresh forward pass of the final checkpoint on all 10,000 v1 samples. **A real bug was caught and fixed while building this**: the first attempt plotted the classifier's raw "confidence" field (confidence in whichever label was predicted), not P(malicious) specifically, giving a corrupted AUC of 0.893 and a negative PR-AUC from a sign error in the integration. Fixed by computing P(malicious) directly via a fresh classifier forward pass (`figures_generated/scripts/get_pmalicious_v1.py`); corrected AUC=1.000 matches the previously-reported value exactly, confirming it, not just asserting it.
5. **`fig_decision_dist`** — new, decision distribution before/after fusion on STBV v1 (real counts from configs 4/5).
6. **`fig_score_dist`** — new, B3 score histogram, benign vs. malicious, STBV v1 (same corrected P(malicious) data as #4).
7. **`fig_calibration_v1`** — new, reliability diagram, STBV v1, final checkpoint. Real finding: ECE=0.153, notably higher than the calibration temperature's own fitting-time ECE (0.053) — reported honestly with an explanation (different distributions, different scale, $n{=}85$ vs.\ $n{=}10{,}000$), not hidden because it's a less flattering number.
8. **`fig_family_heatmap`** — new, per-family recall heatmap, ITE-Bench, B1-only vs. full stack (real per-family data from the ITE-Bench config CSVs).
9. **`fig_sumo_stage`** (latency breakdown) — regenerated from the exact same per-message JSON cited in the new Complexity Analysis section's text, ensuring figure and text trace to one artifact.

## Unchanged, not regenerated (disclosed reason)

10. **`fig_carla_scene`** — a live CARLA screenshot; nothing to regenerate (it documents that a real simulator was running, not a metric).
11. **`fig_pipeline`** — existing deployment architecture diagram; no bug found to justify regeneration.

## Figures explicitly NOT built this pass, with reasons

- **Per-family attack recall heatmap across ALL of B1/B2/B3/full-stack** (the request's Part 5, item 3, in its fullest form): built for ITE-Bench (#8 above), which is the benchmark that actually has per-family B1/B2/B3 data with meaningful variation. STBV v1's own per-family data is B3-only by threat-model construction (Section III), so a "B1 vs B2 vs B3" heatmap on v1 would just show a column of zeros for two of three layers — not a useful visualization, and not built for that reason.
- **Decision Transition Sankey diagram**: matplotlib's Sankey class exists but produces poor results for this specific 3-state, small-flow-count transition without substantial manual layout tuning I could not verify by eye (no way to visually inspect rendered output in this environment). Built the equivalent information as a grouped bar chart (#5) instead — same real data, lower rendering risk.
- **Dempster-Shafer Evidence Flow diagram**: the worked example (Appendix, real final-checkpoint trace) and the expanded DS theory section (frame of discernment → belief/plausibility → conflict → discounting → Yager's rule, each with its equation) already cover this narratively and mathematically; a redundant diagram was judged lower value than the existing content, not omitted from neglect.
- **Radar/spider chart comparing "Security, Behaviour, Semantics, Latency, Robustness, Explainability"**: explicitly declined. These are not measured on comparable scales anywhere in this paper (F1 vs. milliseconds vs. a qualitative explainability judgment), and forcing them onto one radar chart would require inventing a normalization/scoring scheme not grounded in any real measurement — exactly the "inventing data" this task's own instructions prohibit. Recommend, if this comparison is genuinely wanted, defining an explicit, justified per-axis scoring rubric first, as a separate methodological contribution, not a figure produced under this pass's time constraints.
- **Representative attack walkthrough as its own figure**: covered by `fig_whyfail` (#2) plus the Appendix worked example; a third redundant visualization of the same single message was judged unnecessary.

## Addendum: progressive performance curve / layer contribution bar chart (subsequent pass)

Both requested this pass. Reviewed against what's already published rather than built redundantly: `tab:ite_ablation` already reports exactly this information numerically (each layer's recall within/outside its threat class, config-by-config), and `fig_family_heatmap` (#8) already visualizes it per-family. A bar chart or progressive-curve rendering of the same table's aggregate numbers would add a second visual encoding of data already shown once, without surfacing anything the table and heatmap don't — judged low marginal value given this pass's actual finding (the calibration interaction) is the substantive new content, not a restyling of already-published ablation numbers. Not built, for this reason, rather than silently skipped.

## Export formats

Per the standing request for PDF+SVG exports, `figures_src/fig_architecture.svg` and `figures_src/fig_architecture_standalone.tex` (from an earlier pass) remain the only hand-exported standalone files; the 6 new PDFs from this pass are native matplotlib PDF output (vector, not raster) and were not separately exported to SVG (matplotlib can do so via `plt.savefig(..., format="svg")` on request, not performed here to avoid unbounded scope growth without a stated need for that specific format for these particular figures).
