# ROBUSTNESS_EVAL_REPORT.md — presentation/structure phase (Tasks 1–4)

## Task 1 — benchmark classification

| Benchmark | Class | Rationale |
|---|---|---|
| STBV-Bench v1, full stack | **A. Core** | Canonical, statistically powered ($n=10{,}000$), architecturally central (drives the layer-ablation contribution). Stays in main Results with its in-distribution caveat intact. |
| STBV-Bench v1, B3-alone | **A. Core** | Same benchmark, diagnostic row within the same table — necessary to isolate B3's marginal contribution from fusion's. |
| STBV-Bench v2 (windowed) | **B. Supporting** | Answers a distinct question (ambient-traffic realism) the main benchmark can't; kept, but correctly subordinate to v1 as "contextual, not competing." |
| STBV-Bench v2.5 | **C. Exploratory / methodology-internal** | Not separately reported as a headline number in the main text — its role is as the fine-tuning training-data source (Appendix, provenance), not an independent evaluation claim. No change needed. |
| External semantic corpus | **A. Core** | The paper's primary defense against "is this benchmark too easy" — independently authored, five disjoint sources, still the strongest *in-scope* OOD evidence. Stays in main Results. |
| Mixed-threat case study | **B. Supporting** | Demonstrates the recall/FPR trade under realistic co-occurring kinematic+semantic threats; narrower scope than a standalone capability claim. |
| Adaptive-attack | **A. Core** | Safety-critical, genuinely OOD relative to specific training sentences, the paper's clearest robustness win (ASR 21.6%). Stays in main Results. |
| CP full evaluation | **B. Supporting** | Architecturally motivated (isolates one component's contribution); already appropriately scoped as supplementary to the main ablation. |
| Deployment (SUMO, final checkpoint) | **A. Core** | Required for any systems/deployability claim; SUMO column now fully re-verified against the final checkpoint. |
| Deployment (CARLA, prior checkpoint) | **B. Supporting, disclosed gap** | Retained with explicit "not re-verified against final checkpoint" caveat at every point of use — correctly positioned as supporting evidence, not a headline claim, given the disclosed staleness. |
| Layer ablation (`tab:main_ablation`) | **A. Core** | The paper's architectural-contribution evidence (B1+B2+CP+B3 fusion); explicitly kept per the earlier phase's clarification that this is architecture, not checkpoint-history. |
| Robustness perturbation battery (11 families) | **B. Supporting** *(this phase: closed and now correctly positioned)* | Previously disclosed-but-stale; now rerun against the final checkpoint (Task 3, below) and integrated into its existing "Calibration, Robustness, and Latency" location — appropriately supporting, not headline, evidence. |
| **Hard-OOD benchmark** | **D. Future Work / Limitations** | The benchmark's own audit (`HARD_OOD_BENCHMARK_AUDIT.md`) already established this is a real, currently-unresolved generalization gap *deliberately probing outside the paper's declared deployment scope* — exactly a Task 5 "D" candidate, not a data-quality problem (the audit ruled that out explicitly: correcting the benchmark made the gap larger, not smaller). Its findings are informative about future work, not about current in-scope capability, so it belongs where readers expect boundary-probing/exploratory findings: Limitations/Future Work, not alongside the in-scope core benchmarks it is not a fair comparison against. |

## Task 2 — trim decision

No further trimming performed beyond what Task 1's classification and
Task 5's relocation already produce. Every remaining Class A/B table and
figure answers a question no other remaining table/figure answers; no
redundancy was found beyond what prior phases already removed (the
strict-argmax baseline row, the stale calibration-transfer figure, the
checkpoint-comparison content that was never present to begin with). This
matches the task's own instruction not to re-litigate settled trims.

# ROBUSTNESS_EVAL_REPORT.md — Task 3, in-scope perturbation-battery rerun

## What this closes

`stbv_paper.tex` has, since the mixed-corpus checkpoint became final,
carried a disclosed but unclosed gap: the "Calibration, Robustness, and
Latency" section's 11-family perturbation battery (paraphrase, synonym
substitution, typo, unicode homoglyph, formatting, instruction-hiding,
long-prompt padding, context-poisoning, role-confusion, mixed
benign/malicious, contradictory) was never re-run against
`semantic_gate_v3_mixed_lora_merged` — every other B3-dependent result in
the paper had been, but this one was explicitly flagged as "not
independently re-run... in this evaluation pass" in three separate places
in the manuscript. This is exactly the kind of already-covered-but-stale
gap Task 3 asked to close, not a new exotic angle — hard-OOD (Future Work)
already covers stylistic/register OOD; this closes the standard,
in-scope, already-designed-for-this-checkpoint robustness angle instead.

## Method

