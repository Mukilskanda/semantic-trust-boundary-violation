# MIXED_CORPUS_RESULTS.md — Mixed-Corpus LoRA Retrain of B3

**Question.** `REGRESSION_REPORT.md` found that the v2.5-only LoRA finetune
(`semantic_gate_v3_v25_lora_merged`) overfit to STBV-Bench v2.5's templates:
huge gains on v2.5 itself, severe regressions on v1/v2/external.
`RECALIBRATION_RESULTS.md` showed threshold recalibration fixes v1 but not
v2/external — evidence the problem is representational (catastrophic
forgetting), not miscalibration. This task retrains the same LoRA recipe
(identical hyperparameters, `b3_eval/v25_finetune/train_lora.py`, unchanged)
on a **broader training mixture** — STBV-Bench v2.5 + a disjoint slice of
STBV-Bench v1 — to test whether broadening the distribution fixes the
forgetting without re-inducing it elsewhere.

**Verdict, upfront: partial, uneven success — not a clean fix.** The mixed
checkpoint fixes v1 and produces a large, genuine adaptive-attack robustness
gain, is roughly a wash on STBV-Bench v2 and mixed-threat (same F1 as
original, reached via a much more aggressive/high-recall, higher-false-positive
operating point rather than genuine improvement), and is a **small but real
regression on the external semantic corpus** relative to both the original
and the v2.5-only checkpoint. It is not the case that broadening training
data uniformly "solves" the forgetting problem — see §6 for the full,
unsmoothed breakdown.

## 1. Training data

See `b3_eval/v25_finetune/MIXED_CORPUS_REPORT.md` for the full build
methodology and leakage audit. Summary:

- **v2.5**: reused as-is (8,535 train / 1,898 val rows, template-disjoint
  from its own test split, `make_splits.py`).
- **v1**: STBV-Bench v2 and the external semantic corpus are used in their
  **entirety** as evaluation sets by the existing rerun scripts (v2: all 150
  windows; external: all 117 entries) — there is no unused portion of either
  to add to training without contaminating the very benchmarks this report
  evaluates against. They are therefore **excluded from training entirely**.
  v1 reserves only its first 10,000 rows (of 100,000) for evaluation, so its
  remaining 90,000-row pool is available; 8,505 rows were drawn from it
  (stratified by `attack_family`, seed 42, capped to the same order of
  magnitude as v2.5 so v1 doesn't drown out v2.5 in the mixture), rendered to
  text via `pipeline.synthesizer.synthesize_message(..., TemplateStyle.DEFAULT)`
  (the same deterministic, model-free renderer B3's production pipeline
  uses), split 85/15 into 7,229 train / 1,276 val rows.
- **Final mixed corpus**: 15,764 train rows (8,535 v2.5 + 7,229 v1), 3,174
  val rows (1,898 v2.5 + 1,276 v1).
- **Leakage audit**: zero `sample_id` overlap between the v1 training pool
  and v1's eval-reserved first-10,000 rows (hard assertion); zero exact-text
  duplicates between `mixed_train`/`mixed_val` and v2.5's held-out
  `test_split_full.jsonl`; a targeted check also confirmed zero exact-text
  overlap between the synthesized eval-region v1 texts and the
  synthesized training-region v1 texts (see §6 caveat on v1's near-perfect
  result — this rules out literal leakage but not distributional
  similarity, which is discussed honestly below).

## 2. Training

`b3_eval/v25_finetune/train_lora_mixed.py` — byte-identical to
`train_lora.py` except the data paths (`data/mixed_train_split.jsonl`,
`data/mixed_val_split.jsonl`) and output directory. Same hyperparameters
throughout (LoRA r=16/alpha=32/dropout=0.05 on
query/key/value_proj+attention-output/intermediate/output dense across all 6
encoder layers, embeddings frozen, pooler+classifier fully trainable, AdamW
lr=1e-5, batch=16, weight_decay=0.01, warmup 10%, grad clip 1.0, up to 10
epochs, early stopping patience=2 on val F1, seed 42).

| | |
|---|---|
| Best epoch | 6 (of 8 run; early-stopped) |
| Best val F1 | **0.8992** (precision 0.856, recall 0.947, accuracy 0.852, n=3,174) |
| Total wall time | 2,959s (~49.3 min), RTX 4050 Laptop GPU |
| Trainable params | 1,919,234 / 143,815,684 (1.33%) |

Full curve: `b3_eval/v25_finetune/training_log_mixed.jsonl`. For reference,
the v2.5-only run reached val F1=0.801 after 10 epochs on its (easier,
single-source) validation set — the mixed run's val F1 is higher, but the
two validation sets are not the same distribution, so this is not a like-for-like
comparison, only reported for completeness.

Adapter: `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora/`.
Merged dense checkpoint (via `merge_mixed_lora.py`, `peft`'s
`merge_and_unload()`, base weights on disk never touched):
`b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged/`.
Both are new directories; `semantic_gate_v3/` (original) and
`semantic_gate_v3_v25_lora(_merged)/` (v2.5-only) are untouched.

## 3. Calibration (STBV-Bench v1 only — see §5 for why)

Same procedure as `RECALIBRATION_RESULTS.md`: `recalibrate_v1_collect_mixed.py`
collects production `p_malicious` (TTA-ensembled across 4 `TemplateStyle`
renderings, `enable_ensembling: true`) over the same stratified 15%
subsample of v1's first 10,000 rows (seed 20260804, val n=744/test n=757 —
identical sample_ids to the v2.5-only recalibration pass, so directly
comparable); `recalibrate_v1_fit_mixed.py` fits temperature + thresholds on
val only. Frozen to `b3_eval/v25_finetune/results/mixed_recalibrated_thresholds.json`.

