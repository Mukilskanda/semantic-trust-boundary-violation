# Final Numerical Consistency Check (this pass, read-through only unless noted)

Read Abstract -> Introduction -> Results -> Tables -> Figures -> Discussion ->
Conclusion of the current `stbv_paper.tex` in one pass. Findings:

- v2.5b F1 0.957 / ROC-AUC 0.989: consistent across Abstract, Table III, and
  the Key Takeaway paragraph. **Re-derived from raw JSON in the continuation
  pass** (`b3_eval/v25_finetune/results/hardmine_v25b_eval.json`,
  `hardmine_checkpoint` key: f1=0.9574, roc_auc=0.9892 — exact match to
  three-decimal rounding).
- Table IV (v2.5b pipeline, F1 0.877/precision 0.782/recall 0.999/FPR 0.315)
  and Table II (ITE-Bench, all four reported rows) **re-derived exactly from
  raw per-message CSVs** in the continuation pass — zero discrepancies. See
  `FINAL_PAPER_READINESS_REPORT.md` Section E for the full table-by-table
  comparison.
- Attack-family figure (Fig. `fig_attack_family_v25b`) per-category
  below-threshold counts (0/817, 22/1706, 47/1596, 35/1245) **re-derived
  exactly from `config_5.csv`** in the continuation pass — exact match.
- New baseline table (`tab:baseline`, added this continuation): keyword
  0.282 F1, TF-IDF+LogReg 1.000 F1 (caveated, in-domain), B3 0.957,
  Full-STBV 0.877 — all four values consistent with the source computation
  in `BASELINE_EVALUATION_REPORT.md` and with the already-verified B3/Full-STBV
  numbers above (no new B3 number introduced, only two new baseline rows).
- Full-STBV v2.5b F1 0.877 vs. ITE-Bench Full-STBV F1 0.945: manuscript
  explicitly and correctly labels these as two different benchmarks on the
  same checkpoint (line ~298) — no contradiction, this is handled correctly
  already.
- CARLA latency: Abstract and Results both say 76.6 ms for the final
  checkpoint; 80.1 ms appears only as an explicit "prior checkpoint"
  comparison, never as a competing headline — **verified against raw JSON in
  this pass** (mean recomputed = 76.61 ms, matches).
- SUMO latency (81.2 ms) is explicitly labeled "prior (continued) checkpoint"
  in the text — correctly distinguished from the CARLA final-checkpoint
  number, not conflated as the same experiment.
- VeReMi recall figures (0.987 vehicle-level headline in Abstract) match
  Table V's DataReplay vehicle-level recall 0.987 — consistent by inspection.
- CARLA scenario table (Table VI): **verified exactly against raw JSON** in
  this pass (see FINAL_PAPER_READINESS_REPORT.md item J).
- Baseline results: **now present in the manuscript body** (`tab:baseline`,
  Section V-B), evaluated directly on v2.5b (not the v1 baseline in
  `BASELINE_COMPARISON.md`, which remains correctly excluded from the paper
  as a different-benchmark result). See `BASELINE_EVALUATION_REPORT.md`.

No cross-section numeric contradiction was found. As of the continuation
pass, this now includes independent re-derivation from raw data for: CARLA
Table VI + latency, v2.5b Table III (final two checkpoint rows) and Table IV
(all three rows), ITE-Bench Table II (all four reported rows), the
attack-family figure's per-category counts, and the new baseline table.
**Still not independently re-derived from raw logs**: VeReMi (Table V), SUMO
replay, adaptive-attack evaluation, and Table III's two oldest checkpoint
rows (untuned base, mixed corpus pre-continuation) — these rely on internal
textual consistency plus this repo's pre-existing audit trail from prior
sessions, not a fresh raw-file check in this pass.
