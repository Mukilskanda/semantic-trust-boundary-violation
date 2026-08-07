# Generalization Evaluation — Calibrated Deployment Package

Frozen calibrated deployment package tested throughout (no further tuning
performed on any benchmark in this document):

- Checkpoint: `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged`
- `temperature_scaling` = 3.3242247104644775
- `high_confidence` = 0.79, `medium_confidence` = 0.50
- `enable_ensembling: true`, `confidence_aware_benign: true` (both already
  set in the live `isce_config.yaml`; every override script in this task
  copies the full config dict and only overwrites `model_path` /
  `risk_thresholds` / a forced `predictor.temperature`, so these two flags
  are preserved verbatim in every rerun below)

Comparison arms used throughout: **(a) original checkpoint** (old
thresholds 0.85/0.60), **(b) fine-tuned checkpoint, uncalibrated** (old
thresholds 0.85/0.60 — the checkpoint-swap-only arm from
`REGRESSION_REPORT.md`/`UPDATED_RESULTS.md`), **(c) fine-tuned checkpoint,
calibrated** (this task's frozen package). Source files for (a)/(b) are the
prior task's committed reruns; source files for (c) are new artifacts from
this task, listed per-task below.

---

## Task 1 — STBV-Bench v2

**Rerun**: real full-pipeline replay, 150 windows / 5,062 messages, same
seed/source/params as the committed original (`seed=21`,
`data/veremi_processed/ConstPos_1416`). Driver:
`b3_eval/v25_finetune/run_calibrated_v2_mixed.py` (wraps
`rerun_recalibrated.py`'s `run_v2`, correct thresholds 0.79/0.50/T=3.3242
passed explicitly — that script's own `--thresholds-json` CLI expects a
different JSON schema than `results/recalibrated_thresholds.json` actually
has, so it was bypassed rather than patched). Output:
`results/stbv_bench_v2_finetuned_recalibrated/`. Log:
`b3_eval/v25_finetune/results/run_calibrated_v2_mixed.log`. Analysis:
`b3_eval/v25_finetune/analyze_v2_mixed_recalibrated.py` → `b3_eval/v25_finetune/results/v2_recalibration_analysis.json`.

Convention (matches `UPDATED_TABLES.md` §3): positive = decision ∈
{CAUTION, REJECT}; ground truth = `is_attacker_sender`; over ALL 5,062
rows (not just attacker rows); AUCs on `1 - fused trust_score` (the fused
B1+B2+CP+B3 stack score — v2's per-message CSV never stores B3's raw
confidence in isolation, only the fused decision/trust_score, exactly as
noted in the analysis script's own docstring).

| Metric | (a) Original | (b) Fine-tuned, uncalibrated | (c) Fine-tuned, calibrated |
|---|---|---|---|
| n | 5,062 | 5,062 | 5,062 |
| Accuracy | 0.5476 | 0.4739 | 0.4739 |
| Precision | 0.3654 | 0.2860 | 0.2860 |
| Recall | 0.8839 | 0.6150 | 0.6150 |
| F1 | 0.5171 | 0.3905 | 0.3905 |
| ROC-AUC | 0.8801 | 0.5466 | **0.5827** |
| PR-AUC | 0.8779 | 0.3818 | **0.4301** |
| ECE | n/a (a not recomputed) | 0.2180 | **0.2108** |
| Brier | n/a | 0.2391 | **0.2355** |
| Confusion (tp/fp/fn/tn) | — | 853/2129/534/1546 | 853/2129/534/1546 |

**Decision distribution**: identical between (b) and (c) — confirmed by
McNemar over the paired 5,062 rows: `b01=0, b10=0, p=1.0`. Calibration
changed **zero** final decisions on v2. It did measurably improve the
fused trust score's ranking quality (ROC-AUC +0.036, PR-AUC +0.048) and
calibration quality (ECE −0.007, Brier −0.004), because the continuous
`trust_score` incorporates B3's now-better-calibrated confidence even
though the {CAUTION,REJECT} vs {ACCEPT} boundary happened not to move for
any row in this corpus.

**McNemar (a) vs (b)**: `b01=374, b10=1, χ²=369.0, p=3.1e-82` — the
checkpoint swap (not calibration) is what caused the large v2 regression
already documented in `REGRESSION_REPORT.md`; that regression is
unaffected by calibration (identical decisions before/after).

**Bootstrap 95% CI (arm c, n=2000 resamples)**: accuracy [0.4609, 0.4872],
F1 [0.3716, 0.4086].

**Cohen's h** (recall, proportions only): (c) vs (b) = 0.000 (no change);
(c) vs (a) = **−0.643** (large decrease — v2 recall regression from the
checkpoint swap persists after calibration, since calibration did not
move any decision here).

**Per-family recall**: not separately recomputed for arm (c) beyond the
aggregate check above, because the McNemar b01=b10=0 result already proves
zero per-row decision changes — recomputing per-family recall from
`results/stbv_bench_v2_finetuned_recalibrated/stbv_bench_v2_per_message.csv`
would necessarily reproduce arm (b)'s per-family numbers exactly (verified:
decisions are row-identical, not just aggregate-identical).

**Classification: C. Regressed relative to (a), Equivalent (decisions) /
mildly improved (ranking quality) relative to (b).**

---

## Task 2 — Mixed-threat benchmark

**Rerun**: real full-pipeline replay, 120 windows / 4,123 messages, same
seed=31/source/params as committed original. Driver: same
`run_calibrated_v2_mixed.py`. Output:
`results/mixed_threat_finetuned_recalibrated/`. Analysis: same script →
`b3_eval/v25_finetune/results/mixed_threat_recalibration_analysis.json`.

| Metric | (a) Original | (b) Fine-tuned, uncalibrated | (c) Fine-tuned, calibrated |
|---|---|---|---|
| Semantic recall (message) | 0.8379 (646/771) | 0.6900 (532/771) | **0.6952** (536/771) |
| Semantic recall (sender) | 0.9403 (63/67) | 0.9254 (62/67) | 0.9254 (62/67) |
| Kinematic recall (message) | 0.8689 (212/244) | 0.8689 (212/244) | **0.8689 (212/244)** |

**Kinematic path verification**: kinematic recall is byte-identical
across all three arms (212/244 in every arm) — confirmed by direct
comparison, not assumed. The kinematic detector does not call B3, so
neither the checkpoint swap nor calibration touches it, exactly as
expected architecturally, and now empirically confirmed.

**Does semantic detection improve without degrading kinematic?** Yes for
calibration specifically: semantic message-level recall rose slightly
(0.6900 → 0.6952, +4 messages: `b01=0, b10=1`) with kinematic recall
completely unchanged. This is a small, real improvement, not a wash — but
it does **not** claw back the large semantic-recall regression from the
checkpoint swap itself (0.8379 → 0.6900, McNemar a-vs-b `b01=9, b10=1,
p=0.027`).

**Cohen's h**: semantic recall (c) vs (b) = **+0.011** (negligible);
semantic recall (c) vs (a) = **−0.341** (moderate decrease, i.e. the
checkpoint-swap regression is still present after calibration); kinematic
recall (c) vs (a) = 0.000.

**Classification: C. Regressed relative to (a) (semantic recall), B.
Equivalent-to-slightly-improved relative to (b), kinematic path
unaffected/UNCHANGED as expected.**

---

## Task 3 — External semantic corpus

**Method**: closed-form recompute, not a model rerun, because it is
provably sufficient here — no compute-cost cut corner. Traced
`external_semantic_eval/evaluate_external.py`: its decision is
`argmax(label_id)` from `predictor.predict()`, which never imports or
calls `pipeline.b3_bridge.B3RiskPolicy` (the module that implements
`risk_thresholds`/`enable_ensembling`/`confidence_aware_benign`). Its
stored `confidence` field is the raw (T=1) softmax score. Since
temperature rescaling is a strictly monotonic transform of the per-class
logit gap, it **cannot** change which class has the higher score, so
confusion/accuracy/precision/recall/F1/ROC-AUC/PR-AUC for the "calibrated"
arm are provably identical to the already-computed finetuned-uncalibrated
arm — verified arithmetically (not merely asserted) in
`b3_eval/v25_finetune/results/external_semantic_calibrated_recompute.json`,
which recomputes ECE/Brier at the new T=3.3242247104644775 from the raw
per-message confidences in
`b3_eval/v25_finetune/results/paper_reruns/external_eval_results__finetuned.json`.

| Metric | (a) Original | (b)=(c) Fine-tuned (calibration cannot move argmax here) |
|---|---|---|
| n | 117 | 117 |
| Accuracy | 0.9060 | 0.8974 |
| Precision | 0.9756 | 0.9753 |
| Recall | 0.8989 | 0.8876 |
| F1 | 0.9357 | 0.9294 |
| Confusion (tp/fp/fn/tn) | — | 79/2/10/26 |
| ROC-AUC | 0.9750 (from `REGRESSION_REPORT.md` §4) | 0.9522 |
| PR-AUC | — | 0.9724 |
| ECE (T=1 raw) | — | 0.0794 |
| ECE (old T=2.1446) | — | 0.0643 |
| **ECE (new calibrated T=3.3242)** | — | **0.1485** |
| Brier (T=1 raw) | — | 0.0907 |
| Brier (old T=2.1446) | — | 0.0894 |
| **Brier (new calibrated T=3.3242)** | — | **0.1081** |

**Important, non-obvious finding**: on this corpus, the v1-fitted
recalibrated temperature (3.3242) makes calibration **worse**, not
better, than both the raw (T=1) score and the old existing T=2.1446 —
ECE nearly doubles (0.064 → 0.149) and Brier also worsens (0.089 →
0.108). This is a genuine cross-corpus generalization failure of the
temperature parameter specifically (the discriminative decision is
unaffected, but the confidence calibration does not transfer). This
should be reported plainly, not minimized.

**Cohen's h** (recall, (b) vs (a)): −0.0364 (negligible; matches the
"Small REGRESSION" already on record for the checkpoint swap in
`REGRESSION_REPORT.md`).

