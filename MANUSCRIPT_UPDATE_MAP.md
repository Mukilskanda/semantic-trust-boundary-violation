# MANUSCRIPT_UPDATE_MAP.md — Required `stbv_paper.tex` Edits

**`stbv_paper.tex` itself is NOT modified by this task.** This document
lists every location that would need an edit if the fine-tuned checkpoint
were adopted, with old text (quoted/paraphrased) → new values. Per
`REGRESSION_REPORT.md`'s recommendation, **the current recommendation is to
NOT adopt the fine-tuned checkpoint for this manuscript** — so in practice
none of these edits should currently be applied; this map exists so the
decision is fully informed and the edits are ready if the recommendation is
revisited after a threshold-recalibration pass. Line numbers refer to
`stbv_paper.tex` as of this session.

---

## Abstract (line 48)

**Old:** "The semantic verification layer (B3) alone achieves 100% precision
and 55.7% recall (F1=0.715)... the complete fused architecture achieves
F1=0.718... McNemar p=3.06e-29... routes 92.5% of its decision changes
through... Caution... B3 achieves 89.9% recall and 97.6% precision (ROC AUC
0.975)... 83.7% attack success rate... CP... recovers 11 of 21 attacker
messages..."

**New values if checkpoint swapped:** B3-alone F1 **0.390** (recall 24.2%,
precision 100%); full stack F1 **0.403** (recall 25.5%, precision 96.3%);
McNemar/Cohen's h old-vs-new (not old-vs-fused) would need restating since
the abstract's existing McNemar figure compares B3-alone vs. full-stack
*within* one checkpoint — that internal comparison should be recomputed on
the new checkpoint's numbers (not done in this pass; low priority since the
recommendation is not to swap). External corpus: recall **88.8%**, precision
**97.5%** (ROC-AUC 0.952). Adaptive ASR: **84.3%** (aggregate unchanged in
substance, small n/discrepancy noted in `UPDATED_TABLES.md` §5). CP row:
unchanged (11/21 finding is B3-independent, confirmed byte-identical).
**Given the severity of the v1 F1 regression (0.718→0.403), the abstract's
central headline numbers would need a fundamental rewrite, not a
find-and-replace, if the checkpoint were swapped — recommend NOT swapping.**

---

## §RQ1, Table `tab:main_ablation` (lines 283–327)

**Old:** "Precision=1.000, Recall=0.557, F1=0.715, FPR=0.000" (B3 alone);
full-stack "0.688 / 0.983 / 0.565 / 0.718 / 0.023".

**New (if swapped):** B3 alone: Acc 0.469 / Prec 1.000 / Rec **0.242** / F1
**0.390** / FPR 0.000. Full stack: Acc 0.471 / Prec 0.963 / Rec **0.255** /
F1 **0.403** / FPR 0.023. Rows 1–2 (B1 only, B1+B2) unchanged (checkpoint-
independent, verified 0/10,000 decisions differ).

**Fig `fig_confusion`, `fig_per_family`**: regenerate from
`UPDATED_FIGURES/fig_confusion_updated.png`, `fig_per_family_updated.png` if
swapping (per-family recall drops broadly, not just in aggregate — see
`b3_eval/v25_finetune/results/ablation_rerun_comparison.json` for exact
per-family numbers).

## §RQ2 (lines 329–343), Fig `fig_transitions`

**Old:** "Binary F1 improves marginally, 0.715→0.718 (McNemar
p=3.06e-29)... 1,713 real decision changes... 1,585 (92.5%) Caution→Reject."

