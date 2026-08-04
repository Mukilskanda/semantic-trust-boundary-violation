# STBV-Bench Benchmark Audit

**Status: v1 is scientifically unacceptable for claims of semantic-reasoning evaluation.**
This document reports the measurements that establish that, and the same
measurements repeated on the redesigned corpus (v2.5). Every number here is
computed by [`benchmark/audit_v1.py`](benchmark/audit_v1.py) and
[`benchmark/corpus_metrics.py`](benchmark/corpus_metrics.py); raw output is at
`results/benchmark_audit/audit_v1.json` and `results/benchmark_audit/audit_v25.json`.
Reproduce with:

```
python benchmark/audit_v1.py
python benchmark/stbv_bench_v25.py
python benchmark/lexical_leakage.py --corpus v25
```

## 1. Headline finding

STBV-Bench v1's benign class collapses to **10 unique message strings** repeated
across 2,993 samples. Five independent bag-of-words classifiers with zero
semantic capacity (TF-IDF+LogReg, TF-IDF+LinearSVC, Count+NB, TF-IDF+RandomForest,
TF-IDF+DecisionTree) each separate benign from malicious at **F1 = 1.0000,
ROC-AUC = 1.0000** under 5-fold stratified cross-validation. This is not because
the models understand the attacks — it is because the benign class is a lookup
table of 10 strings and the malicious class shares almost no vocabulary with it.
Any claim of "semantic reasoning" evaluated on this benchmark is confounded by
lexical memorization and cannot be supported.

## 2. STBV-Bench v1 — full statistics (n = 10,000)

| Metric | Overall | Benign (n=2,993) | Malicious (n=7,007) |
|---|---|---|---|
| Unique message strings | 534 | **10** | 524 |
| Unique ratio | 5.3% | **0.33%** | 7.5% |
| Duplicate rate | 99.98% | **100.0%** | 99.97% |
| Max repeat count | 312 | 312 | 195 |
| Vocabulary size (types) | 306 | **23** | 303 |
| Type-token ratio (TTR) | 0.0017 | **0.00091** | 0.0020 |
| MTLD (lexical diversity) | 63.6 | 19.9 | 68.6 |
| Mean length (tokens) | 18.0 | **8.4** | 22.1 |
| Std length (tokens) | 8.8 | 2.1 | 7.2 |
| Self-BLEU (within-class) | — | **0.977** | 0.554 |
| Mean normalized edit distance | — | 0.462 | 0.734 |
| Fraction of pairs with edit distance < 0.20 | — | **19.6%** | 2.0% |
| TF-IDF cosine similarity (mean) | — | 0.318 | 0.055 |
| Transformer embedding cosine (mean, n=300 sample) | — | **0.905** | 0.516 |
| Fraction embedding cosine > 0.95 | — | **49.9%** | 15.3% |

**Attack-family diversity**: 21 families total (20 malicious + benign_control),
family sizes range 317–2,993, but per-family diversity is equally collapsed:
`indirect_prompt_injection` and `instruction_injection` each contain only
**2 unique strings** across 350+ samples (self-BLEU = 1.0000, i.e. every sample
in the family is a verbatim duplicate up to slot substitution). No family
exceeds 50 unique strings.

**Cross-class n-gram overlap** (this is the number that most directly explains
why lexical models achieve perfect separation): 4-gram Jaccard similarity
between the benign and malicious vocabularies is **0.0035** — the two classes
share almost no 4-grams at all, so a linear model needs only a handful of
class-exclusive n-grams as features to separate them perfectly.

**Length as a standalone shortcut**: benign messages average 8.4 tokens,
malicious 22.1 — an almost 3x gap with non-overlapping IQRs. A single-feature
"token count" classifier alone would already recover most of the label.

### Lexical-shortcut probe (v1), 5-fold stratified CV

| Model | Accuracy | F1 | ROC-AUC |
|---|---|---|---|
| TF-IDF + LogisticRegression | 1.0000 | 1.0000 | 1.0000 |
| TF-IDF + LinearSVC | 1.0000 | 1.0000 | n/a (no proba) |
| Count + MultinomialNB | 1.0000 | 1.0000 | 1.0000 |
| TF-IDF + RandomForest | 1.0000 | 1.0000 | 1.0000 |
| TF-IDF + DecisionTree | 1.0000 | 1.0000 | 1.0000 |

