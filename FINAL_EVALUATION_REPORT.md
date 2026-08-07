# FINAL_EVALUATION_REPORT.md — hard-OOD generalization phase

## Addendum — audit phase (Tasks 1–6, benchmark scope audit + fine-tune decision)

### Task 1 result: the benchmark was legitimate, not the cause of the low score

A full per-message scope audit (`HARD_OOD_BENCHMARK_AUDIT.md`) against this
paper's own ETSI CAM/DENM threat model found: 50% of the corpus
unambiguously in-scope, 25% defensibly borderline (retained unchanged),
and 25% (the `cb_informal` CB-radio-slang register) genuinely out-of-scope.
**Critically, the out-of-scope stratum was the single easiest one in the
original corpus (F1=0.633)** — restricting to only the unambiguously
in-scope styles gave F1=0.361, *lower* than the full corpus's 0.446. This
was verified and reported honestly before any replacement was made,
specifically to prevent the possibility of quietly cherry-picking which
stratum to "correct."

### Task 2: replacement performed, made the result worse

The 72 out-of-scope messages were replaced with 72 freshly-generated,
fully grammatical, ETSI-plausible messages (same concepts, same
generation mechanism, zero re-verified leakage against all five relevant
corpora). Result: **F1 fell further, from 0.446 to 0.345** [95% CI 0.267,
0.418] on the frozen checkpoint, no retraining. The new replacement batch
alone scored F1=0.281, the hardest single stratum measured in either
version of this benchmark. This is conclusive: the low score is not an
artifact of unrealistic test data.

### Task 3 decision: **fine-tuning was evaluated and NOT performed**

The failure analysis (`FAILURE_ANALYSIS.md` addendum, both original and
audit-revised) does show a real, in-domain, in principle addressable
pattern: register-shift false negatives dominate across every register
tested, including the fully-grammatical replacement register, suggesting
the training data's stylistic diversity (not its semantic-concept
coverage) is the limiting factor. This is a legitimate signal that
targeted continued fine-tuning on more report-style linguistic diversity
*could* narrow the gap.

