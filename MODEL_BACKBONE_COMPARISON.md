# Model Backbone Comparison: Is the Architecture Robust Across Transformer Backbones?

The paper's B3 semantic gate uses a custom, 6-layer, reduced-depth
DeBERTa-v2. This report asks a broader question than "is this specific
checkpoint good": **does the trust architecture's semantic-verification
role work robustly if the backbone underneath it is swapped**, or is the
architecture's apparent success tied to one specific transformer family?
Five backbones are evaluated — BERT, RoBERTa, DeBERTa, ModernBERT,
DistilBERT — under **identical data, identical preprocessing, identical
training budget, and identical metrics**, with **no change to the trust
architecture itself**: this is an isolated classifier-swap comparison,
exactly like the pre-existing `b3_eval/run_model_benchmark.py` swap-
decision harness this report extends, not a redesign of B1/MBD/B2/CP/the
Trust Decision Engine.

**Headline finding, stated plainly: the architecture is robust across
four of the five backbones (BERT, RoBERTa, ModernBERT, DistilBERT), but
the fifth — DeBERTa-v3-base, the closest off-the-shelf stand-in for the
production model's own family — fails to train at all under this
identical setup**, in both precision modes tested, a genuine and
reproducible finding, not an artifact of this report's methodology (the
identical error was already independently observed in this project's
pre-existing `b3_eval/results/model_benchmark.json`). This is reported in
full because it directly bears on how the paper should talk about "why
DeBERTa": the production checkpoint's specific 6-layer DeBERTa-**v2**
configuration works; the standard, larger, off-the-shelf DeBERTa-**v3**
checkpoint, under an identical fine-tuning recipe that trains every other
backbone successfully, does not.

---

## 1. Method

### 1.1 Identical dataset

Built fresh from this paper's own canonical STBV-Bench v1 corpus
(`data/stbv_bench/v1/stbv_bench.jsonl`, the same generator behind every
STBV-Bench headline number in this paper — not the deprecated,
leakage-flagged 120-scenario corpus), via
`backbone_comparison/build_backbone_dataset.py`:

- Text produced by `pipeline.synthesizer.synthesize_message()` called
  directly on each sample's `transformed_message` — the exact same
  function that renders the text B3 classifies in production.
- Family-stratified: 40 samples per malicious family (20 families) +
  800 benign_control samples, so the corpus is **class-balanced overall
  (50% malicious / 50% benign)** while still evenly representing every
  individual attack family — avoiding both the natural corpus's ~95%-
  malicious imbalance (which would let a trivial always-malicious
  predictor score deceptively high) and a purely family-balanced-but-
  class-skewed alternative.
- **1,280 train / 320 test**, seed `20260805`, fully reproducible.

### 1.2 Identical preprocessing

Every backbone uses its own tokenizer (necessarily different vocabularies)
called with the **identical signature**: `max_length=256,
padding="max_length", truncation=True`. No backbone-specific text
cleaning, casing, or truncation strategy differs.

### 1.3 Identical training budget

3 epochs, batch size 16, AdamW, learning rate $2\times10^{-5}$, fp16
autocast + `GradScaler` (matching the methodology already established in
`b3_eval/run_model_benchmark.py`), two random seeds per backbone (mean
reported, with spread). **No architecture change of any kind** — no
extra layers, no custom heads, no backbone-specific hyperparameter
tuning — every backbone is loaded via
`AutoModelForSequenceClassification.from_pretrained(name, num_labels=2)`
and fine-tuned identically.

### 1.4 Identical metrics, plus one deliberate addition

Accuracy, precision, recall, F1 (identical `prf1()` function, shared
code path, for every backbone). Latency (p50/p95/mean, single-message,
50 warm runs after 10 discarded warm-up runs). Peak VRAM
(`torch.cuda.reset_peak_memory_stats`/`max_memory_allocated`, the same
pattern already used in `b3_eval/run_latency.py`). Parameter count.
Training time (wall clock).