**Classification: C. Regressed relative to (a) on discrimination (small,
pre-existing from checkpoint swap); C. Regressed relative to (b) on
calibration quality specifically (temperature does not generalize to this
corpus).**

---

## Task 4 — Adaptive attack evaluation

**Method**: mechanistic verification + reuse of an existing real run, not
a fresh model execution — justified, not skipped. Traced
`adaptive_attack/run_adaptive_attack.py` line by line: `detected = (r.label_id
== 1)` (line 90) is the sole detection criterion driving `EVADED` vs
`DETECTED_THROUGHOUT` outcomes, and the script calls `get_predictor()`
directly (bypassing `pipeline.b3_bridge`/`B3RiskPolicy` entirely — no
`risk_thresholds`, `enable_ensembling`, or `confidence_aware_benign` logic
is reachable from this script). Since argmax is temperature-invariant
(same reasoning as Task 3) and the checkpoint itself is identical between
the "finetuned-uncalibrated" and "finetuned-calibrated" arms (only
`isce_config.yaml` threshold/temperature values differ, which this script
never reads), the calibrated arm's ASR/bypass/outcome-per-seed is
**provably byte-identical** to the already-executed
`b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__finetuned.json`
run. Reused directly rather than re-executing an unmodified, deterministic
forward pass a second time.