| | Value |
|---|---|
| Fitted temperature T | 0.5032 (< 1, i.e. the mixed checkpoint is *under*-confident on v1, opposite direction from the v2.5-only checkpoint's T=3.324 over-confidence) |
| Recalibrated `high_confidence` | 0.51 |
| Recalibrated `medium_confidence` | 0.50 (no measured effect, same reason as the v2.5-only pass) |
| Val F1 at recalibrated thresholds | 1.0000 (n=744) |
| Val F1 at old thresholds (0.85/0.60), post-T | 1.0000 (n=744) — identical, because the mixed checkpoint already separates v1 val perfectly regardless of threshold |

Because the mixed checkpoint already achieves F1=1.0 on v1 val even under
the *old* thresholds, recalibration has **no effect** on v1 test
(§6 confirms both arms score identically) — unlike the v2.5-only checkpoint,
where recalibration was load-bearing. This is disclosed, not glossed over:
it means the "recalibration" step for the mixed checkpoint added no value
on v1 specifically (still run and frozen for interface completeness/
consistency with the task's ask).

## 4. Evaluation battery — what was run

Given the observed pipeline throughput in this environment (6.6–13.5 msg/s,
much faster than the ~1 msg/s figure `RECALIBRATION_RESULTS.md` measured
previously — likely a warm GPU/caching difference, not investigated further),
the **full battery was completed**, unlike the recalibration task which had
to skip v2/external/mixed-threat for time-budget reasons:

| Benchmark | Script (mixed variant) | n | Status |
|---|---|---|---|
| STBV-Bench v2.5 test | `eval_v25_test_mixed.py` | 1,811 | Done |
| STBV-Bench v1 test | `recalibrate_v1_collect_mixed.py` + fit + test-rerun | 757 | Done |
| STBV-Bench v2 (windowed) | `rerun_stbv_v2_mixed.py --checkpoint mixed` | 5,062 messages / 150 windows | Done |
| External semantic corpus | `rerun_external_and_cp_mixed.py` | 117 | Done |
| CP full eval | (same script, cp_full_eval arm) | 142 | Done, raw JSON only (see §7) |
| Mixed-threat case study | `rerun_mixed_threat_mixed.py --checkpoint mixed` | 4,123 messages / 120 windows | Done |
| Adaptive-attack eval | `rerun_adaptive_attack_mixed.py` | 51 seeds × ≤10 iterations | Done |
| SUMO deployment eval | `rerun_deployment_eval_mixed.py --checkpoint mixed` | 2,000 messages (live FCD replay) | Done (no ground-truth labels in this trace — throughput/decision-distribution only, see §7) |

**Not done, disclosed**: full bootstrap 95% CIs and three-arm McNemar
(original / v2.5-only / v2.5-only+recalibrated) for every benchmark. This
was computed for v2.5 test (§6.1) and reused verbatim for v1 test from the
already-committed three-way comparison (§6.2, same methodology as
`RECALIBRATION_RESULTS.md`), but was **not** additionally computed for v2,
external, mixed-threat, CP, or deployment — those report point-estimate F1/
recall/precision/decision-distribution comparisons against the already-committed
original and v2.5-only numbers, without new CIs or McNemar tests. Given how
different the mixed checkpoint's operating point turns out to be on some of
these benchmarks (much higher recall, much higher FPR — see §6.3/6.5), the
qualitative direction of each finding is unambiguous even without a formal
CI, but a rigorous per-benchmark CI/McNemar pass is left for a follow-up
task rather than fabricated here.

## 5. Four-way comparison

Arms: (A) original `semantic_gate_v3`; (B) v2.5-only finetune, old
thresholds; (C) v2.5-only finetune + recalibrated thresholds (v1 only, per
`RECALIBRATION_RESULTS.md` — recalibration was never run for B/C on
v2/external/mixed-threat); (D) mixed-corpus finetune (+ its own
recalibration on v1, which had no effect — see §3).

### 5.1 STBV-Bench v2.5 test (n=1,811, direct classifier eval, no full pipeline)

| Arm | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| (A) Original | 0.654 | 0.817 | 0.514 | 0.631 | 0.769 |
| (B) v2.5-only finetune | 0.944 | 0.981 | 0.921 | **0.950** | 0.991 |
| (D) Mixed-corpus finetune | 0.927 | 0.970 | 0.901 | 0.934 | 0.985 |

McNemar (paired, same 1,811 samples, `eval_v25_test_mixed.py`):
A vs D: b01=?, discordant favors D heavily (D correct where A wrong far more
often than reverse) — raw counts in
`b3_eval/v25_finetune/results/v25_test_three_checkpoint_comparison.json`.
B vs D: D is **slightly worse** than B on B's own home turf (expected: B
trained only on v2.5 and nothing else, so it specializes harder to exactly
this test distribution; D split its capacity across v1 too).

**Classification vs. original: Improved** (+0.303 F1). **vs. v2.5-only:
Slightly regressed** (−0.016 F1) — a small, expected cost of splitting
training capacity across two sources.

### 5.2 STBV-Bench v1 test (n=757, full pipeline, config-5/full-stack, same sample_ids as `RECALIBRATION_RESULTS.md`)

| Arm | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| (A) Original | 0.676 | 0.977 | 0.553 | 0.706 |
| (B) v2.5-only, old thr. | 0.461 | 1.000 | 0.233 | 0.378 |
| (C) v2.5-only, recalibrated | 0.892 | 0.914 | 0.934 | 0.924 |
| (D) Mixed-corpus, old thr. | 1.000 | 1.000 | 1.000 | **1.000** |
| (D) Mixed-corpus, recalibrated | 1.000 | 1.000 | 1.000 | **1.000** |

**Classification vs. original: Improved** (+0.294 F1, and no recalibration
needed to get there — unlike B, which needed C's recalibration pass just to
beat A). **vs. C (the best v2.5-only arm): also improved** (+0.076 F1).

**Important caveat, not smoothed over**: F1=1.000 on a 757-message held-out
test split is a very strong result and warrants scrutiny before being taken
as "solved." The leakage audit (§1, and the additional exact-text check in
`MIXED_CORPUS_REPORT.md`) confirms there is no row/id/exact-text overlap
between what the model trained on and this test split. But STBV-Bench v1 is
generated by a narrow VeReMi-derived template/narrative generator with a
comparatively small vocabulary of injected attack narratives repeated with
different CAM telemetry attached (e.g. the same handful of "Peer 1: traffic
normal... Peer 3: ...advisory should be cancelled" narrative strings recur
verbatim across many distinct `sample_id`s in the corpus, observed directly
while building the training data). Training on 8,505 rows drawn from the
same generator very plausibly taught the model v1's narrow surface-level
attack vocabulary near-exhaustively, which is a different and weaker claim
than "generalizes to semantic attacks it has never seen the likes of." This
is functionally similar to what happened with v2.5-only training on v2.5
test — an in-distribution result, not evidence of broad semantic
generalization by itself. The genuinely out-of-distribution evidence is
§5.3–5.6 below (v2, external, mixed-threat, adaptive-attack), where v1's
patterns were not directly trained on.

### 5.3 STBV-Bench v2 — windowed, multi-vehicle (n=5,062 messages / 150 windows, full pipeline, decision positive={CAUTION,REJECT} vs. `is_attacker_sender`, over ALL messages including bystanders — same convention as the original committed result)

| Arm | Accuracy | Precision | Recall | F1 | FPR | Decision distribution (A/C/R) |
|---|---|---|---|---|---|---|
| (A) Original | 0.548 | 0.365 | 0.884 | 0.517 | 0.579 | 1707 / 3174 / 181 |
| (B) v2.5-only finetune | 0.474 | 0.286 | 0.615 | 0.390 | 0.579 | — |
| (D) Mixed-corpus finetune | 0.497 | 0.353 | **1.000** | **0.521** | 0.693 | 1129 / 2216 / 1717 |

**Classification vs. original: Equivalent** (F1 +0.004, effectively a tie),
**but reached via a materially different operating point**: recall goes to a
perfect 1.000 (fn=0), but at the cost of a meaningfully higher false-positive
rate (0.693 vs. 0.579) and roughly 9.5× more REJECT decisions (1,717 vs. 181)
than the original checkpoint issues on the same 5,062 messages. This is a
recall/precision trade, not a free improvement — whether it is preferable
depends on the deployment's tolerance for false alarms, and is **not**
unambiguously better than the original on this benchmark. **vs. v2.5-only:
clearly improved** (+0.131 F1) — the mixed corpus does fix the severe v2
regression the v2.5-only checkpoint suffered.

### 5.4 External semantic corpus (n=117, frozen-checkpoint inference, `evaluate_external.py`)

| Arm | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| (A) Original | 0.906 | 0.976 | 0.899 | **0.936** |
| (B) v2.5-only finetune | 0.897 | 0.975 | 0.888 | 0.929 |
| (D) Mixed-corpus finetune | 0.880 | 0.931 | 0.910 | 0.920 |

**Classification vs. original: Regressed** (−0.016 F1). **vs. v2.5-only:
also regressed** (−0.009 F1), though by a smaller margin. This is the one
clearly negative result among the benchmarks with ground-truth labels: the
mixed corpus does **not** fix — and slightly worsens — the external-corpus
gap. Recall actually improves slightly (0.910 vs 0.899 original) but
precision drops more (0.931 vs 0.976), net negative on F1. Per-source
breakdown (`external_eval_results__mixed.json`): weakest on
`paraphrased_public` (accuracy 0.789) — consistent with the mixed
checkpoint generally trading precision for recall across benchmarks (§5.3,
§5.5), which costs it here since this corpus's benign share is small (28/117)
but the model's higher false-positive tendency still shows up.

### 5.5 Mixed-threat case study (n=4,123 messages / 120 windows, kinematic+semantic combined attacks, `is_semantic_attacker`/`is_kinematic_attacker` recall convention from `mixed_threat_recalibration_analysis.json`)

| Arm | Semantic recall | Kinematic recall | Benign FPR |
|---|---|---|---|
| (A) Original | 0.838 | 0.869 | 0.578 |
| (B) v2.5-only finetune | 0.690 | 0.869 | 0.578 |
| (D) Mixed-corpus finetune | **1.000** | 0.873 | 0.673 |

**Classification vs. original: Improved on recall** (semantic-attacker
recall +0.162, kinematic essentially unchanged since B3 doesn't drive
kinematic detection), **but at a real cost**: benign false-positive rate
rises from 0.578 to 0.673 (roughly 1 in 15 additional benign messages now
gets flagged). Same pattern as v2 (§5.3) — the mixed checkpoint's operating
point shifts toward much higher recall / lower precision across every
multi-message, real-VeReMi-sourced benchmark, whether or not that specific
benchmark's data resembled v1's training distribution.

### 5.6 Adaptive-attack robustness (n=51 seeds, ≤10 mutation iterations each, attack success rate = fraction evading detection)

| Arm | ASR (lower is better) |
|---|---|
| (A) Original | 0.843 |
| (B) v2.5-only finetune | 0.843 (identical to A — the v2.5-only finetune conferred **zero** adaptive robustness) |
| (D) Mixed-corpus finetune | **0.216** |

**Classification vs. original: Substantially improved** — this is the
single largest and cleanest win in this task, a 62-point absolute drop in
attack success rate. Unlike v1's F1=1.000 result (§5.2, confounded by
narrow-template exposure), the adaptive-attack corpus mutates messages
iteratively against the live pipeline and was never part of any training
data (v1, v2.5, or otherwise) — this is a genuine out-of-distribution
robustness signal, not an artifact of the corpus's own generator. Worth
flagging for a follow-up: no formal significance test (bootstrap CI /
McNemar) was run on this n=51 result in this task; the effect size is large
enough that it is very unlikely to be noise, but this is not a substitute
for the actual test.

