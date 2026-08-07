# UPDATED_RESULTS_FINAL.md — old vs. new, `semantic_gate_v3_mixed_lora_merged`

Every number below traces to a rerun artifact produced against the final
production checkpoint (`b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged/`,
SHA-256 `638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`).
"Old" = the number previously in `stbv_paper.tex` (measured against the
original, non-fine-tuned `semantic_gate_v3` checkpoint). "New" = this pass's
fresh rerun. Artifact paths are given for every row.

## STBV-Bench v1, full pipeline ($n=10{,}000$)

Rerun via `b3_eval/v25_finetune/rerun_paper_ablation.py --checkpoint mixed`
(new `mixed` checkpoint mode added to the script in this pass).

| Metric | Old (original ckpt) | New (mixed ckpt) | Artifact |
|---|---|---|---|
| B3 alone (config 4): Acc/Prec/Rec/F1/FPR | 0.689 / 1.000 / 0.557 / 0.715 / 0.000 | 0.9999 / 0.9999 / 1.000 / 0.9999 / 0.0003 | `b3_eval/v25_finetune/ablation_results/mixed/ablation_config_4.csv` |
| Full stack (config 5): Acc/Prec/Rec/F1/FPR | 0.688 / 0.983 / 0.565 / 0.718 / 0.023 | 0.993 / 0.990 / 1.000 / 0.995 / 0.023 | `.../ablation_config_5.csv` |
| Full-stack confusion (TP/FP/FN/TN) | -- | 7,007 / 70 / 0 / 2,923 | same |
| Per-family recall, full stack | 8/20 families at 100%, 6 at ≤9% | **all 20/20 families at 100%** (in-distribution result; see external-corpus caveat below) | `FINAL_FIGURES/fig_per_family_recall.*` |
| B1 only / B1+B2 (=B1+B2+CP) | 0.299 / -- ; 0.305/0.643/0.018/0.034/0.023 | unchanged (B3 not loaded; verified byte-identical by construction on all 10,000 rows) | `.../ablation_config_{1,2,3}.csv` |
| McNemar, config4 vs config5 (paired, n=10,000) | χ²-based, p=3.06e-29 (128 discordant) | χ²(1, continuity-corrected)=67.0, p<1e-15 (69 discordant: 69 config4-correct/config5-incorrect, 0 the reverse) | computed directly in this session from both CSVs |
| Cohen's h (recall) | -0.026 | 0.000 (recall unchanged at 1.000 in both arms; all discordance is on precision) | same |
| Three-way transitions (config4→5) | 1,713 total (1,585 Caution→Reject, 128 Accept→Caution) | 84 total (69 Accept→Caution, 15 Caution→Reject), 0 de-escalations, 0 direct Accept↔Reject | same |
| ROC-AUC / PR-AUC (B3-alone confidence, config 4) | 0.747 / 0.911 | 1.000 / 0.9998 | `FINAL_FIGURES/fig_roc.*`, `fig_pr.*` |
| ECE / Brier (B3-alone raw confidence, config 4) | 0.0619→0.0280 / 0.0613→0.0553 (post T=2.145) | 0.0172 / 0.0012 (raw, no temperature refit for this checkpoint/benchmark pair) | `FINAL_FIGURES/fig_calibration.*` |

**Data-integrity note on this specific rerun**: the first full-battery attempt at this rerun (`ablation_config_4/5.csv`, all 5 configs together) suffered file corruption from a stray orphaned process left over from an earlier failed background-launch attempt, concurrently writing to the same output files (confirmed by malformed `sample_id` values like `sstbv-...` and row counts inconsistent with the clean, unique-id count). This was detected via row-count/ID-set cross-checks against the byte-identical, uncorrupted configs 1–3, and fixed by deleting the corrupted files and rerunning configs 4–5 in isolation (`b3_eval/v25_finetune/rerun_ablation_configs45_mixed.py`, a new lean single-writer variant of the ablation script, with per-row `flush()` calls) as a single, unshared process. The numbers above are from that clean rerun, verified to have exactly 10,000 unique, correct sample IDs in every config file.

## STBV-Bench v2 (windowed, contextual), $n=5{,}062$ messages / 150 windows

Rerun via `b3_eval/v25_finetune/rerun_stbv_v2_mixed.py --checkpoint mixed`.

| Metric | Old | New | Artifact |
|---|---|---|---|
| Accuracy | 0.548 | 0.497 | `results/stbv_bench_v2_mixed/stbv_bench_v2_per_message.csv` |
| Precision | 0.365 | 0.353 | same |
| Recall | 0.884 | **1.000** | same |
| F1 | 0.517 | 0.521 | same |
| FPR | 0.579 | **0.693** | same |

## External semantic corpus ($n=117$, frozen checkpoint)

Rerun via `b3_eval/v25_finetune/rerun_external_and_cp_mixed.py --checkpoint mixed`.