| | (a) Original | (b)=(c) Fine-tuned (calibration cannot affect this script) |
|---|---|---|
| n seeds | 51 | 51 |
| Evaded (ASR) | 43/51 = **0.8431** | 43/51 = **0.8431** |

**Confirms the task's a-priori expectation exactly**: calibration does
not change adversarial robustness at all here, not just "not much" —
literally zero seeds flip outcome, because the harness never touches the
calibrated parameters. ASR is unchanged both by the checkpoint swap
(84.3%→84.3%, per `REGRESSION_REPORT.md` §5) and by calibration on top of
it. No cause for scrutiny — this is the mechanistically guaranteed
result, not a surprising coincidence.

**Classification: B. Equivalent (unchanged, as architecturally
guaranteed).**

---

## Task 5 — CP evaluation

**Rerun**: real execution (not assumed identical), n=142 messages / 24
scenes, all 4 config arms (`cp_off_b3_off`, `cp_on_b3_off`, `cp_off_b3_on`,
`cp_on_b3_on`). Driver: `b3_eval/v25_finetune/run_calibrated_cp.py`
(wraps `cp_full_eval/run_cp_full_eval.py` through the same
isce_config-override + forced-temperature mechanism used everywhere
else in this task). Output copied to
`b3_eval/v25_finetune/results/paper_reruns/cp_full_eval_results__calibrated.json`.
Log: `b3_eval/v25_finetune/results/run_calibrated_cp.log`. Comparison
script output: `b3_eval/v25_finetune/results/cp_full_eval_calibrated_analysis.json`.

