# Table Audit: B3-Alone F1 ≈ 1.000 on STBV-Bench v1

**Numbering note**: this audit targets the table the request describes ("B3-only F1 = 1.000 or near-perfect", main ablation) — in the current manuscript this is **Table I** ("Layer Contribution, STBV-Bench v1"), not Table II (the ITE-Bench per-layer table). Flagged here rather than silently guessing; the finding below applies regardless of which number the table carries.

## The value in question

Table I reports B3-alone F1 = **1.000** on STBV-Bench v1 ($n{=}10{,}000$), re-verified against the final checkpoint this session (7,007/7,007 attacks caught, 0 false positives).

## Investigation

Five candidate explanations were checked, in order of how directly each is supported by evidence already in this repository.

### 1. Exact-duplicate / sample-level leakage — RULED OUT, verified by construction
`b3_eval/v25_finetune/build_mixed_corpus.py` (line 57): `V1_EVAL_LIMIT = 10000  # rows [0:V1_EVAL_LIMIT] are reserved for eval scripts; never read for training`. The final checkpoint's training data draws its stratified v1 slice exclusively from `rows[10000:]` of the 100,000-row `data/stbv_bench/v1/stbv_bench.jsonl` file; the evaluated 10,000 samples (`rows[0:10000]`) are never read by any training script. This is a hard row-index partition, not merely a `sample_id`-uniqueness check — the strongest available guarantee against literal duplicate leakage.

### 2. Template-level / generator-family leakage — **CONFIRMED, this is the real explanation**
STBV-Bench v1 is generated entirely by one seeded, rule-based semantic transformation engine: "each of 21 transformation rules... defines a bank of slot-fillable text templates" (Appendix, Semantic Transformation Engine). **Both the evaluated 10,000 rows and the training-used 90,000 rows are drawn from the same finite template bank** — the row-index partition above prevents the model from seeing the exact evaluated *rows*, but does not prevent it from seeing the exact same underlying *templates*, just with different slot-fills (different road names, timestamps, station IDs), during training. This is template-family leakage: a real, well-documented phenomenon distinct from and easy to miss alongside sample-level deduplication checks. STBV-Bench v2.5b was built specifically to close this exact gap — an entirely new template bank, verified zero template-id overlap against v2.5's own training templates (Section~V.C of the manuscript) — and this is precisely why it shows a lower, more conservative F1 (0.945, not 1.000).

### 3. Threshold effects — RULED OUT
Table I's B3-alone row uses the same fixed risk-band decision rule (`MALICIOUS`, or `BENIGN` with confidence below 0.85) used identically across every benchmark in this paper. No threshold was tuned per-benchmark.

### 4. Calibration — RULED OUT as the cause, though real and separately documented
The final checkpoint's calibration temperature ($T{=}2.82$) was fit on an independent 85-sample calibration split, not on STBV-Bench v1, and does not change argmax predictions (temperature scaling rescales confidence, not the decision boundary) — it cannot be responsible for a change in F1.

### 5. Benchmark design (attacker/benign class separability) — a documented, contributing factor, not the primary one
The original (pre-compression) manuscript's baseline comparison found STBV-Bench v1's benign class historically drawn from a small number of unique sentence templates, which two trivial bag-of-words baselines (TF-IDF+LogReg, TF-IDF+LinearSVC) also solved perfectly (F1=1.000) when trained and evaluated on this same corpus family. This is consistent with, and additional evidence for, explanation 2: the benchmark's own construction makes the semantic classification task highly separable for any model — including a linear one — that has seen the template family before, which the final checkpoint's training data does include (rows[10000:] of the same file).

### 6. Genuine model capability — real, but not what this specific number measures
The final checkpoint's genuine semantic-understanding capability is better estimated by STBV-Bench v2.5b (F1=0.945, entirely new templates, zero overlap with any training data) than by v1's F1=1.000. The gap between 1.000 and 0.945 is itself the evidence for how much of v1's ceiling is attributable to template-family exposure during training rather than open-ended generalization.

## Recommendation

**Do not change Table I's reported value** — 1.000 is the correct, honestly re-verified output of the final checkpoint on the final, unmodified STBV-Bench v1 sample set, and altering it would itself be a form of manipulation the audit's own charter prohibits. **The manuscript already recommends, and this audit confirms with concrete new evidence, that v2.5b (Table II in the current numbering) is the number that should anchor any deployment-capability claim, not Table I's F1=1.000.** This audit adds specificity the manuscript's existing hedge language did not previously have: the mechanism is template-family exposure via the `rows[10000:]` training slice, not a vague appeal to "in-distribution effects." Recommend adding one sentence to Section~V.A citing this mechanism explicitly (see manuscript diff below) rather than leaving the explanation at the level of "same generator family."

## Manuscript change made as a direct result of this audit

Added one sentence to the Layer Ablation subsection's discussion, citing the exact training-data partition mechanism (`rows[10000:]` vs. `rows[0:10000]`) rather than repeating the pre-existing, less specific "in-distribution benchmark drawn from the same generator family" hedge alone.
