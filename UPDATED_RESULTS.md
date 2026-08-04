# Updated Results: B3 on STBV-Bench v2.5

**B3 was not retrained.** Every number in this document comes from running
the existing, frozen checkpoint (`b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3`,
`pytorch_model.bin`) over STBV-Bench v2.5 exactly once
(`results/benchmark_audit/b3_v25_predictions.jsonl`), then slicing those same
predictions under different thresholds and split protocols. Reproduce with:

```
python benchmark/b3_reeval_v25.py
```

Figures: `results/benchmark_audit/figures/b3_v25_reeval.{png,pdf}`. Full
numeric output: `results/benchmark_audit/b3_reeval_v25.json`.

## Headline finding — reported as required by the research-integrity brief, not softened

**B3 performs poorly on STBV-Bench v2.5, and a same-protocol trained lexical
baseline outperforms it by a wide, statistically significant margin.**

| | Accuracy | F1 | ROC-AUC |
|---|---|---|---|
| **B3 (frozen, strict thr=0.50)** | **0.558** [95% CI 0.549–0.567] | **0.529** [0.519–0.540] | **0.610** [0.600–0.620] |
| TF-IDF + LogisticRegression, template-disjoint (trained on v2.5) | 0.738 | 0.728 | 0.843 |

This is a genuine, unfavorable finding and is reported as such, per the
research-integrity requirement that negative results not be hidden. **The
comparison above is not apples-to-apples and must not be read as "the
lexical baseline is a better detector than B3" without the caveat in §4 —
B3 is being evaluated zero-shot/out-of-distribution on a corpus it was never
trained or tuned on, while the lexical baseline is trained directly on v2.5.**
Both facts matter and neither should be dropped.

## 1. Threshold / decision-mode comparison (Task 6)

B3's own configured risk policy (`pipeline/b3_bridge.py::B3RiskPolicy`) has
two operating points: `high_confidence=0.85`, `medium_confidence=0.60`. We
evaluate binary malicious/benign decisions at:

- **Strict label mode**: predict malicious iff `p_malicious >= 0.50` (B3's
  raw argmax label)
- **Confidence-aware mode**: predict malicious iff `p_malicious >= 0.60`
  (B3's own `medium_confidence` gate — the threshold below which B3's risk
  policy would not even call something "medium" risk)

| Mode | TN | FP | FN | TP | Accuracy | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Strict (thr=0.50) | 3,791 | 1,821 | 3,589 | 3,043 | 0.5582 | 0.6256 | 0.4588 | 0.5294 | 0.3245 |
| Confidence-aware (thr=0.60) | 3,901 | 1,711 | 3,795 | 2,837 | 0.5503 | 0.6238 | 0.4278 | 0.5075 | 0.3049 |

Raising the threshold to the confidence-aware operating point trades ~110
false positives for ~200 additional false negatives — it **does not**
rescue overall performance; both modes sit well below any usable operating
point for a safety gate (recall under half in both modes at prevalence
0.542). ROC-AUC = 0.610, PR-AUC = 0.628 (threshold-independent), consistent
with the near-coin-flip discrimination implied by both fixed thresholds.

## 2. Calibration

- **ECE = 0.313**, **Brier score = 0.343** (both computed over 10 equal-width
  confidence bins, no post-hoc temperature scaling applied — this measures
  B3's raw calibration on this corpus, not a repaired version of it).
- These are poor calibration numbers in absolute terms (ECE > 0.3 means the
  average gap between stated confidence and empirical accuracy across bins
  exceeds 30 percentage points) — see the reliability diagram in
  `figures/b3_v25_reeval.png`.

## 3. Per-family recall (strict, thr=0.50) — the finding that explains the low overall F1

Precision is not reported per-family: every malicious family's subset
contains no benign examples, so a naive `precision_score` computed within
one family's rows is trivially 1.0 whenever any true positive exists (there
are no negatives in the subset for a false positive to come from). Only
pooled precision (§1) is meaningful; per-family recall is the informative
number here.

| Attack family | n | Recall |
|---|---|---|
| sensor_discreditation | 543 | **0.967** |
| fabricated_consensus | 501 | **0.796** |
| indirect_prompt_injection | 447 | 0.609 |
| instruction_hiding | 523 | 0.627 |
| narrative_poisoning | 497 | 0.559 |
| authority_override | 509 | 0.479 |
| cross_source_contradiction | 534 | 0.483 |
| priority_manipulation | 507 | 0.351 |
| false_clearance | 559 | 0.358 |
| context_inversion | 504 | 0.268 |
| traffic_efficiency_lure | 511 | 0.207 |
| role_confusion | 492 | 0.159 |
| **goal_manipulation** | 505 | **0.083** |
| benign_control (specificity) | 5,612 | 0.676 |

**B3's detection ability is extremely uneven across families** — near-perfect
on `sensor_discreditation` (0.967) and near-zero on `goal_manipulation`
(0.083) and `role_confusion` (0.159). Benign specificity of 0.676 means
roughly a third of legitimate messages are flagged malicious. This pattern —
strong on some families, close to chance on others, mediocre specificity —
is consistent with a model that learned surface correlates of a few attack
families from its original (v1-style) training distribution and does not
transfer that to families whose v2.5 phrasing is less similar to what it
saw in training, rather than a model reasoning uniformly about the
underlying pragmatic attack structure.