| Metric | Old | New | Artifact |
|---|---|---|---|
| Accuracy | 0.906 | 0.880 | `b3_eval/v25_finetune/results/paper_reruns/external_eval_results__mixed.json` |
| Precision | 0.976 | 0.931 | same |
| Recall | 0.899 | 0.910 | same |
| F1 | 0.936 | **0.920 (B3's weakest benchmark in this paper)** | same |
| ROC-AUC | 0.975 | 0.897 | same |
| PR-AUC | 0.981 | 0.932 | same |
| Confusion (TP/FP/FN/TN) | 80/2/9/26 | 81/6/8/22 | same |
| Weakest family | `spoofed_authority_override` (recall 0.500) | `phantom_hazard_fabrication` (recall 0.700); `spoofed_authority_override`/`sensor_discreditation` tie for 2nd-weakest (0.875) | same, `per_family_recall` key |
| Calibration transfer (existing T applied, not refit) | ECE 0.054 → 0.169 (worsens) | ECE 0.1054 → 0.0995 (slightly improves) | same, `calibration` key |

## Adaptive-attack evaluation

Rerun via `b3_eval/v25_finetune/rerun_adaptive_attack_mixed.py --checkpoint mixed`.

| Metric | Old | New | Artifact |
|---|---|---|---|
| n seeds | 49 | 51 (seed set depends on which external-corpus items this checkpoint currently detects) | `b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__mixed.json` |
| Attack Success Rate | 83.7% (41/49) | **21.6% (11/51)** | same |
| Avg. iterations, all seeds | 4.06 | 8.69 | same |
| Avg. iterations, successful only | 2.90 | 3.91 | same |
| Detection probability, round 0/2/10 | 1.000 / 0.592 / 0.163 | 1.000 / 0.922 / 0.784 | same, computed directly from per-seed trace |
| Family ASR range | every family ≥66.7% | 0.0%–33.3% (no family ≥50%) | same |

## Mixed-threat case study ($n=4{,}123$ messages / 120 windows)

Rerun via `b3_eval/v25_finetune/rerun_mixed_threat_mixed.py --checkpoint mixed`.

| Metric | Old (paper's Table `tab:coverage`) | New | Artifact |
|---|---|---|---|
| Kinematic-attacker recall | 90.3% | 87.3% (message-level) | `results/mixed_threat_mixed/mixed_threat_per_message.csv` |
| Semantic-attacker recall | 70.3% | **100.0%** | same |
| Benign FPR (new metric, not previously in this table) | not reported | **0.673** | same |

## CP full evaluation ($n=142$, isolated `enable_cp` delta)

Rerun via `b3_eval/v25_finetune/rerun_external_and_cp_mixed.py --checkpoint mixed`.

| Metric | Old | New | Artifact |
|---|---|---|---|
| Decision changes | 33/142 | 33/142 (**byte-identical**) | `b3_eval/v25_finetune/results/paper_reruns/cp_full_eval_results__mixed.json`, verified by direct per-message decision comparison in this pass |
| Escalations : de-escalations | 33 : 0 | 33 : 0 | same |
| Attacker messages recovered | 11/21 | 11/21 | same |
| fp_off / fp_on | 99 / 121 | 99 / 121 | same |
| fn_off / fn_on | 0 / 0 | 0 / 0 | same |

## Deployment (SUMO replay spot-check, $n=2{,}000$)

Rerun via `b3_eval/v25_finetune/rerun_deployment_eval_mixed.py --checkpoint mixed`.

| Metric | Old (paper table) | New spot-check | Artifact |
|---|---|---|---|
| Mean latency | 66.8 ms | 73.9 ms | `deployment_eval/results/deployment_eval_results_mixed.json` |
| p95 latency | 78.9 ms | 90.4 ms | same |
| p99 latency | 85.0 ms | 100.2 ms | same |
| B3 share | 98.6% | 98.7% | same |
| Throughput | 14.95 msg/s | 13.51 msg/s | same |

Difference is within the same order of magnitude previously observed as
run-to-run system noise on this shared laptop GPU (the mixed checkpoint has
identical architecture/parameter count post-merge, 141.9M params); the
paper's existing SUMO/CARLA table numbers were **not** replaced with this
spot-check's numbers, only footnoted, since the spot-check used a smaller
window/config than the full table's original measurement protocol.

## Live CARLA (NOT rerun — disclosed gap)

No CARLA-capable environment was available in this pass (same infeasibility
documented previously). `tab:carla_scenarios` and the "B3 returned BENIGN on
all 3,585 attack messages" finding are carried forward from the prior
evaluation, with an explicit caveat added to the manuscript stating this was
not re-verified against the exact final checkpoint.

## Appendix / methodology numbers changed

- Checkpoint SHA-256: `9ee7475e...` (original) → `638ed0fada07808...` (final, full hash in Appendix A).
- Semantic Classifier training description: rewritten from the original
  checkpoint's from-scratch training hyperparameters to the LoRA
  fine-tuning recipe that produced the final production checkpoint (rank
  16/alpha 32/dropout 0.05, mixed v2.5+v1 training data, best epoch 6, val
  F1 0.899).
