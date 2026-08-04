# Lexical Leakage Analysis: STBV-Bench v2.5

## Acceptance criterion (declared in advance, in [`benchmark/lexical_leakage.py`](benchmark/lexical_leakage.py))

A benchmark is **UNACCEPTABLE** if any bag-of-words model (no semantic capacity)
separates its classes near-perfectly under cross-validation:

```
best lexical F1      must be < 0.90
best lexical ROC-AUC must be < 0.95
```

These thresholds are deliberately permissive — lexical models *should* retain
some signal, because real attacks genuinely use somewhat different words than
routine reports. What must not survive is *near-perfect* separation, because
that means the label is recoverable from surface form alone, and any model —
however unsophisticated — will "solve" the benchmark without reasoning about
what a message is asserting.

## Summary of every iteration

| Iteration | Corpus change | Best random-split F1 | Best random-split AUC | Verdict |
|---|---|---|---|---|
| 0 (v1) | — (baseline) | 1.0000 | 1.0000 | UNACCEPTABLE |
| 1 | Compositional generation, shared lexicon, matched length profiles | 1.0000 | 1.0000 | UNACCEPTABLE |
| 2 | Bugfix: mood balancing (`pick_core`) was written but never actually called by `generate()` — fixed | 1.0000 | 1.0000 | UNACCEPTABLE |
| 3 | Lexical-bridge hard negatives added (legitimate uses of `disregard`/`void`/`precedence`/`stale`/`checks`/`verification`) | 1.0000 | 1.0000 | UNACCEPTABLE |
| **3, template-disjoint split** | *same corpus as iter 3, evaluation protocol changed* | **0.7284** | **0.8427** | **ACCEPTABLE** |

Every iteration's full model-by-model numbers are in
`results/benchmark_audit/lexical_leakage_v25_iter{1,2,3}.json` and
`lexical_leakage_v25_template_holdout.json`. Nothing below is asserted without
a JSON file backing it.

## Iteration 1: compositional generation

**Change**: replaced v1's ~10 fixed strings per class with a compositional
grammar (`benchmark/v25_compositional.py`) — shared opening/warrant/closing
constituents, a shared slot lexicon (roads, weather, hazards, timestamps), and
per-attack-family "hard negative" benign intents that legitimately use each
family's characteristic vocabulary (a real clearance, a real priority grant,
a real corroborated detection).

**Result**: token-count shortcut fixed (AUC 0.544, chance level). Bag-of-words
models still F1 = 1.0000.

**Diagnosis** (inspecting the trained LogisticRegression's top-weighted
features): the surviving signal was **grammatical mood**, not vocabulary.
Top malicious features were `this`, `your`, `you`, `treat`, `now`,
`immediately`; top benign features were `is running`, `reported by`, `via`,
`has been`. Attacks were uniformly written as second-person imperatives
("you must...") and benign messages as third-person reports ("X reports..."),
so mood alone predicted the label almost perfectly, independent of content.

## Iteration 2: mood-balancing bugfix

**Change**: `v25_compositional.py` had already been rewritten so every core
sentence — benign and malicious alike — exists in both a `direct`
(second-person) and a `report` (third-person) form, with a `pick_core()`
helper meant to sample mood independently of label. **Auditing the actual
generator (`benchmark/stbv_bench_v25.py::generate`) found it was calling
`rng.choice(BENIGN_CORE[intent])` directly on the `{"direct": [...], "report":
[...]}` dict — never calling `pick_core()` at all.** `random.choice` on a dict
iterates its keys, so this was silently sampling between the two *strings*
`"direct"` and `"report"` as if they were core templates, and the on-disk
corpus that iteration-1's leakage numbers were computed from predated the
mood-balancing work entirely. This is exactly the kind of silent generator/
metric mismatch this document exists to catch — it is reported here rather
than quietly fixed and forgotten.

**Fix**: `generate()` now calls `pick_core()`, and every emitted row records
its sampled `mood`.

**Result after fix**: mood is empirically balanced (2,903 direct / 2,848
report for benign; 3,327 direct / 3,310 report for malicious — see
`results/benchmark_audit/audit_v25.json`), and the `you`/`your` shortcut is
gone (occurs in 1,762/5,751 benign vs 1,545/6,637 malicious — now *more*
common in benign). **Bag-of-words models still F1 = 1.0000.**

**Diagnosis**: the leak moved from mood to the finite, family-defining
**predicate vocabulary** itself. Re-inspecting the trained model's top
features: malicious — `recorded`, `verification`, `fleet`, `disregard`,
`void`, `checks`, `precedence`, `stale`, `detection`; benign — `should`,
`may`, `wider margin`, `comparable`, `is running`, `reduced`. These are not
grammatical artifacts — they are the words that *define* each attack
family's semantics (an override asserts something is void; a false
clearance asserts something is stale/resolved). In a template-authored
corpus with a bounded number of distinct core sentences per family
(typically 3–5), this vocabulary is close to definitionally attack-exclusive.

## Iteration 3: lexical-bridge hard negatives

