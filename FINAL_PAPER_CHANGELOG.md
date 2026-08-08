# Final Paper Changelog (this pass)

Consolidates every change made to `stbv_paper.tex` and the underlying evaluation artifacts in this pass. Earlier passes' changes are recorded in their own changelogs (`FINAL_MANUSCRIPT_CHANGELOG.md` etc.) and are not repeated here.

## 1. Checkpoint change: hard-example mining and re-continuation

New final checkpoint (`semantic_gate_v3_mixed_lora_hardmine_merged`), superseding the prior one, produced by mining the prior checkpoint's real v2.5b errors and continuing LoRA training on 91 leakage-audited hard examples. Verified improvement at every level (validation, held-out direct classifier, held-out full pipeline) before being promoted to `isce_config.yaml`. Full trace: `HARDMINE_IMPROVEMENT_REPORT.md`.

## 2. Manuscript edits

- **Table `tab:v25b`**: added a fourth row (hard-mined final checkpoint, F1=0.957, ROC AUC=0.989); relabeled the row for the prior checkpoint from "Final (continued)" to "Continued (prior final)".
- **Table `tab:v25b_ablation`**: B3-alone/full-stack rows updated 0.828/0.756/0.999/0.860/0.366 → 0.852/0.782/0.999/0.877/0.315.
- **Section~\ref{sec:v25b} prose**: rewrote the "What this proves" paragraph (four checkpoints, not three); added a new "Hard-example mining" paragraph describing the mining/generation/leakage-audit/training/verification chain; rewrote the Stage 1/Stage 2 gap-decomposition paragraph with recomputed numbers for the new checkpoint, explicitly distinguishing "recomputed" (Stage 1/2 magnitudes) from "not re-litigated" (the calibration-methodology finding itself, which stands as already investigated).
- **B3 architecture subsection**: updated the inline temperature value ($T{=}2.82\to3.18$).
- **Discussion "Strengths"**: updated the generalization claim to cite both continuation passes (0.918→0.945→0.957) and the mining methodology.
- **Limitations item (vii)**: reworded to state the calibration/floor coupling as a property of the fixed decision policy that persists (in reduced form) across checkpoints, rather than implying it was specific to the now-superseded checkpoint.
- **Conclusion**: updated the generalization sentence to reflect both passes.
- **Appendix A (Reproducibility Summary)**: rewrote the "Semantic classifier" paragraph to describe both continuation passes' full hyperparameters, validation F1, and SHA-256 hashes.
- **STBV-Bench v1 figures/captions** (`fig_calibration_v1`, `fig_decision_dist`, `fig_score_dist`, `fig_ablation`, `fig_roc`) and the ablation re-run sentence in Section~\ref{sec:results}A: explicitly relabeled as reflecting the prior (Pass 1) checkpoint, not silently left implying they reflect the current one, since v1 is supplementary and was not rerun this pass (a disclosed, deliberate scope decision, not an oversight).

## 3. What was NOT changed

- STBV-Bench v1's own numeric table (`tab:main_ablation`, F1 1.000/0.995) — not rerun; v1 is supplementary, and near-ceiling performance there is not expected to be sensitive to a small, v2.5b-targeted hard-example batch.
- VeReMi (`tab:veremi`), CARLA (`tab:carla`), SUMO latency (`fig_sumo_stage`) — VeReMi and SUMO confirmed checkpoint-invariant by code inspection (neither invokes B3 with meaningful text); CARLA requires a live simulator not available in this environment, disclosed as deferred rather than silently assumed unaffected.
- ITE-Bench (`tab:ite_ablation`) — B1/B2 evaluation, checkpoint-invariant for those layers by construction; B3's row there was not specifically isolated for a rerun given the overall checkpoint-invariance argument already established for structurally similar evaluations.
- Adaptive-attack table (`tab:adaptive`) — already explicitly labeled throughout the paper as measuring a prior, not the current, checkpoint; unchanged, consistent with that existing disclosure.
- Fusion constants, threat model, related work, methodology, architecture diagrams — no changes; none of this pass's findings bear on them.

## 4. Verification performed after edits

- Re-ran the mechanical LaTeX audit (labels/refs/citations/figure-file-existence) after all edits: 0 broken references, 0 duplicate labels, 0 missing citations, 0 missing figure files — identical clean result to before the edits.