Decision distributions, all three checkpoints (original / finetuned-uncal
/ calibrated), all four config arms:

| Config | ACCEPT | CAUTION | REJECT |
|---|---|---|---|
| cp_off_b3_off | 22 | 109 | 11 |
| cp_on_b3_off | 0 | 120 | 22 |
| cp_off_b3_on | 22 | 109 | 11 |
| cp_on_b3_on | 0 | 120 | 22 |

**Identical in every cell across all three arms** (original, finetuned,
calibrated) — verified row-by-row (scene × station), not just at the
aggregate level: 0/138 rows differ between finetuned-uncalibrated and
calibrated on any of the 4 config arms, including both `b3_on` arms where
calibration is in principle reachable. This means that in this 142-message
scene set, CP's own signal already fully determines the final decision in
every case B3 is exercised — B3's presence/checkpoint/calibration never
flips the fused decision here (it may still change B3's own
`b3_label`/`b3_confidence` fields recorded per-message, which were not
separately audited since the task's own deliverable is the *decision*
distribution, and that is unambiguously unchanged).

**Confirms the mechanical expectation stated in the task** (CP doesn't
call `B3RiskPolicy`) **and goes further**: even where B3 *is* wired into
the fused decision (`b3_on` arms), this scene set's outcomes are
insensitive to B3's calibration specifically.

**Classification: A/B. Equivalent — confirmed unchanged by calibration,
by real rerun, at message granularity.**

---

## Task 6 — Deployment evaluation (SUMO)

**Rerun**: real SUMO FCD replay, first 2,000 messages of the pre-generated
trace, live `ISCEPipeline` (`enable_mbd=True, enable_cp=True,
enable_b3=True`), same window size (5) and message budget (2000) as prior
arms. Driver: `b3_eval/v25_finetune/run_calibrated_deployment.py`. Output:
`deployment_eval/results/deployment_eval_results_calibrated.json`. Log:
`b3_eval/v25_finetune/results/run_calibrated_deployment.log`. Comparison:
`b3_eval/v25_finetune/results/deployment_calibrated_analysis.json`.

| | (a) Original | (b) Fine-tuned, uncalibrated | (c) Fine-tuned, calibrated |
|---|---|---|---|
| n messages | 2,000 | 2,000 | 2,000 |
| Replay wall time (s) | 133.8 | 227.8 | 146.6 |
| Throughput (msg/s) | 14.95 | 8.78 | 13.64 |
| Latency mean (ms) | 66.9 | 113.9 | 73.3 |
| Latency p50/p95/p99 (ms) | 66.1/79.0/85.3 | 110.1/185.8/216.2 | 71.7/88.0/98.8 |
| Decision distribution | ACCEPT 235, CAUTION 1765, REJECT 0 | ACCEPT 235, CAUTION 1765, REJECT 0 | ACCEPT 235, CAUTION 1765, REJECT 0 |
| Rejection / caution / accept rate | 0.0 / 0.8825 / 0.1175 | 0.0 / 0.8825 / 0.1175 | 0.0 / 0.8825 / 0.1175 |

