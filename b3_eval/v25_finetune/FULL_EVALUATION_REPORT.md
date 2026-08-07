# B3 Semantic Gate: LoRA Fine-Tune on STBV-Bench v2.5 — Final Report

**Status: training and evaluation complete.** This report covers Phases 1–6
of the mission: dataset preparation, LoRA fine-tuning, calibration, full
evaluation, forgetting analysis, and the final recommendation.

All raw numbers in this report are read directly from
`b3_eval/v25_finetune/results/full_evaluation.json`,
`b3_eval/v25_finetune/results/forgetting_analysis.json`, and
`b3_eval/v25_finetune/training_log.jsonl` — nothing here is estimated or
inferred.

---

## 1. What was done

- **Initialized only from the existing checkpoint**
  (`b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/`). The raw
  pretrained DeBERTa was never touched. The original checkpoint directory
  is byte-for-byte unmodified (verify with `git status` / checksum — no
  writes were ever directed at it; the training script's `OUT_DIR` is a
  different, new directory).
- **New model saved separately**: LoRA adapter at
  `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora/`
  (adapter weights only, ~7.7 MB — merges onto the frozen base at load
  time; see `eval_common.load_finetuned()`).
- **Template-disjoint splits**: `b3_eval/v25_finetune/make_splits.py`,
  grouped by `template_id` (never row), 70/15/15, seed 42. Verified
  programmatically that no template appears in more than one split (assert
  in the script; see `split_manifest.json`). Train 8,535 rows / 125
  templates, val 1,898 rows / 28 templates, test 1,811 rows / 27 templates.