## 4. Zero-shot vs. trained comparison (Task 7) — kept explicitly distinct, as required

| Model | Training relationship to v2.5 | Protocol | Accuracy | F1 | ROC-AUC |
|---|---|---|---|---|---|
| **B3 (semantic_gate_v3)** | **zero-shot** — frozen checkpoint, never trained or fine-tuned on v2.5 | pooled (all 12,244 msgs) | 0.558 | 0.529 | 0.610 |
| TF-IDF + LogisticRegression | trained per-fold on v2.5 | template-disjoint GroupKFold(5) | 0.728 | 0.728 | 0.843 |
| TF-IDF + LinearSVC | trained per-fold on v2.5 | template-disjoint GroupKFold(5) | 0.734 | 0.715 | 0.836 |
| Count + MultinomialNB | trained per-fold on v2.5 | template-disjoint GroupKFold(5) | 0.753 | 0.762 | 0.861 |
| TF-IDF + RandomForest | trained per-fold on v2.5 | template-disjoint GroupKFold(5) | 0.668 | 0.641 | 0.752 |
| TF-IDF + DecisionTree | trained per-fold on v2.5 | template-disjoint GroupKFold(5) | 0.583 | 0.566 | 0.587 |
| Regex detector | not run this pass | — | — | — | — |
| Zero-shot LLM | not run this pass — no external LLM API wired into this evaluation harness | — | — | — | — |

**The distinction that must not be dropped**: every lexical row in this
table was **trained directly on STBV-Bench v2.5**, so it has seen this
corpus's vocabulary and register (just not the exact template skeleton, per
the template-disjoint protocol). **B3 has seen none of STBV-Bench v2.5** —
it is being asked to generalize zero-shot from whatever distribution it was
originally trained on. A frozen zero-shot model losing to a freshly-trained
in-distribution baseline is expected and does not, by itself, mean B3's
underlying architecture or approach is worse — it means **B3 has not been
adapted to the redesigned benchmark**, which is exactly what re-running the
benchmark was supposed to surface. The regex detector and an external
zero-shot LLM comparator are not included in this pass (no regex ruleset or
LLM API was wired into the evaluation harness used here); both remain open
follow-on work.

## 5. Statistical comparison: B3 vs. best lexical baseline (McNemar test)

Both models scored on the **same** template-disjoint test folds
(`GroupKFold(5)` on `template_id`), so this is a paired comparison of B3
(frozen, threshold 0.50) against TF-IDF+LogisticRegression (trained per fold):

| | Value |
|---|---|
| n | 12,244 |
| B3 accuracy (these folds) | 0.5582 |
| Lexical baseline accuracy (these folds) | 0.7381 |
| Messages B3 got right, lexical got wrong | 1,509 |
| Messages B3 got wrong, lexical got right | 3,712 |
| McNemar χ² | 928.71 |
| **McNemar p-value** | **5.6 × 10⁻²⁰⁴** |
| Cohen's h (effect size, accuracy difference) | −0.380 (medium-to-large) |

The difference is not noise: on 3,712 messages the trained lexical baseline
was correct where B3 was wrong, versus only 1,509 the other way. Given the
zero-shot/trained asymmetry in §4, the correct reading of this test is "B3's
current checkpoint does not transfer to v2.5 as well as a simple model
trained on v2.5 does" — not "logistic regression is a better semantic
reasoner than B3."

## 6. What this means, stated plainly (Task 9)

- **B3 performs worse on the corrected benchmark than it likely appeared to
  on v1.** v1's own audit (BENCHMARK_AUDIT.md §2) shows the benign class
  there was 10 memorizable strings; a model that had absorbed any of that
  distribution's surface regularities would score artificially high on v1
  in a way that does not reflect semantic understanding. This document does
  not have v1-corpus B3 numbers to cite for a direct before/after (out of
  scope for this pass — flagged, not fabricated), but the mechanism is the
  same one the lexical-leakage analysis identifies for bag-of-words models.
- **Lexical baselines outperform B3 under the template-disjoint protocol.**
  Reported as required, without qualification-softening, in §5.
- **This is a finding about the currently deployed checkpoint's
  out-of-distribution transfer, not a final verdict on B3's architecture.**
  The honest next step is fine-tuning or re-calibrating B3 on v2.5 (or a
  held-out split of it) and re-running this exact harness — which was
  explicitly out of scope ("WITHOUT retraining B3") for this document.

## 7. Explicitly not done in this pass

- Regex baseline and external zero-shot LLM comparator (§4 table gaps).
- Fine-tuning/recalibrating B3 on v2.5 (excluded by the task's own "without
  retraining" constraint; noted here as the natural next step, not silently
  dropped).
- Rewriting `stbv_paper.tex`'s Results/Discussion sections to incorporate
  these numbers — tracked separately, not represented as done here.
