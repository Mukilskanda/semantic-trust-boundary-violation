# Baseline Comparison — STBV-Bench Semantic Detection

**Reproduce with one command:**

```bash
python baselines/run_baselines.py              # Baselines 1-3
python baselines/run_baselines.py --llm-judge  # + Baseline 4 (local Ollama)
```

Outputs: `results/baselines/metrics/{baseline_metrics.csv,.json,baseline_per_family.csv}`,
`results/baselines/figures/*.{pdf,png}` (vector).

**Nothing in `b3/`, `pipeline/`, or `trust_engine/` was modified, retrained,
or re-run.** B3's predictions are read from the already-committed artifact
`results/stbv_bench/v1/stbv_bench_per_message.csv`. The only pipeline import
is the message **synthesizer**, used read-only so every detector is scored on
the byte-identical text string B3 itself received.

---

## 1. Headline result

| Detector | Trained on STBV-Bench? | F1 [95% CI] | Precision | Recall [95% CI] | FPR | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|
| **TF-IDF + Logistic Regression** | **yes** (5-fold CV) | **1.0000** [1.0000, 1.0000] | 1.0000 | **1.0000** [1.0000, 1.0000] | 0.0000 | **1.0000** | **1.0000** |
| **TF-IDF + Linear SVM** | **yes** (5-fold CV) | **1.0000** [1.0000, 1.0000] | 1.0000 | **1.0000** [1.0000, 1.0000] | 0.0000 | **1.0000** | **1.0000** |
| B3 — paper's config-4 criterion | no (zero-shot) | 0.7151 [0.7054, 0.7247] | 1.0000 | 0.5566 [0.5448, 0.5682] | 0.0000 | 0.7465 | 0.9116 |
| B3 — strict `MALICIOUS` label | no (zero-shot) | 0.3110 [0.2981, 0.3240] | 1.0000 | 0.1841 [0.1752, 0.1933] | 0.0000 | 0.7465 | 0.9116 |
| Zero-shot LLM judge (Mistral 7B) | no (zero-shot) | 0.2673 [0.2324, 0.3034] | 1.0000 | 0.1543 [0.1315, 0.1788] | 0.0000 | — | — |
| Regex / keyword | no (hand-written) | 0.2346 [0.2216, 0.2466] | 1.0000 | 0.1329 [0.1246, 0.1407] | 0.0000 | 0.5664 | 0.7405 |

$n=10{,}000$; malicious prevalence 0.7007; CIs are 2,000-resample percentile
bootstrap (the same protocol already used elsewhere in this project).

**Two trivial bag-of-words baselines solve STBV-Bench perfectly and
substantially outperform B3.** This is reported plainly because it is what
the data shows. Section 2 explains why the correct reading is *not*
"logistic regression is a better semantic-attack detector than DeBERTa."

---

## 2. Why the perfect baseline scores are a finding about the benchmark

A bag-of-words model reaching ROC-AUC $=1.0000$ on a semantic-manipulation
task is not plausible as genuine semantic understanding. Auditing the corpus
directly (`benchmark_diagnostic()` in the runner) shows why:

| Class | Samples | Unique peer-report strings | Type/token ratio |
|---|---|---|---|
| **benign_control** | 2,993 | **10** | **0.0033** |
| malicious (20 families) | 7,007 | 335 | 0.0478 |

**All 2,993 benign control messages in STBV-Bench are drawn from just ten
sentences** — two templates crossed with five street names:

```
"No incidents to report near {Main Street | Exit 12 | Route 9 |
                             the ring road | the A4 corridor} at this time."
"Traffic moving normally on {Main Street | Exit 12 | Route 9 |
                             the ring road | the A4 corridor}."
```

The learned model confirms it is exploiting exactly this. The most negative
logistic-regression coefficients are the benign template n-grams themselves
(`traffic moving` $-6.44$, `moving normally` $-6.44$, `no incidents` $-4.05$,
`to report` $-4.05$), while the positive side is diffuse function words
(`for`, `is`, `as`). The classifier is not detecting attacks — it is
**memorising a ten-element closed set and labelling everything else
malicious.**

**Consequence for the paper.** STBV-Bench's negative class provides
essentially no lexical variety, so:

1. A perfect score on it measures **benchmark triviality, not detector
   capability**. The TF-IDF rows above should never be quoted as evidence
   that linear models are competitive semantic-attack detectors.
2. B3's frequently-quoted **"100% precision, FPR = 0.000"** is a much weaker
   result than it appears: the negative class it must avoid is ten strings.
   Every detector in the table, including the regex, achieves precision
   1.0000 and FPR 0.0000 — the metric cannot discriminate between them.
