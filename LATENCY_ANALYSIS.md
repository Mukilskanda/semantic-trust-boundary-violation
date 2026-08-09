# Latency Analysis

**Update: CARLA has since been rerun against the final checkpoint (see `DEPLOYMENT_AUDIT.md`'s "Resolution" section), and a real CARLA latency figure (`fig_carla_deployment_summary`, script: `figures_generated/scripts/generate_carla_deployment_summary.py`) is now in the manuscript (Section V-C), built from that rerun's real per-message data.** The analysis below, based on the prior checkpoint's data, is left intact as the historical record that motivated the rerun; its numbers are superseded in the manuscript by the final-checkpoint figure, not by anything in this file.

**Original scope (prior checkpoint, historical):** real, message-by-message latency data (400 real messages, `deployment_eval/carla_results/carla_deployment_eval_results_run3_with_fix.json`), provided as reference material for a future final-checkpoint rerun.

## Real statistics (no smoothing of the reported numbers, only a rolling-mean overlay on the plot)

- Mean: 80.1 ms (matches the manuscript's existing aggregate figure exactly, confirming this is the same underlying dataset the manuscript already cites, just now broken out per-message)
- $p_{95}$: 97.2 ms
- $p_{99}$: 110.8 ms
- Max: 119.3 ms -- a real spike, not removed or smoothed; it occurs in `normal_driving` (message index 0, the very first message, consistent with one-time model/CUDA warm-up cost rather than a recurring bottleneck, though this is stated as an observation, not re-verified via a repeat run)
- No message exceeds the ETSI 100 ms budget by more than 20 ms; the large majority (see figure) sit comfortably under it.

## Figure

`deployment_eval/carla_results/REFERENCE_latency_timeline_prior_checkpoint.png` -- message index (x) vs.\ real end-to-end latency (y), a 15-message rolling mean overlay, the ETSI 100 ms line, mean and $p_{95}$ reference lines, and scenario boundaries (every 40 messages, matching the 10-scenario/40-message-each structure). Spikes are plotted as-measured, not smoothed away, per this task's explicit instruction.

## Relationship to the manuscript's existing latency figure

The manuscript's `fig_sumo_stage` already reports a real per-message latency timeline, but for the **SUMO** trace, not CARLA -- CARLA's existing manuscript reporting (Section V-C) is aggregate-only (mean/$p_{95}$/$p_{99}$/throughput in text, no per-message plot). This report's figure is the CARLA-side per-message equivalent, using the same real data source the manuscript's aggregate numbers are already drawn from -- it does not introduce a new experiment, only a finer-grained view of an existing one. Recommended for inclusion in the manuscript once regenerated against the final checkpoint (Future Work, already updated in this pass to list this rerun explicitly).

## Trust-score evolution (Step 7)

The same `per_message` records **do** contain a continuous field, `trust_score` (the real pignistic score, e.g.\ `0.9744` for the first message) -- so, unlike the CARLA trust-evolution figure flagged as infeasible in the immediately preceding evaluation-redesign pass (`FINAL_FIGURE_REPORT.md`), a genuine trust-score-vs-message-index plot **is** producible from this run's data. Not built as a manuscript figure this pass, for the same checkpoint reason as everything else in this report -- but this corrects the earlier pass's finding: the limitation was that the *specific* CSV files used in that pass lacked continuous scores, not that no CARLA run in the repository has them. Flagged for the final-checkpoint rerun to capture the same `trust_score` field, which it will if the rerun uses the same instrumented harness (`deployment_eval/run_carla_evaluation.py`).