**New:** Needs full recomputation on the new checkpoint's config-4/5 pair
(not done in this pass — three-way transition analysis was deprioritized
behind the headline-metric recompute; `analyze_ablation_rerun.py` currently
only reports the binary McNemar/Cohen's h old-vs-new, not the new
checkpoint's own internal config4-vs-5 three-way breakdown). If swapping,
this three-way analysis must be rerun before publishing this subsection.

## §Layer Ablation (lines 345–353), Table `tab:full_ablation` (App., line 862)

Same source data as RQ1 — auto-updates with the table above. Fig
`fig_ablation_summary`: `UPDATED_FIGURES/fig_ablation_summary_updated.png`.

## §RQ3 (VeReMi kinematic, lines 355–362) — NO CHANGE

B3 contributes exactly 0 to this benchmark under either checkpoint
(kinematic-only content, no text field). **Not touched, correctly.**

## §RQ4/RQ5, Table `tab:coverage` (lines 364–399)

**Old:** "kinematic-attacker vehicles are detected at 90.3%, semantic-attacker
vehicles at 70.3%".

**New:** Cannot be filled in with a directly comparable absolute number —
this session could not reproduce the manuscript's exact per-vehicle
aggregation methodology (see `UPDATED_TABLES.md` §2 for the full disclosure).
Using this session's own consistent methodology: semantic recall
83.8%(msg)/94.0%(sender) → **69.0%/92.5%**; kinematic recall unchanged
(86.9%/100%). **Before editing this table, the original 70.3%/90.3%
methodology should be located or the table re-derived from scratch with a
documented method** — do not silently substitute this session's numbers for
the published ones without noting the methodology change.

## §Calibration/Robustness/Latency (lines 411–460)

**Old:** "T=2.145 reduces ECE from 0.0619 to 0.0280... ROC AUC=0.747 (ROC),
AUC=0.911 (PR)... instruction-hiding and role-confusion... 100% over-defense
rate... latency averages 110ms."

**New (if swapped):** ROC-AUC **0.956**, PR-AUC **0.985** (both improve —
ranking quality is better). ECE/Brier by this session's proxy measure
**worsen** (0.365→0.539 ECE-proxy) — **the exact T=2.145-style refit
procedure was not rerun on v1 in this pass** (out of scope: recalibrating
production thresholds/temperature was explicitly excluded by this task's
rules) — a proper refit is needed before this paragraph could be rewritten
with a new T value. Robustness battery (11-family, instruction-hiding/
role-confusion 100% over-defense): **not rerun** in this pass (deprioritized;
see `DEPENDENCY_TABLE.md` row 13) — do not edit this sentence without a
rerun. Latency: **unchanged**, verified via `FULL_EVALUATION_REPORT.md`'s
isolated batch=1 benchmark (checked explicitly, no edit needed).

Figs `fig_roc`, `fig_pr`, `fig_calibration`: `UPDATED_FIGURES/fig_roc_pr_updated.png`,
`fig_calibration_updated.png` (AUC values only — the exact reliability-diagram
temperature-refit figure was not reproduced with the paper's exact n=85
val-split methodology; this session's version uses config-4's full n=10,000
with the argmax-confidence proxy, a different but related figure).

## §External Semantic Evaluation, Table `tab:external_eval` (lines 470–500)

**Old:** Accuracy 0.906, Precision 0.976, Recall 0.899, F1 0.936, ROC AUC
0.975, PR AUC 0.981.

**New (if swapped):** Accuracy **0.897**, Precision 0.975, Recall **0.888**,
F1 **0.929**, ROC AUC **0.952**. PR-AUC not recomputed in this pass (only
ROC captured in the rerun harness's output schema; add if swapping). Fig
`fig_ext_roc`: `UPDATED_FIGURES/fig_ext_roc_updated.png`. Fig
`fig_ext_per_family`: not regenerated in this pass (per-family breakdown
available in `b3_eval/v25_finetune/results/paper_reruns/external_eval_results__finetuned.json`
if needed).

**Calibration-transfer sentence** ("Applying B3's existing... T=2.145...
increases ECE from 0.054 to 0.169"): would need a fresh transfer-test rerun
with the finetuned checkpoint's own new temperature (once fit) — not done.

## §Adaptive Attack Evaluation, Table `tab:adaptive` (lines 503–530)

**Old:** "Seeds are the 49 external-corpus messages... ASR 83.7% (41/49)...
avg iterations 4.06/2.90... detection probability round 0/2/10:
1.000/0.592/0.163."

**New (if swapped):** ASR **84.3% (43/51)** — note the seed corpus itself
re-derives to n=51 under this session's live rerun of even the *unchanged*
original checkpoint (see `UPDATED_TABLES.md` §5 for the full disclosure of
this discrepancy versus the committed n=49 artifact). Per-round detection
probability curve, avg iterations, per-family breakdown: **not recomputed**
in this pass (only the aggregate ASR was extracted) — would need
`adaptive_attack/analyze_adaptive_results.py`-equivalent analysis on
`b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__finetuned.json`
before editing this table/figure. Fig `fig_adaptive_confidence`: not
regenerated (needs the per-round analysis first). **The paper's central
claim ("this is the single most serious finding in this paper") is
unaffected either way — ASR is unchanged in aggregate.**

## §CP Full Evaluation, Table `tab:cp_full` (lines 541–560) — NO CHANGE NEEDED

Byte-identical between checkpoints. **Not touched, correctly — confirmed,
not merely assumed.**

## §Baseline Comparison, Table `tab:baselines` (lines 568–600)

**Old:** "B3, banded: recall 0.557... 0.747 [ROC-AUC]"; "B3, strict label:
... recall 0.184"; "0.311/0.715 vs. 0.267... 0.235".

**New (if swapped):** B3's numbers here are read directly from the main
ablation artifact per the paper's own stated convention — they auto-update
to the new checkpoint's config-4/5 numbers above (recall **0.242** banded,
strict-label recall not separately recomputed in this pass — would need the
same strict-argmax slicing `analyze_ablation_rerun.py` doesn't currently
do). **This table's entire "B3 wins the like-for-like zero-shot contest"
conclusion (line 598) is now in question** — B3's recall (0.242 banded)
would need to be re-compared against the zero-shot LLM judge (0.267) and
regex (0.235) baselines; a naive re-read suggests B3 may no longer win this
comparison under the new checkpoint (0.242 < 0.267). **This is exactly the
kind of headline-conclusion-reversing consequence that argues against
swapping the checkpoint without a full, careful re-derivation of this
entire table.**

## §Deployment Feasibility (lines ~606–720), Table `tab:deployment`

**SUMO column**: decisions byte-identical between checkpoints (1765
CAUTION/235 ACCEPT both) — if the manuscript's SUMO numbers derive from this
same message stream, **no change to detection outcomes**, though the
manuscript's own committed SUMO section content was not independently
verified against this session's rerun beyond decision-count parity (out of
scope: the manuscript's exact SUMO table columns were not cross-checked
line-by-line in this pass). Latency: use `FULL_EVALUATION_REPORT.md`'s
isolated benchmark, not this session's contention-confounded SUMO run.

**CARLA column, `tab:carla_scenarios`, all CARLA figures**: **cannot be
updated** — CARLA infeasible in this environment, not rerun, not
fabricated. Any manuscript edit here is blocked pending a CARLA-capable
environment.

## App. §Reproducibility — checkpoint SHA-256

**Old:** references the original checkpoint's SHA-256 (see
`external_semantic_eval/generate_external_figures.py`'s captured
`checkpoint_status()` output, `sha256_16: 9ee7475e08f76ce6`, size
567,622,450 bytes).