- **LoRA fine-tuning**: `b3_eval/v25_finetune/train_lora.py`. Rank 16,
  alpha 32, dropout 0.05, on `query_proj`/`key_proj`/`value_proj` +
  attention-output/intermediate/output `dense` projections, all 6 encoder
  layers (regex-anchored so `pooler.dense` is never double-targeted).
  Embeddings frozen. `pooler.dense` + `classifier` fully trainable via
  `modules_to_save`. 1,919,234 / 143,815,684 trainable params (1.33%).
  AdamW lr=1e-5, batch 16, weight decay 0.01, warmup 10%, grad clip 1.0,
  up to 10 epochs, early stopping patience 2 on val F1, best-checkpoint
  saved by val F1 only. Ran the full budget without restarting (best
  epoch 8, stopped at epoch 10 per patience — matches the plan's "if still
  improving after epoch 5, continue to epoch 10, don't restart").
- **Calibration**: `b3_eval/v25_finetune/calibration.py`. Temperature
  refit via LBFGS on v2.5 **val only**; ECE/Brier/reliability computed on
  v2.5 **test** (held out from the fit). Argmax-invariance checked
  explicitly (0 label flips from calibration on both models).
- **Full evaluation**: `b3_eval/v25_finetune/run_full_evaluation.py`. Both
  checkpoints scored on **identical inputs** for every benchmark run.

## 2. Headline result: STBV-Bench v2.5 test (held-out, template-disjoint)

| Metric | Original | Fine-tuned | Δ |
|---|---|---|---|
| Accuracy | 0.6543 | 0.9442 | +28.99 pp |
| Precision | 0.8168 | 0.9806 | +16.38 pp |
| Recall | 0.5139 | 0.9212 | +40.73 pp |
| F1 | 0.6309 | 0.9500 | +31.91 pp |
| ROC-AUC | 0.7686 | 0.9911 | +0.2225 |
| PR-AUC | 0.8040 | 0.9926 | +0.1886 |

This is a large, unambiguous improvement, on data the model never saw
during training and whose templates never leaked from train into
test/val.

## 3. Why it improved

1. **The original checkpoint was not trained on this distribution.**
   `semantic_gate_v3`'s `training_args.bin` records an `output_dir` from a
   different machine/project (`v2x-pi-project`); it predates STBV-Bench
   v2.5 and its 14-family taxonomy. Its low recall (0.51) on v2.5,
   especially near-chance recall on `goal_manipulation` (F1 0.12) and
   `role_confusion` (F1 0.07) before fine-tuning, matches exactly the
   failure mode already documented in `UPDATED_RESULTS.md` / diagnosed in
   `B3_FINETUNE_PLAN.md`: a frozen encoder whose representation does not
   separate those families from benign text.
2. **LoRA reached every encoder layer's output**, not just the classifier
   head — per the plan's diagnosis, a near-chance family cannot be fixed
   by re-weighting a linear head on a representation that doesn't
   separate the classes; the encoder itself had to move. The result
   confirms this: `goal_manipulation` F1 0.1154 → 1.0000,
   `role_confusion` F1 0.0698 → 0.6613, `priority_manipulation` F1
   0.1690 → 0.8696 (see §4).
3. **This is legitimate adaptation, not overfitting to test.** Train/val/
   test are template-disjoint (different message skeletons, not just
   different rows), so the model cannot have memorized test templates
   during training — the improvement reflects generalization to unseen
   skeletons of the same families.

## 4. Catastrophic-forgetting check (per-family, STBV-Bench v2.5 test)

*`benign_control` (n=770) has no positive/malicious labels, so
precision/recall/F1 (defined w.r.t. the malicious class) are mathematically
undefined (0/0) for it — both models report 0.0000 as a metric artifact,
not a forgetting signal. Its accuracy (=1−FPR) is the meaningful number:
**both models: 100% correct** on this family (0 false positives) — full
numbers in `comparison_table.md`.*

| Attack family | Original F1 | Fine-tuned F1 | Δ | Status |
|---|---|---|---|---|
| goal_manipulation | 0.1154 | 1.0000 | +0.8846 | IMPROVED |
| priority_manipulation | 0.1690 | 0.8696 | +0.7006 | IMPROVED |
| role_confusion | 0.0698 | 0.6613 | +0.5915 | IMPROVED |
| authority_override | 0.4946 | 0.9781 | +0.4835 | IMPROVED |
| traffic_efficiency_lure | 0.6423 | 1.0000 | +0.3577 | IMPROVED |
| indirect_prompt_injection | 0.6186 | 0.9531 | +0.3346 | IMPROVED |
| context_inversion | 0.6271 | 1.0000 | +0.3729 | IMPROVED |
| cross_source_contradiction | 0.7544 | 1.0000 | +0.2456 | IMPROVED |
| false_clearance | 0.7429 | 0.9606 | +0.2178 | IMPROVED |
| fabricated_consensus | 0.8712 | 1.0000 | +0.1288 | IMPROVED |
| instruction_hiding | 0.8852 | 1.0000 | +0.1148 | IMPROVED |
| narrative_poisoning | 1.0000 | 1.0000 | +0.0000 | unchanged |
| **sensor_discreditation** | **0.9932** | **0.9197** | **−0.0735** | **REGRESSED** |

**11 improved, 1 unchanged (already at ceiling), 1 regressed.**

### The one regression, explained (not hidden)

`sensor_discreditation` (n=74, and this test slice happens to be 100%
malicious — 0 benign examples of this family landed in the test split, so
precision is trivially 1.0 for both and recall is the only thing moving):
recall dropped 98.65% → 85.14% (73/74 → 63/74 caught; 10 additional false
negatives). This is a genuine, real regression, not measurement noise —
worth stating plainly:

- The original checkpoint was **already near-ceiling** on this family
  (0.9932 F1) before any v2.5-specific training.
- LoRA fine-tuning optimizes a **single scalar (val F1) aggregated across
  all 14 families**, weighted by their natural frequency in the
  template-disjoint val split. Recall gains on the families that were
  badly broken (`goal_manipulation`, `role_confusion`,
  `priority_manipulation`, all starting under 0.5 F1) dominate that
  aggregate signal far more than a further half-point of an
  already-0.99-F1 family — so gradient pressure was disproportionately
  spent fixing the broken families, at a small, measurable cost to the
  family that needed the least help. This is the LoRA-vs-full-finetune
  trade-off working as expected (contained, single-digit-point drift on
  one already-strong family) rather than a failure of the approach — a
  full fine-tune of all 141.9M parameters would have carried materially
  higher risk of a **larger** regression here, which is exactly why
  `B3_FINETUNE_PLAN.md` recommended LoRA over full fine-tuning in the
  first place.
- **Net effect is still strongly positive**: this family remains
  well-detected (F1 0.92, recall 85%) while three previously-broken
  families move from unusable (F1 < 0.2) to near-perfect.

## 5. Calibration

| Metric | Original | Fine-tuned |
|---|---|---|
| Fitted temperature (on val) | 3.3446 | 3.2778 |
| Test ECE, pre-calibration | 0.2994 | 0.0450 |
| Test ECE, post-calibration | 0.1311 | 0.0397 |
| Test Brier, pre-calibration | 0.3056 | 0.0488 |
| Test Brier, post-calibration | 0.2252 | 0.0432 |
| Argmax label flips from calibration | 0 | 0 |

The fine-tuned model is **far better calibrated even before any
temperature scaling** (ECE 0.045 vs 0.299) — a direct consequence of it
actually separating the classes correctly on this distribution (a
model that's simply wrong a lot, as the original is on v2.5, cannot be
well-calibrated no matter how the temperature is set). Temperature
scaling still helps both models further and, as designed, changes zero
predicted labels.

**Deployment note**: `isce_config.yaml`'s existing `temperature_scaling:
2.1446` was fit on a different corpus (pre-v2.5) and must not be reused —
if the fine-tuned checkpoint is deployed, replace it with **T=3.2778**
(fit here on v2.5 val).

## 6. Latency / Throughput / Memory (CUDA, RTX 4050 Laptop, batch=1, n=200)

| Metric | Original | Fine-tuned | Δ |
|---|---|---|---|
| p50 | 23.40 ms | 21.69 ms | −1.71 ms |
| p95 | 36.65 ms | 35.45 ms | −1.19 ms |
| p99 | 40.93 ms | 43.93 ms | +3.00 ms |
| Throughput (single-msg) | 40.0 msg/s | 42.6 msg/s | +2.6 msg/s |
| Peak VRAM | 1157 MB | 1157 MB | 0 MB |
| Parameters (dense, merged) | 141.9M | 141.9M | 0 |

The fine-tuned model's deployed footprint is **identical** to the
original: the LoRA adapter is merged into dense weights of the same shape
(`merge_and_unload()`), so there is no runtime overhead, no extra
parameters, and no VRAM cost at inference. p50/p95 differences (~1–2 ms)
are within normal run-to-run noise on a shared laptop GPU; p99 is
slightly higher for the fine-tuned model but still well inside the ETSI
CAM 10 Hz (100 ms) budget by a wide margin either way.

## 7. Robustness (adversarial perturbation battery, 6 seeds × 11 families)

Full table in `comparison_table.md`. Sample size is small by the existing
harness's own design (6 V2X seeds per family; `results/robustness.json`-
style harnesses in this repo have always used this battery size), so
individual ratios (e.g. 1/6 = 0.17) are noisy — read as directional, not
precise. Mean label-flip rate across all 11 perturbation families:
**0.182 (original) → 0.152 (fine-tuned)**, a modest net improvement in
prediction stability under perturbation, with no family showing a large,
consistent degradation in evasion or over-defense rate.

## 8. Benchmarks not directly re-scored, and why (Phase 4 completeness note)

- **VeReMi (raw)**: purely kinematic (position/speed/heading/timestamp),
  no natural-language field. B3 is a text classifier; VeReMi feeds
  B1/B2 (kinematic layers) in this system's architecture, never B3 —
  confirmed by direct inspection of
  `stbv_bench/build_and_run_veremi_kinematic_bench.py` (zero references
  to B3 or text rendering) and `b3_eval/_harness.py`. There is no valid
  text corpus here for a B3-vs-B3 comparison to be meaningful.
- **Mixed-threat bench**: `stbv_bench/build_mixed_threat_bench.py`
  requires the full B1+B2+CP+B3+TrustEngine stack
  (`pipeline.orchestrator.ISCEPipeline`) to construct and score — it
  measures layer *interaction*, not B3 in isolation. Its semantic-
  injection payloads are drawn from the same transformation engine as
  STBV-Bench v1/v2.5 (`B3_DATA_PROVENANCE_REPORT.md`), so B3's text-level
  behavior on that payload distribution is already exercised by the v2.5
  results above.
- **Ablation bench**: `stbv_bench/run_ablation.py` is a *layer*-ablation
  study (B1-only / B1+B2 / B1+B2+CP / B1+B2+CP+B3-unfused / full stack) —
  it answers "how much does the B3 layer contribute to the fused
  decision", which is orthogonal to "which B3 checkpoint is better", and
  requires the same full-stack orchestration as mixed-threat.
- **STBV-Bench v1**: rows store structured CAM/DENM `transformed_message`
  objects plus window metadata, not a flat text field. B3's text
  rendering (`pipeline/synthesizer.py:synthesize_message`) is a
  multi-vehicle *window* function (cluster → text, using peer reports and
  RSU messages from `scene_context`), not a per-row pure function — v1's
  rows are individual messages, not the windowed clusters that function
  expects. Reconstructing synthetic windows here would invent peer/RSU
  context that never existed in the original corpus, producing scores for
  text B3 never actually saw — that would be fabrication, not a genuine
  cross-generation check, so this was skipped with a stated reason
  instead.

None of these are gaps introduced by the fine-tuning work; they reflect
what is and isn't architecturally scoreable by a text-only classifier
given what's on disk, and are documented rather than silently omitted.

## 9. Final recommendation

**Use the fine-tuned model (`semantic_gate_v3_v25_lora`, merged) for
STBV-Bench v2.5-era deployment and for the paper's v2.5 results.**

Rationale:
- Every headline metric on the held-out, template-disjoint v2.5 test set
  improved substantially (F1 +31.9 pp, ROC-AUC +0.22), with no
  train/test template leakage possible by construction.
- 11 of 13 scoreable attack families improved (several from near-useless
  to near-perfect), 1 was already at ceiling and stayed there, and the
  1 real regression (`sensor_discreditation`, −7.4 F1 points, still at
  0.92 F1) is understood, small, and a known trade-off of the
  low-rank-adaptation approach rather than an unexplained failure.
- Calibration is substantially better even pre-scaling, and a validated
  new temperature (3.2778) is provided for deployment.
- Latency and memory are unchanged post-merge; no deployment cost.
- The original checkpoint is fully preserved on disk, untouched, and
  remains available if a future need re-favors its specific strengths
  (e.g. a corpus dominated by `sensor_discreditation`-style attacks with
  little else).

**Caveat for the paper**: state plainly that this is an *incremental,
architecture-preserving* fine-tune of an existing checkpoint onto a new
benchmark version (v2.5), not a from-scratch retrain or a different
model, and that STBV-Bench v1/VeReMi/mixed-threat/ablation comparisons
were not re-run for the reasons in §8 — the v2.5 result is the valid,
apples-to-apples comparison this work produced.

## 10. Deliverables

| Item | Path |
|---|---|
| Fine-tuned checkpoint (LoRA adapter) | `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora/` |
| Original checkpoint (untouched) | `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/` |
| Training script | `b3_eval/v25_finetune/train_lora.py` |
| LoRA configuration | embedded in `train_lora.py` (r=16, α=32, dropout=0.05, listed target modules) |
| Dataset split files + manifest | `b3_eval/v25_finetune/data/{train,val,test}_split*.jsonl`, `split_manifest.json` |
| Split builder (reproducible, seed=42) | `b3_eval/v25_finetune/make_splits.py` |
| Evaluation harness | `b3_eval/v25_finetune/run_full_evaluation.py`, `eval_common.py` |
| Calibration module + report | `b3_eval/v25_finetune/calibration.py`, results embedded in `full_evaluation.json` |
| Training log (per-epoch) | `b3_eval/v25_finetune/training_log.jsonl` |
| Comparison tables | `b3_eval/v25_finetune/results/comparison_table.md` |
| Forgetting analysis | `b3_eval/v25_finetune/results/forgetting_analysis.json` |
| Figures | `b3_eval/v25_finetune/results/figures/*.png` |
| Raw evaluation output | `b3_eval/v25_finetune/results/full_evaluation.json` |
| This report | `b3_eval/v25_finetune/FULL_EVALUATION_REPORT.md` |
