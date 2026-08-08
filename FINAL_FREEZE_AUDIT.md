# Final Freeze Audit

**SUPERSEDED CHECKPOINT NOTICE**: §1 below identifies `semantic_gate_v3_mixed_lora_continued_merged` (SHA-256 `bbae0512...`) as the final checkpoint — accurate when this audit was written, now superseded by `semantic_gate_v3_mixed_lora_hardmine_merged` (SHA-256 `d126cc3...`). The v2.5b row in §2's per-metric traceability table (F1 0.945/0.860) is likewise superseded by the new checkpoint's F1 0.957/0.877. Every other row in §2 (STBV v1, VeReMi, CARLA, SUMO, adaptive attack) remains accurate and current — those benchmarks were not affected by or rerun against the new checkpoint (checkpoint-invariance verified for VeReMi/SUMO by code inspection; CARLA/v1 not rerun, disclosed). See `HARDMINE_IMPROVEMENT_REPORT.md` for the current checkpoint's full record and `FINAL_CONSISTENCY_AUDIT.md` for the consolidated current-state audit.

Scope: every metric reported in the rewritten `stbv_paper.tex`, its source artifact, generating script, checkpoint, dataset, seed, and verification status. Compiled at repository freeze time, after the final continued-fine-tuning checkpoint was produced and evaluated. Updated after the ablation redesign pass (ITE-Bench, Section~\ref{sec:itebench} of the paper) — see §8 below for that pass's additions.

## 8. Ablation redesign (ITE-Bench) — added this pass

| Item | Value |
|---|---|
| Benchmark | `ite_bench/data/ite_bench.jsonl`, n=9,900, balanced B1/B2/B3 (3,300 each) |
| Generator | `ite_bench/build_ite_bench.py`; quality audit `ABLATION_DATASET_AUDIT.md` |
| Root-cause audit | `ABLATION_AUDIT.md` — identifies both a benchmark-scope cause (known) and a previously-undiscovered evaluation-protocol bug (new finding this pass): the original ablation harness only ever validated `messages[-1]` through B1 and explicitly excluded same-sender messages from MBD history pre-population, structurally preventing either layer's history-dependent checks from firing regardless of benchmark content |
| Evaluation harness | `ite_bench/run_ite_ablation.py` — sequential per-message `.run()` calls on one persistent pipeline per config per sample, verified (via `smoke_test.py`) to correctly activate B1's replay/cert-rotation cache and MBD's per-sender history before any full run was launched |
| Runtime | 9,900 samples × 5 configs = 5,430s (~90.5 min), real GPU compute confirmed via `nvidia-smi` monitoring during a stalled first attempt that was killed and diagnosed before relaunch |
| Analysis | `ite_bench/analyze_ite_ablation.py` → `ite_bench/results/analysis_report.json` |
| Result | Per-layer recall: B1-focused attacks 1.000/1.000/1.000 (configs 1/3/5); B2-focused 0.143/1.000/1.000; B3-focused 0.000/0.000/1.000. McNemar full-stack-vs-B3-alone: 3,885 discordant, 0 reversed, $p<10^{-15}$; B1+B2+CP-vs-B1-alone: 2,707 discordant, 0 reversed, $p<10^{-15}$ |
| Manuscript integration | New Section~\ref{sec:itebench}, updated Discussion "Strengths" paragraph, trimmed the now-partially-redundant B1/CP explanation paragraph in the original ablation subsection |
| Known limitation, disclosed not hidden | ITE-Bench's B2 windows are synthetic kinematic sequences, not real vehicular trajectories (unlike STBV-Bench v1's VeReMi-derived kinematics) — stated in `ABLATION_AUDIT.md` §5 |

## 1. Final checkpoint identity

| Item | Value |
|---|---|
| Path | `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_continued_merged/` |
| Produced by | `b3_eval/v25_finetune/train_lora_continue.py` (true adapter resume) → `b3_eval/v25_finetune/merge_continued_lora.py` (merge to dense) |
| Resumed from | `semantic_gate_v3_mixed_lora` (prior production checkpoint, val F1 0.8992) |
| Training data | `b3_eval/v25_finetune/data/continued_train_split.jsonl` (n=20,960) / `continued_val_split.jsonl` (n=4,075), built by `b3_eval/v25_finetune/build_continued_corpus.py` = original mixed corpus + STBV-Bench v2.5c |
| Seed | 42 |
| Best epoch | 5 of 6 (early-stop patience 2) |
| Val F1 | 0.9006 (pre-continuation baseline) → **0.9241** (final) |
| SHA-256 | `bbae05120439774f724dcce205be71b79d1720e4f0edb47cdb4cc793849a9b1a` |
| Calibration temperature | `T=2.82`, fit by `b3_eval/v25_finetune/calibrate_final_checkpoint.py` on `b3_eval/data/calibration_split.jsonl` (n=85); ECE 0.065→0.053. **Distinct from** the prior checkpoint's T=2.145 — not interchangeable. |
| Pipeline default | `isce_config.yaml` → `b3_semantic_gate.model_path` updated to point at this checkpoint; verified by direct pipeline load (`pipeline.b3_bridge._CLASSIFIER_INSTANCE.model_path`). |