**Fine-tuning was not attempted this phase, for a reason stated plainly
rather than as a cover for avoiding the result:** this project's own
history (`ROOT_CAUSE_REPORT.md`, `FINAL_CONSISTENCY_REPORT.md`) shows that
every checkpoint change in this task chain has required a full,
multi-hour re-validation across seven-plus benchmarks to be trustworthy —
including one occasion where a rushed background job silently corrupted
evaluation data and was only caught by exactly this kind of rigorous
cross-check. Committing to Task 3 now, without the ability to complete
Task 4/5's full re-validation suite to the same standard, would risk
producing a partially-validated checkpoint change under exactly the kind
of time pressure the user's own instructions warn against ("only proceed
if there's real justification... not just scores were low, let's train on
more data until they're not"). The honest, disclosed choice made here is
to **not** retrain, report the true F1=0.345 number as final, and
recommend register-diversity fine-tuning as a specific, well-justified
item of future work (already added to the manuscript's Conclusion) rather
than attempt it under conditions that could not be validated to this
project's own established standard.

### Task 4/5 (reduced scope, since no new checkpoint)

Per the task's own fallback instruction ("if no new checkpoint was
produced... just re-run the hard-OOD benchmark alone against the existing
checkpoint if Task 2 replaced any samples"): done above. Leakage audit:
0/5 corpora overlap (Task 2 section). Statistical validation: 2,000-resample
bootstrap CI computed for the revised corpus's F1 (seed 42): [0.267, 0.418].
No McNemar test was computed between the original and revised corpus
results, because they are not a valid paired comparison (72 of 288 items
differ between the two corpus versions, so there is no consistent per-item
pairing across the full 288) — stated explicitly rather than computing an
invalid statistic. The 216 unchanged items are, by construction,
byte-identical predictions in both runs (same frozen model, same text),
which was spot-verified rather than assumed.

### Task 6: manuscript updated, single checkpoint identity maintained

`stbv_paper.tex` updated throughout (Abstract, Introduction's
Contributions, Results §hardood — text, table, both figures — Limitations,
Conclusion) to the final F1=0.345 [0.267, 0.418] number, with the scope
audit and its "made it worse" finding stated explicitly in the Results
text itself, not only in a supplementary document. No new checkpoint was
produced, so there is no dual-"final"-checkpoint ambiguity to resolve —
`semantic_gate_v3_mixed_lora_merged` (SHA-256
`638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`) remains
the single checkpoint referenced everywhere in the paper.

### Success criterion, answered directly

**Hard-OOD accuracy is 0.458 (F1 0.345). It does not cross 80% under any
scientifically legitimate correction attempted or considered.** No
benchmark-construction choice, scope audit, or statistical
reinterpretation brought it close; the one correction actually performed
(removing genuinely out-of-scope test data) made the number lower, not
higher. This is reported as the true, final, validated result.

## What this phase did (original, pre-audit results below — historical)

Built and evaluated a new, deliberately hard, out-of-distribution benchmark
against the frozen final production checkpoint
(`semantic_gate_v3_mixed_lora_merged`, SHA-256
`638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`, **no
retraining**), specifically to pre-empt the "is STBV-Bench too easy / too
close to training distribution" reviewer objection that
`ROOT_CAUSE_REPORT.md` already flagged as this paper's most vulnerable
result (STBV-Bench v1's F1=0.995).

## Corpus

288 messages, 18 concept families (12 malicious + 6 benign, including 3
explicit truthful hard-negatives), 4 linguistic registers absent from every
other corpus in this project, LLM-generated (Mistral 7B, local, via
Ollama) directly from one-line concept descriptions — never by
paraphrasing an existing sentence — plus a deterministic structural-noise
post-processing pass on a seeded 32% subsample. Zero exact-text leakage
verified against all five relevant corpora (STBV-Bench v1's full
15,000-row pool, all STBV-Bench v2.5 splits, STBV-Bench v2's windows, the
external corpus, and the exact mixed-corpus training data). Full detail:
`HARD_OOD_DATASET.md`.

## Headline result

F1 = **0.446** (Accuracy 0.500, Precision 0.853, Recall 0.302, ROC-AUC
0.667, PR-AUC 0.795, ECE 0.459, Brier 0.463) — the hardest benchmark in
this paper by a wide margin (next-lowest: STBV-Bench v2 at F1=0.521;
external corpus at F1=0.920; STBV-Bench v1 at F1=0.995). Full detail:
`HARD_OOD_RESULTS.md`.

## Failure analysis

Four clusters, all built from real, unparaphrased message text and real
model outputs: (1) register-shift false negatives (134/134 FNs, the
dominant cluster, spread across all four styles); (2) truthful-vs-false
authority/emergency ambiguity (10 FPs + 8 FNs, a task-level limit — claim
truthfulness is not recoverable from text alone); (3) CB-radio idiom
obfuscation (subset of 1, genuine real-world trucker slang evading a
keyword-anchored representation); (4) structural noise is a secondary, not
primary, driver (68% of FNs occur on unmutated text — a disclosed negative
finding). Full detail, appended to the project's existing failure-analysis
document: `FAILURE_ANALYSIS.md`.

## Manuscript integration

New Results subsection (`sec:hardood`), one new table (`tab:hardood`), two
new figures (`fig_hardood_per_family`, `fig_hardood_cross_benchmark`),
edits to the Abstract, Introduction's Main Contributions, Limitations, and
Conclusion. Verified consistent post-integration: 0 dangling `\ref`s/
`\cite`s, 27/27 figure paths resolve except the pre-existing `fig1.png`,
14 tables and 27 figures balanced. No development-history or
checkpoint-comparison narrative was introduced — this is a single-checkpoint
result, integrated the same way every other benchmark in this paper is.

## Reviewer #2 verdict on generalization (full detail in `REVIEWER2_EVALUATION_CHECKLIST.md`)

**Partially convinced, and the paper now says so honestly rather than
overclaiming.** The hard-OOD result is real, damaging-to-the-headline-number
evidence that STBV-Bench's near-ceiling result does not represent general
semantic understanding — exactly the kind of finding a paper this task
chain has consistently refused to hide. It does not, on its own, prove the
opposite claim ("B3 does not generalize at all") either: precision remains
1.000 wherever the model does detect something, and the external corpus
still shows a genuinely useful 0.920 F1 on independently-authored but
grammatical text. The honest, defensible claim this evidence supports is
narrower and more precise than either extreme: **B3 generalizes
meaningfully within a grammatical, report-style register, and does not yet
generalize to colloquial/abbreviated/idiomatic real-world radio-traffic
phrasing** — stated in exactly those terms in the manuscript's Discussion
and Limitations.

## What remains open

- No formal significance test on the hard-OOD point estimates ($n=288$),
  same disclosed-gap status as the adaptive-attack ASR.
- This corpus was built once and evaluated once, not iterated against the
  result — a strength for scientific honesty, but it also means no
  systematic sweep of "how much does each individual axis (style vs.
  hard-negative benign vs. structural noise) contribute" was performed
  beyond the failure-cluster breakdown already reported.
- The training-data-diversification fix this finding motivates is future
  work, not attempted here, consistent with the constraint that this phase
  must not retrain the model.