**Conclusion: STBV-Bench v1 is unusable as evidence of semantic understanding.**
Every classifier tested — including a decision tree, which cannot represent
anything beyond literal token thresholds — achieves perfect separation. The
benchmark rewards memorizing which of ~550 fixed strings a message is, not
understanding what the message asserts.

## 3. STBV-Bench v2.5 — same statistics, redesigned corpus (n = 12,244)

See [BENCHMARK_REDESIGN.md](BENCHMARK_REDESIGN.md) for the generation method.

| Metric | Overall | Benign (n=5,612) | Malicious (n=6,632) |
|---|---|---|---|
| Unique message strings | 12,244 | **5,612** | 6,632 |
| Unique ratio | **100%** | **100%** | 100% |
| Duplicate rate | 0% | 0% | 0% |
| Vocabulary size (types) | 2,289 | 1,734 | 1,209 |
| Type-token ratio (TTR) | 0.0071 (**4.2x v1**) | 0.0115 (**12.6x v1**) | 0.0070 |
| MTLD | 70.3 | 73.9 | 67.5 |
| Mean length (tokens) | 26.4 | 26.8 | 26.0 |
| Std length (tokens) | 5.4 | 5.9 | 5.0 |
| Self-BLEU (within-class) | — | **0.263** (v1: 0.977) | **0.296** (v1: 0.554) |
| Mean normalized edit distance | — | 0.743 | 0.737 |
| Fraction of pairs with edit distance < 0.20 | — | **0%** (v1: 19.6%) | 0% |
| TF-IDF cosine similarity (mean) | — | 0.037 | 0.038 |
| 4-gram cross-class Jaccard | 0.198 (**56x v1's 0.0035**) | | |

Length is now matched within 0.8 tokens between classes (26.8 vs 26.0, vs. an
almost-3x gap in v1) and confirmed non-diagnostic by a dedicated probe (below).
Diversity, duplication, TTR, self-BLEU, and cross-class n-gram sharing are all
fixed by one to two orders of magnitude relative to v1.

### Length-only and lexical-shortcut probes (v2.5, random 5-fold split)

| Probe | Accuracy | F1 | ROC-AUC |
|---|---|---|---|
| **Length-only** (token count, single feature) | 0.533 | 0.567 | 0.533 |
| TF-IDF + LogisticRegression | 1.0000 | 1.0000 | 1.0000 |
| TF-IDF + LinearSVC | 1.0000 | 1.0000 | 1.0000 |
| Count + MultinomialNB | 0.9974 | 0.9976 | 1.0000 |
| TF-IDF + RandomForest | 0.9986 | 0.9987 | 1.0000 |
| TF-IDF + DecisionTree | 0.9808 | 0.9823 | 0.9805 |

**The length shortcut is eliminated** (0.533 accuracy is chance level, since
prevalence is 0.54). **The n-gram shortcut is not eliminated by diversity alone
under a random train/test split** — see [LEXICAL_LEAKAGE_ANALYSIS.md](LEXICAL_LEAKAGE_ANALYSIS.md)
for why, and for the evaluation-protocol fix (template-disjoint splitting) that
does resolve it, taking the same models' F1 down to 0.56–0.76 and AUC to 0.59–0.86.

## 4. Reproducibility

- Corpus generator: [`benchmark/stbv_bench_v25.py`](benchmark/stbv_bench_v25.py),
  [`benchmark/v25_compositional.py`](benchmark/v25_compositional.py)
- Metrics library: [`benchmark/corpus_metrics.py`](benchmark/corpus_metrics.py)
- Leakage probes: [`benchmark/lexical_leakage.py`](benchmark/lexical_leakage.py)
- Raw JSON: `results/benchmark_audit/audit_v1.json`, `audit_v25.json`,
  `lexical_leakage_v25_iter{1,2,3}.json`, `lexical_leakage_v25_template_holdout.json`
- Seed: `20260802` (generation), `42` (all CV probes)
