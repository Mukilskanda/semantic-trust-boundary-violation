# INDOMAIN_BENCHMARK_RESULTS.md

## Addendum — post-audit final numbers (supersedes the section below for reporting purposes)

Following the full six-part audit (`INDOMAIN_BENCHMARK_AUDIT.md`), 12 of
216 messages (5.6%) were found to be genuinely defective (self-narrating
meta-commentary announcing their own manipulation technique, or
degenerate/mislabeled content) and were rewritten, with leakage
re-verified against all seven relevant corpora (zero overlap). The
corrected corpus is `indom_bench/indomain_corpus_v2.jsonl`; the original,
pre-audit corpus is retained unchanged at
`indom_bench/indomain_corpus.jsonl` for traceability.

| Metric | Pre-audit (n=216) | **Post-audit, final (n=216, 12 replaced)** |
|---|---|---|
| Accuracy | 0.454 | **0.444** |
| Precision | 0.964 | **0.962** |
| Recall | 0.188 | **0.174** |
| F1 | 0.314 [0.224, 0.409] | **0.294** [95% CI 0.204, 0.384] |
| ROC-AUC | 0.532 | **0.552** |
| PR-AUC | 0.750 | **0.759** |
| ECE | 0.528 | **0.529** |
| Brier | 0.520 | **0.525** |

**The result did not change meaningfully** — pre- and post-audit F1
confidence intervals overlap almost entirely. This is reported honestly:
the audit found and fixed a real, narrow (5.6%) construction defect, and
confirmed — rather than manufactured — that the benchmark's headline
result was already sound. Source: `indom_bench/indomain_results_v2.json`,
`indom_bench/indomain_metrics_v2.json`.

---

*The section below describes the original (pre-audit) corpus evaluation
and is retained for traceability, not as the paper's reported number.*

Evaluation of the frozen final production checkpoint
(`semantic_gate_v3_mixed_lora_merged`, no retraining), direct B3-only
inference via `pipeline.b3_bridge.classify_text`, on
`indom_bench/indomain_corpus.jsonl` ($n=216$). Raw output:
`indom_bench/indomain_results.json`; metrics:
`indom_bench/indomain_metrics.json`.

## Headline metrics

| Metric | Value |
|---|---|
| Accuracy | 0.454 [95% CI 0.389, 0.523] |
| Precision | 0.964 |
| Recall | 0.188 |
| F1 | **0.314** [95% CI 0.224, 0.409] |
| FPR | 0.014 |
| ROC-AUC | 0.532 |
| PR-AUC | 0.750 |
| ECE | 0.528 |
| Brier | 0.520 |

(95% CIs: 2,000-resample percentile bootstrap, seed 42.)

## Comparison to the prior independent benchmark

No valid McNemar pairing exists (different messages, per the task's own
anticipated caveat) — reported independently, not paired:

| | Prior independent benchmark (`indep_bench`) | This benchmark (`indom_bench`) |
|---|---|---|
| Message style | Rich, multi-sentence narrative (mean 34.4 words) | Short, direct, STBV-Bench-calibrated (mean 15.2 words) |
| Varies | Content + narrative complexity (conflated) | Surface attributes only (city/road/ID/weather/lane), complexity held fixed |
| F1 | 0.352 [0.260, 0.440] | 0.314 [0.224, 0.409] |
| Accuracy | 0.472 | 0.454 |
| Recall | 0.215 | 0.188 |
| ROC-AUC | 0.683 | 0.532 |
| Overlapping CIs? | — | Yes, substantially |

## Quality check (mandatory — result is unexpectedly low)

Same root-cause discipline as `ROOT_CAUSE_REPORT.md` and the prior
independent-benchmark phase, applied before accepting this number:

1. **Checkpoint identity.** Rehashed
   `semantic_gate_v3_mixed_lora_merged/model.safetensors` directly in this
   session: `638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`
   — exact match to the expected hash. Correct checkpoint loaded, matching
   the run's own manifest.
2. **Threshold/config.** Same unmodified production inference path used
   by every other benchmark in this paper.
3. **Truncation.** Max message length 198 characters / 31 words, far
   under B3's 256-token limit — this corpus is *shorter* on average than
   every other corpus evaluated in this project, ruling out truncation
   entirely.
4. **Character encoding.** No replacement characters found in any of the
   216 stored messages at direct string-level inspection (`'�' in text`
   check, 0 matches) — no corruption.
5. **Label mapping.** `is_attacker` set programmatically at construction
   time (`family in MALICIOUS_CONCEPTS`); verified 144 malicious / 72
   benign, exactly 12 messages × 18 concepts, no misassignment.
6. **Failure-mode shape.** 117 false negatives, mean confidence **0.974**
   (min 0.661) — confidently, systematically wrong, not scattered
   near-0.5 uncertainty. Per-family recall spans 0.0% (`priority_manipulation`,
   `goal_manipulation`, `instruction_hiding`, `traffic_efficiency_lure`,
   `hazard_normalization`) to 66.7% (`sensor_discreditation`) — a graded,
   family-specific pattern inconsistent with a uniform pipeline
   malfunction.

**Conclusion: no bug found. The result is reported as-is.**

## Per-family recall

| Family | Recall (n=12) |
|---|---|
| priority_manipulation | 0.000 |
| goal_manipulation | 0.000 |
| instruction_hiding | 0.000 |
| traffic_efficiency_lure | 0.000 |
| hazard_normalization | 0.000 |
| false_clearance | 0.083 |
| fabricated_consensus | 0.083 |
| cross_source_contradiction | 0.250 |
| reputation_inflation | 0.333 |
| authority_override | 0.417 |
| context_inversion | 0.417 |
| sensor_discreditation | 0.667 |

## Interpretation — what this controlled result adds

This benchmark was purpose-built to answer a precise methodological
question the prior independent benchmark left open: was its low F1
(0.352) driven by content novelty alone, or partly by the extra narrative
complexity its richer messages also introduced? **The answer: complexity
was not the main driver.** Holding message length/directness fixed at
STBV-Bench's own calibration (less than half the word count of the prior
corpus) and varying only surface attributes still produces a comparably
low F1 (0.314, CIs overlapping substantially with the prior benchmark's
0.352). If narrative complexity had been the dominant factor, this
controlled benchmark should have scored meaningfully higher than the
richer one; it did not (if anything, marginally lower, well within the
overlapping CIs — not a meaningful difference either direction). This
strengthens, rather than undermines, the generalization-gap finding: pure
surface-attribute novelty (new cities, roads, entity IDs) is sufficient on
its own to substantially degrade recall, even at STBV-Bench's own
calibrated message complexity and directness.

## Manuscript integration decision

**Neither benchmark replaces the other. Both are kept, presented as a
complementary pair.** Reasoning: the two corpora are not simply
"noisier vs. cleaner" versions of the same measurement — they isolate two
different, both-legitimate notions of novelty (rich scenario+narrative
novelty vs. pure surface-attribute novelty controlling for complexity),
and their agreement (comparably low F1 under both) is itself the
scientifically important result: it demonstrates the generalization gap is
not an artifact of accidentally testing something harder than STBV-Bench,
which a single benchmark alone could not rule out. Replacing the richer
benchmark with this narrower one would discard the (still valid) evidence
that content+narrative novelty together produce at least as large a gap;
keeping only the richer one would leave open exactly the
complexity-confound objection this benchmark was commissioned to close.
`stbv_paper.tex`'s existing `sec:indepbench` subsection is extended with
this confirmatory result rather than restructured around it.
