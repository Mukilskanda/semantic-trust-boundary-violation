# Baseline Evaluation Report

## Status: implemented and evaluated in this pass on the actual v2.5b held-out set

## 0. Two existing/prior baseline artifacts found and used
1. `baselines/run_baselines.py` + `BASELINE_COMPARISON.md` (prior session): a
   real, already-executed baseline suite (TF-IDF+LogReg, TF-IDF+SVM, regex,
   zero-shot Mistral-7B LLM judge) — but evaluated on **STBV-Bench v1**
   (`results/stbv_bench/v1/stbv_bench_per_message.csv`), **not** v2.5b, the
   benchmark the current manuscript actually reports Table III/IV numbers on.
   That report also found v1's benign class is drawn from only **10 unique
   sentences** (2 templates x 5 street names), making any precision/FPR/AUC
   comparison on v1 uninformative (every detector, including a hand-written
   regex, trivially hits precision=1.000/FPR=0.000 on a 10-string negative
   class). **This v1 baseline result is not used as v2.5b evidence** in the
   manuscript, because the benchmarks differ and the task's own rule (#8)
   forbids comparing results from different datasets as if they were the
   same benchmark.
2. The "7B instruction-tuned model achieved F1=0.267 zero-shot" figure
   already quoted in the manuscript's "Why DeBERTa-v2" paragraph is exactly
   `BASELINE_COMPARISON.md`'s Mistral-7B row (F1=0.2673, recall=0.1543,
   precision=1.0000, $n$=987 stratified subsample) — **confirmed as a real,
   traceable number**, but it too is a v1 (not v2.5b) result. The sentence
   citing it is about backbone/latency choice, not a v2.5b benchmark claim,
   so it is left as-is and not read as a v2.5b baseline comparator.

## 1. New evaluation on the actual v2.5b held-out set (this pass)
Source data: `data/stbv_bench/v25b/stbv_bench_v25b.jsonl` ($n{=}10{,}098$,
same `sample_id`s as `b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_5.csv`,
the file behind Table III/IV). Script written to the session scratchpad
(`run_v25b_baseline.py`), executed with scikit-learn 1.7.2, seed=42
throughout.

**Benign-class diversity check (the exact defect found in v1) was repeated
on v2.5b first**: v2.5b's benign class has **4,734/4,734 unique strings**
(vs. v1's 10/2,993) and malicious has 5,364/5,364 unique strings. v2.5b does
**not** have v1's severe template-collision defect.

### Baseline A — Keyword/lexical detector (zero-shot, no training)
Fixed hand-written list of 25 phrases associated with authority/override/
clearance/injection language. Evaluated on the same 2,020-message test split
used below, for direct comparability.

### Baseline B — TF-IDF (1-2gram) + Logistic Regression (in-domain trained)
Stratified 60/20/20 train/val/test split (seed 42) of the v2.5b JSONL
itself. TF-IDF fit on train only; LogisticRegression (`class_weight=balanced`)
fit on train only; **decision threshold selected on val only**
(F1-maximizing, threshold=0.415); all metrics below are on the **untouched
2,020-message test split**.

### Results (test split, $n{=}2{,}020$; 1,073 malicious / 947 benign)

| Method | Acc. | Precision | Recall | F1 | FPR | ROC-AUC |
|---|---|---|---|---|---|---|
| Keyword/lexical (zero-shot) | 0.503 | 0.606 | 0.184 | 0.282 | 0.135 | n/a |
| TF-IDF + LogReg (in-domain trained)$^\dagger$ | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 |
| B3 direct classifier (Table III, final checkpoint, full $n{=}10{,}098$) | 0.954 | 0.946 | 0.969 | 0.957 | -- | 0.989 |
| Full STBV pipeline (Table IV) | 0.852 | 0.782 | 0.999 | 0.877 | 0.315 | -- |

$^\dagger$See Section 2 — this score is real but explained by a template
register artifact, not by genuine semantic understanding; see below before
citing it as "beats B3."

Per-family recall for the TF-IDF+LogReg baseline on its test split: **1.0000
for all 13 malicious families** (n=69-96 each).

## 2. Sanity check on the perfect TF-IDF+LogReg score (required — 1.000 must
be investigated, not accepted at face value)
A perfect in-domain score, even with a fully lexically-diverse benign class,
was still suspicious and was investigated:
- Inspected the model's top positive/negative coefficients. Top "malicious"
  n-grams: `recorded`, `favour`, `recorded as`, `this transmission`, `over`,
  `as`. Top "benign" n-grams: `rsu`, `corridor node`, `roadside controller`,
  `corridor supervisor`, `dispatch`, `highway`.
- These are **not attack-content markers** (no "ignore", "override",
  "bypass", etc. among the top coefficients) — they are **register/phrasing
  artifacts of the template generator**: malicious templates are
  synthesized in one narrative register (transmission/recording language),
  benign templates in another (infrastructure/dispatch language), even
  though the generator does not repeat exact strings.
- **Conclusion**: like the v1 finding (but less severe — no exact string
  duplication here), a linear bag-of-words model trained in-domain on v2.5b
  exploits generator-level register differences between the two classes
  rather than learning to detect semantic manipulation. This is a genuine
  property of the benchmark's synthetic construction, not a scoring bug or
  conventional data leakage (train/test are disjoint by `sample_id`, split
  is stratified and non-overlapping).
- **Consequence**: the TF-IDF+LogReg row is reported for transparency but
  explicitly flagged as **not evidence that a linear model is a better
  semantic-attack detector than B3** — it is evidence that in-domain linear
  models can exploit v2.5b's template-register structure, a
  benchmark-construction property orthogonal to genuine semantic
  understanding. The scientifically meaningful, like-for-like zero-shot
  comparator is the keyword baseline (F1=0.282), which B3 (F1=0.957,
  evaluated zero-shot against a template-disjoint bank) clearly and
  legitimately beats.

## 3. Fairness disclosure
- TF-IDF+LogReg is trained directly on v2.5b (in-domain). B3 is trained on a
  disjoint template bank (Section IV, "zero verified template overlap") and
  evaluated zero-shot-to-templates on v2.5b — not the same experimental
  condition, stated explicitly in both this report and the manuscript.
- Keyword/lexical is a genuine zero-shot, no-training comparator and is the
  fairest apples-to-apples baseline against B3's generalization claim.

## 4. What was added to the manuscript
A compact baseline table was added to Section V-B (Semantic Validation)
referencing this report, with the in-domain-trained caveat stated in the
table footnote.

## 5. Reproduction
TF-IDF/LogReg/keyword baseline: stratified 60/20/20 split (seed 42) of
`data/stbv_bench/v25b/stbv_bench_v25b.jsonl`; `TfidfVectorizer(ngram_range=(1,2),
min_df=2, max_features=20000)`; `LogisticRegression(class_weight='balanced',
max_iter=2000, random_state=42)`; threshold selected on val by F1;
scikit-learn 1.7.2.

## 6. Source files
- `BASELINE_COMPARISON.md` (prior v1 baseline report, not reused as v2.5b evidence)
- `baselines/run_baselines.py` (v1 baseline entry point)
- `data/stbv_bench/v25b/stbv_bench_v25b.jsonl` (v2.5b raw text/labels used for this pass's baseline)
- `b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_5.csv` (B3/Full-STBV per-message decisions, same sample_ids)