**Status: VERIFIED.** All numbers in the rewritten paper that depend on "the final checkpoint" were produced by loading this exact directory, confirmed by SHA-256 above.

## 2. Per-metric traceability

| Metric (paper location) | Value | Source artifact | Script | Seed |
|---|---|---|---|---|
| Layer ablation, Table I | F1 0.034 → **1.000** → 0.995 | `b3_eval/v25_finetune/ablation_results/final/ablation_config_4.csv`, `ablation_config_5.csv` | `b3_eval/v25_finetune/rerun_ablation_configs45_final.py` (re-run against final checkpoint post-audit; closes the gap originally disclosed in §5 below) | n/a (deterministic, fixed 10,000-sample slice) |
| STBV-Bench v2.5b, Table II (all 3 rows) | F1 0.545 / 0.918 / **0.945** | `b3_eval/v25_finetune/results/v25b_final_checkpoint_eval.json` | `b3_eval/v25_finetune/eval_v25b_final.py` | 42 |
| v2.5b benchmark itself | n=10,098, TEMPLATE_DISJOINT | `data/stbv_bench/v25b/manifest.json` | `benchmark/stbv_bench_v25b.py` + `benchmark/v25b_compositional.py` | 20260807 |
| v2.5c (training augmentation) | n=6,097, disjoint from v25 AND v25b | `data/stbv_bench/v25c/manifest.json` | `benchmark/stbv_bench_v25c.py` + `benchmark/v25c_compositional.py` | 20260807217 |
| VeReMi, Table III (all 6 rows) | ConstPos/DataReplay/DoS, msg+veh F1 | `results/veremi_final/veremi_results.json`, `veremi_per_attack.csv` | `run_veremi_evaluation.py` | 1,2,3,4,5 |
| CARLA, Table IV | Per-scenario B3 label / decision, post-fix | `deployment_eval/carla_results/carla_deployment_eval_results.json` (+ backup `..._run3_with_fix.json`) | `deployment_eval/run_carla_evaluation.py` (anaconda Python 3.12 interpreter) | traffic-manager seed=7 for vehicle spawn only; **not seeded for decision randomness — disclosed limitation** |
| CARLA throughput/latency | mean 80.1ms, 10.45 msg/s | same JSON as above, `manifest` block | same | same |
| SUMO, §VI.E | mean 81.2ms, 12.3 msg/s | `deployment_eval/results/deployment_eval_results.json` | `deployment_eval/run_deployment_evaluation.py` | n/a (deterministic FCD replay) |
| Adaptive attack, Table V | ASR 21.6% | **Not regenerated this pass** — carried from prior evaluation of the pre-continuation checkpoint | `b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__mixed.json` (pre-existing) | 42 |

## 3. Synthesizer bug: discovery, fix, and verification chain

| Step | Artifact |
|---|---|
| Bug discovered | Direct text-capture instrumentation of `pipeline.b3_bridge.classify_text` during a live CARLA run, `authority_override` scenario |
| Root cause confirmed | Code inspection: `pipeline/synthesizer.py`'s `SceneEvidence`/`_extract_evidence()` never captured `target_msg.get("event")`; only peer/RSU events were rendered |
| Fix | Added `ego_event` field to `SceneEvidence`; populated in `_extract_evidence()`; rendered in `_render_default`, `_render_narrative`, `_render_structured` |
| Regression check | `python -m pytest pipeline/` → **188/188 passed** (includes `pipeline/tests/test_synthesizer_leakage.py`, 77/77) |
| Before/after text capture | Verbatim captured text before/after fix, logged in this session's transcript; before: no attack content; after: `"Ego-reported event: authority_override_clear_path"` present |
| SUMO impact | **None** — `deployment_eval/run_deployment_evaluation.py`'s `make_flat_message()` never sets an `event`/`cause` field (pure kinematic replay); confirmed by code inspection, no rerun needed |