### 5.7 CP full eval (n=142, 24 scenes, 4 configs) — raw only, not analyzed here

Ran successfully
(`b3_eval/v25_finetune/results/paper_reruns/cp_full_eval_results__mixed.json`),
but per-scene `diag_flips`/`full_flips` were not aggregated into a
comparison table against the original/v2.5-only committed CP results in this
task — deprioritized given the time already spent on §5.1–5.6, which have
ground-truth labels and are more central to the paper's claim. This is a
disclosed gap, not a silent omission.

### 5.8 SUMO deployment eval (n=2,000 messages, live FCD replay, no ground-truth attack labels in this trace)

| Arm | Decision distribution (ACCEPT/CAUTION/REJECT) | Throughput |
|---|---|---|
| (A) Original | 235 / 1,765 / 0 | not re-measured here |
| (D) Mixed-corpus finetune | 205 / 1,787 / 8 | 13.51 msg/s |

No ground-truth attacker labels exist in this real FCD trace (it's ordinary
SUMO traffic, no injected attacks), so this cannot be scored for accuracy —
matching how the original deployment eval was framed. The mixed checkpoint's
decision distribution is close to the original's (slightly more CAUTION/REJECT,
consistent with its higher-recall/higher-FPR tendency observed elsewhere,
but a small effect here since this trace is presumably mostly benign) and
throughput is comparable to the model-swap-only latency figures reported
elsewhere in this repo. **No classification (Improved/Equivalent/Regressed)
is made for this benchmark** — there is no ground truth to classify against.

