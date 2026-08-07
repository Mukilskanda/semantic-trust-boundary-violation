# INDEPENDENT_BENCHMARK_RESULTS.md

Evaluation of the frozen final production checkpoint
(`semantic_gate_v3_mixed_lora_merged`, SHA-256
`638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`,
independently reconfirmed via the run's own manifest, no retraining),
direct B3-only inference via `pipeline.b3_bridge.classify_text`, on
`indep_bench/independent_corpus.jsonl` ($n=216$). Script:
`indep_bench/eval` logic embedded in this evaluation session (same
pattern as every other `*_mixed` evaluation in this project). Raw output:
`indep_bench/independent_results.json`; computed metrics:
`indep_bench/independent_metrics.json`.

## Headline metrics

| Metric | Value |
|---|---|
| Accuracy | 0.472 [95% CI 0.412, 0.542] |
| Precision | 0.969 |
| Recall | 0.215 |
| F1 | **0.352** [95% CI 0.260, 0.440] |
| FPR | 0.014 |
| ROC-AUC | 0.683 |
| PR-AUC | 0.829 |
| ECE | 0.490 |
| Brier | 0.493 |
| Confusion (TP/FP/FN/TN) | 31 / 1 / 113 / 71 |

(95% CIs: 2,000-resample percentile bootstrap, seed 42.)

## This is unexpectedly low — mandatory investigation (Task 6)

This corpus is fully in-scope (grammatical, professional, ETSI CAM/DENM
register — verified by construction and by the leakage/scope audit in
`INDEPENDENT_BENCHMARK.md`), yet F1=0.352 is close to hard-OOD's
deliberately-out-of-scope F1=0.345, and far below STBV-Bench v1 (0.995)
and the external corpus (0.920). Per this project's own established
process, this result is not accepted at face value — the same root-cause
rigor used in `ROOT_CAUSE_REPORT.md` was applied before reporting it.

**Checks performed, with evidence:**

1. **Checkpoint identity.** The evaluation run's own manifest records
   `sha256_16: "638ed0fada078083"`, matching the final checkpoint's known
   hash prefix exactly (cross-checked against the independently-rehashed
   full SHA-256 established in `ROOT_CAUSE_REPORT.md`). Correct checkpoint
   loaded.
2. **Threshold/config.** Same production inference path
   (`pipeline.b3_bridge.classify_text`) used by every other benchmark in
   this paper; no custom or modified threshold config was introduced for
   this evaluation.
3. **Preprocessing / truncation.** Message lengths (mean 34.4 words / 231
   characters, max 64 words / 405 characters) are well within B3's
   256-token inference limit — truncation ruled out as a cause.
4. **Character encoding.** A visual artifact in this session's own
   terminal output (a Windows console codepage limitation) made
   non-ASCII city names (e.g. "Kraków") appear corrupted when printed to
   the shell; the actual stored JSON data was directly inspected at the
   codepoint level (`ord()` on each character) and confirmed **correctly**
   UTF-8 encoded (`ó` = U+00F3, intact) — this was a display artifact in
   this investigation, not a data-corruption bug, and does not affect the
   evaluated text.
5. **Label mapping.** `is_attacker` is set programmatically
   (`family in MALICIOUS_CONCEPTS`) at construction time, not by the LLM
   or any post-hoc heuristic — verified correct by direct inspection
   (144 malicious / 72 benign, exactly 12 concepts × 12 messages each, no
   off-by-one or family misassignment found).
6. **Failure-mode shape.** False negatives are uniformly **high-confidence**
   (mean confidence 0.963, min 0.582, max 0.993) -- the model is
   confidently, systematically wrong, not noisily uncertain. A
   preprocessing/pipeline bug would typically produce scattered,
   near-0.5-confidence errors; this pattern instead matches a genuine,
   confident representational gap, the same signature already documented
   for the (structurally different, out-of-scope) hard-OOD benchmark.
7. **Family-level gradient, not a uniform failure.** Recall ranges from
   0.0% (`goal_manipulation`, `instruction_hiding`, `context_inversion`,
   `reputation_inflation`, `hazard_normalization`) to 66.7%
   (`authority_override`) -- a graded, family-specific pattern. A global
   pipeline malfunction (wrong checkpoint, broken tokenizer, inverted
   labels) would be expected to produce a uniform near-0% or near-100%
   result across every family, not this spread. This is additional
   evidence the result reflects real, uneven semantic difficulty per
   attack concept, not a systemic bug.

**Conclusion: no bug found. The result is reported as-is.** This is a
genuine, surprising, and important finding: even holding register and
scope fixed at exactly what the paper claims as its deployment target,
novel scenario/entity/narrative content alone drives a large recall drop.
Precision remains very high (0.969, 1 false positive in 72 benign
messages) — the failure mode is silence on novel malicious content, not
false alarms, consistent with the pattern found elsewhere in this project
but now demonstrated to hold even fully in-scope.

## Per-family recall

| Family | Recall (n=12) |
|---|---|
| goal_manipulation | 0.000 |
| instruction_hiding | 0.000 |
| context_inversion | 0.000 |
| reputation_inflation | 0.000 |
| hazard_normalization | 0.000 |
| traffic_efficiency_lure | 0.167 |
| fabricated_consensus | 0.250 |
| sensor_discreditation | 0.250 |
| priority_manipulation | 0.333 |
| false_clearance | 0.417 |
| cross_source_contradiction | 0.500 |
| authority_override | 0.667 |

Every family that has any detections retains near-perfect precision on
this corpus overall (1 FP total, on a benign family) — the recall
gradient above is the informative axis, not precision.

## Statistical comparison to existing benchmarks

McNemar's test requires a valid paired comparison (same items scored
under two conditions). **No valid McNemar pairing exists between this
corpus and any existing benchmark** — every existing benchmark (STBV-Bench
v1/v2/v2.5, external corpus, hard-OOD) uses entirely different messages,
so there is no consistent per-item pairing across corpora. This is stated
explicitly rather than computing an invalid statistic. The comparison
that *is* valid and reported is the non-overlapping bootstrap CIs:
this corpus's F1 CI [0.260, 0.440] does not overlap STBV-Bench v1's
point estimate (0.995) or the external corpus's (0.920) at all, and sits
close to (slightly below) hard-OOD's CI [0.267, 0.418] despite being
constructed to stay fully in-scope where hard-OOD deliberately was not —
itself a notable, disclosed finding.

## Interpretation

This is now the paper's single strongest piece of evidence that
STBV-Bench v1's F1=0.995 does not represent general semantic-attack
detection capability: unlike hard-OOD (which could be, and was, critiqued
for testing outside the paper's declared scope), this benchmark holds
register and scope fixed at exactly the paper's own claimed deployment
target and still finds a comparably large gap, driven by content/scenario
novelty rather than register shift. Combined with hard-OOD's independent
finding (driven by register shift instead), the two results triangulate
on the same underlying conclusion via two structurally different,
leakage-verified corpora: B3's semantic understanding, as currently
trained, is substantially narrower than STBV-Bench's near-ceiling result
alone would suggest, along **both** the content-novelty and the
register-shift axes independently.