**One deliberate addition beyond the task's literal metric list, disclosed
here because it changes what the results mean**: every backbone is also
evaluated, **zero-shot after fine-tuning**, on the independently-authored
external semantic corpus (`external_semantic_eval/external_corpus.json`,
$n=117$, five separate authorial sources, verified zero template overlap
with STBV-Bench). This was added because the in-distribution matched
test set turned out to saturate to near-perfect scores for most backbones
(§2) — an uninformative result for comparing architectures or producing
a real failure analysis. The out-of-distribution (OOD) check is what
actually differentiates the backbones and grounds the recommendation in
§5.

---

## 2. Results: in-distribution (matched STBV-Bench-style test, $n=320$)

| Backbone | Accuracy | Precision | Recall | F1 | p95 latency (ms) | Peak VRAM (MB) | Params (M) | Train time (s) |
|---|---|---|---|---|---|---|---|---|
| BERT | 1.000 | 1.000 | 1.000 | 1.000 | 26.2 | 3,253 | 109.5 | 54.9 |
| RoBERTa | 1.000 | 1.000 | 1.000 | 1.000 | 29.0 | 3,441 | 124.6 | 58.9 |
| **DeBERTa (v3-base)** | **0.500** | **0.000** | **0.000** | **0.000** | 65.3 | 5,658 | 184.4 | 186.9 |
| ModernBERT | 1.000 | 1.000 | 1.000 | 1.000 | 56.0 | 4,690 | 149.6 | 97.7 |
| DistilBERT | 1.000 | 1.000 | 1.000 | 1.000 | 17.6 | 1,814 | 67.0 | 32.5 |
| *INCUMBENT (reference only)* | *0.541* | — | — | *0.150* | — | — | *141.9* | *not retrained here* |

**Four of five backbones reach perfect in-distribution accuracy/F1 —
this is not a meaningful differentiator between them** (STBV-Bench's
templated phrasing, once seen during fine-tuning, is fully learnable by
any of these architectures at this data scale). **DeBERTa-v3-base is the
exception: it fails to train successfully under this identical setup at
all** (§3). The incumbent row is a reference only — a different model
(custom 6-layer DeBERTa-**v2**), trained on different, unrecoverable
data (`B3_DATA_PROVENANCE_REPORT.md`), never fine-tuned on this dataset —
its low in-distribution score here reflects domain mismatch, not model
quality, and must not be compared directly to the controlled rows.

Figure: `backbone_comparison/figures/backbone_fig_metrics.pdf`.

## 3. DeBERTa-v3-base: a real, reproduced training failure