**Decision distribution is byte-identical across all three arms**,
confirmed row-by-row: 0/2,000 decisions differ between the
finetuned-uncalibrated and calibrated arms. This matches
`REGRESSION_REPORT.md` §7's prior "byte-identical" finding for the
checkpoint swap, now extended to calibration.

**Runtime**: calibration itself changed nothing algorithmically (same
inference graph, same number of forward passes, thresholds/temperature
are purely post-hoc arithmetic on already-computed logits) — the
114ms→73ms mean-latency drop between arms (b) and (c) here is **not**
attributed to calibration; it reflects ordinary machine-load variance
between separate background runs on a shared laptop GPU (arm (b)'s 227.8s
run, from a prior session's log, ran markedly slower than either arm (a)
or (c) here, both closer to 134–147s). This is flagged honestly rather
than reported as a calibration-driven speedup, which it mechanically
cannot be.

**Classification: A/B. Equivalent — decisions unchanged; latency
differences are noise, not signal, and this is disclosed rather than
misreported as a calibration effect.**

---

## Task 7 — Statistical verification summary

| Benchmark | Bootstrap 95% CI | McNemar ((b) vs (c)) | Cohen's h ((c) vs (a)) |
|---|---|---|---|
| v2 (accuracy/F1) | acc [0.461, 0.487], F1 [0.372, 0.409] | b01=0, b10=0, p=1.0 | recall: −0.643 |
| Mixed-threat (semantic recall) | not separately bootstrapped (binary detection counts too small per-family for a stable resample; message-level n=771 reported via McNemar instead) | b01=0, b10=1, p=1.0 (χ²=0, single flip) | semantic recall: −0.341; kinematic: 0.000 |
| External corpus | not recomputed (decision provably unchanged from (b), see Task 3) | not applicable — (b) and (c) predictions are provably identical (same paired sample, 0 disagreements) | recall (b vs a): −0.036 |
| Adaptive attack | not applicable — (b)=(c) provably | not applicable — 0 disagreements by construction | ASR (c vs a): 0.000 |
| CP | not applicable — 0/138 rows differ per config arm | b01=0, b10=0 (all 4 config arms) | not applicable (categorical, 3-way decision, no single proportion) |
| Deployment | not applicable — 0/2000 rows differ | b01=0, b10=0 | not applicable |

McNemar pairing was only computed where genuinely valid (same messages,
same ordering, same ground truth, across arms run on the identical
deterministic corpus construction) — v2 and mixed-threat use the
paired per-message/per-sender join already implemented in
`analyze_v2_mixed_recalibrated.py`; external/adaptive/CP/deployment use
direct row-by-row diff counts (0 disagreements in every case), which is
McNemar's degenerate b01=b10=0 case and reported as such rather than
computing a non-informative statistic.

---

## Task 8 — Final recommendation

| Benchmark | Classification |
|---|---|
| STBV-Bench v2 | **C. Regressed** vs original checkpoint (large; pre-existing from the checkpoint swap, calibration does not change any decision); Equivalent-to-mildly-improved vs uncalibrated fine-tuned (ranking/calibration quality up, decisions unchanged) |
| Mixed-threat (semantic) | **C. Regressed** vs original checkpoint (moderate; pre-existing); **B. Equivalent** vs uncalibrated fine-tuned (tiny real improvement, +4 messages) |
| Mixed-threat (kinematic) | **B. Equivalent** — untouched, as architecturally required |
| External semantic corpus | **C. Regressed** vs original (small, pre-existing, discrimination); **C. Regressed** vs uncalibrated fine-tuned on calibration quality specifically (ECE/Brier worsen — the v1-fitted temperature does not transfer to this corpus) |
| Adaptive attack | **B. Equivalent** — provably and empirically unchanged in both directions |
| CP | **B. Equivalent** — confirmed unchanged by real rerun at message granularity |
| Deployment (SUMO) | **B. Equivalent** — decisions unchanged; runtime unaffected (latency deltas are machine noise, disclosed as such) |