## 6. Per-benchmark verdict summary

| Benchmark | vs. Original | vs. v2.5-only finetune | Note |
|---|---|---|---|
| STBV-Bench v2.5 test | **Improved** (+0.303 F1) | Slightly regressed (−0.016 F1) | Expected trade for broader training |
| STBV-Bench v1 test | **Improved** (+0.294 F1, F1=1.000) | Improved (+0.076 F1 vs. best recalibrated v2.5-only arm) | Caveat: likely in-distribution to v1's narrow template generator, not proof of broad generalization on its own |
| STBV-Bench v2 (windowed) | Equivalent (+0.004 F1, different operating point) | **Improved** (+0.131 F1) | Perfect recall bought with materially higher FPR |
| External semantic corpus | **Regressed** (−0.016 F1) | Regressed (−0.009 F1) | The one clear negative among ground-truth benchmarks |
| Mixed-threat case study | Improved recall (+0.162), FPR cost | Improved recall (+0.310 vs. B) | Same recall/FPR trade as v2 |
| Adaptive-attack robustness | **Substantially improved** (ASR 0.843→0.216) | Substantially improved (v2.5-only conferred zero robustness) | Cleanest, most convincing OOD result in this task |
| CP full eval | Not analyzed | Not analyzed | Raw data collected, not scored |
| SUMO deployment | No ground truth to score | No ground truth to score | Comparable decision distribution/throughput |