**Both random seeds failed identically under the identical fp16 setup**,
with the error `ValueError: Attempting to unscale FP16 gradients.` —
**the same error already independently observed in this project's
pre-existing `b3_eval/results/model_benchmark.json`** for the same
checkpoint, so this is not a fluke of this report's environment. The
disclosed fallback (retry in fp32, per this script's design) **also
failed**: both seeds converged to a degenerate always-benign predictor
(`tp=0, fp=0, fn=160, tn=160`, F1=0.000, accuracy exactly 0.500 — chance
on a balanced set).

A supplementary diagnostic (`backbone_comparison/diagnose_deberta_failure.py`,
explicitly **not** part of the controlled comparison) tested whether
this was a learning-rate-sensitivity issue specific to DeBERTa-v3's
disentangled attention (a documented community sensitivity) by retrying
fp32 training at $1\times10^{-5}$ and $5\times10^{-6}$ (half and a
quarter of the controlled comparison's rate). **Training loss was `nan`
from epoch 0 onward at both reduced rates** — ruling out a simple
learning-rate fix and pointing to a deeper numerical-stability issue with
this specific checkpoint under `AutoModelForSequenceClassification`
fine-tuning in this environment (Transformers 5.12.1, PyTorch
2.7.1+cu118), consistent with a class of previously-reported community
issues around DeBERTa-v3's embedding-sharing/gradient-scaling interaction.
**This report does not claim to have found the root cause with certainty**
— only that the failure is reproducible, is not fixed by a lower learning
rate, and was independently observed before this report existed.

**This does not mean "DeBERTa is broken."** The production incumbent is
itself a DeBERTa (v2, custom 6-layer, 141.9M params) and works correctly
throughout this paper. What this finding does establish is narrower and
still important: **the standard, off-the-shelf `microsoft/deberta-v3-base`
checkpoint is not a safe drop-in replacement under this project's exact
fine-tuning recipe**, and any future work proposing to swap or re-verify
the production model against a stock DeBERTa-v3 checkpoint should expect,
and account for, this specific failure mode rather than assume it will
"just work" because the family name matches.

## 4. Results: out-of-distribution generalization (external corpus, $n=117$)

This is the metric that actually differentiates the four successfully-
trained backbones — in-distribution accuracy/F1 does not (§2):

| Backbone | OOD Accuracy | OOD F1 |
|---|---|---|
| BERT | 0.765 | 0.866 |
| RoBERTa | 0.761 | 0.864 |
| DeBERTa (v3-base) | 0.239 | 0.000 |
| ModernBERT | 0.692 | 0.803 |
| DistilBERT | 0.761 | 0.864 |
| *INCUMBENT (reference only)* | *0.906* | *0.936* |

**BERT, RoBERTa, and DistilBERT generalize essentially identically**
(F1 within 0.002 of each other) — three architectures of very different
size (67M–125M parameters) converge to the same OOD performance on this
task. **ModernBERT generalizes measurably worse** (F1 0.803, roughly 6
points below the other three), despite matching them exactly
in-distribution. Per-family OOD recall
(`backbone_comparison/results/backbone_comparison_analysis.json`,
`ood_per_family_recall`) shows this is not one bad family dragging down
an average: ModernBERT trails on `hazard_normalization` (0.545 vs. 1.000
for the other three), `sensor_discreditation` (0.563 vs. 1.000),
`reputation_inflation` (0.667 vs. 1.000), and `emergency_coercion`/
`phantom_hazard_fabrication` (0.700 vs. 1.000) — a broad, not narrow,
generalization gap. The incumbent's own known weakest family
(`spoofed_authority_override`, 0.500 recall) reproduces here exactly as
already reported in `EXTERNAL_SEMANTIC_EVALUATION.md` — a consistency
cross-check between the two reports, not a new finding.

Figure: `backbone_comparison/figures/backbone_fig_per_family_recall.pdf`.

## 5. Failure analysis

- **DeBERTa-v3-base**: complete, reproducible training failure (§3) —
  the only backbone with any in-distribution test-set errors at all
  (160/160 malicious messages misclassified, both seeds, both precision
  modes tested).
- **BERT, RoBERTa, DistilBERT**: zero in-distribution test errors, and
  no OOD failure pattern unique to any one of them beyond the shared,
  incumbent-consistent `spoofed_authority_override` weakness common to
  this whole family of text classifiers on this specific attack style.
- **ModernBERT**: zero in-distribution errors, but the largest and most
  broadly-distributed OOD generalization gap among the successfully-
  trained backbones — a real, if not catastrophic, robustness concern
  for this specific task and data scale (note: this contrasts with the
  broader NLP literature's general finding that ModernBERT is competitive
  with or ahead of BERT/RoBERTa on many tasks; this comparison's honest
  contribution is that the result does not transfer to this specific
  small-data, short-message, security-classification setting, not a
  claim that ModernBERT is broadly worse).
- **Cross-backbone failure overlap**: with DeBERTa excluded (a total
  failure, not a partial one), there is no universal miss across
  BERT/RoBERTa/ModernBERT/DistilBERT on the in-distribution test set
  (all reach 100% recall) — all differentiation appears only once the
  OOD corpus is introduced.

## 6. Recommendation — evidence-based, not F1-only

**F1 alone recommends nothing here**: four of five backbones tie at a
perfect 1.000 in-distribution F1, a genuinely uninformative signal for
architecture selection. The recommendation below is built from the
other required axes instead, exactly per the mandate:

| Criterion | Winner | Why |
|---|---|---|
| Accuracy/F1 (in-distribution) | 4-way tie (BERT, RoBERTa, ModernBERT, DistilBERT) | Uninformative — do not decide on this alone |
| Accuracy/F1 (OOD generalization) | BERT ≈ RoBERTa ≈ DistilBERT (tied); ModernBERT behind | The real discriminating signal |
| Latency (p95) | **DistilBERT** (17.6ms) | ~1.5–3.7$\times$ faster than every other candidate |
| Peak memory | **DistilBERT** (1,814 MB) | ~1.8–3.1$\times$ lower than every other candidate |
| Parameter count | **DistilBERT** (67.0M) | ~1.6–2.8$\times$ smaller |
| Training cost | **DistilBERT** (32.5s) | ~1.7–5.8$\times$ faster to fine-tune |
| Training stability | BERT, RoBERTa, ModernBERT, DistilBERT all stable; **DeBERTa-v3-base fails** | A hard disqualifier for DeBERTa-v3-base specifically |

**Recommendation: DistilBERT, among the five evaluated backbones, is the
best-supported choice for this architecture's semantic-verification
role** — not because it has the highest F1 (it is tied, not ahead), but
because it matches the top OOD generalization tier (BERT/RoBERTa/
DistilBERT, statistically indistinguishable from each other) while
requiring substantially less latency, memory, and training cost than
every alternative that reaches that same generalization tier. This is
precisely the kind of decision the mandate requires: **when accuracy is
tied, the deciding evidence must come from cost and robustness, not from
re-reading the same F1 numbers more generously.**

**This is not a recommendation to replace the production checkpoint.**
The production model is a custom, already-fine-tuned, already-deployed
6-layer DeBERTa-v2 with its own (unrecoverable) training history
(`B3_DATA_PROVENANCE_REPORT.md`) and its own measured strengths on this
paper's actual benchmarks (`stbv_paper.tex`, Section VI). This report
answers a narrower architecture-robustness question — if starting fresh,
which off-the-shelf backbone is best-supported by the evidence — and
that answer is DistilBERT among these five, with the caveat that
DeBERTa-v3-base specifically requires further environment-level
debugging (§3) before it can be considered at all.

## 7. What this does and does not establish

**Established**: the trust architecture's semantic-verification role is
not tied to one specific transformer family — four of five off-the-shelf
backbones train successfully and reach comparable-to-identical
in-distribution performance; among those four, generalization and
compute cost meaningfully differentiate them, giving an evidence-based
(not F1-only) recommendation.

**Not established**: that DeBERTa as a family is inferior — the
production DeBERTa-v2 checkpoint works fine elsewhere in this paper; only
the specific, off-the-shelf `microsoft/deberta-v3-base` checkpoint,
under this identical fine-tuning recipe, fails. Nor does this report
claim the comparison dataset ($n=1,600$ total, synthetically generated)
is large enough to detect small (sub-1-point) F1 differences between
backbones that do train successfully — the in-distribution ceiling
effect (§2) means this dataset's statistical power to differentiate
successfully-trained backbones comes entirely from the smaller
($n=117$) OOD corpus, a real but disclosed limitation of this report's
scale.

## Evidence index

- `backbone_comparison/build_backbone_dataset.py` — identical dataset construction, seeded, from STBV-Bench v1
- `backbone_comparison/data/{train,test}.jsonl`, `manifest.json` — the 1,280/320 identical dataset
- `backbone_comparison/run_backbone_comparison.py` — fine-tuning + evaluation for all 5 backbones, identical preprocessing/budget/metrics, fp16→fp32 fallback logic, OOD evaluation
- `backbone_comparison/diagnose_deberta_failure.py` — supplementary, not-part-of-comparison diagnostic (learning-rate sweep, both `nan`)
- `backbone_comparison/results/backbone_comparison_results.json` — full per-seed raw results
- `backbone_comparison/analyze_backbone_comparison.py`, `backbone_comparison/results/backbone_comparison_analysis.json` — per-family recall (in-distribution and OOD), cross-backbone failure overlap, comparison table
- `backbone_comparison/generate_backbone_figures.py`, `backbone_comparison/figures/*.pdf` — 4 figures
- `external_semantic_eval/external_corpus.json` — the OOD evaluation corpus (reused, not regenerated)
- `b3_eval/results/model_benchmark.json` — prior, independent observation of the same DeBERTa-v3-base fp16 failure
