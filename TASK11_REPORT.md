# Task 11 Report: Architecture-Centric Ablation Redesign

## Inspected the implementation first, as instructed

`b1_scsv/scsv.py`: certificate/PKI validity is one of B1's own structural evidence checks (station-ID format, certificate presence, replay/rotation cache), not an independently-gateable pipeline stage. `pipeline/orchestrator.py`'s `ISCEPipeline` constructor exposes exactly three independent boolean toggles: `enable_mbd`, `enable_cp`, `enable_b3`. There is no `enable_pki` toggle, and none should be added — PKI is not a separate stage in the running system, it is folded into B1's evidence, confirmed by direct code inspection, not assumed. This was already established in an earlier pass (`UPDATED_ABLATION_RESULTS.md`) and is not re-litigated here, only re-applied.

**Consequence for the requested configuration list**: "Traditional Stack (PKI+MBD+CP)" and "Traditional + B1" are not two different system states — a config with MBD/CP enabled necessarily also has B1's structural checks active (they are unconditional in the code, not toggleable), so "PKI+MBD+CP without B1" is not a real, distinct configuration either. The realizable degrees of freedom are exactly `enable_mbd` × `enable_cp` × `enable_b3` — 8 boolean combinations in principle, of which the architecturally meaningful, monotonically-additive subset is the 6 actually run.

## The six configurations run (all real, all on v2.5b, current final checkpoint)

| # | Configuration | Realizable as | Result source |
|---|---|---|---|
| 1 | Traditional (PKI+B1) | `enable_mbd=False, enable_cp=False, enable_b3=False` | `config_1.csv` (existing, this pass's checkpoint) |
| 2 | +B2 (B1+B2) | `enable_mbd=True, enable_cp=False, enable_b3=False` | `config_2.csv` |
| 3 | +CP (B1+B2+CP) | `enable_mbd=True, enable_cp=True, enable_b3=False` | `config_3.csv` |
| 4 | B3 only | separate B3-only decision path (bypasses fusion for isolation) | `config_4.csv` |
| 5 | B1+B2+B3 (no CP) | `enable_mbd=True, enable_cp=False, enable_b3=True` | `config_6.csv` -- **new this pass**, the one cell flagged-but-not-run in the earlier reconciliation, now actually executed (10,098 samples, real pipeline run, not estimated) |
| 6 | Full STBV Framework | `enable_mbd=True, enable_cp=True, enable_b3=True` | `config_5.csv` |

No config was invented or estimated. Configuration 5 above (B1+B2+B3, no CP) required a genuinely new experiment — `run_v25b_config6_hardmine.py` — run this pass, not reused from any prior artifact.

## Results (real, from the table now in `stbv_paper.tex`)

| Configuration | Acc. | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|---|
| Traditional (PKI+B1) | 0.469 | -- | 0.000 | -- | 0.000 |
| +B2 | 0.469 | -- | 0.000 | -- | 0.000 |
| +CP | 0.469 | -- | 0.000 | -- | 0.000 |
| B3 only | 0.852 | 0.782 | 0.999 | 0.877 | 0.315 |
| B1+B2+B3 (no CP) | 0.845 | 0.775 | 0.999 | 0.873 | 0.329 |
| **Full STBV Framework** | **0.852** | **0.782** | **0.999** | **0.877** | **0.315** |

**New finding from Configuration 5, not previously known**: CP's marginal contribution *given B3 is already active* is small but real and positive — FP drops from 1,559 (B1+B2+B3, no CP) to 1,491 (full stack, +CP), F1 rises 0.873→0.877. This directly answers a question the original 5-config sweep could not: CP is not redundant once B3 is active, it contributes a small additional precision gain. Previously, CP's contribution could only be measured in the absence of B3 (config 2 vs. 3, both showing 0 recall since neither reads content) — this pass's new Configuration 5 is the first real measurement of CP's effect *conditioned on* semantic detection already being active.

## Why "PKI only" and "PKI+B1" are not separate rows (repeated from Task 10's reasoning, load-bearing here)

Forcing a 9-row table by inventing an artificial PKI-only path (e.g., disabling B1's own structural checks while keeping only certificate parsing) would not measure anything the deployed system does — it was not built, per this session's standing no-fabrication rule. The 6-row table above is not a compromise; it is the complete, accurate enumeration of what the implementation genuinely supports.

## Figures generated (all real, from the same six CSVs, no additional experiments)

- `fig_confusion_grid_v25b.pdf` — six confusion matrices, one per configuration.
- `fig_progressive_performance_v25b.pdf` — Accuracy/Precision/Recall/F1 across the six configurations.
- `fig_layer_contribution_v25b.pdf` — marginal F1 per added layer (built, not embedded in main text — see `FINAL_RESULTS_STRUCTURE.md` for the figure-inclusion decision and reasoning).
- `fig_heatmap_family_x_layer_v25b.pdf` — 14 attack families × 5 configurations, real per-family recall, N/A cells for `benign_control` (no malicious ground truth to recall) marked distinctly from 0.00 (genuinely present but undetected).

## ITE-Bench validation (the complementary benchmark this task explicitly anticipated needing)

Confirmed already present and unchanged: `tab:ite_ablation` shows B1 reaching 1.000 recall on B1-native families, B2 reaching 1.000 on B2-native families (rising from 0.143 under B1-alone), and B3 reaching 1.000 on B3-native families — the real per-layer detection capability that v2.5b, by design, cannot show. The v2.5b ablation subsection now explicitly cross-references this table (Fig.~\ref{fig_v25b_heatmap}'s caption: "Compare Table~\ref{tab:ite_ablation}, where the same layers reach 1.000 recall on a benchmark built to give them attacks of their own kind.") so a reader encountering v2.5b's 0.000 recall rows is pointed directly at the benchmark that shows the true capability, not left to wonder if B1/B2 are broken.