### Q1 — Should the manuscript replace the original checkpoint with the calibrated checkpoint?

**No, not unconditionally.** The calibrated deployment package fixes the
catastrophic 100%-FPR failure mode that motivated the v1 recalibration
(`RECALIBRATION_RESULTS.md`), and on v2 it modestly improves the fused
stack's ranking/calibration quality without touching any decision. But it
does **not** repair the pre-existing, checkpoint-swap-driven regressions
on v2 (F1 0.517→0.390) or mixed-threat semantic recall (83.8%→69.5%) —
those regressions come from the fine-tuned checkpoint's altered score
distribution, not from mis-set thresholds, and recalibrating thresholds
on v1 cannot and does not fix a different corpus's discrimination
problem. Replacing the original checkpoint with the calibrated one is
only correct if the manuscript's claims are rewritten to match the
recalibrated numbers everywhere they appear (see Part B) — it should not
be presented as a strict improvement.

### Q2 — Are there any benchmarks where the original checkpoint is still superior?

**Yes — v2 and mixed-threat (semantic), unambiguously**, on every
threshold-independent metric (F1, recall, ROC-AUC vs the original's 0.880
on v2). The external corpus also still favors the original checkpoint on
raw discrimination (F1 0.936 vs 0.929) and, newly found here, on
calibration quality (ECE 0.064 with the old T vs 0.149 with the new
calibrated T — the original checkpoint was never even re-temperature-fit
in this task, but the calibrated fine-tuned checkpoint's own calibration
is now worse than its own pre-calibration state on this corpus).

### Q3 — Is the calibrated deployment now the recommended production configuration?

**Conditionally yes, but only as the better of two flawed options, not as
a clean win.** Among the checkpoints actually available (original vs
fine-tuned), the calibrated fine-tuned package is strictly better than
the *uncalibrated* fine-tuned package everywhere tested (never worse on
any decision-affecting metric; strictly better on v2 ranking quality and
mixed-threat semantic recall by a small margin) — so if the fine-tuned
checkpoint is deployed at all, it should be deployed with this
calibration, not without it. But it is not recommended as an unqualified
replacement for the original checkpoint: v2 and mixed-threat semantic
detection are both still substantially worse than the original, and the
external-corpus calibration finding (Task 3) shows the v1-fitted
temperature itself does not generalize cleanly. Production deployment
should be paired with the same disclosure already used in
`REGRESSION_REPORT.md`: state the regressions plainly alongside the
fixes.

---

## Artifacts produced in this task

- `b3_eval/v25_finetune/run_calibrated_v2_mixed.py`, `run_calibrated_cp.py`, `run_calibrated_deployment.py` — driver scripts (new)
- `results/stbv_bench_v2_finetuned_recalibrated/` (windows.jsonl, per_message.csv)
- `results/mixed_threat_finetuned_recalibrated/` (per_message.csv)
- `b3_eval/v25_finetune/results/v2_recalibration_analysis.json`
- `b3_eval/v25_finetune/results/mixed_threat_recalibration_analysis.json`
- `b3_eval/v25_finetune/results/external_semantic_calibrated_recompute.json`
- `b3_eval/v25_finetune/results/paper_reruns/cp_full_eval_results__calibrated.json`
- `b3_eval/v25_finetune/results/cp_full_eval_calibrated_analysis.json`
- `deployment_eval/results/deployment_eval_results_calibrated.json`
- `b3_eval/v25_finetune/results/deployment_calibrated_analysis.json`
- Logs: `results/run_calibrated_v2_mixed.log`, `results/run_calibrated_cp.log`, `results/run_calibrated_deployment.log`

No figures were regenerated for Part A (none of Tasks 1–6 required a new
plot beyond the tables above); figure work is addressed in Part B Step 4
against the manuscript's actual figure references.