**New (if swapped):** finetuned-merged checkpoint SHA-256 prefix
`b3a85943127fa4c7`, size 567,598,552 bytes (from
`b3_eval/v25_finetune/results/paper_reruns/external_eval_results__finetuned.json`
manifest). Architecture/param-count text is unchanged (141.9M params,
confirmed in `FULL_EVALUATION_REPORT.md` §6). A new subsection describing
the LoRA continuation-training run (rank 16, α=32, dropout 0.05, 6 encoder
layers, 1,919,234/143,815,684 trainable params) should be added, drawing
directly from `FULL_EVALUATION_REPORT.md` §1.

## App. §Semantic Transformation Engine — Worked example (line 892)

**Old:** "B3 -- label=MALICIOUS, confidence=0.699, risk_level=medium...
Dempster combination: conflict K=0.321, fused mass m_A=0.14, m_{Ā}=0.38,
m_Θ=0.48, pignistic trust_score=0.381. Final decision: REJECT."

**New (if swapped):** confidence **0.9895**, risk_level **high** (not
medium) — this crosses into the B1-pass+B3-high→REJECT band directly
(`trust_engine/policy.py`'s `semantic_high_confidence=0.85` cutoff), which
changes the fusion-mass narrative structurally (the paper's specific mass
values are for the *medium*-band case; the high-band case follows a
different code path per the policy's own documented rule "B1 pass + B3 high
-> REJECT (semantic override)"). **This paragraph needs a full rewrite, not
a number substitution**, if the checkpoint is swapped — the pedagogical
point ("only the content-reading layer disagrees") still holds, but the
specific mechanism illustrated (graded medium-confidence fusion) would need
a different example, since the new checkpoint answers this specific message
with high, not medium, confidence.

Worked example 2 (`hazard_suppression`, confidence=0.569): **not
reproduced** — exact text not quoted in the manuscript, only paraphrased;
cannot be re-run without guessing. If the checkpoint is swapped, this
example would need to be re-selected/re-verified from scratch.

## §Discussion, §Conclusion, §Limitations (Category A/B mixed, lines throughout)

Every prose sentence summarizing the numbers above inherits that number's
status. Given the scale of the v1/mixed-threat/v2/external regressions
found in this pass, **most of the Discussion/Conclusion's positive framing
of B3's semantic-detection capability would need to be substantially
softened or reworked if the checkpoint were swapped** — not a mechanical
find-and-replace. This is the strongest single reason, beyond the raw
numbers, to prefer the recommendation in `REGRESSION_REPORT.md`: adopting
the new checkpoint changes the paper's *narrative*, not just its numbers.

## §Limitations — narrative-indirection gap, robustness weaknesses, adaptive-attack severity

Direct restatements of RQ1/robustness-battery/adaptive numbers above — same
edit status as those sections (RQ1: needs edit if swapped; robustness
battery: not rerun, cannot yet edit; adaptive: ASR unchanged, minimal edit
needed).

## Everything else (Related Work, Problem Statement, Proposed Architecture,
## Theoretical Properties, Methodology, App. Fusion Constants, App. Training
## Data Provenance's existing text, App. Statistical Methodology, App.
## External corpus construction/leakage check)

**No change** — these are architectural/methodological/proof text
independent of B3's specific weights, correctly excluded from this pass
per `DEPENDENCY_TABLE.md`'s Category C rows.
