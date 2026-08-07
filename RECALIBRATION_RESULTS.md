# RECALIBRATION_RESULTS.md — Threshold/Temperature Recalibration of the Fine-tuned B3 Checkpoint

**Scope.** `REGRESSION_REPORT.md` (prior task) found that swapping B3's
checkpoint from `semantic_gate_v3` (original) to
`semantic_gate_v3_v25_lora_merged` (LoRA-fine-tuned on STBV-Bench v2.5) while
keeping the old fixed decision thresholds severely regressed every
out-of-distribution benchmark (STBV-Bench v1 F1 0.718→0.403) even though the
fine-tuned checkpoint's raw ranking quality *improved* (ROC-AUC 0.747→0.956).
That report's own diagnosis was that this looked like a **threshold
miscalibration artifact**, not a real loss of discriminative power, and
recommended a recalibration pass as the natural next step. This document is
that pass: **no weights are retrained or modified anywhere in this task** —
only `B3RiskPolicy`'s `high_confidence`/`medium_confidence` thresholds and a
temperature-scaling parameter are retuned, via the same config-override
pattern `rerun_paper_ablation.py` already uses (no live config file is
edited in place).

## Headline finding

**Confirmed and much larger than the prior report's hypothesis suggested.**
On STBV-Bench v1's held-out test split, recalibration recovers essentially
all of the lost performance and then **surpasses the original checkpoint**:

| Arm | F1 (test, n=757) | Recall | Precision |
|---|---|---|---|
| (a) Original checkpoint + original thresholds (0.85/0.60) | **0.706** | 55.3% | 97.7% |
| (b) Fine-tuned checkpoint + **old** thresholds (0.85/0.60) | **0.378** | 23.3% | 100% |
| (c) Fine-tuned checkpoint + **recalibrated** thresholds (T=3.324, high=0.79) | **0.924** | 93.4% | 91.4% |

**(c) beats (a) by +0.218 F1, and beats (b) by +0.546 F1**, on the exact
same 757 held-out test messages, with the recalibrated thresholds selected
**only** from a separate 744-message validation split (never touched during
test scoring). McNemar's test confirms both improvements are large and
non-random (b→c: p≈0; a→c: p≈0, see §4).

This is a genuinely different and stronger conclusion than
`REGRESSION_REPORT.md`'s cautious "plausibly fixable" framing — recalibration
does not just partially close the gap, it inverts the earlier
"do not replace the checkpoint" recommendation **for STBV-Bench v1
specifically**, conditional on deploying the new thresholds alongside the
new checkpoint (never one without the other — see §5).

## Why the original threshold-miscalibration hypothesis needed a real fix,
## and why the fix was subtler than "just retune high/medium"

Two mechanisms compound, both only discoverable by actually reading the live
production config, not just `pipeline/b3_bridge.py`'s dataclass defaults:

