# STBV-Bench Human Validation — Report

> ## ⚠ STATUS: AWAITING HUMAN ANNOTATION — NO RESULTS IN THIS REPORT
>
> Every agreement and validity number below is a **PLACEHOLDER**. No
> annotations have been collected, and this pipeline does not and will not
> generate them. Do **not** cite any figure from this file until it has been
> regenerated from real completed annotator files.

## 1. Why this study exists

STBV-Bench's ground-truth labels are assigned by the same seeded generator
that produces the message text. No independent check currently establishes
that a message labelled `malicious` reads as malicious to a competent human
annotator, or that a `benign_control` message reads as benign. Without that
check, a detector "miss" cannot be distinguished from a mislabelled item,
and the benchmark's headline precision/recall inherit that ambiguity.

## 2. Sampling methodology

- **Population:** the 10,000-message slice of STBV-Bench v1 evaluated in the paper.
- **Sample size:** 300 messages.
- **Strategy:** stratified by attack_family, proportional with a floor of 14/family, remainder to largest families; presentation order shuffled to de-correlate family from position
- **Seed:** `20260802` (deliberately distinct from the modelling seed 42).
- **Families covered:** 21 of 21.
- **Malicious prevalence in sample:** 0.9333
- Presentation order is shuffled so annotators cannot infer family from position.

| Attack family | Sampled | Malicious | Benign |
|---|---|---|---|
| `authority_override` | 14 | 14 | 0 |
| `benign_control` | 20 | 0 | 20 |
| `collaborative_semantic_agreement` | 14 | 14 | 0 |
| `context_inversion` | 14 | 14 | 0 |
| `context_poisoning` | 14 | 14 | 0 |
| `cross_source_contradiction` | 14 | 14 | 0 |
| `false_clearance` | 14 | 14 | 0 |
| `goal_manipulation` | 14 | 14 | 0 |
| `hazard_amplification` | 14 | 14 | 0 |
| `hazard_suppression` | 14 | 14 | 0 |
| `indirect_prompt_injection` | 14 | 14 | 0 |
| `infrastructure_semantic_manipulation` | 14 | 14 | 0 |
| `instruction_injection` | 14 | 14 | 0 |
| `mixed_semantic_attacks` | 14 | 14 | 0 |
| `multi_message_context_poisoning` | 14 | 14 | 0 |
| `planner_manipulation` | 14 | 14 | 0 |
| `priority_manipulation` | 14 | 14 | 0 |
| `role_manipulation` | 14 | 14 | 0 |
| `semantic_narrative_poisoning` | 14 | 14 | 0 |
| `temporal_context_drift` | 14 | 14 | 0 |
| `traffic_efficiency_lure` | 14 | 14 | 0 |

## 3. Annotation protocol

1. Two annotators work **independently**, with no communication until both
   submit. Each receives only `item_id` and `message` — never the ground
   truth, the attack family, or the other annotator's file.
2. Task definition given to annotators: *"Does this V2X message attempt to
   manipulate the receiving vehicle's understanding of the situation — e.g.
   fabricating peer agreement, falsely clearing a real hazard, claiming
   authority it does not have, or injecting instructions? Answer `malicious`
   or `benign`."*
3. Optional `confidence` on 1–5; optional free-text `notes`.
4. Neither annotator may consult the generator, its templates, or any
   pipeline output.
5. Disagreements are **not** reconciled before computing κ — the raw
   independent labels are the measurement.

## 4. Results

- **Annotator A:** template present but **0 of 300 labels filled**.
- **Annotator B:** template present but **0 of 300 labels filled**.

| Metric | Value |
|---|---|
| Items annotated by both | *PLACEHOLDER* |
| Percent agreement | *PLACEHOLDER* |
| Cohen's κ | *PLACEHOLDER* |
| κ interpretation | *PLACEHOLDER* |
| Human vs. generator accuracy | *PLACEHOLDER* |
| Human vs. generator precision | *PLACEHOLDER* |
| Human vs. generator recall | *PLACEHOLDER* |
| Items where both humans disagree with generator | *PLACEHOLDER* |

## 5. Limitations (apply regardless of outcome)

- n=300 of 10,000 (3%); per-family cells are small (~14 items), so
  per-family agreement estimates will be wide and should not be
  over-interpreted.
- Two annotators is the minimum for κ; three or more would permit
  Fleiss' κ and majority-vote adjudication.
- Annotators drawn from the project's own domain area are not blind to V2X
  conventions and may share priors with the generator's author, which
  inflates apparent agreement relative to naive annotators.
- κ measures agreement, not correctness. High κ with both annotators
  disagreeing with the generator would indicate a *labelling* problem, not
  an annotation problem — this is precisely the case this study is designed
  to be able to detect.

## 6. How to complete this study

```bash
# 1. Two people independently fill the `label` column (malicious|benign):
#      validation/annotation_template_annotator_A.csv
#      validation/annotation_template_annotator_B.csv
# 2. Regenerate this report from the real annotations:
python validation/agreement_analysis.py
```