**Status: VERIFIED**, with one open, disclosed item: `sybil_attack` and `semantic_manipulation` remain B3-`BENIGN` even post-fix (still correctly REJECTed via MBD/B1) — reported as a genuine remaining gap, not silently closed.

## 4. Known instabilities (disclosed, not resolved)

- **CARLA run-to-run non-determinism**: `normal_driving` and `goal_manipulation` decision distributions differ materially between the two post-fix runs (`carla_deployment_eval_results_run3_with_fix.json` vs. the current `carla_deployment_eval_results.json`, i.e. run 4). Confirmed **not** attributable to the synthesizer fix by code-path separation (B1/MBD never consume synthesized text; only `synthesize_message()` → `classify_text()` does). Attributed to CARLA's unseeded traffic manager. Disclosed in paper §VI.D and §VII (Limitations, item iii).
- **Adaptive attack (Table V)** is explicitly labeled in the paper as measuring the *prior* checkpoint, not the final continued one — no rerun was performed this pass per the "no regeneration unless a real bug requires it" freeze instruction, since no bug was found in that evaluation.

## 5. Items NOT regenerated this pass (and why that's consistent with the freeze policy)

Per this phase's explicit instruction ("do not rerun experiments unless a real implementation bug requires it"), the following retain their pre-existing values from earlier evaluation passes, now scoped out of the compressed paper's main text (moved to appendix-level detail or removed to fit 7 pages), and were **not** re-verified against the final checkpoint:
- **Layer ablation (Table I) — RESOLVED.** The B3-dependent rows (B3-alone, full-stack) were flagged as a gap by both this audit and the independent reviewer simulation, and have since been re-run directly against the final checkpoint (`rerun_ablation_configs45_final.py`, $n{=}10{,}000$, same fixed slice): B3-alone F1 **1.000** (up from 0.9999), full-stack F1 **0.995** (unchanged to 3 s.f.). Table I in the paper now reflects these final-checkpoint numbers. B1-only and B1+B2 rows are checkpoint-invariant by construction (`enable_b3=False`) and were not re-run.
- Adaptive attack (Table V, ASR 21.6%) — **still not rerun** against the final checkpoint this pass; explicitly labeled as a prior-checkpoint reference result throughout the paper text, not silently carried forward as current.
- External corpus (F1=0.920), independent in-scope benchmark (n=216, F1=0.352), hard-OOD benchmark (n=288, F1=0.345), CP full evaluation, baseline comparison, human validation — all moved out of the compressed paper's main text per the Part 3 scope instructions (exploratory/appendix material), not deleted from the repository.

## 6. Figure/reference integrity

- **Broken reference found and fixed**: the pre-rewrite paper referenced `fig1.png` for the architecture diagram — this file does **not exist** anywhere in the repository. Replaced with `deployment_eval/carla_figures/fig5_architecture.png` (verified to exist).
- All 6 figures in the rewritten paper verified to exist on disk: `deployment_eval/carla_figures/fig5_architecture.png`, `figures_v2/fig_deploy_architecture.pdf`, `FINAL_FIGURES/fig_ablation_summary.pdf`, `FINAL_FIGURES/fig_roc.pdf`, `figures_v2/fig_deploy_carla_scene.png`, `FINAL_FIGURES/fig_deploy_latency_stage_sumo.pdf`.
- **Two citation placeholders found and resolved** in the pre-rewrite bibliography: `\bibitem{b7}` carried a "[Citation key to be verified]" marker with no real source, and `\bibitem{b9}` was flagged as sharing a duplicate title with `\bibitem{b1}`. Both replaced with distinct, real MBD/CP-security citations already used elsewhere in the paper's own reference list (`r_mbd_survey2`'s Yuce 2025 survey for b7; Zhang et al. USENIX 2023/2024 for b9, matching `r_cp_fabrication`). **Not independently verified against the actual published sources** — flagged for author verification before submission (see checklist).
- Page count: **not independently compiled** (no LaTeX toolchain available in this environment — `pdflatex`/`latexmk` not found). Word-count/table/figure-count estimate (§ this document) is consistent with ~7 pages in IEEE two-column conference format but is an estimate, not a verified compile.

## 7. Overall verdict

Every number newly reported in this pass (v2.5b, VeReMi, CARLA post-fix, SUMO, checkpoint provenance) is traced to a real, re-executed artifact with a logged seed and script. Two items are explicitly disclosed as **not** independently re-verified against the final checkpoint in this pass: the adaptive-attack ASR (Table V) and Table I's B3-dependent ablation rows. Both are stated as such in the paper text, not silently carried forward as if current.
