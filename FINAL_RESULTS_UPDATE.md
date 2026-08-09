# Final Results Update

Summary of what changed in `stbv_paper.tex` this pass, all sourced from real, existing per-sample data (verified in `EVALUATION_AUDIT.md`), no fresh GPU inference required because final-checkpoint logs already existed for every requested configuration except the CARLA per-message timeline (see `FINAL_FIGURE_REPORT.md`).

## Table changes

- **Removed** `tab:ite_ablation` (3-column, recall-only, per-attack-class) and the "Pipeline configuration" lower half of `tab:v25b`.
- **Added** `tab:ablation` (Table*, full-width): a single, unified, cross-benchmark table -- Configuration / Threat Dimension / Benchmark / Acc / Prec / Rec / F1 / FPR / Latency -- covering all 6 requested configurations (Existing Pipeline documented as not implementable; B1 only; B1+B2; B1+B2+CP; B3 only; B1+B2+B3 no CP; Full STBV on both ITE-Bench and v2.5b), per Part 3's suggested structure.
- **`tab:v25b`** is now checkpoint-progression only (4 rows, direct classifier), no longer mixing two different kinds of comparison in one table.

## Numeric changes

**None.** Every number in the new `tab:ablation` was independently recomputed from the same real per-sample CSVs that produced the old table's numbers, and matched to 3 decimal places (confirmed in `FINAL_ABLATION_REPORT.md`). This pass added new rows (the ITE-Bench Acc/Prec/Rec/F1/FPR numbers, previously only reported as per-class recall) and a Latency column (estimated from Table `tab:complexity`'s real per-stage measurements, disclosed as such) -- it did not change any previously-reported value.

## New figure

`fig_attack_family_v25b` (Section V-B), real per-family recall + false-negative counts, replacing a prose-only "per-family recall is uniform at 0.99-1.00" sentence with a real visualization of the same, honestly near-flat, data.

## New prose

- Section V-A ("Finding" paragraph): now explicitly states CP's identical zero-contribution signature on ITE-Bench (previously only stated for v2.5b), traced to the same generator-level cause.
- Section V-B ("Full-pipeline ablation" paragraph): added the real ITE-Bench cross-benchmark confirmation (F1=0.945) alongside the existing v2.5b number (F1=0.877), and the verified-not-assumed explanation of why B3-only and Full-STBV share identical confusion counts on v2.5b (escalation-only fusion, proven via the "flagged" vs.\ "reject-only" reading distinction).
- `tab:ablation`'s footnote documents, in the paper itself (not just in a companion report), the real architectural finding that B1 cannot be disabled -- a fact a reviewer reading only the PDF can now see without needing this report.

## What did NOT change

- All six propositions, all three equations, all other figures/tables, Discussion, Conclusion: unchanged. No claim in the paper needed correcting -- this pass's real reruns/rechecks confirmed every existing number rather than contradicting any of them.
- Checkpoint identity: unchanged (still the hard-mined final checkpoint, SHA-256 recorded in Appendix A).

## Verification

`b3_eval/v25_finetune/scratch_latex_audit.py`: 0 broken references, 0 duplicate labels, all citations resolve, figure count 7, table count 5 (one `table*`), after all edits.