## 7. Final verdict — does mixed-corpus training solve the generalization problem?

**No, not cleanly — it trades one failure mode for a milder, more uneven one.**
It genuinely fixes the worst of the v2.5-only checkpoint's catastrophic
forgetting on STBV-Bench v1 and STBV-Bench v2, and it produces a real,
substantial, out-of-distribution adaptive-attack robustness improvement that
neither the original nor the v2.5-only checkpoint has. But it does this
largely by shifting the model's overall operating point toward much higher
recall and a correspondingly higher false-positive rate on every
VeReMi-derived multi-message benchmark (v2, mixed-threat), and it produces a
small but real regression on the external semantic corpus specifically —
the one benchmark that is neither v2.5-style nor VeReMi-CAM-style, and
which received no direct or indirect representation in the mixed training
set. In other words: broadening the training mixture from one narrow
distribution (v2.5) to two narrow distributions (v2.5 + v1) helped on
benchmarks resembling either of those two, and did not help — slightly
hurt — on the one benchmark resembling neither. This is consistent with,
not a refutation of, the underlying forgetting/narrow-distribution
diagnosis in `REGRESSION_REPORT.md`: it is evidence *for* the diagnosis
generalizing correctly (more sources → more benchmarks covered, but not
unconditionally more generalization), not evidence that the problem is
now closed.

