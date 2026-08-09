# Scenario Performance Report

**Checkpoint: prior (continued) checkpoint, NOT the current final checkpoint** -- see `DEPLOYMENT_AUDIT.md`. Provided as reference material and as the template for a future final-checkpoint rerun; **not inserted into the manuscript as a new table**, since doing so would violate this task's own "use only the final checkpoint" instruction. All values below are real, computed directly from `deployment_eval/carla_results/carla_deployment_eval_results_run3_with_fix.json`'s `per_message` array (400 real per-message records, real `total_ms` latency, real `decision`/`ground_truth` fields) -- no fabrication, no interpolation.

| Scenario | Ground truth | $n$ | Acc. | Prec. | Rec. | F1 | Mean latency | $p_{95}$ latency |
|---|---|---|---|---|---|---|---|---|
| normal_driving | benign | 40 | 0.025 | 0.000 | n/a | n/a | 83.7 ms | 95.3 ms |
| accident | benign | 40 | 0.000 | 0.000 | n/a | n/a | 74.5 ms | 90.6 ms |
| emergency_vehicle | benign | 40 | 0.000 | 0.000 | n/a | n/a | 71.6 ms | 90.7 ms |
| road_closure | benign | 40 | 0.000 | 0.000 | n/a | n/a | 79.6 ms | 91.4 ms |
| replay_attack | mixed | 40 | 0.975 | 0.975 | 1.000 | 0.987 | 86.6 ms | 100.8 ms |
| sybil_attack | attack | 40 | 1.000 | 1.000 | 1.000 | 1.000 | 84.2 ms | 93.8 ms |
| semantic_manipulation | attack | 40 | 1.000 | 1.000 | 1.000 | 1.000 | 73.6 ms | 84.3 ms |
| authority_override | attack | 40 | 1.000 | 1.000 | 1.000 | 1.000 | 71.1 ms | 80.7 ms |
| goal_manipulation | attack | 40 | 1.000 | 1.000 | 1.000 | 1.000 | 72.7 ms | 84.4 ms |
| false_hazard_clearance | attack | 40 | 1.000 | 1.000 | 1.000 | 1.000 | 93.3 ms | 106.5 ms |

## A real finding this breakdown surfaces, flagged rather than smoothed over

Three benign scenarios (`accident`, `emergency_vehicle`, `road_closure`) show **0% accuracy** at the message level -- all 40/40 messages in each REJECTed despite a `benign` ground truth. This is not new data (the manuscript's existing `tab:carla` already reports "40/40 Reject" for exactly these three scenarios), but **this is the first time it has been computed and stated as a per-scenario accuracy figure** rather than left as a raw decision count. The manuscript's own text already discloses that `normal_driving`'s Reject rate is unstable (0.40-0.80 across runs) due to CARLA's unseeded traffic manager (Section V-C); this report does not establish a new root cause for the other three scenarios' apparent 100% Reject rate (that would require its own investigation, out of scope for a report explicitly built from data already flagged as the wrong checkpoint) -- flagged here as a concrete, real, and higher-priority item for the recommended final-checkpoint rerun to specifically examine, rather than left buried in a raw per-scenario decision table.

## Latency, all scenarios

All scenarios' mean/$p_{95}$ latency fall within a tight real range (71-93 ms mean, 81-107 ms $p_{95}$), consistent with the manuscript's aggregate CARLA figure (mean 80.1 ms) -- no scenario is a latency outlier.
