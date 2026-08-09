# Final Consistency Audit

This supersedes the prior version of this file (from an earlier pass, checkpoint-identity focused) with the consistency check for this pass's evaluation redesign (unified ablation table, attack-family figure). The prior pass's checkpoint-identity findings still hold and are not re-litigated here.

## Cross-reference / label integrity

`scratch_latex_audit.py`, final run this pass: **0 broken references, 0 duplicate labels, 0 missing citations, 0 orphan bibitems.** Figure count 7, table count 5. Three labels (`sec:novelty`, `sec:conclusion`, `sec:related`) are unreferenced by any `\ref` (informational only, pre-existing from a prior pass, not introduced this pass) -- harmless, not an error.

## Numerical consistency, spot-checked

- `tab:ablation`'s B3-only/Full-STBV-v2.5b rows (0.852/0.782/0.999/0.877/0.315) match `tab:v25b`-adjacent prose ("Full-stack F1 on v2.5b is 0.877...") and `fig_v25b_confusion_grid`'s caption (FN=6, FP=1,491 of $n{=}10{,}098$: $1{,}491/4{,}734{=}0.315$ FPR, $5{,}358/5{,}364{=}0.999$ recall) -- all three sources agree to 3 decimals, verified by direct arithmetic, not by assuming consistency.
- `tab:ablation`'s Full-STBV-ITE-Bench row (0.913/0.896/1.000/0.945/0.349) is a new number this pass; cross-checked against the existing McNemar statistics already in Section V-A prose (3,885/0 discordant favoring the full stack vs.\ B3-alone) -- consistent direction (full stack strictly dominates), no contradiction.
- Checkpoint-progression numbers in `tab:v25b` (untuned 0.545 F1 $\to$ hard-mined 0.957 F1) are unchanged from before this pass and were not recomputed this pass (no reason to -- they are direct-classifier numbers, unaffected by the pipeline-ablation table redesign); flagged here as intentionally not re-verified, not silently assumed correct.
- Fig.~`fig_attack_family_v25b`'s false-negative counts (1, 1, 4 across three families, summing to 6) match `fig_v25b_confusion_grid`'s caption FN=6 exactly -- the same 6 real messages, counted two different ways, agree.

## Stale-value check

Grepped the full manuscript for the removed table label (`tab:ite_ablation`) and the removed lower-half of the old `tab:v25b` -- zero remaining references (confirmed by the clean audit run above). The old table's "not meaningfully evaluable" placeholder text is superseded by `tab:ablation`'s footnote, which now explains *why* (B1 hard-wired into `ISCEPipeline`, no `enable_b1` flag) rather than only stating the fact.

## What this audit did NOT re-verify (explicitly disclosed)

- The CARLA and SUMO deployment sections' real numbers (Section V-C: 80.1ms/10.45msg/s CARLA, 81.2ms/12.3msg/s SUMO) were not rerun this pass and are unchanged -- this pass's scope was the ablation table and attack-family figures, not the live-deployment sections, and there is no evidence those numbers are stale (the same final checkpoint this pass's ITE-Bench/v2.5b reruns used is the checkpoint the existing CARLA/SUMO numbers were already measured against).
- Discussion and Conclusion prose was checked for any reference to the old table structure (none found) but not rewritten beyond the cross-reference fixes already covered above, since none of their claims depended on the specific rows/columns changed this pass.
- The CARLA per-message latency timeline and trust-evolution figures requested in Part 5/7 were not producible from data currently in the repository (see `FINAL_FIGURE_REPORT.md`) -- flagged there, not silently omitted.

## Conclusion

No stale value, contradictory claim, or broken cross-reference remains as a result of this pass's table redesign and figure addition. Every real number newly reported this pass traces to a specific, reproducible script and real per-sample CSV, documented in `FINAL_ABLATION_REPORT.md`.
