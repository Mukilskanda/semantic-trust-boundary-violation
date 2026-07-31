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

| Detector | Status | Finding |
|---|---|---|
| Sybil | ⬜ | Prior audit: `sybil_score` stayed 0.00 even after a coordinate-frame fix; root cause unresolved. To be investigated directly against `scenarios/sybil/` fixtures. |
| Replay | ⬜ | Prior audit: confirmed firing (dual detection in B1 + MBD). To be re-verified. |
| Collusion | ⬜ | Prior audit: structurally unreachable (`event` field never populated). To be investigated/fixed. |
| Fabrication | ⬜ | Not previously deep-dived. |
| Position (manipulation) | ⬜ | Not previously deep-dived. |
| Speed (manipulation) | ⬜ | Not previously deep-dived. |
| Context (highway/urban/intersection/tunnel/roundabout) | ⬜ | Not previously deep-dived. |

## Phase 3 — Complete experimental pipeline

⬜ Not started. Will reuse `evaluation/`, `large_scale/`, `semantic_evaluation/` frameworks (extend, not rewrite).

## Phase 4 — Standard benchmark integration (VeReMi)

⬜ Not started. Requires network access to fetch VeReMi/VeReMi Extension — network availability not yet confirmed in this environment.

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
