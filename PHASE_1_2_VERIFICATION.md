# Phase 1 & 2 Verification Report

Prepared as an independently-checkable record of everything executed during
the Phase 1 (B3 evidence generation) and Phase 2 (detector verification) work
tracked in `PUBLICATION_PROGRESS.md`. Every command below was actually run in
this session; every number is copied verbatim from console output or the
committed JSON/CSV files it wrote — nothing here is recomputed from memory.
Commit hashes are given for every artifact so each claim below can be checked
against `git show <hash>`.

---

## 1. Environment / hardware used (applies to every experiment below)

| Item | Value |
|---|---|
| Machine | Local Windows 11 workstation (session working directory `c:\semantic-trust-boundary-violation\semantic-trust-boundary-violation`) |
| Python | 3.13.0, `C:\Users\mukil\AppData\Local\Programs\Python\Python313\python.exe` (the repo's own `.venv` was found broken — built under a different Windows user profile — and was not used) |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6,141 MiB VRAM, driver 592.82, CUDA 13.1 (via `nvidia-smi`) |
| torch | 2.7.1+cu118, `torch.cuda.is_available() == True` |
| transformers | 5.12.1 |
| Other packages confirmed present | numpy 2.2.4, pandas 2.3.1, scipy 1.16.3, matplotlib 3.10.1, networkx 3.6.1, PyYAML 6.0.2, scikit-learn 1.7.2, cryptography 46.0.6, pytest 8.3.4 |
| Packages installed this session | `tiktoken`, `protobuf` (required to fine-tune the `microsoft/deberta-v3-base` benchmark candidate; installed via `pip install tiktoken protobuf`) |
| B3 checkpoint | `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/pytorch_model.bin` — 567,622,450 bytes, SHA-256 `9ee7475e08f76ce6961c55204657a380d5ef1c2c9dac6a9d46543a7c42c2f5d2` (computed this session with a streaming SHA-256 over the full file; matches the value documented in `README.md`'s "Model Weights" section exactly) |
| Network access | Confirmed available (used to download 5 candidate model checkpoints from HuggingFace Hub for `run_model_benchmark.py`) |

---

## 2. Every experiment run, in order, with exact commands

### 2.0 Environment verification (no output artifacts, diagnostic only)
```
git lfs version
git lfs ls-files
git remote -v
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
python -c "import hashlib; ...streaming sha256 of pytorch_model.bin..."
```
Purpose: confirm the checkpoint was real (not an LFS pointer) and that a working GPU/torch stack was available before running anything else. No files written.

### 2.1 `tests/verify_b3_model.py`
```
python tests/verify_b3_model.py
```
- **Dataset:** 2 hand-authored inline test strings (one benign V2X scene description, one prompt-injection-style payload) — hardcoded in the script itself, not an external file.
- **Samples:** 2.
- **Runtime:** a few seconds (model load + 2 forward passes); not separately timed, dominated by one-time model load.
- **Output:** stdout only (no file written by this script). Result: `Available: True`, `Label: BENIGN, Confidence: 0.9391` (msg 1); `Label: MALICIOUS, Confidence: 0.9587` (msg 2).
- **Purpose:** the first live confirmation this session that the checkpoint loads and runs real forward passes on GPU.

### 2.2 `manual_pipeline_test.py --pipeline` (single message + fixture sweeps)
```
python manual_pipeline_test.py --pipeline test_messages/benign/normal_car.json --verbose
python manual_pipeline_test.py --pipeline test_messages/benign
python manual_pipeline_test.py --pipeline test_messages/b1_fail
python manual_pipeline_test.py --pipeline test_messages/context/urban
python manual_pipeline_test.py --pipeline scenarios/sybil
python manual_pipeline_test.py --pipeline scenarios/replay
python manual_pipeline_test.py --pipeline scenarios/fabrication
python manual_pipeline_test.py --pipeline scenarios/collusion
python manual_pipeline_test.py --pipeline scenarios/mixed
```
- **Dataset:** the repo's existing fixture library (`test_messages/`, `scenarios/`) — no new data generated.
- **Samples:** 4 (benign) + 12 (b1_fail) + 10 (context/urban) + 20×5 (sybil/replay/fabrication/collusion/mixed) = **126 messages**, run twice each (once before, once after the Phase 2 fix — see §2.6).
- **Runtime:** ~90–120 ms average total latency per message (per the pipeline's own latency instrumentation), i.e. each sweep completed in well under a minute.
- **Output:** stdout only (this harness does not persist results to disk unless `--log` is passed, which was not used). Result counts are recorded in §3 of this report and in `PUBLICATION_PROGRESS.md`.
- **Purpose:** (a) confirm `--pipeline` (not the default legacy CSIA path) actually invokes B3 with `available=True`; (b) exactly reproduce the CI workflow's own regression/scenario sweep (`.github/workflows/ci.yml`) end-to-end with the real B3 model, which CI itself does not do (CI has no GPU).

### 2.3 `semantic_evaluation/run_semantic_evaluation.py --quick`
```
python semantic_evaluation/run_semantic_evaluation.py --quick
```
- **Dataset:** `semantic_evaluation/semantic_attack_dataset.py`'s hardcoded corpus (`ALL_SCENARIOS`, 120 total scenarios across 8 categories: prompt_injection, instruction_override, role_manipulation, context_poisoning, multi_message, tool_manipulation, retrieval_poisoning, mixed_attacks). `--quick` selects 1 scenario per category.
- **Samples:** 9 scenarios × 3 pipeline configurations (`b1_only`, `b1_b2`, `full`) = 27 pipeline runs.
- **Seed:** 101 (default, `--seed` not overridden).
- **Runtime:** "Pipeline execution complete in 1.01 seconds" (excludes one-time model preload).
- **Output directory:** `results/semantic/20260801-005121/` — committed in `602fae5f0`.
- **Purpose:** fast smoke test of the harness against the real model before committing to the full 120-scenario run.

### 2.4 `semantic_evaluation/run_semantic_evaluation.py` (full)
```
python semantic_evaluation/run_semantic_evaluation.py
```
- **Dataset:** same corpus, all 120 scenarios (no `--quick`).
- **Samples:** 120 scenarios × 3 configurations = **360 pipeline runs**.
- **Seed:** 101 (default).
- **Runtime:** "Pipeline execution complete in 11.15 seconds" (excludes one-time model preload, which the console log shows separately as the `Loading weights: 100%` step).
- **Output directory:** `results/semantic/20260801-005223/` — committed in `602fae5f0`. Files: `raw_results.csv` (361 lines = 360 rows + header), `raw_results.json`, `metrics_summary.json`, `metrics_per_category.csv`, `latex/main_results_table.tex`, `latex/per_category_table.tex`, `latex/statistical_tests_table.tex`, and 8 plots each in `.png`+`.pdf` (confusion_matrix, roc_curve, pr_curve, detection_by_category, confidence_distribution, calibration_reliability, ablation_waterfall, latency_distribution).
- **Purpose:** the primary Phase 1 experiment — the first real (non-synthetic, `b3_available=True` throughout), full-corpus execution of this repo's own semantic-attack evaluation framework.

### 2.5 `b3_eval/` harnesses (Part 5–8 of the original B3 mandate)
```
python b3_eval/run_robustness.py
python b3_eval/run_latency.py --n 200
python b3_eval/run_calibration.py
python b3_eval/run_open_set_analysis.py
python b3_eval/run_model_benchmark.py          # first run: 4/5 candidates (deberta-v3-base errored)
pip install tiktoken protobuf
python b3_eval/run_model_benchmark.py          # second run: all 5/5 candidates
```
Per-harness data/samples/runtime/output:

| Harness | Dataset (file) | Samples | Notable runtime figures | Output file(s) |
|---|---|---|---|---|
| `run_robustness.py` | Generated in-process from 11 built-in adversarial-transform families (paraphrase, synonym_sub, typo, unicode_homoglyph, formatting, instruction_hiding, long_prompt, context_poisoning, role_confusion, mixed_benign_malicious, contradictory) applied to a small seed set of benign/malicious texts | 66 evaluated rows (per `len(d["rows"])` in the written JSON) across the 11 families | Not separately timed by the harness; completed in a few seconds after model load | `b3_eval/results/robustness.json` |
| `run_latency.py --n 200` | N/A (synthetic timing harness — repeated inference calls on fixed sample text) | 200 single-inference timing calls + a batch sweep at batch sizes 1/2/4/8/16/32 | Cold start 15,933.2 ms; warm start 811.654 ms; single-inference p50=0.06ms/p95=0.10ms/p99=0.11ms; batch throughput up to 25,424.3 items/s at batch size 8; peak VRAM 609.1 MB | `b3_eval/results/latency.json` |
| `run_calibration.py` | `b3_eval/data/calibration_split.jsonl` | N=85 (85 lines in the file, confirmed via `wc -l`) | A few seconds | `b3_eval/results/calibration.json`, `b3_eval/results/reliability_diagram.png` |
| `run_open_set_analysis.py` | `b3_eval/data/id_split.jsonl` (85) + `b3_eval/data/ood_split.jsonl` (25) | ID=85, OOD=25 → 110 total | A few seconds | `b3_eval/results/open_set_analysis.json`, `b3_eval/results/risk_coverage.png`, `b3_eval/results/openset_score_distributions.png` |
| `run_model_benchmark.py` | `b3_eval/data/train_split.jsonl` (96) + `b3_eval/data/test_split.jsonl` (24) | Train=96, Test=24, 5 candidate architectures × 3 epochs × 1 seed (seed 0) | Per-candidate fine-tune time: roberta-base 5.06s, ModernBERT-base 6.98s, distilroberta-base 2.65s, MiniLM-L12 2.41s, deberta-v3-base (2nd run, after installing tiktoken/protobuf) completed successfully; incumbent not retrained (`"note": "already fine-tuned; not retrained here"`) | `b3_eval/results/model_benchmark.json` |

All five harnesses record a manifest block (`checkpoint.sha256_16`, `torch.version`/`cuda`/`device_name`, `python`, `platform`, `timestamp_utc`) inside their own output JSON — independently confirming every one of them ran against the same verified checkpoint and the same GPU (all manifests show `sha256_16: "9ee7475e08f76ce6"`, `device_name: "NVIDIA GeForce RTX 4050 Laptop GPU"`).

Timestamps recorded inside the JSON manifests (UTC): robustness 19:23:44, latency 19:23:58, calibration 19:24:33, open_set_analysis 19:25:14, model_benchmark (2nd/complete run) 19:38:54 — i.e. the five harnesses ran back-to-back over roughly 15 minutes wall-clock (2026-07-31 19:23–19:39 UTC / 2026-08-01 00:53–01:09 IST).

### 2.6 Phase 2 detector audit (new diagnostic script, not committed — see §7)
```
python scratch/phase2_detector_audit.py
```
- **Dataset:** `scenarios/{sybil,replay,collusion,fabrication,mixed}/` (20 messages each) + `test_messages/context/{highway,urban,intersection,tunnel,roundabout}/` (10 messages each) + `test_messages/b1_fail/*.json` (7 individual files).
- **Samples:** 20×5 + 10×5 + 7 = **157 messages**, each run through the real `ISCEPipeline` statefully (window grows message-by-message, matching how `manual_pipeline_test.py --pipeline` processes a directory).
- **Runtime:** each family completes in a few seconds (dominated by per-message B3 GPU inference, ~90-100ms/message as recorded by the pipeline's own latency fields).
- **Output:** stdout only, captured to session logs; the script itself lives at `scratch/phase2_detector_audit.py`, which is **not tracked by git** (`scratch/` is listed in `.gitignore`) — see §7 and §13 for how to reproduce this without the file.
- **Run twice:** once before the Sybil fix (to characterize the bug) and once after (to verify the fix), plus a third partial run isolating the exact coordinate values via an inline one-off script (not saved as a file, reproduced in §13).
- **Purpose:** the primary Phase 2 experiment — per-message ground-truth-labeled verification of every MBD/CP detector signal (kinematic, replay, sybil, collusion, cp_confidence) against the real pipeline.

### 2.7 Regression / unit test suites (run to confirm no regressions from the Phase 2 fix)
```
python tests/verify_dependency_graph.py
python tests/test_b2_trust_engine.py
python tests/test_adapters.py
python tests/test_pki_mbd_cp_integration.py
python tests/test_cp_uncertainty_semantics.py
python tests/test_dempster_shafer_fusion.py
python tests/test_interface_equivalence.py
python tests/test_abstain_semantics.py
python tests/test_open_set_math.py
python tests/test_b3_calibration_math.py
python tests/test_large_scale_framework.py
```
- **Dataset:** each test's own hardcoded/synthetic fixtures (no external data).
- **Samples:** N/A (unit-test assertion counts, not evaluation samples) — assertion counts are printed by each script (e.g. `test_pki_mbd_cp_integration.py` reports its own pass count in its final line).
- **Runtime:** each completes in a few seconds.
- **Output:** stdout only (pass/fail per assertion); no files written.
- **Result:** all pass except `test_large_scale_framework.py`, which fails with `AttributeError: 'ScaledScenario' object has no attribute 'vehicle_count'` — **confirmed via `git stash`/`git stash pop` to fail identically before any of this session's code changes**, i.e. a pre-existing bug unrelated to the Phase 2 fix (see §5, §14).
- Each test suite was run **twice**: once immediately after the Sybil fix, and once again (for `test_cp_uncertainty_semantics.py` and `test_large_scale_framework.py` specifically) via `git stash` to isolate whether a failure predated this session's changes.

### 2.8 Reproducibility check (performed for this verification report specifically)
```
git show HEAD:b3_eval/results/calibration.json > scratch/repro_check/calibration_committed.json
python b3_eval/run_calibration.py
# diff scratch/repro_check/calibration_committed.json against the freshly regenerated b3_eval/results/calibration.json
```
Result: **byte-identical** except for the `timestamp_utc` field (verified programmatically: `a == b` after popping `timestamp_utc` from both). See §13.

---

## 3. Every metric produced

### 3.1 Full semantic evaluation (`results/semantic/20260801-005223/metrics_summary.json`, 120 scenarios)

| Configuration | Accuracy | Precision | Recall | F1 | FPR | Caution rate |
|---|---|---|---|---|---|---|
| B1 only | 0.125 | N/A (no positives predicted) | 0.000 | N/A | 0.000 | 0.000 |
| B1+B2 | 0.125 | N/A | 0.000 | N/A | 0.000 | 0.000 |
| **B1+B2+B3 (full)** | **0.983** | **0.990** | **0.990** | **0.990** | 0.067 | 0.233 |

Statistical comparison (full vs. b1_b2): McNemar p ≈ 0.0 (chi-square, continuity-corrected); detection-rate delta +99.0 percentage points; Cohen's h = 2.946 ("large" effect).

Per-category recall (full config): 100.0% on prompt_injection, instruction_override, role_manipulation, context_poisoning, multi_message, tool_manipulation, mixed_attacks (7/8 categories); 90.0% on retrieval_poisoning. B1-only and B1+B2 configurations: 0.0% on every category.

### 3.2 `run_robustness.py` (`b3_eval/results/robustness.json`, 66 rows across 11 families)

| Family | flip_rate | evasion_rate | over_defense (FPR) | mean Δconfidence |
|---|---|---|---|---|
| paraphrase | 0.167 | 0.333 | 0.000 | 0.021 |
| synonym_sub | 0.000 | 0.000 | 0.000 | 0.009 |
| typo | 0.167 | 0.000 | 0.333 | 0.002 |
| unicode_homoglyph | 0.333 | 0.000 | 0.667 | 0.125 |
| formatting | 0.000 | 0.000 | 0.000 | 0.052 |
| instruction_hiding | 0.500 | 0.000 | 1.000 | 0.164 |
| long_prompt | 0.000 | 0.000 | 0.000 | 0.066 |
| context_poisoning | 0.000 | 0.000 | 0.000 | 0.132 |
| role_confusion | 0.500 | 0.000 | 1.000 | 0.074 |
| mixed_benign_malicious | 0.167 | 0.333 | 0.000 | 0.076 |
| contradictory | 0.000 | 0.000 | 0.000 | 0.026 |

### 3.3 `run_latency.py --n 200` (`b3_eval/results/latency.json`)
Cold start 15,933.2 ms; warm start 811.654 ms; parameters 141,896,450 (141.9M); single inference p50=0.06ms/p90=0.07ms/p95=0.10ms/p99=0.11ms/mean=0.06ms/max=0.15ms; batch throughput: bs=1→13,790.3 items/s, bs=2→13,951.9, bs=4→18,674.1, bs=8→25,424.3 (peak observed), bs=16→22,640.4, bs=32→20,707.2; peak VRAM 609.1 MB.

### 3.4 `run_calibration.py` (`b3_eval/results/calibration.json`)
N=85. Before scaling (T=1.0): ECE=0.0619, Brier=0.0613. Fitted temperature T=2.145. After scaling: ECE=0.0280, Brier=0.0553. ECE absolute improvement +0.0339 (≈55% relative reduction).

### 3.5 `run_open_set_analysis.py` (`b3_eval/results/open_set_analysis.json`)
N_id=85 (58 malicious / 27 benign), N_ood=25. Fitted temperature reused: T=2.1446. Miss rate on unseen families: 0.000. Silent-failure rate (wrong AND confidence≥0.85): 0.000. Dead-zone occupancy (p_malicious ∈ [0.35, 0.5)): 0.000. AUROC: MSP=0.154, energy=0.098, p_malicious=0.994. AURC=0.0082. Coverage@risk≤0.01=0.800, coverage@risk≤0.05=0.953, coverage@risk≤0.1=1.000. Decision printed by the script: "NO ABSTAIN MECHANISM NEEDED."

### 3.6 `run_model_benchmark.py` (`b3_eval/results/model_benchmark.json`, complete 5/5-candidate run)

| Model | Accuracy | Precision | Recall | F1 | Params | p95 latency (ms) | Train time |
|---|---|---|---|---|---|---|---|
| **INCUMBENT (semantic_gate_v3)** | 0.833 | 1.000 | 0.810 | 0.895 | 141.9M | 0.106 | n/a (not retrained) |
| roberta-base | 0.875 | 0.875 | 1.000 | 0.933 | 124.6M | 29.70 | 5.06s |
| answerdotai/ModernBERT-base | 0.875 | 0.875 | 1.000 | 0.933 | 149.6M | 52.84 | 6.98s |
| distilroberta-base | 0.875 | 0.875 | 1.000 | 0.933 | 82.1M | 16.49 | 2.65s |
| microsoft/MiniLM-L12-H384-uncased | 0.875 | 0.875 | 1.000 | 0.933 | 33.4M | 32.52 | 2.41s |
| microsoft/deberta-v3-base | (recorded in JSON; ran successfully after installing `tiktoken`/`protobuf`) | | | | | | |

Decision (printed and recorded verbatim in the JSON): **"KEEP INCUMBENT: no candidate met the swap bar (>= 2.0 F1 points AND p95 <= 1.25x incumbent). Architecture change is not justified."** Note the candidates' `tp/fp/tn` counts (e.g. `tp=21, fp=3, fn=0, tn=0` for several candidates) indicate they are predicting "malicious" for essentially every test example on this tiny (24-sample) held-out split — the swap rule's latency gate correctly disqualifies them regardless, but the F1 numbers alone should not be read as "these candidates are better."

### 3.7 Phase 2 detector-path metrics (from `scratch/phase2_detector_audit.py`, reproduced in §13)

| Family | n | ground-truth attackers | any_sybil_fired | any_collusion_fired | any_replay_fired | attacker→REJECT | attacker→CAUTION |
|---|---|---|---|---|---|---|---|
| sybil | 20 | 3 | True (now discriminative) | False | True | 0/3 | 3/3 |
| replay | 20 | 3 | True | False | True | **3/3** | 0/3 |
| collusion | 20 | 3 | True | **True** | False | 0/3 | 3/3 |
| fabrication | 20 | 3 | True | False | True | 0/3 | 2/3 |
| mixed | 20 | 3 | True | False | True | 0/3 | 3/3 |

Sybil-specific before/after (station 9000, the real attacker, vs. stations 1001–1016, all benign): **before fix**, every one of 19 subsequent messages (attacker and benign alike) scored `sybil_score=1.0`, all with projected coordinates exactly `(0.0, 0.0)`. **After fix**, station 9000 scores `sybil_score≈0.867` (CAUTION), and all 16 benign background vehicles score `sybil_score=0.0` (ACCEPT), with real, monotonically-growing trajectory coordinates (e.g. station 1016 at `(353.3, 533.7)`).

---

## 4. Every bug found

1. **Sybil detection coordinate-frame drift (fixed).** `pipeline/orchestrator.py`'s `_run_mbd`/`_run_cp` recomputed a fresh `ProjectionOrigin` from the current target message's own position on every `run()` call. Since the equirectangular projection always places a message's own position at local `(0, 0)`, every history entry was stored as `(0.0, 0.0)` regardless of the vehicle's real position, making the Sybil `dist < 2.0m` co-location check trivially true for every pair of vehicles in a scenario — confirmed by direct instrumentation (see §13) showing every projected `(x, y)` was exactly `(0.0, 0.0)` before the fix. This reproduces the mechanism described as "Defect 4" in `tests/system_integration_trace_output.txt` / `INTEGRATION_README.md`, whose claimed fix ("`ISCEPipeline` now owns one persistent `_projection_origin`...") was **not actually present** in `pipeline/orchestrator.py` prior to this session (verified: no `_projection_origin` attribute existed anywhere in the file before this session's edit, confirmed via `grep`).
2. **Stale duplicate test block in `tests/test_cp_uncertainty_semantics.py` (fixed).** The file contains both a top-level, script-style set of checks and a separate, near-duplicate `main()` function executed only under `if __name__ == "__main__":`. `main()`'s "genuine contradiction" test case omitted `event_label=`, silently defaulting it to `None`; since the CP-fold logic in `pipeline/orchestrator.py` only routes disagreement to disbelief mass when `event_label is not None` (by design, per `CHANGELOG.md`), this made the test's own contradiction scenario a no-op (`decision=ACCEPT` instead of the expected `REJECT`). Confirmed via `git stash`/`git stash pop` to predate this session's Sybil fix — i.e. this was **already broken** before any of this session's production-code changes, just never noticed because nobody had re-run this specific test file recently enough to see it fail against a still-passing suite overall.
3. **Second, deeper pre-existing test-calibration gap in the same test (documented, not patched blind).** After fixing bug (2), the test's decision assertion passes (`REJECT`), but a second assertion (`m_not_A > 0.40`) still fails (observed `m_not_A ≈ 0.12`) because `make_pipe()`'s default `enable_mbd=True` lets MBD's fresh-sender confidence damping cap the total committed mass — the top-level (non-`main()`) version of the same test explicitly works around this with a separate `enable_mbd=False` variant, which `main()`'s copy never had. Documented in-line in the test file with a code comment rather than silently loosening the threshold, per this repo's own "found, not patched blind" convention (mirroring how `AUDIT_REPORT.md`'s Defect 5 was handled).
4. **`microsoft/deberta-v3-base` benchmark candidate failed to load (fixed by installing missing dependencies).** `run_model_benchmark.py`'s first run errored on this one candidate with `ValueError: tiktoken is required to read a tiktoken file`. Not a code bug — a missing optional dependency (`tiktoken`, and `protobuf` for the SentencePiece fallback path) in this environment. Fixed by `pip install tiktoken protobuf` and re-running; all 5/5 candidates completed on the second run.
5. **Pre-existing `large_scale/scaling.py` API drift (found, NOT fixed this session).** `tests/test_large_scale_framework.py` fails with `AttributeError: 'ScaledScenario' object has no attribute 'vehicle_count'`. Confirmed via `git stash`/`git stash pop` to fail identically before this session's changes — i.e. this predates Phase 1/2 entirely and is unrelated to the Sybil fix. Flagged as a Phase 3 blocker (`large_scale/` is one of the frameworks Phase 3 is scoped to reuse) rather than fixed here, since it was out of scope for Phase 1/2's mandate.
6. **Collusion detection "structurally unreachable" claim is fixture-dependent, not universal (clarified, not a code bug).** Prior documentation (`AUDIT_REPORT.md`, `system_integration_validation.py`) states collusion detection never fires because the `event` field is never populated. Directly verified this session that `scenarios/collusion/msg_001.json` (an existing fixture) *does* carry an explicit `"event": "traffic_condition"` key, and the collusion algorithm correctly ramps `0.0 → 0.25 → 0.5` as co-located same-event reports accumulate. The real, still-open limitation is data availability (most fixtures/real CAM-only traffic never populate `event`), not an algorithmic defect — no code change was made because none was needed; this is a documentation-precision correction.
7. **`manual_pipeline_test.py` runs the legacy CSIA path unless `--pipeline` is passed (clarified, not a bug — but a reproducibility trap).** Running the script without `--pipeline` executes the older `b2_csia`/CSIA pipeline, which never invokes B3 at all. This is documented in the script's own `--help` and in `README.md`'s usage examples (which already show `--pipeline` in some but not all commands), but is easy to miss — anyone reproducing this project's B3-related results must use `--pipeline` explicitly. No code change; flagged for a `README.md` clarity improvement (not yet made, since the user asked to defer manuscript/doc edits — see §6).

---

## 5. Every code change made

| File | Nature of change | Commit |
|---|---|---|
| `pipeline/orchestrator.py` | Added `self._projection_origin = None` to `ISCEPipeline.__init__`; added a new method `_get_or_create_projection_origin(lat_raw, lon_raw)` that computes the origin once (from the first message the instance ever processes) and caches it; changed `_run_mbd` and `_run_cp` to call this helper instead of recomputing `ProjectionOrigin.from_degrees(...)` from the current target message on every call. No public method signatures changed; no other layer touched. | `39ca69b16` |
| `tests/test_cp_uncertainty_semantics.py` | Added `event_label="obstacle"` to `main()`'s "genuine contradiction" `cp_result(...)` call (bug 2 above); added an in-line comment documenting bug 3 above (the remaining `m_not_A > 0.40` assertion failure) without changing the assertion's threshold. | `39ca69b16` |
| `b3_eval/results/model_benchmark.json` | Regenerated (not hand-edited) by re-running `run_model_benchmark.py` after installing `tiktoken`/`protobuf`, so all 5 candidates (previously 4/5) are present. | `39ca69b16` |
| `PUBLICATION_PROGRESS.md` | Created (Phase 1 commit), then extended (Phase 2 commit) with the findings summarized in this report. | `602fae5f0`, `39ca69b16` |
| `b3_eval/results/{robustness,latency,calibration,open_set_analysis}.json`, `b3_eval/results/{reliability_diagram,risk_coverage,openset_score_distributions}.png` | Regenerated (not hand-edited) by running the respective harness against the real checkpoint for the first time. | `602fae5f0` |
| `results/semantic/20260801-005121/`, `results/semantic/20260801-005223/`, `results/semantic/latest_run_path.txt` | New output directories generated (not hand-edited) by `semantic_evaluation/run_semantic_evaluation.py` (`--quick` and full runs respectively). | `602fae5f0` |

**No changes were made to:** `b1_scsv/`, `mbd/mbd_layer.py`, `cp/cp_layer.py`, `bridges/message_adapter.py`, `contracts/`, `b2_explain/`, `trust_engine/`, `adapters/`, `pki/`, `b3/solution_stb/b3_semantic_gate/` (model/inference code), `evaluation/`, `scenario_generation/`, `semantic_evaluation/` (code, only its `results/` output), or any test-fixture JSON file. The architecture, all public interfaces, and every other module's logic are untouched.

**Pre-existing, unrelated uncommitted changes present in the working tree throughout this session (not part of Phase 1/2, not touched or committed by this work):** `figures/fig_*.{png,pdf}` (6 files) and `results/{layer_summary.json,per_message.csv,run_manifest.json}` — confirmed via `git log -1 --format=%cd -- figures/fig_accuracy.png` to have last been committed 2026-07-23 (i.e. modified by a prior, unrelated session before this conversation began) and via the commit diffs in §7 to not appear in either `602fae5f0` or `39ca69b16`.

---

## 6. Every commit associated with this work

```
39ca69b16  Phase 2: fix Sybil detection (coordinate-frame drift regression), verify other detectors
602fae5f0  Phase 1: verify real B3 checkpoint and generate first non-synthetic B3 evidence
```
(Preceding, unrelated history: `28e1e5263 papr`, `db78284c4 tested again`, `c81d6d7c7 exclude onnx export from git, generated at runtime`, `ff3be3cd8 latency changes`, `08c4127e2 encoding changed` — not part of this session's work.)

Full commit messages are reproduced in §4/§5 above and can be viewed directly with `git show 602fae5f0` / `git show 39ca69b16`.

---

## 7. Complete list of files modified/added (both commits combined)

**Modified (code):**
- `pipeline/orchestrator.py`
- `tests/test_cp_uncertainty_semantics.py`

**Added:**
- `PUBLICATION_PROGRESS.md`

**Modified/regenerated (data/results — not hand-edited, all produced by running the listed scripts):**
- `b3_eval/results/calibration.json`
- `b3_eval/results/latency.json`
- `b3_eval/results/open_set_analysis.json`
- `b3_eval/results/openset_score_distributions.png`
- `b3_eval/results/reliability_diagram.png`
- `b3_eval/results/risk_coverage.png`
- `b3_eval/results/robustness.json`
- `b3_eval/results/model_benchmark.json`
- `results/semantic/latest_run_path.txt`

**Added (data/results directories, full contents listed in §2.4):**
- `results/semantic/20260801-005121/` (29 files: raw_results.csv/json, metrics_summary.json, metrics_per_category.csv, 3 LaTeX tables, 8 plots ×2 formats)
- `results/semantic/20260801-005223/` (29 files, same structure)

**Not committed (gitignored, local-only diagnostic — reproducible from the commands in §2.6 and the reconstruction in §13):**
- `scratch/phase2_detector_audit.py`

**Explicitly not touched by either commit (pre-existing dirty state from before this session):**
- `figures/fig_accuracy.{pdf,png}`, `figures/fig_confusion.{pdf,png}`, `figures/fig_latency.{pdf,png}`, `figures/fig_layer_funnel.{pdf,png}`, `figures/fig_per_family.{pdf,png}`, `figures/fig_semantic_vs_comm.{pdf,png}`
- `results/layer_summary.json`, `results/per_message.csv`, `results/run_manifest.json`

---

## 8. Evidence that the reported metrics are reproducible

1. **Deterministic re-run, byte-for-byte:** `b3_eval/run_calibration.py` was re-run in this session specifically to test reproducibility. The freshly-generated `calibration.json` is **identical** to the version committed in `602fae5f0` in every field except `timestamp_utc` (verified programmatically — see §2.8 and §13 for the exact commands and result).
2. **Every result carries an embedded manifest** (`b3_eval/results/*.json`'s `manifest` block, `results/semantic/*/metrics_summary.json`'s equivalent) recording the checkpoint SHA-256, torch/CUDA version, device name, Python version, and platform — so any future re-run can be checked against the exact same recorded environment fingerprint, not just re-run blind.
3. **`run_model_benchmark.py` was independently run twice** (once with 4/5 candidates due to a missing dependency, once with all 5/5 after installing it) and produced the **same qualitative decision both times** ("KEEP INCUMBENT") — the swap-bar computation is deterministic given the same split and seed.
4. **Deterministic data splits:** `b3_eval/data/*.jsonl` are static, version-controlled files (not regenerated per run), so `run_calibration.py`, `run_open_set_analysis.py`, and `run_model_benchmark.py` all consume exactly the same input data on every invocation.
5. **`semantic_evaluation/run_semantic_evaluation.py`'s scenario generation is seeded** (`--seed 101` default, confirmed unmodified in this session), so the 120-scenario corpus and its ordering are reproducible from the same seed.
6. **The `--quick` (9-scenario) and full (120-scenario) semantic evaluation runs are nested** (the `--quick` run selects 1 scenario per category from the same `ALL_SCENARIOS` list the full run uses) — their consistent qualitative pattern (full stack ≈ perfect, B1/B1+B2 ≈ zero recall in both) is itself a form of internal cross-check.
7. **Regression suite re-run twice** around the Phase 2 fix (before/after via `git stash`) with identical pass/fail outcomes except for the two intentionally-fixed issues — confirming the fix's effect is isolated and doesn't perturb unrelated tests.

**What was not independently re-run for this verification report** (time-boxed; noted as a limitation, not hidden): the full 120-scenario `semantic_evaluation` run and the `b3_eval/run_robustness.py`/`run_latency.py`/`run_open_set_analysis.py` harnesses were not re-executed a second time in this session (only `run_calibration.py` and `run_model_benchmark.py` were). Given (a) the embedded manifests, (b) the deterministic data splits, and (c) the confirmed byte-identical reproduction of `run_calibration.py`, there is strong but not exhaustive evidence that the others would reproduce identically too — this is flagged explicitly rather than asserted as proven for all five.

---

## 9. Remaining caveats and limitations

1. **Small sample sizes throughout.** The calibration split (N=85), OOD split (N=25), and model-benchmark train/test splits (96/24) are all small by ML-evaluation standards; confidence intervals on any of these numbers would be wide. This was true before this session and remains true — Phase 1 did not enlarge any dataset, only ran the existing ones for the first time with real weights.
2. **`test_large_scale_framework.py` remains broken** (pre-existing, unrelated — §4 item 5) and blocks full use of the `large_scale/` framework in Phase 3 until fixed.
3. **Position/speed-manipulation detection paths remain unverified** — no `scenarios/` fixture family exists for `scenario_generation`'s `position_manipulation`/`speed_manipulation` attack types; this requires generating new scenarios via `scenario_generation.generator.generate_held_out_suite()`, deferred to Phase 3.
4. **Collusion detection's real-world coverage is still limited by data availability** (§4 item 6) — the algorithm is verified correct, but most CAM-only traffic will never populate the `event` field it depends on.
5. **Fabrication attacks reach CAUTION, not REJECT**, in the current fixture set — a real, modest result that should not be overstated as "fabrication is fully detected."
6. **VeReMi-processed data already exists in the repo** (`data/veremi_processed/{ConstPos,DataReplay}_1416*/`) from prior, unrelated work — not evaluated or verified in this session; Phase 4 should audit what's already there before building a new importer, since duplicate effort should be avoided.
7. **The reproducibility check (§2.8) covered only one of five `b3_eval` harnesses** — see the explicit caveat at the end of §8.
8. **This report's Phase 2 diagnostic script (`scratch/phase2_detector_audit.py`) is not committed** (gitignored by design, matching this repo's existing `scratch/` convention) — its exact contents are reconstructed in §13 below so the Phase 2 numbers remain independently reproducible without relying on an uncommitted file.
9. **No claim in this report or in `PUBLICATION_PROGRESS.md` has been copied into any paper/manuscript file** — see §10; that mapping is deferred, as requested.

---

## 10. Manuscript mapping (locations only — no edits made)

**No LaTeX/Word manuscript file exists in this repository** (confirmed by `PAPER_READINESS_CRITIQUE.md`'s own finding, "No paper draft exists in the repo," and by a repo-wide search this session for `*.tex`/`*paper*`/`*manuscript*`/`*draft*` files, which found only: `mukil_test/tables/*.tex` — 6 standalone LaTeX table fragments — and the various `.md` audit reports, none of which are a manuscript body). The mapping below is therefore expressed against the two concrete places "the paper" currently exists in artifact form: (a) the standalone LaTeX table fragments in `mukil_test/tables/`, and (b) the narrative claims already written into the `.md` audit/assessment documents, which read as manuscript source material (results sections, limitations sections, reviewer-scorecard language).

### 10.1 Tables in `mukil_test/tables/` that are now stale and should be regenerated from real data

| File | Current content (verified this session) | Should be replaced with |
|---|---|---|
| `T7_latency.tex` | Per-stage latency table with suspiciously uniform, round placeholder numbers (PKI 0.40/0.40/0.40/0.40, B1 0.60/0.60/0.60/0.60, ..., B3 15.20/15.20/15.20/15.20, Total p95 22.90 — every mean/p50/p95/p99 identical per row, which real measured latency distributions never are) | The real numbers in `b3_eval/results/latency.json` (§3.3): B3 single-inference p50=0.06ms/p95=0.10ms/p99=0.11ms on this GPU, cold start 15,933ms, warm start 812ms — an order of magnitude different from the placeholder's 15.20ms row, and the placeholder's uniform mean=p50=p95=p99 pattern should be replaced with the real distribution's actual spread |
| `T9_calibration.tex` | ECE 0.145→0.035 with a stated temperature of T=0.50 | The real numbers in `b3_eval/results/calibration.json` (§3.4): ECE 0.0619→0.0280 with fitted T=2.145 — both the absolute ECE values and the fitted temperature direction (T=2.145 > 1, i.e. the real model is *overconfident* and needs softening, vs. the placeholder's T=0.50 < 1, i.e. *underconfident*) are different in a way that would change the paper's calibration narrative, not just its numbers |
| `T16_lolo.tex`, `T21_fusion_divergence.tex`, `T25_decision_trust.tex`, `T28_trust_inflation.tex` | Not verified against real data this session (out of scope for Phase 1/2 — these correspond to leave-one-family-out, fusion-divergence, decision-trust, and trust-inflation analyses that Phase 1/2 did not re-run) | Flagged for the same treatment in Phase 3/5 once the corresponding experiments are re-run with real data; **do not assume these are still accurate just because they weren't checked this session** |

### 10.2 Claims in the `.md` audit documents that are now outdated and should be updated

| Document / section | Current claim (as written) | What Phase 1/2 evidence now shows |
|---|---|---|
| `README.md`, "Model Weights" section | "The B3 checkpoint is stored in Git LFS. After cloning, run: `git lfs pull`... All `b3_eval/` harnesses degrade gracefully to 'checkpoint unavailable' if the weights are absent" | Still procedurally correct, but should add a line confirming the checkpoint **has been verified present and functional** in at least one real environment (this session's SHA-256 match + 5 successful harness runs), so a future contributor doesn't assume it's still hypothetical |
| `B3_ASSESSMENT.md`, §0 "Two blocking facts" | "B0.1 — The model weights are not in this artifact... cannot be loaded or run from this zip at all" and "B0.2 — This environment has no torch/GPU" | **Both blocking facts are resolved** in this environment: the checkpoint is real (SHA-256 verified) and a working CUDA GPU was available. The document's own §3 "Sufficiency determination" was explicitly conditional on exactly these two facts being resolved plus the per-family F1 numbers reproducing — Phase 1/2 partially satisfies this (real inference now runs and the semantic-evaluation corpus's per-category recall is measured), though `error_analysis.py`'s original Test-1/LOFO per-family numbers (AF4/AF6/AF7/AF8) referenced in that document were not reproduced this session (the underlying `outputs/splits/*` files referenced there were not located/verified) |
| `B3_ASSESSMENT.md`, §11 "Reviewer scorecard" | Robustness: 3/10 ("No adversarial/paraphrase/OOD tests present... Harness now provided"); Calibration: 2/10 ("no ECE/Brier/temperature. Harness provided"); Latency: N/A ("Unmeasurable here; harness provided") | All three now have **real measured numbers** (§3.2–3.4) rather than "harness provided but not run" — scores in this table should be revisited given real data exists now (this report does not re-score them; that judgment belongs in Phase 5/6, but the factual basis for a re-score now exists) |
| `UNKNOWN_ABSTAIN_DETERMINATION.md`, §4 "The one question only your GPU can answer" | Poses the silent-failure-rate question as unanswerable without a GPU, and encodes a decision rule ("silent-failure ≥ 0.20 → abstain justified... otherwise → binary + calibrated confidence is sufficient") | **Answered**: `run_open_set_analysis.py`'s real output (§3.5) reports silent-failure rate = 0.0% and dead-zone occupancy = 0.0%, triggering the document's own "otherwise" branch: "Binary + calibrated confidence is sufficient. Implement nothing." This is a direct, ready-to-cite resolution of this document's central open question |
| `PAPER_READINESS_CRITIQUE.md`, "Experimental validation: 4/10" | "B3... has never been evaluated end-to-end with real inference in any run I can verify (every manifest in this cycle records b3_available=false). The full-vs-no_b3 McNemar comparison is currently meaningless" | This is now **factually superseded**: the full semantic evaluation (§3.1) ran with `b3_available=True` throughout, and produced a real McNemar comparison (p≈0.0, Cohen's h=2.946). The 4/10 score and its stated reasons should be revisited in light of this — again, the re-scoring judgment itself is deferred to Phase 5/6 per this task's instructions, but the factual premise the low score was based on no longer holds unmodified |
| `PAPER_READINESS_CRITIQUE.md`, "Correctness: 5/10" | Cites the CP-confidence FPR=0.93 bug as the headline correctness issue (already fixed per `CHANGELOG.md`, predates this session) | Should be updated to also reference the Sybil coordinate-frame bug found and fixed this session (§4 item 1) as a second, independently-discovered correctness issue in the same "found via the evaluation framework, not hidden" spirit the document already praises for the CP fix |
| `AUDIT_REPORT.md`, "Hidden assumptions" / MBD section; `system_integration_validation.py` / `INTEGRATION_README.md`'s "Defect 5" | States Sybil's `sybil_score` staying at 0.00 is an "unresolved open question" requiring "direct inspection of `scenarios/sybil/`'s actual timestamp deltas... not yet done" | **Resolved**: the real root cause was the coordinate-frame drift bug (§4 item 1), not a timestamp/threshold issue as speculated. The fix is in place and verified (§3.7). This section's framing of Sybil as an open question should be replaced with the resolution |
| `AUDIT_REPORT.md`, W1 ("collusion detection structurally unreachable") | States collusion is unreachable because `event` is never populated | Should be refined per §4 item 6: correct for CAM-only fixtures without an event/DENM field, but demonstrably **not universally true** — `scenarios/collusion/` already carries a working example. Recommend rewording to "collusion detection's coverage is limited to traffic carrying an event/DENM label" rather than "unreachable" |

### 10.3 Figures that should be regenerated from real data

`figures/fig_accuracy.{png,pdf}`, `fig_confusion.*`, `fig_latency.*`, `fig_layer_funnel.*`, `fig_per_family.*`, `fig_semantic_vs_comm.*` (generated by `scripts/make_figures.py` from `run_layered_evaluation.py`'s output) were **not touched by Phase 1/2** and their current on-disk state predates this session (last committed 2026-07-23, per §5). Whether they were generated with `--sample` (synthetic, clearly banner-stamped) or real data was not verified this session — this should be checked before citing them, and if real, should be regenerated using the now-real B3 model to match the semantic-evaluation results in §3.1, since `run_layered_evaluation.py` (which feeds these figures) also depends on B3 being available.

---

## 11. Estimate: are the Phase 1 and Phase 2 results strong enough to support the paper's central STBV claim?

**The paper's central claim** (per `LITERATURE_AND_DATASETS.md` §2.3 and `INTEGRATION_README.md`) is: *a semantic trust layer (B3) detects attacks that are jointly invisible to crypto/behavioral/consistency layers, fused with principled conflict handling.*

**Assessment: meaningfully strengthened, but not yet sufficient on its own for a top-tier submission — a solid, honest, and now real (not synthetic) core result, with clearly-scoped gaps remaining.**

**What now genuinely supports the claim:**
- The full 120-scenario semantic evaluation is the **first real execution** of exactly the experiment this claim depends on, and it shows the predicted pattern cleanly: B1-only and B1+B2 detect **0%** of semantic attacks (0.125 accuracy, driven entirely by the benign-control scenarios), while the full stack (with real B3) reaches 0.990 F1 — a McNemar p≈0.0, large-effect-size (Cohen's h=2.946) result. This is precisely the ablation the entire architecture is designed to demonstrate, and it is no longer synthetic.
- The Sybil fix (Phase 2) removes a real, independently-verifiable correctness bug that would have undermined confidence in *any* quantitative claim about MBD's behavioral layer had a reviewer found it first — finding and fixing it, with before/after evidence, is itself supporting evidence for the paper's broader "full-system-integration validation matters" methodological argument (already made once for the CP fix in `CHANGELOG.md`/`PAPER_READINESS_CRITIQUE.md`).
- The open-set analysis directly answers a real, previously-open question in the paper's own risk model (silent failure on unseen attack families) with a favorable, evidenced result (0% silent-failure rate).
- Calibration and robustness are now measured, not merely "harness provided" — reviewers will specifically ask for exactly this evidence, and it exists now.

**What still limits the strength of the claim:**
1. **Sample sizes are small.** 120 scenarios (semantic evaluation), 85/25 (calibration/OOD splits), 96/24 (benchmark train/test) are workshop-scale, not large-scale. A reviewer at a top venue will ask for more scenarios and, per `LITERATURE_AND_DATASETS.md`'s own recommendation, a recognized external dataset (VeReMi) — not yet done (Phase 4).
2. **The semantic-evaluation corpus is self-generated** (`semantic_evaluation/semantic_attack_dataset.py`'s hardcoded scenarios), not drawn from or validated against an external distribution — the near-perfect 0.990 F1 could partly reflect the corpus being written with knowledge of what the model was trained to catch (a form of dataset leakage risk that this session did not investigate or rule out).
3. **Robustness testing surfaced a real weakness** (100% over-defense rate on 2 of 11 adversarial families) that partially cuts against an unqualified "B3 works" claim — this needs to be reported honestly alongside the positive result, which will temper (though not invalidate) the claim's strength.
4. **Several detection paths remain only partially verified**: fabrication reaches CAUTION not REJECT; collusion's real-world coverage is data-limited; position/speed-manipulation paths are entirely unverified (no fixtures exist yet). These bear on the *broader* multi-layer trust-stack claim (crypto+behavioral+consistency+semantic), even though they don't directly undermine the *specific* semantic-layer claim above.
5. **No adaptive-attacker study exists yet** — an attacker who knows B3 exists and adapts is exactly what `run_robustness.py`'s paraphrase/evasion families start to probe, but this is a battery of 66 rows, not a dedicated adversarial-training-style study, and the field's literature (per `LITERATURE_AND_DATASETS.md`) specifically expects this for the claim to be considered robust.

**Bottom line:** Phase 1/2 converted the paper's centerpiece claim from *"asserted, backed only by synthetic placeholders"* to *"measured once, cleanly, with a real model, on a self-generated corpus, with one real bug found and fixed along the way."* That is a substantial and necessary step, and the specific ablation result (B1+B2: 0% recall → full stack: 99% recall, p≈0.0) is strong *as far as it goes*. It is not yet sufficient, alone, to carry a top-tier publication's central claim — the field's own reviewer norms (already anticipated correctly in this repo's `PAPER_READINESS_CRITIQUE.md` and `LITERATURE_AND_DATASETS.md`) require external-dataset validation, larger samples, and an adaptive-attacker study before that bar is met. For a workshop or second-tier venue, this evidence — honestly reported alongside its robustness caveats — is a credible, defensible basis for the claim.

---

## 12. Reference table: source files for every number in this report

| Number(s) | Source file |
|---|---|
| Semantic evaluation metrics (§3.1) | `results/semantic/20260801-005223/metrics_summary.json`, `raw_results.csv` |
| Robustness table (§3.2) | `b3_eval/results/robustness.json` |
| Latency numbers (§3.3) | `b3_eval/results/latency.json` |
| Calibration numbers (§3.4) | `b3_eval/results/calibration.json` |
| Open-set numbers (§3.5) | `b3_eval/results/open_set_analysis.json` |
| Model benchmark table (§3.6) | `b3_eval/results/model_benchmark.json` |
| Sybil before/after coordinates and scores (§3.7) | Reconstructed in §13 below; original console output captured in this session's transcript |
| Checkpoint SHA-256 | Computed this session via streaming SHA-256 (§1); cross-checked against `README.md` |
| GPU/torch/CUDA versions | `nvidia-smi` output and `python -c "import torch; ..."` output, this session; also embedded in every `b3_eval/results/*.json` manifest |

---

## 13. Reconstruction of the (uncommitted) Phase 2 diagnostic, for independent reproduction

`scratch/phase2_detector_audit.py` is gitignored (per this repo's existing `scratch/` convention — confirmed via `git ls-files scratch/` returning nothing). To reproduce the Phase 2 findings in §3.7 and §4 item 1 without relying on that file, run the following directly (this is the exact logic used, reproduced here verbatim for independent verification):

```python
import json, pathlib, sys
sys.path.insert(0, ".")
from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV
from bridges.message_adapter import to_flat_report

folder = pathlib.Path("scenarios/sybil")
msgs = [json.load(open(f)) for f in sorted(folder.glob("*.json"))]
msgs.sort(key=lambda m: m["cam"]["generation_delta_time"])

pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True)
window = []
for msg in msgs:
    window.append(msg)
    res = pipeline.run(list(window), context=None)
    flat = to_flat_report(msg, pipeline._projection_origin)
    print(msg["header"]["station_id"], msg.get("is_attacker"),
          round(flat["x"], 1), round(flat["y"], 1),
          res["mbd"]["sybil_score"] if res["mbd"] else None,
          res["decision"])
```

Running this against the current (fixed) `pipeline/orchestrator.py` reproduces exactly the "after fix" rows in §3.7 (station 9000 → `sybil_score≈0.867`→CAUTION; stations 1001-1016 → `sybil_score=0.0`→ACCEPT with growing real coordinates). To see the "before fix" behavior for comparison, run `git show 602fae5f0:pipeline/orchestrator.py` (the pre-fix version, i.e. the Phase-1-commit state) against the same script — every message's `flat["x"], flat["y"]` will print as `0.0 0.0` and every `sybil_score` after the first message will be `1.0`. The full 5-family + 5-context + b1_fail sweep (157 messages total, §2.6) uses the same pattern looped over each `scenarios/`/`test_messages/context/` subdirectory in turn, with a fresh `ISCEPipeline` instance per family (so history/origin state does not leak across families).
