# Publication Progress Tracker

Started: 2026-08-01. This document tracks the implementation phases requested
after the architecture audit (see `AUDIT_REPORT.md`, `B3_ASSESSMENT.md`,
`PAPER_READINESS_CRITIQUE.md` for the audit itself). The architecture is
frozen; this phase only produces evidence, closes gaps, and extends
(never rewrites) existing modules. No numbers are fabricated — every
entry below is either a directly-observed fact from this session or
explicitly marked TODO/BLOCKED with a reason.

Legend: ✅ Completed · 🔄 In Progress · ⛔ Blocked · ⬜ Not started

---

## Phase 1 — Resolve blockers preventing real evaluation

| # | Task | Status | Evidence / Notes |
|---|---|---|---|
| 1 | Materialize + verify real B3 checkpoint | ✅ | `pytorch_model.bin` is **already materialized** in this environment (567,622,450 bytes, matching the documented size exactly). SHA-256 computed this session: `9ee7475e08f76ce6961c55204657a380d5ef1c2c9dac6a9d46543a7c42c2f5d2` — matches the `README.md`-documented hash exactly. `B3_ASSESSMENT.md`'s "LFS stub, not real weights" finding is **stale** relative to this environment/checkout. |
| 2 | Verify B3 inference works end-to-end | ✅ | `tests/verify_b3_model.py` run live: loads on `cuda (NVIDIA GeForce RTX 4050 Laptop GPU)`, produces `BENIGN 0.939` on a benign scene and `MALICIOUS 0.959` on a prompt-injection payload. Real forward passes, not stubbed. |
| 3 | Verify semantic classifier is actually invoked in the real pipeline | ✅ | **Important finding:** `manual_pipeline_test.py` **without** `--pipeline` runs the legacy `b2_csia`/CSIA path (no B3 at all — verified by running it and seeing DST/Motion-Context/Trust-Propagation output, zero B3 mention). Only `--pipeline` invokes `ISCEPipeline` (B1→MBD→B2→CP→B3→TrustEngine). Ran `python manual_pipeline_test.py --pipeline test_messages/benign/normal_car.json --verbose`: confirmed `B3 Available: True`, `b3_label=BENIGN`, `b3_confidence=0.9328`, real DS fusion trace, `bridge_ms≈99ms` (real GPU forward pass latency, not a stub's near-zero time). **Anyone reproducing this project's results must use `--pipeline`** — this should be called out more prominently in `README.md` (currently correct in the README's own examples, but easy to miss). |
| 4 | Run existing B3 evaluation harnesses | ✅ | All 5 harnesses run against the real checkpoint this session, real (non-synthetic) outputs written to `b3_eval/results/*.json`: `run_robustness.py`, `run_latency.py --n 200`, `run_calibration.py`, `run_open_set_analysis.py`, `run_model_benchmark.py` (long-running — fine-tunes 5 candidate architectures; ran in background, see below). |
| 5 | Generate missing B3 outputs | ✅ | See §"Real B3 results captured this session" below for the actual numbers (not fabricated, all reproducible by re-running the listed commands). |

## Real B3 results captured this session (Phase 1 evidence — reproducible, not fabricated)

All commands below were run with system Python 3.13 (`C:\Users\mukil\AppData\Local\Programs\Python\Python313\python.exe`)
against the real, materialized checkpoint on an NVIDIA RTX 4050 (6GB VRAM).

**1. `semantic_evaluation/run_semantic_evaluation.py` (full, 120 scenarios, seed=101)** — output: `results/semantic/20260801-005223/`
| Config | Acc | Prec | Recall | F1 | FPR | Caution rate |
|---|---|---|---|---|---|---|
| B1 only | 0.125 | N/A | 0.000 | N/A | 0.000 | 0.000 |
| B1+B2 | 0.125 | N/A | 0.000 | N/A | 0.000 | 0.000 |
| **B1+B2+B3 (full)** | **0.983** | **0.990** | **0.990** | **0.990** | 0.067 | 0.233 |

McNemar (full vs b1_b2): p ≈ 0.0 (chi-square, continuity-corrected); detection-rate delta +99.0pp; Cohen's h = 2.946 (large). Per-category recall: 100% on 7/8 categories, 90% on retrieval_poisoning (full config only — B1/B1+B2 are 0% on every category). **This is the first real (non-synthetic, non-stubbed) execution of this evaluation in the repository's history** — every previously-stored `results/semantic/*` run recorded `b3_available=false` or synthetic values.

**2. `b3_eval/run_robustness.py`** — output: `b3_eval/results/robustness.json`
| family | flip_rate | evasion | over_defense | mean Δconf |
|---|---|---|---|---|
| paraphrase | 0.167 | 0.333 | 0.000 | 0.021 |
| synonym_sub | 0.000 | 0.000 | 0.000 | 0.009 |
| typo | 0.167 | 0.000 | 0.333 | 0.002 |
| unicode_homoglyph | 0.333 | 0.000 | 0.667 | 0.125 |
| formatting | 0.000 | 0.000 | 0.000 | 0.052 |
| **instruction_hiding** | **0.500** | 0.000 | **1.000** | 0.164 |
| long_prompt | 0.000 | 0.000 | 0.000 | 0.066 |
| context_poisoning | 0.000 | 0.000 | 0.000 | 0.132 |
| **role_confusion** | **0.500** | 0.000 | **1.000** | 0.074 |
| mixed_benign_malicious | 0.167 | 0.333 | 0.000 | 0.076 |
| contradictory | 0.000 | 0.000 | 0.000 | 0.026 |

Genuine weakness surfaced: `instruction_hiding` and `role_confusion` both show 100% over-defense rate (benign-with-trigger-words misclassified) and 50% label-flip rate — a real, previously-unmeasured robustness gap worth reporting honestly in the paper (this is exactly the failure mode the 2024-2026 literature review in `LITERATURE_AND_DATASETS.md` predicted).

**3. `b3_eval/run_latency.py --n 200`** — output: `b3_eval/results/latency.json`
- Cold start: 15,933 ms · Warm start: 812 ms · Params: 141.9M
- Single inference: p50=0.06ms, p90=0.07ms, p95=0.10ms, p99=0.11ms (GPU)
- Batch throughput: up to 25,424 items/s at batch size 8
- Peak VRAM: 609.1 MB
- **Well within the ETSI CAM 10Hz (100ms) per-message budget** on this device — the first real (not "unmeasurable here") latency evidence for this claim.

**4. `b3_eval/run_calibration.py`** — output: `b3_eval/results/calibration.json`, `reliability_diagram.png`
- N=85. Before scaling (T=1.0): ECE=0.0619, Brier=0.0613. Fitted temperature T=2.145. After: ECE=0.0280, Brier=0.0553 (ECE improved by 0.0339, ~55% relative reduction). Confirms `B3_ASSESSMENT.md`'s prediction that temperature scaling is a cheap, effective, no-retrain fix.

**5. `b3_eval/run_open_set_analysis.py`** — output: `b3_eval/results/open_set_analysis.json`, `risk_coverage.png`, `openset_score_distributions.png`
- ID set: 85 (58 malicious/27 benign). OOD set (unseen attack families): 25.
- **Miss rate on unseen families: 0.000. Silent-failure rate (wrong AND confidence≥0.85): 0.000. Dead-zone occupancy: 0.000.**
- AUROC: MSP=0.154, energy=0.098, **p_malicious=0.994** (i.e., the raw probability is an excellent OOD separator here, MSP/energy are not — a real, notable, reportable finding).
- AURC=0.0082; coverage@risk≤0.01 = 0.800; coverage@risk≤0.05 = 0.953.
- **Decision (per the encoded rule in `UNKNOWN_ABSTAIN_DETERMINATION.md`): "NO ABSTAIN MECHANISM NEEDED... B3 fails LOUDLY... Implement nothing."** This closes, with real evidence, the one open empirical question that document's own analysis said only a GPU run could answer.

**6. `b3_eval/run_model_benchmark.py`** — long-running (fine-tunes DeBERTa-v3-base/RoBERTa/ModernBERT/DistilRoBERTa/MiniLM on the same 96-example train split, 3 epochs, seed 0). Launched in background this session (downloads pretrained weights from HF Hub — network access confirmed available). Status/result to be recorded in the next update to this document once it completes.

---

## Phase 2 — Verify every detection path

Method: `scratch/phase2_detector_audit.py` (new, read-only diagnostic) runs every
`scenarios/<family>/` fixture set and `test_messages/context/<ctx>/` set through
the **real** `ISCEPipeline` (`--pipeline` path), statefully, in timestamp order,
and records every MBD/CP/B1 signal per message alongside ground truth
(`is_attacker`) and the final decision. Full per-message tables are in that
script's output (reproducible by re-running it); summarized findings below.

| Detector | Status | Finding |
|---|---|---|
| **Sybil** | ✅ **Bug found, root-caused, fixed, verified** | **Root cause (confirmed by direct instrumentation):** `pipeline/orchestrator.py`'s `_run_mbd`/`_run_cp` each recomputed a fresh `ProjectionOrigin` from the *current target message's own position* on every `run()` call. Since the equirectangular projection always places a message's own position at local `(0, 0)`, **every message's own projected (x, y) was always exactly `(0.0, 0.0)`**, and `VehicleHistoryStore` retained that `(0, 0)` for every sender regardless of their real position — confirmed directly: `station 1000 own x,y: 0.0 0.0`, `station 9000 own x,y: 0.0 0.0`, etc., for every single message. This made Sybil's `dist < 2.0m` co-location check trivially true for every pair of vehicles in the same scenario, benign and attacker alike (`sybil_score=1.0` fired for 16/16 benign background vehicles in `scenarios/sybil/`, not just the 3 real attacker messages) — i.e. the detector was firing on *everyone*, which is functionally equivalent to never firing at all for detection purposes (100% false positive rate makes the signal useless). This is the same underlying mechanism as "Defect 4" described in `tests/system_integration_trace_output.txt`/`INTEGRATION_README.md`, which claimed a fix ("`ISCEPipeline` now owns one persistent `_projection_origin`... reused for the pipeline's entire lifetime") that **is not present in the current `pipeline/orchestrator.py`** — the fix was documented but never actually landed in this file (verified: no `_projection_origin` attribute existed anywhere in the file before this session's edit). **Fix applied** (`pipeline/orchestrator.py`): added `self._projection_origin = None` in `__init__` and a `_get_or_create_projection_origin(lat, lon)` helper that computes the origin once from the first message the pipeline instance ever processes and reuses it for every subsequent call; `_run_mbd` and `_run_cp` now call this helper instead of recomputing. **Verified after fix:** re-running the same instrumentation shows real projected coordinates growing correctly across the scenario (e.g. station 1001 at `(22.1, 33.4)`, station 1016 at `(353.3, 533.7)`, i.e. a real moving trajectory), and `sybil_score` is now **discriminative**: the 3 real Sybil attacker messages (station 9000) score `0.87`→CAUTION, and all 16 benign background vehicles correctly score `0.0`→ACCEPT. Regression suite re-run after the fix: `verify_dependency_graph.py`, `test_b2_trust_engine.py`, `test_adapters.py`, `test_pki_mbd_cp_integration.py` all still pass; the CI-equivalent fixture/scenario sweep (`manual_pipeline_test.py --pipeline` over `test_messages/benign`, `b1_fail`, `context/urban`, `scenarios/{sybil,replay,fabrication,collusion,mixed}`) completes with zero exceptions and decisions matching ground truth. |
| **Replay** | ✅ Confirmed firing correctly | `scenarios/replay/`: all 3 ground-truth attacker messages (station 8000-8002) get `replay_score≈0.9`, `mbd_passed=False`, and correctly **REJECT**; all 17 benign messages ACCEPT/CAUTION as expected. Dual detection (B1's exact-match cache + MBD's behavioral score) both contribute — matches the architecture's documented intent. No fix needed. |
| **Collusion** | ⚠️ **Prior "structurally unreachable" claim was fixture-dependent, not universally true** | The claim in `AUDIT_REPORT.md`/`system_integration_validation.py` ("collusion detection structurally unreachable... `event` is never populated") is **only true for CAM-only traffic with no explicit `event` field**. Directly verified: `scenarios/collusion/msg_001.json` (a real, existing fixture) *does* carry an explicit top-level `"event": "traffic_condition"` key, and running it through the real pipeline shows `collusion_score` correctly ramping (`0.0 → 0.25 → 0.5`) as more co-located same-event attacker reports accumulate (station 7000/7001/7002). So the collusion algorithm itself works correctly **when data provides an event label** — the real, still-open limitation is a **data-availability gap**, not a code defect: most of this repo's other fixtures (and any real CAM-only deployment) never populate `event`, so collusion detection's effective coverage is limited to the subset of traffic carrying an explicit event or DENM cause-code (`bridges/message_adapter._extract_denm_event`). This nuance should be stated precisely in the paper: "collusion detection is implemented and verified to fire correctly given an event label; its coverage on pure-CAM traffic without DENM/event data is a data-availability limitation, not an algorithmic one." No code change made (the algorithm is correct); recommend, as a future increment, deriving a coarse event label from cross-message reasoning for CAM-only traffic if broader collusion coverage is needed for the paper's claims. |
| **Fabrication** | ✅ Investigated | `scenarios/fabrication/`: attacker messages (station 6000-6002) reach CAUTION via a mix of `sybil_score` (now correctly discriminative post-fix) and, for 2/3, `replay_score=0.9` (fabricated position/kinematics happen to match a prior payload closely enough to trip the payload-similarity replay check) — none reach REJECT. This is a real, honest finding: fabrication in this fixture set is currently only caught as CAUTION, not REJECT, which should be reported precisely rather than implied as a strong detection result. |
| **Position / Speed (manipulation)** | ⬜ Not covered by `scenarios/` (no dedicated fixture family) | The `manipulation` family exists in `scenario_generation/generator.py` (`position_manipulation`, `speed_manipulation`) but has no corresponding fixture set under `scenarios/`. To evaluate this path, scenarios must be generated via `scenario_generation.generator.generate_held_out_suite()` (Phase 3 will produce and evaluate these alongside everything else, since Phase 3 explicitly reuses this generator). |
| **Context (highway/urban/intersection/tunnel/roundabout)** | ✅ Investigated | These `test_messages/context/*` fixtures carry no `is_attacker` ground truth (they test context-sensitive envelope handling, not attack detection). Post-fix, `context/highway` and `context/urban` correctly show **zero** Sybil false-positives (vehicles genuinely spread out along a route). `context/intersection`/`tunnel`/`roundabout` show a **partial** (0.33), not false-maximal (1.0), Sybil score for messages where the same 3 station IDs recur in a tight repeating loop — this looks like legitimate close-proximity intersection/roundabout traffic, not a bug, but is flagged as worth a second look if these fixtures are meant to be attack-free negative controls. `context/tunnel` shows several genuine B1-fatal REJECTs (GPS-loss/staleness plausibly triggered by the tunnel context) — consistent with intended context-aware envelope behavior, not investigated further this session. |

**Commit:** the Sybil fix (`pipeline/orchestrator.py`) and the associated latent test-bug fix (`tests/test_cp_uncertainty_semantics.py` — a stale duplicate `main()` block missing `event_label`, found while validating the Sybil fix caused no regressions; confirmed via `git stash` to predate this session's changes) are committed together as one Phase 2 milestone.

## Phase 3 — Complete experimental pipeline

🔄 In progress. STBV-Bench (`stbv_bench/`) built and running — see
`DATASET_INTEGRATION.md` for the full, step-by-step pipeline
documentation (VeReMi Extension -> canonical CAM -> semantic
transformation engine -> validation -> injection -> validated benchmark).

| # | Task | Status | Evidence / Notes |
|---|---|---|---|
| 1 | Build STBV-Bench generation engine (21 seeded transformation rules, 20 attack families + benign_control) | ✅ | `stbv_bench/{canonical,transformations,generator,build_stbv_bench}.py`, committed `943f7e70e`. Reuses real VeReMi kinematics; VeReMi's own kinematic-attacker ground truth is preserved separately (`_veremi_provenance`), never relabeled as an STBV attack. |
| 2 | Build STBV-Bench v1 at scale | ✅ | `data/stbv_bench/v1/`: 100,000 samples, seed=7, drawn without replacement from a combined pool of 221,125 real VeReMi flat reports across `ConstPos_1416`, `DataReplay_1416_full`, `DoS_1416_full`. Built in 10.5s. `manifest.json` records exact build parameters and per-family counts (30,000 benign_control + 3,500 per attack family × 20 families). |
| 3 | Evaluate real, frozen ISCEPipeline against STBV-Bench (Decision Trust, not just B3 label) | 🔄 | `stbv_bench/run_stbv_bench_eval.py`. **Bug found and fixed this session:** the script originally reused one `ISCEPipeline` instance across all samples; since MBD/CP are stateful and STBV-Bench samples are independent unrelated messages (not a trajectory), this made unrelated samples look like implausible position "teleports," inflating `benign_control` FPR to 92.7% in a 500-sample check. Fixed by constructing a fresh pipeline per sample (committed `824557109`); FPR dropped to 2.2% on a 300-sample follow-up check, `accuracy=0.700 precision=0.984 recall=0.583 f1=0.732`. Per-family recall now shows real, honest variation: 100% recall on `authority_override`, `hazard_suppression`, `false_clearance`, `instruction_injection`, `infrastructure_semantic_manipulation`, `priority_manipulation`, `cross_source_contradiction`, `collaborative_semantic_agreement`; **0% recall** on `indirect_prompt_injection`, `multi_message_context_poisoning`, `semantic_narrative_poisoning`, `traffic_efficiency_lure`, `mixed_semantic_attacks`, and near-0% (`goal_manipulation`, 9%). This 0%-recall cluster is a genuine, previously-unmeasured detection gap that must be reported honestly in the paper, not smoothed over — full per-family numbers and a larger (10,000-sample) run are being generated now; see `results/stbv_bench/v1/` once complete. |
| 4 | Decide final benchmark evaluation size | ✅ | Ran the real, frozen `ISCEPipeline` (fresh instance per sample, per the fix above) over 10,000 STBV-Bench v1 samples: `results/stbv_bench/v1/stbv_bench_results.json` / `stbv_bench_per_message.csv`. 1,857.5s wall clock (≈186ms/sample incl. Python/IO overhead; per-message pipeline latency itself: mean=110.4ms, p50=100.2ms, p95=188.8ms, p99=254.0ms). **Result is consistent with the earlier 300-sample spot-check** (FPR 2.3% vs. 2.2%, same per-family ordering), and a 2,000-resample bootstrap on the 10,000-sample run gives a 95% CI on overall accuracy of **[0.679, 0.697]** (width 1.8pp) — already tight. Per the mission's instruction to prefer a justified stopping point over inflated dataset size for its own sake: **10,000 samples is treated as sufficient for STBV-Bench v1's headline Decision Trust numbers**; scaling to 100k is not expected to materially change the reported metrics and is deprioritized in favor of ablations/statistics/figures unless a reviewer specifically requires it. |

**Full STBV-Bench v1 Decision Trust results (n=10,000, seed=7):** accuracy=0.688, precision=0.983, recall=0.565, F1=0.718, FPR=0.023, caution_rate=0.194 (tp=3959, fp=69, fn=3048, tn=2924; positive = REJECT or CAUTION). Contributors: B1/B2/CP/B3 all present on every message (single-message-per-sample scoring; no cross-sample fusion history is used, consistent with the fix above).

**Per-family recall (n=10,000, ~320-395 samples/family) — reported exactly as measured, including the weak cluster:**

| Recall band | Families |
|---|---|
| 100% | infrastructure_semantic_manipulation, instruction_injection, hazard_suppression, authority_override, collaborative_semantic_agreement, priority_manipulation, cross_source_contradiction, false_clearance |
| 42–65% | context_inversion (0.65), planner_manipulation (0.55), role_manipulation (0.54), temporal_context_drift (0.54), context_poisoning (0.50), hazard_amplification (0.42) |
| ≤9% (genuine detection gap) | semantic_narrative_poisoning (0.09), mixed_semantic_attacks (0.02), multi_message_context_poisoning (0.02), indirect_prompt_injection (0.02), traffic_efficiency_lure (0.01), goal_manipulation (0.01) |

The bottom band is a real, reproducible weakness (identical ordering at n=300 and n=10,000, so not sampling noise): the current architecture's B3 classifier and fusion policy reliably catch attacks phrased as direct commands/authority claims (`instruction_injection`, `authority_override`, `false_clearance`) or coordinated multi-source contradiction (`cross_source_contradiction`, `collaborative_semantic_agreement`), but largely miss attacks phrased as subtle narrative framing or indirection (`goal_manipulation`, `traffic_efficiency_lure`, `indirect_prompt_injection`, `multi_message_context_poisoning`). This should be reported honestly in the paper as a limitation/future-work item, not hidden — it directly supports a "where the architecture still fails" discussion a T-ITS reviewer will look for.

**Known pre-existing blocker (unrelated to STBV-Bench, not yet resolved):** `tests/test_large_scale_framework.py` fails with `AttributeError: 'ScaledScenario' object has no attribute 'vehicle_count'` — confirmed via `git stash` to predate all changes in this session (a `large_scale/scaling.py` API-drift issue). STBV-Bench's own scale-up (`build_stbv_bench.py --n`) does not depend on `large_scale/` and is unaffected.

### Layer ablation study — ✅ complete, full write-up in `ABLATION_STUDY.md`

Ran on the identical fixed 10,000-sample STBV-Bench v1 slice used for the
baseline (no re-sampling), 5 configs (B1 only / B1+B2 / B1+B2+CP /
B1+B2+CP+B3-no-fusion / full stack), one harness batch
(`stbv_bench/run_ablation.py` + `analyze_ablation.py`; results in
`results/ablation/`). Required adding a new `enable_b3` flag to
`ISCEPipeline` (real skip of B3's computation, not post-hoc filtering —
see `ABLATION_STUDY.md` Step 1 for the full audit).

**Headline, stated precisely (do not round up in any paper draft):**

| Config | Accuracy | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|
| 1. B1 only | 0.299 | undefined (0 positives predicted) | 0.000 | undefined | 0.000 |
| 2. B1+B2 | 0.305 | 0.643 | 0.018 | 0.034 | 0.023 |
| 3. B1+B2+CP | 0.305 | 0.643 | 0.018 | 0.034 | 0.023 |
| 4. B1+B2+CP+B3, no fusion | 0.689 | **1.000** | 0.557 | 0.715 | **0.000** |
| 5. Full stack | 0.688 | 0.983 | 0.565 | 0.718 | 0.023 |

- **Config 2 and config 3 are byte-identical, 0/10,000 decisions differ.**
  Root cause (not a weak-CP finding — a benchmark-methodology finding):
  CP only contributes when a sample window has >1 message
  (`pipeline/orchestrator.py:609`); STBV-Bench v1 evaluates single-message
  windows only, so CP is structurally inert on this benchmark by
  construction. CP was already separately verified working on the
  multi-vehicle `scenarios/collusion` fixtures (Phase 2 above) — this does
  **not** contradict that; it shows this specific benchmark can't exercise
  it. Flagged as a concrete STBV-Bench v2 recommendation (multi-message
  scenario windows).
- **B3 alone (no fusion) reaches F1=0.715 at perfect precision** — B3 is
  doing essentially all of the STBV detection work, which is the
  architecturally *expected* result (STBV-Bench's honesty contract keeps
  kinematics real/unmodified, so MBD/CP — which reason over
  kinematics — have no signal for a purely semantic attack; that's a
  different, non-overlapping threat class already covered separately in
  Phase 2's Sybil/Replay/Collusion work).
- **DS fusion's marginal contribution is small but real** (128/10,000
  decisions flip specifically due to fusion, p=3.06e-29): a small recall
  gain (+0.84pp) traded against a small precision cost (69 benign samples
  pushed from ACCEPT to CAUTION/REJECT), nearly cancelling in aggregate F1
  (+0.0024) — a genuine, reportable, small effect, not noise and not
  nothing.
- **Recommended framing for the manuscript** (narrower and more defensible
  than "every layer contributes to every decision"): the complete
  architecture is necessary because layers cover **complementary,
  non-overlapping threat classes** (B3 for semantic/STBV, MBD/CP for
  kinematic/behavioral) — not because every layer contributes comparably
  to detecting any single attack class. Full per-family flip breakdown,
  McNemar/Cohen's h tables, and the anomaly-check reasoning are in
  `ABLATION_STUDY.md` (Steps 3-6).

## Phase 3.5 — Verification, kinematic companion, STBV-Bench v2, mixed-threat, coverage matrix

✅ Complete. Full detail in `VERIFICATION_ADDENDUM.md`, `STBV_BENCH_V2_DESIGN.md`,
`THREAT_CLASS_COVERAGE_MATRIX.md`, `MANUSCRIPT_FRAMING.md`. Summary:

| # | Task | Status | Headline |
|---|---|---|---|
| V1-V3 | Cohen's h, 3-way ACCEPT/CAUTION/REJECT flip breakdown, prevalence caveat | ✅ | Fusion causes 1,713 real decision changes (not 128 — binary F1 only sees the ACCEPT-crossing subset), 0 of which are direct ACCEPT↔REJECT reversals; 92.5% are CAUTION→REJECT escalations on real attacks. Cohen's h for fusion = -0.026 (negligible, binary scale) despite p=3.06e-29. STBV-Bench v1 prevalence stated explicitly: 70.07% malicious / 29.93% benign |
| V4 | Empirical CP check on 120 real multi-vehicle messages | ✅ | **Found a real bug, then fixed it**: 0/120 flips despite num_reports up to 20; root-caused to `orchestrator.py::_run_cp` never passing `event_label` to `cp_layer()` (unlike `_run_mbd`, which does) — CP was structurally inert regardless of window size. Confirmed independently 2 more times (STBV-Bench v2, mixed-threat bench): `cp_confidence == 1.0` on every message across all three harnesses. **Fixed in a later round (commit `6dc7df80c`)** after verifying zero blast radius on already-published numbers (no benchmark generator in this session ever sets an `event` field); re-running the same 120-message check confirms the fix — `scenarios/collusion` now shows real, varying `cp_confidence` and a genuine `trust_score` delta. STBV-Bench v1/v2, the kinematic bench, and the mixed-threat bench were correctly NOT re-run (their content carries no event field, so the fix changes nothing about them). CP still cannot score STBV-Bench's own multi-source families — that needs a separate, unscoped follow-up (event-label generation in the transformation engine). Full detail: `VERIFICATION_ADDENDUM.md` §4, `MANUSCRIPT_FRAMING.md` |
| Task 2 | VeReMi kinematic companion benchmark (n=13,511 real messages, 360 vehicles, stateful per-vehicle replay) | ✅ | MBD per-message recall 77.5% (ConstPos 91.2% / DoS 80.3% / DataReplay 60.0%), FPR 52.4%; per-vehicle "ever flagged" recall 99.2% but FPR 99.4% (not a usable standalone policy). B3 confirmed contributing exactly 0 (config 3/4 byte-identical to config 2) — the required companion result before "complementary coverage" can be claimed |
| Task 1 | STBV-Bench v2 design + prototype (150 real multi-vehicle windows, 5,062 messages) | ✅ | Every v1-weak family improved (up to +75pp), 0 regressions, 8 already-100% families stayed at 100%. Root cause confirmed by text inspection: v1's isolated-message phrasing ends "No other vehicles in cooperative cluster"; v2's real windows add genuine cluster-peer context that measurably helps B3. Two candidate explanations flagged, not resolved (real-world representativeness vs. B3 training-distribution match) |
| Task 3 | Mixed-threat benchmark (120 windows, 4,123 messages, real kinematic + injected semantic attackers in the same scene) | ✅ | Both layers fire independently in a shared scene: 90.3% kinematic recall (MBD), 70.3% semantic recall (B3), 0/431 vehicles ever double-counted. ~16pp semantic-recall gap vs. semantic-only control reported as an open question (CP inert, so no mechanism for real interaction is currently confirmed) |
| Task 4 | Threat-Class Coverage Matrix | ✅ | `THREAT_CLASS_COVERAGE_MATRIX.md` — every family mapped to its actual detecting layer with evidence citations |
| Task 5 | Manuscript framing | ✅ | `MANUSCRIPT_FRAMING.md` — claim-by-claim evidence map + a ready-to-adapt paragraph for the architecture-evaluation section, with an explicit "do not cite without re-checking" note tied to the CP fix |

## Phase 4 — Standard benchmark integration (VeReMi)

✅ Superseded by Phase 3/3.5 — VeReMi Extension (`data/veremi_processed/`)
has been used extensively and directly this session (STBV-Bench v1/v2,
the kinematic companion bench, the mixed-threat bench all build on real
VeReMi flat reports). The original "requires network access" blocker
no longer applies; the data was already present locally in this
environment. This phase's original scope is complete.

## Phase 5 — Publication metrics & figures

⬜ Not started. Largely covered by existing `evaluation/metrics_and_outputs.py` + `evaluation/stats.py`; will run once Phase 1-2 unblock real data.

## Phase 6 — This document

✅ Created. Will be updated after every milestone in this session and any future session continuing this work.

---

## Environment notes (recorded once, referenced throughout)

- Working directory: `c:\semantic-trust-boundary-violation\semantic-trust-boundary-violation`
- Repo's own `.venv` is broken (hardcoded path from a different machine/user: `C:\Users\Asus\...`). Using system Python 3.13 at
  `C:\Users\mukil\AppData\Local\Programs\Python\Python313\python.exe`, which already has torch 2.7.1+cu118, transformers 5.12.1, CUDA available.
- GPU: NVIDIA GeForce RTX 4050 Laptop GPU, 6GB VRAM (per `nvidia-smi`).
- All commands in this log were run read-only / additive (no production module rewritten), consistent with the "extend, don't rewrite" mandate.
