# Attack Figure Selection

Why the chosen design (mean confidence + std.\ dev.\ error bars, sorted; false-negative counts) is better than the recall chart it replaces.

## Recall, rejected

CV = 0.0027 across 13 families (`ATTACK_METRIC_ANALYSIS.md`). A chart of 13 bars all within 1 percentage point of each other communicates "recall does not collapse for any family," which is one sentence, not a figure -- and is already stated as the aggregate Table III number (Rec.\ 0.999).

## Mean confidence + within-family std.\ dev., selected

Mean confidence alone has CV=0.023 -- real, but modest. Its own standard deviation (how spread out individual messages' confidence scores are *within* a family) has CV=1.05, the single most discriminative real metric found in Step 2's sweep. Rendering both together, as an error-bar plot, gives a reviewer two real facts per family in one panel: (1) where the family's typical confidence sits, and (2) whether that family is uniformly easy (tight error bar) or contains a meaningful fraction of borderline messages (wide error bar) even when its aggregate recall still rounds to 1.000. This is the paper's own root-caused finding restated visually, not a new claim: Section V-B already states the architecture's residual cost is concentrated in confidence/calibration interactions, not raw miss rate -- this figure is the first place that finding is shown per-family rather than only in aggregate.

## False-negative counts, retained

Real, concrete, already correctly identified as the one genuinely differentiating count-based signal in the prior version of this figure -- kept unchanged in content, only visually tightened (Step 5 styling requirements) alongside the new Panel A.

## What was considered and rejected

- **Per-family precision / FPR / false-positive count**: not computable -- v2.5b has no benign sub-families (`ATTACK_METRIC_ANALYSIS.md`). Not fabricated to fill this gap.
- **ROC/calibration-error per family**: would require re-binning per-family confidence scores against a reliability curve, a genuinely new per-family metric not already reported anywhere in the manuscript's text; using it here without first establishing it as a validated methodology elsewhere in the paper risked exactly the "invented metric" this task prohibits. Not built.
- **Trust Decision Distribution / layer contribution per family**: on v2.5b, only B3 produces family-attributable evidence (B1/MBD/CP structurally contribute zero on this semantic-only benchmark, established in Table II's benchmark-scope footnote) -- a "layer contribution per family" chart on this benchmark would have 12 of 13 families showing 100% B3 attribution by construction, not a real per-family difference to plot.

## Confirmation

Both panels' data come directly from `config_5.csv`'s `raw_score` field (B3's real calibrated $P(\text{malicious})$ per message) and `decision` field -- no manual entry, no interpolation, no smoothing.