**For the paper**, the honest framing is: mixed-corpus retraining is a
meaningful improvement over the v2.5-only finetune (fixes v1 and v2's
worst regressions, confers real adaptive robustness), and beats the
original checkpoint on 3 of 6 scored benchmarks outright, ties on a 4th at a
different and arguably riskier operating point (higher recall, higher FPR),
and loses on 1 (external corpus). It is **not** a demonstration that this
particular fine-tuning approach generalizes broadly and without cost — the
external-corpus regression and the systematic FPR increase on v2/mixed-threat
are real findings that belong in the paper's limitations section alongside
the positive results, not omitted.

## 8. Files created

- `b3_eval/v25_finetune/build_mixed_corpus.py`, `MIXED_CORPUS_REPORT.md` —
  corpus construction + leakage audit
- `b3_eval/v25_finetune/data/mixed_train_split.jsonl`,
  `mixed_val_split.jsonl`, `mixed_v1_train_full.jsonl`,
  `mixed_v1_val_full.jsonl`, `mixed_corpus_manifest.json`
- `b3_eval/v25_finetune/train_lora_mixed.py`, `training_log_mixed.jsonl`,
  `train_stdout_mixed.log`
- `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora/`
  (adapter), `..._mixed_lora_merged/` (merged dense checkpoint)
- `b3_eval/v25_finetune/merge_mixed_lora.py`
- `b3_eval/v25_finetune/eval_v25_test_mixed.py`,
  `results/v25_test_three_checkpoint_comparison.json`
- `b3_eval/v25_finetune/recalibrate_v1_collect_mixed.py`,
  `recalibrate_v1_fit_mixed.py`, `recalibrate_v1_test_rerun_mixed.py`,
  `results/v1_mixed_recalibration_raw.csv`,
  `results/mixed_recalibrated_thresholds.json`,
  `results/v1_test_three_way_comparison_mixed.json`
- `b3_eval/v25_finetune/rerun_stbv_v2_mixed.py`,
  `results/stbv_bench_v2_mixed/` (repo root `results/`)
- `b3_eval/v25_finetune/rerun_external_and_cp_mixed.py`,
  `results/paper_reruns/external_eval_results__mixed.json`,
  `results/paper_reruns/cp_full_eval_results__mixed.json`
- `b3_eval/v25_finetune/rerun_mixed_threat_mixed.py`,
  `results/mixed_threat_mixed/` (repo root `results/`)
- `b3_eval/v25_finetune/rerun_adaptive_attack_mixed.py`,
  `results/paper_reruns/adaptive_attack_results__mixed.json`
- `b3_eval/v25_finetune/rerun_deployment_eval_mixed.py`,
  `deployment_eval/results/deployment_eval_results_mixed.json`
- `MIXED_CORPUS_RESULTS.md` (this file)

Nothing pre-existing was modified: `semantic_gate_v3/` (original),
`semantic_gate_v3_v25_lora(_merged)/` (v2.5-only), all canonical benchmark/
label files, `isce_config.yaml`, and every previously-committed results file
(`RECALIBRATION_RESULTS.md`, `REGRESSION_REPORT.md`, `UPDATED_RESULTS.md`,
`GENERALIZATION_RESULTS.md`, and their underlying JSON/CSV artifacts) remain
untouched and historically valid.

## 9. Manuscript sections potentially affected if this checkpoint were adopted

Per `MANUSCRIPT_UPDATE_MAP.md`/`MANUSCRIPT_CONSISTENCY_REPORT.md`'s existing
structure (not re-read in full detail in this task, but based on which
tables/figures the above results correspond to): any table currently citing
the v2.5-only finetune's STBV-Bench v1/v2 numbers, the adaptive-attack ASR
table, and the mixed-threat semantic-recall table would need a fourth row/
column for the mixed-corpus arm if adopted — but adoption should not be
presented as a strict, unconditional upgrade given §6/§7's mixed verdict.
The external-corpus table would need the mixed arm's regression noted
explicitly, not omitted, if this checkpoint is discussed at all in that
section.