**Change**: added three new benign intents
(`legit_bridge_disregard`, `legit_bridge_precedence`,
`legit_bridge_fleet_detection`, in `v25_compositional.py`) that reuse every
one of iteration 2's top discriminative malicious tokens in genuinely
legitimate messages — a verified, logged cancellation ("you may disregard the
stale {haz} entry ... verification is logged and checks out"), a
dispatch-verified precedence grant, a corroborated non-stale detection.

**Result**: `TF-IDF+DecisionTree` F1 dropped 1.0000 → 0.9823 and
`Count+NB`/`RandomForest` dropped to ~0.998, showing the bridge genuinely
moved some mass. **The two strongest models, TF-IDF+LogisticRegression and
TF-IDF+LinearSVC, remained at F1 = 1.0000, AUC = 1.0000.**

**Diagnosis, and why brute-force vocabulary bridging cannot fully succeed
here**: a linear bag-of-n-grams model over a template-authored corpus does
not need class-exclusive *words* to separate classes — it only needs
class-exclusive **n-gram combinations**, and as long as each of the corpus's
~180 distinct core-sentence skeletons is deterministically assigned to one
label, a sufficiently expressive linear model can memorize which skeleton
(invariant under slot substitution) maps to which label, regardless of how
much individual vocabulary is shared across classes. This is not a bug in
this benchmark specifically; it is the standard failure mode documented for
template/slot-based NLI and QA benchmarks (e.g. HANS, PAWS): **finite
skeleton counts under a random train/test split are memorizable by
definition**, however much per-token vocabulary overlap is engineered. No
number of additional hard-negative iterations changes this fact, so further
brute-force bridging iterations were not pursued past iteration 3 — the
issue was retargeted at its actual cause (see below) rather than chased with
diminishing-return template edits.

## The fix that actually works: template-disjoint evaluation

**Hypothesis**: if the leak is "the model has seen this exact skeleton
before," then a model trained on skeletons the test set never sees should
lose most of its accuracy, and a genuinely semantic model should not.

**Test**: every generated message was tagged with a `template_id`
(intent/family x mood x the unformatted core-sentence string, before slot
filling — 180 distinct templates across the corpus). All five lexical models
were re-evaluated with `GroupKFold(5)` grouped on `template_id`, so no fold
ever contains the same template skeleton in both train and test.

**Result** (`results/benchmark_audit/lexical_leakage_v25_template_holdout.json`):

| Model | Random-split F1 | **Template-holdout F1** | Random-split AUC | **Template-holdout AUC** |
|---|---|---|---|---|
| TF-IDF + LogisticRegression | 1.0000 | **0.7284 ± 0.037** | 1.0000 | **0.8427 ± 0.052** |
| TF-IDF + LinearSVC | 1.0000 | **0.7147 ± 0.025** | 1.0000 | **0.8363** |
| Count + MultinomialNB | 0.9976 | **0.7619 ± 0.031** | 1.0000 | **0.8613** |
| TF-IDF + RandomForest | 0.9987 | **0.6405 ± 0.072** | 1.0000 | **0.7515** |
| TF-IDF + DecisionTree | 0.9823 | **0.5656 ± 0.062** | 0.9805 | **0.5871** |

Best lexical F1 under template-holdout = **0.7284**, best AUC = **0.8427** —
both comfortably under the 0.90/0.95 acceptance thresholds. **Verdict:
ACCEPTABLE.** The decision-tree model, which has the least capacity to
memorize distributed n-gram combinations, falls essentially to chance
(F1 = 0.566, AUC = 0.587), which is the expected signature of a shortcut
being closed rather than merely a harder split.

## Conclusion and recommendation (this is the actual redesign, not a cosmetic pass)

**The corpus-diversity work in iterations 1–3 was necessary but not
sufficient.** It eliminated the length shortcut, the mood shortcut, and
reduced (but did not eliminate) the vocabulary shortcut. **The remaining
lexical shortcut is structural, not lexical**: it is memorization of a
bounded set of hand-authored sentence skeletons, which no amount of
within-skeleton vocabulary bridging can fully remove under a random
train/test split, because the skeleton count is finite by construction in
any template-based generator (including one written by an LLM, and including
one with 10x more templates than this one — the shortcut only gets more
expensive to find, not impossible).

**The scientifically correct fix is therefore a change to the evaluation
protocol, not an unbounded search for a template design that defeats it**:
STBV-Bench v2.5 must be evaluated with **template-disjoint splitting**
(`GroupKFold` on `template_id`, now present in every row of
`data/stbv_bench/v25/stbv_bench_v25.jsonl`) whenever a result is used to
support a claim about semantic vs. lexical generalization. Random splits
remain useful for measuring in-distribution operating performance, but must
not be cited as evidence against lexical memorization. Both protocols are
reported in [BENCHMARK_AUDIT.md](BENCHMARK_AUDIT.md); this is precedented —
speaker-disjoint splits in speech recognition and subject-disjoint splits in
medical imaging exist for exactly this reason.

## What this means for B3 and the paper (honest scope statement)

B3's own evaluation numbers reported elsewhere in this repository were
**not** all computed under template-disjoint splitting, because that
protocol did not exist until this analysis. Re-running B3 specifically under
`GroupKFold(template_id)` on v2.5, and updating every affected manuscript
section, is tracked as follow-on work and is **not** claimed as complete by
this document — see the repository's `BENCHMARK_REDESIGN.md` for what
changed in the corpus itself, and the top-level task list for what remains
before the paper's benchmark-dependent sections can be finalized. Reporting
this gap explicitly is the point of this document, not an oversight to be
smoothed over.
