# FINAL_REPRODUCIBILITY_REPORT.md

**SUPERSEDED NOTICE (read this first).** Everything below this notice is a much
earlier draft-phase snapshot: it references `semantic_gate_v3_mixed_lora_merged`
and a table/section structure (`tab:coverage`, RQ1–RQ6, `tab:baselines`,
`tab:safety`, etc.) that no longer matches the current `stbv_paper.tex`. It is
kept, not deleted, per this project's standing "preserve superseded work"
convention, but it is **not** an accurate description of the current paper.

**Current, accurate reproducibility record**: `HARDMINE_IMPROVEMENT_REPORT.md`
(latest checkpoint's full provenance and verification chain),
`FINAL_FREEZE_AUDIT.md` (per-metric traceability for the architecture-centric
rewrite that superseded the RQ-numbered draft this file describes), and
`FINAL_CONSISTENCY_AUDIT.md` (cross-reference/checkpoint-consistency audit,
including this pass's checkpoint-supersession addendum). Current final
checkpoint: `semantic_gate_v3_mixed_lora_hardmine_merged`, SHA-256
`d126cc3cb998a4717fa833859c6affcd1320f4d60f38c3c98f9cf175720b3759` — not
`638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3` as stated
below, and not `bbae0512...` either (that was the immediately prior one).

**Also now stale**: the "known configuration/deployment gap" note below,
claiming `isce_config.yaml`'s `model_path` points at a non-fine-tuned
checkpoint — this has not been true since at least the pass that produced
`FINAL_FREEZE_AUDIT.md`; `isce_config.yaml` currently points at the real,
current final checkpoint, verified by direct read of the file this pass.

---

*(Original content below, preserved for audit trail, not current.)*

**Status: finalized.** This is `REPRODUCIBILITY_MAP.md`, carried forward
unchanged in content (that file remains on disk as the working document
this was built from) and confirmed current as of the final submission-prep
pass: re-checked against the paper's current state (post SUMO-deployment
rerun and the p99-latency finding), no entries required updating — the
deployment row was already updated to reflect the real SUMO rerun in the
prior pass, verified still accurate.

---

For every numerical claim in the final `stbv_paper.tex`, this table records:
script → checkpoint → dataset → seed/config → output artifact. All rows use
`semantic_gate_v3_mixed_lora_merged`
(SHA-256 `638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`)
unless marked **[unchanged/C]** (checkpoint-invariant by construction) or
**[not rerun]** (disclosed gap, carried from a prior evaluation).

| Paper location | Script | Dataset | Seed/config | Output artifact |
|---|---|---|---|---|
| `tab:main_ablation` rows 1–3, `tab:full_ablation` rows 1–3 | `stbv_bench/run_ablation.py` logic (reproduced in `rerun_paper_ablation.py`) | `data/stbv_bench/v1/stbv_bench.jsonl`, first 10,000 rows | `enable_b3=False`; deterministic, no seed dependence | `b3_eval/v25_finetune/ablation_results/mixed/ablation_config_{1,2,3}.csv` **[unchanged/C]** |
| `tab:main_ablation`/`tab:full_ablation` "B3 alone" and "full stack" rows; `fig_confusion`; `fig_per_family_recall`; `fig_roc`; `fig_pr`; `fig_calibration`; `fig_ablation_summary`; `fig_decision_transitions`; RQ1/RQ2 text; McNemar/Cohen's-h/transition stats | `b3_eval/v25_finetune/rerun_ablation_configs45_mixed.py` (lean, single-writer variant of `rerun_paper_ablation.py --checkpoint mixed`, written to fix a concurrent-write corruption bug found and root-caused mid-chain) | `data/stbv_bench/v1/stbv_bench.jsonl`, first 10,000 rows | seed 42 (benchmark construction); pipeline is deterministic given fixed weights | `ablation_config_{4,5}.csv`; figures in `FINAL_FIGURES/` via `b3_eval/v25_finetune/generate_final_figures.py` |
| §RQ3, kinematic companion benchmark (MBD recall/precision/F1/FPR by attack type) | `stbv_bench/build_and_run_veremi_kinematic_bench.py` | VeReMi Extension, $n=13{,}511$ | fixed, no B3 involvement | pre-existing committed artifact **[unchanged/C]** — B3 never loaded for this benchmark |
| `tab:coverage` (mixed-threat case study) | `b3_eval/v25_finetune/rerun_mixed_threat_mixed.py --checkpoint mixed` | `stbv_bench/build_mixed_threat_bench.py` output, seed 31, 120 windows | seed 31 | `results/mixed_threat_mixed/mixed_threat_per_message.csv` |
| RQ6 (STBV-Bench v2, windowed) | `b3_eval/v25_finetune/rerun_stbv_v2_mixed.py --checkpoint mixed` | `stbv_bench/build_stbv_bench_v2.py` output, seed 21, 150 windows | seed 21 | `results/stbv_bench_v2_mixed/stbv_bench_v2_per_message.csv` |
| §Calibration/robustness/latency, perturbation-battery sentence | *(not rerun)* | — | — | **[not rerun]**, disclosed via in-text caveat |
| `tab:external_eval`, `tab:external_family`, `fig_ext_roc`, `fig_ext_per_family` | `b3_eval/v25_finetune/rerun_external_and_cp_mixed.py --checkpoint mixed` (wraps `external_semantic_eval/evaluate_external.py`) | `external_semantic_eval/external_corpus.json`, $n=117$ | fixed corpus, no seed | `b3_eval/v25_finetune/results/paper_reruns/external_eval_results__mixed.json` |
| `tab:adaptive`, `fig_adaptive_confidence`, adaptive-attack narrative | `b3_eval/v25_finetune/rerun_adaptive_attack_mixed.py --checkpoint mixed` (wraps `adaptive_attack/run_adaptive_attack.py`) | Seeds = the 51 external-corpus items this checkpoint currently detects correctly | master seed 20260802, 9 mutation strategies, ≤10 rounds | `b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__mixed.json` |
| `tab:cp_full`, `fig_cp_detection` | `b3_eval/v25_finetune/rerun_external_and_cp_mixed.py --checkpoint mixed` (`cp_full_eval` arm) | `cp_full_eval/` fixture, 24 scenes, 142 messages | fixed fixture | `b3_eval/v25_finetune/results/paper_reruns/cp_full_eval_results__mixed.json`; independently cross-checked byte-identical to the prior checkpoint's isolated CP delta, twice across this task chain |
| `tab:baselines` (TF-IDF+LogReg, TF-IDF+LinearSVC, zero-shot LLM, regex) | `baselines/run_baselines.py` | `data/stbv_bench/v1/stbv_bench.jsonl` | 5-fold stratified CV, fixed seed; zero-shot LLM stratified $n=987$ | pre-existing committed artifact **[unchanged/C]** — none of these detectors call B3 |
| `tab:baselines` (B3, banded) | Same source as the `tab:main_ablation` "full stack"/"B3 alone" row (config 4) | same as above | same as above | `ablation_config_4.csv`; CI genuinely bootstrapped (seed 42, 2,000 resamples) — the fabricated placeholder found in the publication-freeze audit was replaced with this real value |
| `tab:deployment` SUMO column (latency, throughput, memory) | `b3_eval/v25_finetune/rerun_deployment_eval_mixed.py --checkpoint mixed` — confirmed protocol-identical to `deployment_eval/run_deployment_evaluation.py` (same `MESSAGE_BUDGET=2000`, `WINDOW_SIZE=5`, same FCD trace) | SUMO FCD trace, 2,000 msgs, full trace 36,256 msgs/1,829 timesteps | message budget 2,000, window size 5 | `deployment_eval/results/deployment_eval_results_mixed.json` |
| `tab:deployment` CARLA column, `tab:carla_scenarios` | *(not rerun — no CARLA-capable environment; exhaustively re-verified absent twice across this task chain)* | — | — | **[not rerun]**, carried from prior checkpoint's evaluation, disclosed at every point of use |
| `tab:safety` | `SAFETY_ANALYSIS.md`'s per-cluster risk assignment (methodology unchanged); adaptive-evasion row rating downgraded HIGH→MEDIUM given the final checkpoint's fresh ASR | — | — | manual risk assignment, not itself a rerun |
| App. §Semantic Classifier (architecture, params, LoRA hyperparameters, SHA-256) | `b3_eval/v25_finetune/train_lora_mixed.py`, `merge_mixed_lora.py` | `data/mixed_train_split.jsonl` + `mixed_val_split.jsonl` (8,535 v2.5 rows + 7,229 v1 rows) | seed 42 throughout | `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged/`; SHA-256 independently rehashed twice across this task chain, identical both times |
| App. §Fusion Constants | `isce_config.yaml` (fixed values, not touched per task rule); independently traced in code (`trust_engine/policy.py`) to confirm no override | — | — | `isce_config.yaml` lines 525–537; `trust_engine/policy.py` defaults |
| App. §Full Five-Configuration Ablation | Same as `tab:main_ablation` | — | — | same artifacts |
| App. §External Semantic Evaluation (corpus construction, per-source table) | `external_semantic_eval/` corpus-construction scripts (pre-existing, dataset-only, not B3-dependent) | `external_semantic_eval/external_corpus.json` | — | **[unchanged/C]** |
| App. §Cooperative Perception Validation | `cp_full_eval/` fixture construction (pre-existing, dataset-only) | 3-message event-labeled fixture | — | **[unchanged/C]** |

## Known configuration/deployment gap (disclosed, not silently fixed)

`isce_config.yaml`'s `b3_semantic_gate.model_path` still points at the
original, non-fine-tuned checkpoint, not the final production checkpoint.
Verified this affects **zero** published numbers (every rerun script
explicitly overrides this path; every artifact's manifest records the
override explicitly). Not fixed, because editing shared production config
used by many unrelated scripts is outside a paper-correctness freeze's
blast radius. Recorded here as a real, disclosed finding.

## LaTeX build environment (checked this pass, see `FINAL_CONSISTENCY_REPORT.md`)

No `pdflatex`/`xelatex`/`latexmk`/`tectonic` binary is present on this
machine (checked via `which`/`where`, filesystem search of `Program Files`
and `Program Files (x86)`, and `pip show pylatex`) — no TeX distribution is
installed. Compilation could not be performed; static consistency checks
(brace/environment balance, `\ref`/`\cite`/`\includegraphics` resolution)
were used as the best available substitute and pass clean except for the
pre-existing, out-of-scope `fig1.png`.
