# Final Results Structure

Current, authoritative map of the Results section after Tasks 10-12. Read this alongside `TASK10_REPORT.md`/`TASK11_REPORT.md`/`TASK12_REPORT.md` for the reasoning; this file is the resulting structure only.

## Section order (unchanged from before this pass; confirmed already RQ-consistent)

```
Results (roadmap paragraph: states v2.5b is primary, maps RQ1-RQ5 to subsections)
├── Layer-wise Architecture Validation (RQ1, RQ2)          -- STBV-Bench v1, progressive ablation only
├── ...ITE-Bench... completing RQ1                          -- ITE-Bench, real per-layer B1/B2/B3 detection
├── Semantic Validation -- Primary Benchmark: v2.5b (RQ3)   -- STBV-Bench v2.5b, headline generalization claim
├── Behavioral and Kinematic Validation -- RQ4 (VeReMi)     -- real kinematic attacks, B2/MBD only
├── Deployment Validation -- RQ5 (Live CARLA)               -- live simulator, synthesizer-bug discovery
└── SUMO Deployment Replay                                  -- throughput/latency, real trace
    └── Adaptive Attack Evaluation                          -- robustness, explicitly prior-checkpoint
```

## Figures, by subsection

| Subsection | Figures |
|---|---|
| Layer-wise Architecture Validation | `fig_ablation` (v1 confusion matrix, prior checkpoint), `fig_decision_dist` (v1, prior checkpoint) |
| ITE-Bench | `fig_family_heatmap` (ITE-Bench per-family, real B1/B2/B3 detection) |
| Semantic Validation (v2.5b) | `fig_v25b_confusion_grid` (NEW, 6 configs), `fig_v25b_progressive` (NEW), `fig_v25b_heatmap` (NEW, attack-family x config), `fig_v25b_roc` (NEW, direct-classifier ROC/PR) |
| Behavioral/VeReMi | (table only, `tab:veremi`) |
| Deployment/CARLA | `fig_carla_scene` |
| SUMO | `fig_sumo_stage` |

## Tables, by subsection

| Subsection | Tables |
|---|---|
| Layer-wise Architecture Validation | `tab:main_ablation` (v1, prior checkpoint) |
| ITE-Bench | `tab:ite_ablation` |
| Semantic Validation (v2.5b) | `tab:v25b` (4-checkpoint progression, current final headline), `tab:v25b_ablation` (NEW: 6-configuration progressive ablation, current checkpoint) |
| Behavioral/VeReMi | `tab:veremi` |
| Deployment/CARLA | `tab:carla` |
| Adaptive | `tab:adaptive` (explicitly prior-checkpoint) |

## New figures generated this pass, not all embedded in main text (disclosed)

Generated and verified but **not** embedded in the main manuscript (kept as supplementary artifacts, referenced from `TASK11_REPORT.md`/`REPOSITORY_AUDIT.md`, available for an appendix or supplementary-material submission if the venue allows): `fig_heatmap_family_performance_v25b.pdf` (precision/recall/F1/FPR per family — judged redundant with the already-embedded family×config recall heatmap plus Table~\ref{tab:v25b_ablation}'s aggregate row), `fig_heatmap_checkpoint_delta_v25b.pdf` (per-family Δ between checkpoints — supports the checkpoint-improvement narrative but duplicates information already conveyed by the McNemar test's aggregate significance result), `fig_heatmap_error_analysis_v25b.pdf` (TP/FP/FN/TN per family — largely redundant with the confusion-matrix grid's full-stack panel plus the family recall heatmap). This is the "remove figures that become redundant... rather than increasing paper length" instruction applied literally: these three were built, inspected, and judged to add less marginal information than the 900-word budget four heatmap-style figures would already cost, given the four embedded ones (confusion grid, progressive curve, family×config heatmap, ROC/PR) already cover the same ground with less redundancy.

## RQ answer locations (all new this pass)

RQ1/RQ2: end of Layer-wise Architecture Validation subsection. RQ3: end of Semantic Validation subsection (ties to the new McNemar result). RQ4: end of Behavioral/VeReMi subsection. RQ5: end of Deployment/SUMO subsection.

## What a reader takes away, checked against the stated goal

Read start to finish, the Results section now: states its own organizing principle before any benchmark name appears; names which question is being answered before presenting numbers; explicitly demotes v1 relative to v2.5b in its own text rather than leaving that inferable; and closes every subsection with a direct answer sentence rather than trailing off into the next benchmark. This satisfies the stated goal ("the reader should remember the architecture, not the datasets") to the extent achievable without physically restructuring section numbering, per the scope decision explained in `TASK12_REPORT.md`.