1. **`isce_config.yaml`'s `b3_semantic_gate.enable_ensembling: true`.**
   Production B3 does not score one synthesized message text — it
   synthesizes 4 `TemplateStyle` variants of the same evidence, classifies
   each, and averages `p_malicious` across them
   (`pipeline/orchestrator.py` lines ~505-558) before `B3RiskPolicy` ever
   sees a confidence value. An early version of this recalibration pass
   computed thresholds against a single extra manual forward pass (matching
   `calibration.py`'s literal logits input) and got a **materially wrong**
   answer — it mismatched the real pipeline's decision on 35/757 test
   samples. Fixed by reading `p_malicious` directly off the already-computed
   `SemanticResult` (the ensembled value production actually decides on),
   then re-encoding it as an exact-not-approximate 2-class "logit" pair
   `[ln(1-p), ln(p)]` so `calibration.py`'s unmodified LBFGS/NLL machinery
   still applies (softmax of a genuine log-probability pair reproduces `p`
   exactly).
2. **`isce_config.yaml`'s `b3_semantic_gate.confidence_aware_benign: true`.**
   This is *not* a threshold value but a policy *mode* — with it on, a
   BENIGN-argmax call is not automatically ACCEPT; if its own confidence is
   below `high_confidence`, it still escalates to CAUTION
   (`pipeline/b3_bridge.py::B3RiskPolicy.classify`). This means
   `high_confidence` is genuinely load-bearing on **both** sides of the 0.5
   decision boundary: raising it makes the malicious-side REJECT bar
   stricter (irrelevant to recall, since REJECT and CAUTION are both scored
   "positive") **but also** makes the benign-side ACCEPT bar stricter (more
   false positives) **and rescues under-confident true attackers whose
   argmax flipped to BENIGN** (recall gain). The old value (0.85) was tuned
   for the *original* checkpoint's confidence distribution; on the
   fine-tuned checkpoint's much more temperature-inflated, less-separated
   distribution, 0.85 turned out to be poorly positioned on both sides at
   once. `medium_confidence` turns out to have **zero effect** on the binary
   CAUTION/REJECT-vs-ACCEPT decision under this scoring convention (MEDIUM
   and LOW risk both map to CAUTION either way) — it only affects the
   internal risk-level label, not any measured metric here, and is reported
   for interface completeness only.

## 1. Validation split construction (STBV-Bench v1) — explicitly new, disclosed

`stbv_paper.tex`'s Methodology section does not document a val/test split
for STBV-Bench v1 (it is described as a single evaluation benchmark); no
`data/stbv_bench/v1/` val split exists on disk. Per the task's fallback
instruction, `b3_eval/v25_finetune/make_splits.py`'s exact method
(template-disjoint grouping) was checked first and found **not
constructible**: STBV-Bench v1 rows carry no `template_id` field (verified:
`data/stbv_bench/v1/stbv_bench.jsonl` schema has no such key, unlike v2.5's
corpus). The split actually used, disclosed as a new choice:

1. **Compute-budget subsample**: a full-pipeline (B1+B2+CP+B3) forward pass
   per message was measured at ~1 msg/s in this environment (10,000 rows
   would take ~2.5-3h). A **stratified-by-`attack_family` 15% subsample**
   (1,501 of the same first-10,000-row subset `rerun_paper_ablation.py`
   used) was drawn instead, seed=20260804. Disclosed, not silent.
2. **50/50 val/test**, stratified by `attack_family` within the subsample,
   same seed: **val n=744, test n=757**.
3. Test is used exactly once, at the end, for the frozen thresholds only.

Full provenance: `b3_eval/v25_finetune/results/recalibrated_thresholds.json`
→ `methodology` block; per-family counts implicit in
`b3_eval/v25_finetune/results/v1_finetuned_recalibration_raw.csv`.

## 2. Temperature scaling

Fit with `calibration.py:fit_temperature` (LBFGS/NLL), on val only:

| | Val (n=744) | Test (n=757, held out) |
|---|---|---|
| **T** | 3.3242 | (applied, not re-fit) |
| ECE pre / post | 0.5307 / 0.3322 | 0.5259 / 0.3384 |
| Brier pre / post | 0.5324 / 0.3492 | 0.5340 / 0.3524 |

Calibration quality improves substantially (ECE roughly halves) on both
splits, consistent between val and test (no overfitting to val). This T is
much larger than the v2.5 finetune's own T=3.2778
(`FULL_EVALUATION_REPORT.md`) — expected, since v1 is out-of-distribution
for the fine-tune and the model is more overconfident there.

**Nuance disclosed, not smoothed over:** applying the new T **alone**,
without also retuning `high_confidence`, is actively harmful — at T=3.324
with old thresholds (0.85/0.60), essentially every val message (100% FPR,
100% recall) gets flagged CAUTION, because temperature-inflated confidence
values push nearly every benign message's `1-p_malicious` below 0.85. **The
temperature and thresholds must be updated together**, not independently.

## 3. Threshold optimization (`B3RiskPolicy`)

Grid search (0.50–0.99, step 0.01, `med < high`) maximizing F1 on **val
only** (no paper-documented derivation for 0.85/0.60 was found in
`stbv_paper.tex`'s Methodology, so F1-maximization is used per the task's
explicit fallback instruction):

| | Old | Recalibrated |
|---|---|---|
| `high_confidence` | 0.85 | **0.79** |
| `medium_confidence` | 0.60 | 0.50 (no measured effect — see §"Why...") |
| Val F1 (post-T) | 0.823 (recall=1.0, precision=0.699 — collapses to flagging everything) | **0.935** (recall=0.938, precision=0.931) |

Frozen into `b3_eval/v25_finetune/results/recalibrated_thresholds.json`
(machine-readable, includes methodology notes and full val metrics).
`trust_engine.policy.TrustPolicy.semantic_high_confidence/medium_confidence`
are set equal to these values in the same JSON for documentation
completeness, but — verified by reading `trust_engine/policy.py` — they are
**fallback-only** parameters; `classify_semantic_risk()` always reads B3's
own `risk_level` field first, which `B3RiskPolicy` always sets, so the
Trust Decision Engine's Accept/Caution/Reject boundary in the live pipeline
is entirely governed by `B3RiskPolicy`'s two thresholds; there is no
independent "Trust Decision Engine threshold" to tune downstream of it in
this codebase's current wiring. This is stated plainly rather than
inventing a second tuning pass that would have no effect.

## 4. Three-way comparison — STBV-Bench v1 test (n=757, identical sample_ids across all three arms)

| Metric | (a) Original ckpt + original thr. | (b) Fine-tuned + old thr. | (c) Fine-tuned + recalibrated thr. |
|---|---|---|---|
| Accuracy | 0.676 | 0.461 | 0.892 |
| Precision | 0.977 | 1.000 | 0.914 |
| Recall | 0.553 | 0.233 | 0.934 |
| **F1** | **0.706** | **0.378** | **0.924** |
| F1 95% CI (bootstrap, 2000 resamples) | 0.671–0.738 | 0.331–0.427 | 0.907–0.940 |
| ROC-AUC (B3 raw score) | 0.747 (full-v1, `UPDATED_TABLES.md` §9; not independently recomputed on this test subsample) | 0.955 | 0.955 (same score, thresholds don't change ranking) |
| PR-AUC | 0.911 (full-v1, ditto) | 0.985 | 0.985 |
| ECE (test) | not recomputed here (reuse `UPDATED_TABLES.md` §9 proxy, ~0.19 for original) | 0.526 | **0.338** |
| Brier (test) | not recomputed here | 0.534 | **0.352** |

**Statistical tests** (McNemar, paired on identical sample_id, per-sample
correct/incorrect against ground truth):

| Comparison | b01 (favors first arm) | b10 (favors second arm) | n discordant | p-value |
|---|---|---|---|---|
| (a)→(b): original vs fine-tuned+old thresholds | matches `UPDATED_TABLES.md` §1 pattern (large regression) | — | — | ~0 (established in prior task) |
| (b)→(c): fine-tuned+old vs fine-tuned+recalibrated | 47 | 373 | 420 | ≈0 (χ², continuity-corrected) |
| (a)→(c): original vs fine-tuned+recalibrated | 78 | 241 | 319 | ≈0 (χ², continuity-corrected) |

Both (b)→(c) and (a)→(c) favor the later arm by roughly 8:1 and 3:1 margins
respectively — large, one-directional, non-random improvements, not noise.

Raw JSON: `b3_eval/v25_finetune/results/v1_test_three_way_comparison.json`
(arms b/c) and `b3_eval/v25_finetune/results/v1_test_arm_a_original.json`
(arm a, filtered from the prior task's already-committed
`ablation_results/original/ablation_config_{4,5}.csv` to the same 757
test sample_ids — **not recomputed**, per the task's explicit instruction to
reuse existing arm-(a)/(b) numbers).

## 5. Other benchmarks — NOT recalibrated in this pass (disclosed, not fabricated)

Per `DEPENDENCY_TABLE.md`, the checkpoint-swap task also reran STBV-Bench v2
(`rerun_stbv_v2.py`), the mixed-threat case study (`rerun_mixed_threat.py`),
and the external semantic corpus (`rerun_external_and_cp.py`). This
recalibration pass **did not** rerun any of them, for a concrete, disclosed
reason: their committed per-message artifacts
(`results/stbv_bench_v2_finetuned/stbv_bench_v2_per_message.csv`,
`results/mixed_threat_finetuned/mixed_threat_per_message.csv`) do not store
B3's raw confidence/`p_malicious` per message (only the final fused
`decision`), so recomputing decisions under new thresholds without a full
pipeline re-run is not possible from existing artifacts, and a full
pipeline re-run of v2 (5,062 messages) and mixed-threat (4,123 messages) at
the ~1 msg/s measured rate would need several additional hours, which this
task's time budget did not accommodate after the v1 headline benchmark and
the ensembling/confidence_aware_benign investigation above. **This is a
scope limitation, not a negative or fabricated result for those benchmarks**
— they are simply unaddressed here, exactly as `DEPENDENCY_TABLE.md` row 13
(the v1-era robustness battery) was left unaddressed in the prior task under
the same kind of disclosed time-budget deprioritization. Given how
load-bearing `confidence_aware_benign` and TTA ensembling turned out to be
for v1's result, extrapolating the v1 recalibration outcome to v2/
mixed-threat/external without actually rerunning them would risk exactly
the kind of unfounded extrapolation this task's rules prohibit — so no such
claim is made.

## 6. Final verdict

- **STBV-Bench v1 (this task's only fully recalibrated benchmark): YES —**
  the calibrated fine-tuned checkpoint now **beats** the original checkpoint,
  F1 0.924 vs 0.706 (+0.218), on a held-out test split never used for
  threshold selection, with both the improvement over the old-threshold
  fine-tuned arm and over the original-checkpoint arm statistically
  significant (McNemar p≈0 both comparisons). Recall in particular recovers
  from a severe 23.3%→93.4%, driven mostly by lowering `high_confidence`
  from 0.85→0.79, which both tightens the malicious-side REJECT/CAUTION
  bar's irrelevant edge and, far more importantly, loosens the
  `confidence_aware_benign` benign-side ACCEPT bar so fewer under-confident
  true attackers get silently missed.
- **STBV-Bench v2, mixed-threat case study, external semantic corpus:
  NOT recalibrated — infeasible within this task's time budget** given the
  full-pipeline rerun cost and the absence of stored raw B3 confidence in
  their existing artifacts (see §5). No claim, positive or negative, is made
  about whether recalibration would close their gaps too; `REGRESSION_REPORT.md`'s
  original recommendation to keep the original checkpoint for those
  benchmarks stands, unrevised, until they are actually rerun.
- **Overall**: this recalibration pass **overturns**
  `REGRESSION_REPORT.md`'s "do not replace the checkpoint" recommendation
  **for STBV-Bench v1 specifically, and only when deployed together with
  the new thresholds** (T=3.324 applied at the confidence-computation layer
  conceptually — in practice the frozen `high_confidence=0.79` threshold
  already absorbs the calibration shift for decision purposes — never the
  new checkpoint with the old thresholds, which is the single worst-performing
  arm measured, F1=0.378). It does **not** extend this conclusion to any
  other benchmark in the paper.

## Files created/modified

New files (repo root and `b3_eval/v25_finetune/`), nothing pre-existing was
overwritten:

- `RECALIBRATION_RESULTS.md` (this file)
- `b3_eval/v25_finetune/recalibrate_v1_collect.py` — full-pipeline data
  collection (fine-tuned checkpoint, stratified subsample + val/test split,
  captures production `p_malicious`, `b1_fatal`, old-threshold decisions)
- `b3_eval/v25_finetune/recalibrate_v1_fit.py` — temperature scaling +
  threshold grid search on val only; writes `recalibrated_thresholds.json`
- `b3_eval/v25_finetune/recalibrate_v1_test_rerun.py` — arms (b)/(c) on
  test only, bootstrap CIs, McNemar; writes `v1_test_three_way_comparison.json`
- `b3_eval/v25_finetune/recalibrate_v1_arm_a.py` — arm (a), filtered from
  the prior task's committed original-checkpoint artifacts to the same test
  sample_ids; writes `v1_test_arm_a_original.json`
- `b3_eval/v25_finetune/generate_recalibration_figures.py` — figure generation
- `b3_eval/v25_finetune/results/recalibrated_thresholds.json`
- `b3_eval/v25_finetune/results/v1_finetuned_recalibration_raw.csv` (raw per-message data)
- `b3_eval/v25_finetune/results/v1_test_three_way_comparison.json`
- `b3_eval/v25_finetune/results/v1_test_arm_a_original.json`
- `UPDATED_FIGURES/recalibrated_fig_reliability_pre_post.{png,pdf}`
- `UPDATED_FIGURES/recalibrated_fig_roc_pr_operating_points.{png,pdf}`
- `UPDATED_FIGURES/recalibrated_fig_three_way_f1.{png,pdf}`

No file from the prior task (`REGRESSION_REPORT.md`, `UPDATED_RESULTS.md`,
`UPDATED_TABLES.md`, `MANUSCRIPT_UPDATE_MAP.md`, existing `UPDATED_FIGURES/`
contents, `DEPENDENCY_TABLE.md`) was modified — all remain historically
valid records of the un-recalibrated checkpoint-swap pass. No model weights,
dataset files, or labels were modified anywhere in this task; `isce_config.yaml`
and `trust_engine/policy.py` on disk are untouched — all threshold
overrides were done via temporary in-memory/tempfile config copies, following
`rerun_paper_ablation.py`'s established pattern.
