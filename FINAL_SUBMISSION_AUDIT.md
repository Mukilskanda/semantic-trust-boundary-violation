# Final Submission Audit (this pass) — see FINAL_PAPER_READINESS_REPORT.md for full detail

This pass did not redo the full Phase-0/Phase-1 source-of-truth map from
scratch (that work exists across this repo's many prior audit `.md` files,
e.g. `FINAL_CONSISTENCY_AUDIT.md`, `TABLE_VALUE_AUDIT.md`,
`PIPELINE_DIFFERENCE_REPORT.md`, `BENCHMARK_AUDIT.md`). Instead this pass:

1. Read `stbv_paper.tex` in full (508 lines) and confirmed current
   title/abstract/checkpoint claims match the task's stated context
   (final checkpoint `..._hardmine_merged`, T=3.18, DeBERTa-v2, 141.9M params
   — all present verbatim in Appendix A of the current .tex).
2. Verified Table VI (`tab:carla`) and the CARLA latency headline number
   against the real per-message JSON
   (`deployment_eval/carla_results_final_checkpoint/carla_deployment_eval_results_final_checkpoint.json`)
   — exact match on scenario decision counts; latency mean matches (76.6 ms);
   p95/p99 match to ~1.5 ms (see FINAL_PAPER_READINESS_REPORT.md item E for
   the unreconciled minor discrepancy).
3. Traced and documented the CARLA benign-scenario 40/40-Reject root cause
   (see `CARLA_FALSE_POSITIVE_ROOT_CAUSE.md`) and updated the manuscript's
   Results/Limitations/Future-Work text accordingly.
4. Compiled the manuscript with real `pdflatex` (MiKTeX), twice, confirming
   9 pages, 0 errors, 0 undefined references.

Not performed in this pass (see `FINAL_PAPER_READINESS_REPORT.md` sections
E, G, L, M for the honest list): fresh baseline implementation, fresh CARLA
relaunch/multi-seed rerun, fresh re-derivation of v2.5b/ITE-Bench/VeReMi/SUMO/
adaptive-attack numbers from raw logs, theory-appendix proof sketches, full
overclaim word-sweep.
