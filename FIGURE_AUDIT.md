# Figure Audit (Task 1)

Every figure in the manuscript at the start of this pass, with a keep/improve/merge/replace/move/remove decision and reason.

| Figure | Decision | Reason |
|---|---|---|
| `fig_architecture` (TikZ, conceptual pipeline) | **Keep, unchanged** | Native vector diagram, not data-dependent, no defect found |
| `fig_whyfail` (TikZ, page-8 comparison) | **Improve** | Already the flagship contribution-map candidate (Task 4); enhanced with explicit "trust validated here" / attack-passes-undetected annotations rather than duplicated as a third architecture diagram |
| `fig_decision_dist` (v1, prior checkpoint) | **Keep, unchanged** | Real data, architectural-validation role already labeled; no v2.5b equivalent needed (same qualitative mechanism independently confirmed in prose for v2.5b) |
| `fig_score_dist` (v2.5b, current checkpoint) | **Keep, restyled** (prior pass) | Already migrated from v1; unchanged this pass |
| `fig_calibration_v1` (v2.5b, current checkpoint) | **Keep, restyled** (prior pass) | Already migrated from v1; unchanged this pass |
| `fig_ablation` (v1, prior checkpoint, consolidated confusion+ROC/PR) | **Keep, unchanged** | Historical comparison role, already labeled |
| `fig_ite_coverage` (ITE-Bench heatmap) | **Keep, unchanged** | Added last pass, real Table IV values, no defect found |
| `fig_family_heatmap` (ITE-Bench per-family) | **Keep, unchanged** | Unique information (real per-layer detection), not duplicated elsewhere |
| `fig_v25b_confusion_grid` (v2.5b confusion matrix) | **Improve** | Redesigned with row-normalized % + count annotations, sequential Blues, per Task 2's explicit spec |
| `fig_v25b_progressive` (v2.5b F1 by configuration) | **Keep, improve styling** | Explicitly called "weak" this pass for containing structural zeros -- kept anyway because it is the paper's single clearest visual of the defining empirical signature (flat-then-jump), but the zero bars are now explicitly grey/labeled "structural" rather than looking like missing data, addressing the actual weakness (ambiguity) rather than removing real information |
| `fig_v25b_heatmap` (attack-family x config) | **Keep, restyled** | Palette unified to Blues; real per-family data unchanged |
| `fig_v25b_roc` (v2.5b ROC/PR) | **Improve** | Redesigned with in-plot AUC/AP box, thicker curve, diagonal baseline |
| `fig_latency_breakdown_final` / `fig_sumo_stage` (per-stage latency) | **Merge/Replace** | Absorbed into the new `fig_deployment_summary` 3-panel figure (Task 7); the standalone per-stage figure is still separately referenced once, early, from the Complexity Analysis section (Section IV-I), where a full deployment panel would be premature -- kept there in its restyled, single-panel form for that one earlier reference |
| `fig_carla_scene` (CARLA screenshot) | **Removed** (prior pass) | Zero quantitative content; not revisited this pass |
| `fig_pipeline` (deployment/bridge diagram) | **Removed** (prior pass) | Duplicated `fig_architecture`; not revisited this pass |

## New figures added this pass

| Figure | Task | Why |
|---|---|---|
| `fig_layer_responsibility` | Task 6 | Qualitative Strong/Moderate/Weak/Not-Exercised matrix, every cell traced to an already-published finding (ITE-Bench, v2.5b, CARLA tables) -- the single figure that most directly answers "why does each layer exist," placed in the Architecture section |
| `fig_deployment_summary` | Task 7 | 3-panel (latency timeline + per-stage breakdown + throughput vs. requirement), replacing the single-panel latency figure in the Results/SUMO section |

## Built but NOT embedded, with reason

| Figure | Why not embedded |
|---|---|
| `fig_v25b_family_bars` (per-family recall, sorted, gradient-colored) | Built per Task 5's exact spec, but every family's recall is 0.99--1.00 on the full-stack configuration -- a real, disclosed finding (this is why the paper's headline recall is 0.999), but a 13-bar chart where every bar is the same shade of green adds a full figure's worth of page space for one sentence of information ("recall is uniformly near-ceiling per family"). Judged redundant with the already-present `fig_v25b_heatmap`, which shows the identical near-ceiling pattern *and* the configuration dimension the bar chart lacks. Available in `figures_generated/` if the venue's page budget allows it. |