`b3_eval/run_robustness.py` (pre-existing, unmodified) reran via a new
thin wrapper, `b3_eval/run_robustness_mixed.py`, which monkeypatches
`b3_eval._harness.MODEL_DIR` to point at the final checkpoint (process-local
only, no file on disk touched, same override pattern used by every other
`*_mixed.py` rerun script in this project) and redirects output to
`b3_eval/results/robustness_mixed.json` so the original checkpoint's
`robustness.json` is preserved unmodified (verified via `git status`/mtime
after the run — untouched). 6 hand-written, V2X-grounded seed messages (3
benign, 3 malicious CAM/DENM-style reports) × 11 deterministic perturbation
families = 66 variants, identical seed set and identical perturbation
functions as the original run (paired by construction). Checkpoint
identity independently confirmed via the run's own manifest:
`sha256_16: "638ed0fada078083"` (prefix-matches the final checkpoint's full
hash).

## Leakage audit

The 6 seeds and 66 generated variants (67 unique texts, since one seed
appears unperturbed in the `truth` baseline) were checked for exact-text
overlap against every corpus used anywhere in this project: STBV-Bench v1
(15,000 rendered rows), all STBV-Bench v2.5 splits, the external corpus,
the mixed-corpus training pool, and the hard-OOD corpus (audit-revised
version). **Zero overlap against all five.**

## Results

### Per-family comparison (original checkpoint vs. final checkpoint)

| Family | Flip rate (orig→final) | Evasion (orig→final) | Over-defense FPR (orig→final) |
|---|---|---|---|
| paraphrase | 0.167→0.000 | 0.333→0.000 | 0.000→0.000 |
| synonym_sub | 0.000→0.000 | 0.000→0.000 | 0.000→0.000 |
| typo | 0.167→0.000 | 0.000→0.000 | 0.333→0.000 |
| unicode_homoglyph | 0.333→0.167 | 0.000→0.000 | 0.667→0.333 |
| formatting | 0.000→0.000 | 0.000→0.000 | 0.000→0.000 |
| instruction_hiding | 0.500→0.333 | 0.000→0.000 | 1.000→0.667 |
| long_prompt | 0.000→0.000 | 0.000→0.000 | 0.000→0.000 |
| context_poisoning | 0.000→0.000 | 0.000→0.000 | 0.000→0.000 |
| role_confusion | 0.500→0.500 | 0.000→0.000 | 1.000→1.000 (unchanged) |
| mixed_benign_malicious | 0.167→0.000 | 0.333→0.000 | 0.000→0.000 |
| **contradictory** | 0.000→**0.500** | 0.000→0.000 | 0.000→**1.000** |

Six of eleven families improve, four are unchanged (all already at their
floor of 0.000, or `role_confusion`'s over-defense, unchanged at 1.000),
and **one family regresses**: `contradictory` (a message that asserts a
claim and then immediately disregards it) goes from 0% to 100%
over-defense — reported plainly, not smoothed away, consistent with this
project's standard throughout.

### Aggregate metrics ($n=66$ paired seed×family variants)

| Metric | Original checkpoint | Final checkpoint |
|---|---|---|
| Accuracy | 0.833 | 0.864 |
| Precision | -- | 0.786 |
| Recall | -- | 1.000 |
| F1 | -- | 0.880 |
| ECE | -- | 0.122 |
| Brier | -- | 0.136 |
| Bootstrap 95% CI on accuracy (2,000 resamples, seed 42) | -- | [0.773, 0.939] |

### Statistical significance

McNemar's test (paired, same 66 seed×family combinations, exact binomial
since $n_{\text{discordant}}=8<25$): $b_{01}=3$ (original-correct/
final-wrong), $b_{10}=5$ (original-wrong/final-correct), $p=0.727$.
**The accuracy improvement (0.833→0.864) is not statistically significant
at this sample size.** This is stated plainly rather than reported as a
win — the per-family pattern (broad, small improvements plus one real
regression) is the more informative result than the aggregate accuracy
delta, which a reviewer should not read as a validated improvement.

## Task 4 — main Results or appendix?

**Appendix**, not main Results. Reasoning: (1) the aggregate accuracy
delta is not statistically significant, so it does not support a headline
claim; (2) this benchmark's *design* already exists in the paper's
appendix-adjacent "Calibration, Robustness, and Latency" subsection as
prior, disclosed content — this rerun closes that specific disclosed gap
rather than introducing a new evaluation axis the reader hasn't seen
before; (3) the one genuinely reportable finding (the `contradictory`
family's regression to 100% over-defense) is exactly the kind of
narrow, family-specific finding this paper's convention already places in
the perturbation-battery paragraph rather than promotes to a standalone
table. It is integrated into the existing "Calibration, Robustness, and
Latency" text (Section~\ref{sec:results}, not a new section), replacing
the stale disclosure sentence with the real, closed result — this is
"adding to an existing appendix-adjacent result," not creating a new
top-level Results subsection.