3. Any *recall* comparison remains meaningful (the malicious class has 335
   distinct strings across 20 families), which is why recall and ROC-AUC are
   the only columns that separate the detectors at all.

This is a benchmark-construction defect, not a detector defect, and it must
be fixed before STBV-Bench's absolute precision/FPR figures can support any
claim. The concrete fix is to generate benign controls with lexical
diversity comparable to the attack classes.

---

## 3. Fairness disclosure (the comparison is biased *toward* the baselines)

- Baselines 1–2 are **trained on STBV-Bench itself** via 5-fold stratified
  cross-validation; they see in-domain labelled examples of every family
  they are then tested on (out-of-fold).
- B3 **never trained on STBV-Bench**; its numbers are zero-shot transfer
  from a different corpus.

So the TF-IDF result does not establish superiority in deployment — it
establishes that STBV-Bench contains an in-domain signature learnable from
a few thousand examples. Conversely, B3 **does** beat both of the zero-shot
baselines it is directly comparable to (regex 0.2346, LLM judge 0.2673 vs.
B3 0.3110 strict / 0.7151 banded), which is the like-for-like comparison and
a genuine, if modest, positive result for B3.

---

## 4. B3's two operating points (an important clarification)

The paper reports B3's recall as **0.5566**. That figure is not a
classification recall. `isce_config.yaml` sets
`confidence_aware_benign: true`, so `B3RiskPolicy.classify()` assigns
non-`none` risk — routing to Caution — whenever B3 predicts **BENIGN but
with confidence < 0.85**. Under that rule a "detection" includes *"predicted
benign, but not confidently."*

Reproduced exactly (recall 0.5566 to four decimals):

| Criterion | Flagged | Recall | Interpretation |
|---|---|---|---|
| `argmax == MALICIOUS` | 1,290 | **0.1841** | B3 actually classifies the message as an attack |
| `MALICIOUS` **or** (`BENIGN` and conf < 0.85) | 3,900 | **0.5566** | includes low-confidence-benign abstentions |

Both are legitimate to report — abstention-routing is a reasonable design —
but they mean different things, and the paper currently reports only the
larger number without stating that two-thirds of it comes from *low-confidence
benign predictions rather than positive detections*. The strict figure
(0.1841) is the one comparable to any binary classifier's recall.

---

## 5. Per-family recall (`baseline_per_family.csv`)

The 6 families the paper documents at ≤9% recall for B3 are recovered
perfectly by both TF-IDF baselines, for the reason in §2 — those families'
text still differs lexically from the 10 benign strings, so a memorising
model separates them trivially even though B3 (which does not memorise the
benign set) cannot.

---

## 6. Baseline 4 — zero-shot LLM judge

Available and run: **Mistral 7B** (`mistral:latest`) via local Ollama.

- Stratified subsample $n=987$ (47/family); the full 10,000 is not tractable
  locally (~1 msg/s, ≈3 h/pass).
- Prompt: fixed one-shot instruction, single-token MALICIOUS/BENIGN answer;
  unparsable output counted conservatively as BENIGN.
- Result: F1 **0.2673**, recall 0.1543, precision 1.0000.

The judge is a genuine zero-shot comparator (no STBV-Bench exposure) and B3
beats it on both operating points — the most defensible positive comparison
in this document.

**Caveat.** The judge's VRAM residency (3.8 GB) must be released before any
GPU-contended experiment; leaving it loaded starved the CARLA server during
the deployment study.

---

## 7. Figures

`results/baselines/figures/` (PDF vector + PNG):

| File | Content |
|---|---|
| `baseline_roc.pdf` | ROC, all score-producing detectors |
| `baseline_pr.pdf` | Precision–Recall, prevalence baseline marked |
| `baseline_confusion.pdf` | Confusion matrices, all detectors |
| `baseline_f1_ci.pdf` | F1 with 95% bootstrap CI error bars |

---

## 8. What should change in the paper

1. Report the baseline table **in full**, including that TF-IDF wins.
2. State the 10-string benign-class defect explicitly, and retire
   "100% precision / FPR 0.000" as a headline claim — it is not
   discriminative on this corpus.
3. Report B3's strict recall (0.1841) alongside the banded 0.5566, with the
   criterion difference stated.
4. Keep the regex and LLM-judge comparisons as the like-for-like zero-shot
   evidence that B3 does add value over trivial and general-purpose
   alternatives.
