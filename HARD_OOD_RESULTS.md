# HARD_OOD_RESULTS.md

## Addendum — audit-revised, final validated result (supersedes the numbers below for paper purposes)

Following `HARD_OOD_BENCHMARK_AUDIT.md`'s scope audit and Task 2's
replacement of the 72 out-of-scope `cb_informal` messages, the frozen final
checkpoint (**no retraining** — Task 3 was evaluated and not triggered,
see `FINAL_EVALUATION_REPORT.md`'s addendum) was re-evaluated on
`hard_ood_bench/hard_ood_corpus_v2.jsonl` ($n=288$).

| Metric | Original corpus | **Revised corpus (final)** |
|---|---|---|
| Accuracy | 0.500 | 0.458 |
| Precision | 0.853 | 0.891 |
| Recall | 0.302 [0.238, 0.369] | 0.214 |
| **F1** | 0.446 [0.368, 0.520] | **0.345 [0.267, 0.418]** |
| ROC-AUC | 0.667 | 0.652 |
| PR-AUC | 0.795 | 0.796 |
| ECE | 0.459 | 0.492 |
| Brier | 0.463 | 0.496 |
| Confusion (TP/FP/FN/TN) | 58/10/134/86 | 41/5/151/91 |

**The scope correction made the result worse, not better: F1 0.446 → 0.345.**
The replaced `cb_informal` stratum was the *easiest* in the original corpus
(F1=0.633); the 72 new realistic, ETSI-plausible replacement messages alone
score F1=0.281, the hardest single stratum measured anywhere in this
benchmark. **This is reported as the true, final, validated hard-OOD
result. It does not cross the 80% accuracy success criterion — accuracy is
0.458, well below it — and no legitimate scope correction or benchmark
audit brought it anywhere close.** The gap is real, in-domain, and not an
artifact of unrealistic test construction. Source:
`hard_ood_bench/hard_ood_results_v2.json`,
`hard_ood_bench/hard_ood_metrics_v2.json`.

---

*The section below describes the original (pre-audit) 288-message corpus
and is retained for traceability, not as the paper's reported number.*

Evaluation of the frozen final production checkpoint
(`semantic_gate_v3_mixed_lora_merged`, no retraining, direct B3-only
inference via `pipeline.b3_bridge.classify_text` — the same production
inference class used throughout this paper) on the new hard-OOD corpus
($n=288$). Script: `hard_ood_bench/eval_hard_ood.py`. Raw output:
`hard_ood_bench/hard_ood_results.json`; computed metrics:
`hard_ood_bench/hard_ood_metrics.json`.

## Headline metrics

| Metric | Value |
|---|---|
| Accuracy | 0.500 |
| Precision | 0.853 |
| Recall | 0.302 |
| F1 | **0.446** |
| FPR | 0.104 |
| ROC-AUC | 0.667 |
| PR-AUC | 0.795 |
| ECE | 0.459 |
| Brier | 0.463 |
| Confusion (TP/FP/FN/TN) | 58 / 10 / 134 / 86 |
| Mean / p50 / p95 latency | 24.3 / 23.3 / 33.9 ms (B3-only, no fusion overhead) |

**This is, by a wide margin, the hardest benchmark in this paper** — F1
0.446 vs. 0.995 (STBV-Bench v1), 0.920 (external corpus), 0.521 (STBV-Bench
v2). It is also markedly *worse calibrated* than any other benchmark (ECE
0.459 vs. 0.017 on STBV-Bench v1's B3-alone confidence) — the model is
frequently both wrong and confident on this corpus, not usefully uncertain.

## Per-family recall (malicious concepts, $n=16$ each)

| Family | Recall | Precision |
|---|---|---|
| hazard_normalization | 0.000 | -- |
| instruction_hiding | 0.000 | -- |
| goal_manipulation | 0.125 | 1.000 |
| traffic_efficiency_lure | 0.188 | 1.000 |
| context_inversion | 0.250 | 1.000 |
| priority_manipulation | 0.313 | 1.000 |
| cross_source_contradiction | 0.313 | 1.000 |
| false_clearance | 0.313 | 1.000 |
| fabricated_consensus | 0.375 | 1.000 |
| sensor_discreditation | 0.500 | 1.000 |
| authority_override | 0.500 | 1.000 |
| reputation_inflation | 0.750 | 1.000 |

Every malicious family that has any detections at all has **precision
1.000** — when B3 flags a hard-OOD message, it is essentially always
correct (only the 10 FPs, all on benign families, break this). The failure
mode here is overwhelmingly **false negatives** (silence on genuinely
malicious OOD text), not false alarms — a materially different failure
profile from every other benchmark in this paper, worth stating plainly
rather than folding into a single aggregate number.

## Benign-side results (false positives)

| Family | FP count (of 16) |
|---|---|
| benign_genuine_emergency | 5 |
| benign_hard_negative_clearance | 2 |
| benign_genuine_hazard | 1 |
| benign_hard_negative_authority | 1 |
| benign_multi_vehicle | 1 |
| benign_routine_status | 0 |

`benign_genuine_emergency` is the single most-confused benign family (5/16
FPs) — genuine, truthful emergency-vehicle announcements are lexically very
close to `authority_override`'s false claims, a structurally expected
confusion (see `FAILURE_ANALYSIS.md`).

## Statistical backing (added during the Reviewer #2 pass, Task 8)

A 2,000-resample percentile bootstrap (seed 42) was computed for F1 and
recall: **F1 0.446 [95% CI 0.368, 0.520]**, **Recall 0.302 [95% CI 0.238,
0.369]**. The interval confirms the headline finding is not a small-sample
artifact — even the CI's upper bound on F1 (0.520) sits below every other
benchmark's point estimate in this paper except STBV-Bench v2 (0.521,
itself measured on ambient-traffic realism, not stylistic OOD). This
closes the CI gap flagged in this document's first draft and in
`FINAL_EVALUATION_REPORT.md`. No CI was separately computed for the
per-family recall breakdown ($n=16$/family, too small for a stable
bootstrap) or for ECE/Brier — disclosed as still-open, lower-priority
items.
