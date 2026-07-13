# b3_eval/ — B3 Semantic Gate Evaluation Harnesses

Implements Parts 5–8 of the B3 mandate. **Nothing here modifies B3, the
model, or any other layer** — these are read-only evaluation harnesses.

Read **`../B3_ASSESSMENT.md` first** — it contains the sufficiency
determination (short version: *do not retrain, do not swap architectures on
current evidence*) and the two blocking facts below.

## Prerequisites (both currently unmet in the delivered artifact)

1. **Materialize the checkpoint.** `pytorch_model.bin` in the repo is a
   **134-byte Git LFS pointer**, not weights (the real file is 542 MB):
   ```bash
   git lfs pull
   ```
   Every harness detects this precisely and refuses to fabricate numbers.

2. **torch + (ideally) CUDA.** The harnesses run on CPU but the
   deployment-relevant latency numbers need the GPU box.

3. **Labeled splits** (for calibration + benchmarking), at:
   - `b3_eval/data/calibration_split.jsonl`
   - `b3_eval/data/train_split.jsonl`, `b3_eval/data/test_split.jsonl`

   Schema — one JSON object per line: `{"text": "...", "label": 0|1}`
   These can be produced from the project's original
   `outputs/splits/test1_stbv_unseen_families.json` (referenced by
   `b3/.../error_analysis.py`) — **also absent from the artifact**; restore
   it from the original project.

## The four harnesses

| Command | Part | Answers |
|---|---|---|
| `python3 b3_eval/run_robustness.py` | 6 | Does B3 survive paraphrase / typos / unicode homoglyphs / instruction-hiding / context-poisoning / role-confusion / long-prompt padding? Reports per-family **label_flip_rate, evasion_rate, over-defense FPR, mean Δconfidence**. |
| `python3 b3_eval/run_calibration.py` | 7 | Is B3's confidence calibrated? Reports **ECE, Brier, reliability diagram, confidence histogram**, and fits **temperature scaling** (post-hoc; changes zero labels). |
| `python3 b3_eval/run_latency.py --n 500` | 8 | **Cold/warm start, CPU/GPU, single vs batch, p50/p90/p95/p99, params, peak VRAM/RSS**, vs the ETSI CAM 10 Hz (100 ms) budget. |
| `python3 b3_eval/run_model_benchmark.py` | 5 | Fine-tunes DeBERTa-v3-base / RoBERTa / ModernBERT / DistilRoBERTa / MiniLM on the **same split, same budget**, compares acc/P/R/F1/latency/params/train-cost. |

Every harness writes `b3_eval/results/*.json` with a manifest (checkpoint
SHA, torch/CUDA version, hardware, timestamp).

## The swap decision rule (encoded, not vibes)

`run_model_benchmark.py` recommends replacing the incumbent **only if** a
candidate beats it by **≥ 2.0 F1 points** on the held-out split **and** its
p95 latency is **≤ 1.25×** the incumbent's. Otherwise it prints
**KEEP INCUMBENT**.

This bar exists because the published evidence already favours the
incumbent's architecture: Antoun et al. 2025 (arXiv:2504.08716), a
*controlled same-data* comparison, find **DeBERTaV3 ≥ ModernBERT** on
accuracy and sample efficiency (ModernBERT wins only on long-context and
speed — irrelevant at 256 tokens), and a deployment-aware study
(arXiv:2605.26999) finds DeBERTa stronger than RoBERTa **at the strict
low-FPR operating point**, which is the regime a safety gate lives in.

## Why calibration is the highest-value no-retrain change

`b3_bridge.B3RiskPolicy` maps confidence → `risk_level` at **0.85 / 0.60**,
and the Trust Engine turns that confidence into **Dempster–Shafer committed
mass**. Miscalibrated confidence therefore propagates directly into the
final trust decision. Temperature scaling fixes this **without touching the
classifier or changing a single predicted label** (argmax is invariant to
T — regression-tested).

The calibration mathematics are unit-tested **without needing the
checkpoint**: `python3 tests/test_b3_calibration_math.py` validates
temperature recovery against known injected temperatures
(3.0 → fitted 2.887; 1.0 → 1.018; 0.4 → 0.394), ECE reduction
(0.144 → 0.012), and argmax invariance (0/2000 label flips).

## Suggested order on the GPU box

```bash
git lfs pull                                   # 1. materialize weights
# 2. restore outputs/splits + write the jsonl splits (see Prerequisites)
python3 b3_eval/run_latency.py --n 500         # 3. cheapest, confirms the model loads
python3 b3_eval/run_calibration.py             # 4. highest-value finding
python3 b3_eval/run_robustness.py              # 5. the reviewer's favourite attack
python3 b3_eval/run_model_benchmark.py         # 6. slowest (fine-tunes 5 models)
```
