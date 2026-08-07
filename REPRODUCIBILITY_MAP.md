# REPRODUCIBILITY_MAP.md

For every numerical claim in the final `stbv_paper.tex`, this table records:
script → checkpoint → dataset → seed/config → output artifact. All rows use
`semantic_gate_v3_mixed_lora_merged`
(SHA-256 `638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`)
unless marked **[unchanged/C]** (checkpoint-invariant by construction) or
**[not rerun]** (disclosed gap, carried from a prior evaluation).

| Paper location | Script | Dataset | Seed/config | Output artifact |
|---|---|---|---|---|
| `tab:main_ablation` rows 1–3, `tab:full_ablation` rows 1–3 | `stbv_bench/run_ablation.py` logic (reproduced in `rerun_paper_ablation.py`) | `data/stbv_bench/v1/stbv_bench.jsonl`, first 10,000 rows | `enable_b3=False`; deterministic, no seed dependence | `b3_eval/v25_finetune/ablation_results/mixed/ablation_config_{1,2,3}.csv` **[unchanged/C]** |
| `tab:main_ablation`/`tab:full_ablation` "B3 alone" and "full stack" rows; `fig_confusion`; `fig_per_family_recall`; `fig_roc`; `fig_pr`; `fig_calibration`; `fig_ablation_summary`; `fig_decision_transitions`; RQ1/RQ2 text; McNemar/Cohen's-h/transition stats | `b3_eval/v25_finetune/rerun_ablation_configs45_mixed.py` (lean, single-writer variant of `rerun_paper_ablation.py --checkpoint mixed`, written this session to fix a concurrent-write corruption bug) | `data/stbv_bench/v1/stbv_bench.jsonl`, first 10,000 rows | seed 42 (benchmark construction); pipeline is deterministic given fixed weights | `ablation_config_{4,5}.csv`; figures in `FINAL_FIGURES/` via `b3_eval/v25_finetune/generate_final_figures.py` |
| §RQ3, kinematic companion benchmark (MBD recall/precision/F1/FPR by attack type) | `stbv_bench/build_and_run_veremi_kinematic_bench.py` | VeReMi Extension, $n=13{,}511$ | fixed, no B3 involvement | pre-existing committed artifact **[unchanged/C]** — B3 never loaded for this benchmark |
| `tab:coverage` (mixed-threat case study) | `b3_eval/v25_finetune/rerun_mixed_threat_mixed.py --checkpoint mixed` | `stbv_bench/build_mixed_threat_bench.py` output, seed 31, 120 windows | seed 31 | `results/mixed_threat_mixed/mixed_threat_per_message.csv` |
| RQ6 (STBV-Bench v2, windowed) | `b3_eval/v25_finetune/rerun_stbv_v2_mixed.py --checkpoint mixed` | `stbv_bench/build_stbv_bench_v2.py` output, seed 21, 150 windows | seed 21 | `results/stbv_bench_v2_mixed/stbv_bench_v2_per_message.csv` |
| §Calibration/robustness/latency, perturbation-battery sentence | *(not rerun this pass)* | — | — | **[not rerun]**, disclosed via in-text caveat |
| `tab:external_eval`, `tab:external_family`, `fig_ext_roc`, `fig_ext_per_family` | `b3_eval/v25_finetune/rerun_external_and_cp_mixed.py --checkpoint mixed` (wraps `external_semantic_eval/evaluate_external.py`) | `external_semantic_eval/external_corpus.json`, $n=117$ | fixed corpus, no seed | `b3_eval/v25_finetune/results/paper_reruns/external_eval_results__mixed.json` |
| `tab:adaptive`, `fig_adaptive_confidence`, adaptive-attack narrative | `b3_eval/v25_finetune/rerun_adaptive_attack_mixed.py --checkpoint mixed` (wraps `adaptive_attack/run_adaptive_attack.py`) | Seeds = the 51 external-corpus items this checkpoint currently detects correctly | master seed 20260802, 9 mutation strategies, ≤10 rounds | `b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__mixed.json` |
| `tab:cp_full`, `fig_cp_detection` | `b3_eval/v25_finetune/rerun_external_and_cp_mixed.py --checkpoint mixed` (`cp_full_eval` arm) | `cp_full_eval/` fixture, 24 scenes, 142 messages | fixed fixture | `b3_eval/v25_finetune/results/paper_reruns/cp_full_eval_results__mixed.json`; cross-checked byte-identical to `..._original.json`'s isolated CP delta, recomputed directly this session |
| `tab:baselines` (TF-IDF+LogReg, TF-IDF+LinearSVC, zero-shot LLM, regex) | `baselines/run_baselines.py` | `data/stbv_bench/v1/stbv_bench.jsonl` | 5-fold stratified CV, fixed seed; zero-shot LLM stratified $n=987$ | pre-existing committed artifact **[unchanged/C]** — none of these detectors call B3 |
| `tab:baselines` (B3, banded) | Same source as the `tab:main_ablation` "full stack"/"B3 alone" row (config 4) | same as above | same as above | `ablation_config_4.csv` — "auto-updates," no separate script |
| `tab:deployment` SUMO column (latency, throughput, memory) | `b3_eval/v25_finetune/rerun_deployment_eval_mixed.py --checkpoint mixed` — confirmed protocol-identical to `deployment_eval/run_deployment_evaluation.py` (same `MESSAGE_BUDGET=2000`, `WINDOW_SIZE=5`, same FCD trace) in Task 3.7's re-verification, so promoted from footnote to the table's actual reported value | SUMO FCD trace, 2,000 msgs, full trace 36,256 msgs/1,829 timesteps | message budget 2,000, window size 5 | `deployment_eval/results/deployment_eval_results_mixed.json` |
| `tab:deployment` CARLA column, `tab:carla_scenarios` | *(not rerun — no CARLA-capable environment; exhaustively re-verified absent in Task 3.7, see `ROOT_CAUSE_REPORT.md`)* | — | — | **[not rerun]**, carried from prior checkpoint's evaluation, disclosed at every point of use |
| `tab:carla_scenarios`, live-CARLA "B3 returned BENIGN on all 3,585 messages" finding | *(not rerun this pass — no CARLA-capable environment)* | — | — | **[not rerun]**, disclosed via in-text caveat at both points of use |
| `tab:safety` | `SAFETY_ANALYSIS.md`'s per-cluster risk assignment (methodology unchanged); adaptive-evasion row rating updated this session from HIGH to MEDIUM given fresh ASR | — | — | manual risk assignment, methodology in `SAFETY_ANALYSIS.md`, not itself a rerun |
| App. §Semantic Classifier (architecture, params, LoRA hyperparameters, SHA-256) | `b3_eval/v25_finetune/train_lora_mixed.py`, `merge_mixed_lora.py` | `data/mixed_train_split.jsonl` + `mixed_val_split.jsonl` (8,535 v2.5 rows + 7,229 v1 rows) | seed 42 throughout | `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged/`; SHA-256 computed directly this session via `hashlib.sha256` over `model.safetensors` |
| App. §Fusion Constants | `isce_config.yaml` (fixed values, not touched per task rule) | — | — | `isce_config.yaml` lines 525–537 |
| App. §Full Five-Configuration Ablation | Same as `tab:main_ablation` | — | — | same artifacts |
| App. §External Semantic Evaluation (corpus construction, per-source table) | `external_semantic_eval/` corpus-construction scripts (pre-existing, dataset-only, not B3-dependent) | `external_semantic_eval/external_corpus.json` | — | **[unchanged/C]** |
| App. §Cooperative Perception Validation | `cp_full_eval/` fixture construction (pre-existing, dataset-only) | 3-message event-labeled fixture | — | **[unchanged/C]** |

## Known configuration/deployment gap (Task 1 finding, disclosed not silently fixed)

`isce_config.yaml`'s `b3_semantic_gate.model_path` (line 525) still points at
the **original**, non-fine-tuned checkpoint
(`b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3`), not the final
production checkpoint described throughout this paper. Every rerun that
produced a number in this paper explicitly overrode this path via a
monkeypatched config copy (`make_override_config()` in each `rerun_*_mixed.py`
script) specifically so as not to mutate this shared, multi-script production
file — so **no published number in this paper is affected** by this gap
(every artifact's manifest records `"model_path":
".../semantic_gate_v3_mixed_lora_merged"` explicitly, verifiable directly in
each JSON). It is, however, a genuine, real deployment-readiness
inconsistency: a naive invocation of the pipeline today without an explicit
override would still load the original checkpoint. This is deliberately
**not fixed** in this pass (editing shared production config is outside a
paper-correctness freeze's blast radius and was not requested), but is
recorded here as a real finding, per Task 1's instruction to report
everything found, fixed or not.
