# Attack-Family Analysis

(`FINAL_ATTACK_ANALYSIS.md` is the same document under the other name requested in this pass's two overlapping instruction sets -- not duplicated to avoid two files silently drifting out of sync.)

All numbers below are computed directly from real per-sample decision logs, current final checkpoint, no fabrication.

## STBV-Bench v2.5b, Full STBV Framework, 13 real attack families

| Attack family | $n$ | Recall (flagged) | False negatives |
|---|---|---|---|
| false_clearance | 450 | 1.000 | 0 |
| priority_manipulation | 413 | 1.000 | 0 |
| cross_source_contradiction | 413 | 1.000 | 0 |
| authority_override | 405 | 1.000 | 0 |
| fabricated_consensus | 404 | 1.000 | 0 |
| context_inversion | 399 | 1.000 | 0 |
| role_confusion | 399 | 1.000 | 0 |
| narrative_poisoning | 392 | 1.000 | 0 |
| indirect_prompt_injection | 386 | 1.000 | 0 |
| instruction_hiding | 421 | 1.000 | 0 |
| sensor_discreditation | 438 | 0.998 | 1 |
| goal_manipulation | 438 | 0.998 | 1 |
| traffic_efficiency_lure | 406 | 0.990 | 4 |

**Why this is not presented as a heatmap.** Recall ranges 0.990-1.000 -- real, computed, non-fabricated, but visually indistinguishable at heatmap color-scale resolution (this is exactly the "all-green chart" failure mode the request explicitly asked to avoid). Fig.~`fig_attack_family_v25b` instead plots (A) this recall column at a zoomed x-axis (0.97-1.002) so the real, small differences are visible, and (B) raw false-negative counts, which is the genuinely differentiating signal: 10 of 13 families have zero false negatives; 3 have 1, 1, and 4 respectively.

**Requested attack-family taxonomy vs.\ what the benchmark actually contains.** The request lists 20 example family names (Instruction Injection, Context Manipulation, Goal Manipulation, Hazard Suppression, Authority Override, Infrastructure Semantic Manipulation, Planner Manipulation, Mixed Semantic Attacks, Indirect Prompt Injection, Temporal Context Drift, Cross-Source Contradiction, Priority Manipulation, False Clearance, Collaborative Semantic Agreement, Behavioural Manipulation, Replay/Timing, Certificate/Signature, Message Forgery, Kinematic Inconsistency, Trajectory Manipulation). STBV-Bench v2.5b's actual 13 families (table above) overlap substantially but use this project's existing, already-audited taxonomy names (e.g., `goal_manipulation`, `authority_override`, `false_clearance`, `context_inversion`, `narrative_poisoning`, `indirect_prompt_injection`, `cross_source_contradiction`, `priority_manipulation` match directly; `instruction_hiding` corresponds to the request's "Instruction Injection"; `role_confusion` and `fabricated_consensus` correspond to "Mixed Semantic Attacks"/"Collaborative Semantic Agreement"). Per the request's own instruction ("do NOT invent a benchmark... use attack families already used throughout this project whenever possible"), the real, existing family names were used rather than renamed to match the request's example list, since renaming real data labels to match a suggested vocabulary would itself be a form of data alteration.

## ITE-Bench: communication/behavioral/certificate/kinematic families, Full STBV Framework

Per-family recall on ITE-Bench's B1-native and B2-native families is uniformly **1.000** for all 21 families under the Full STBV Framework (verified directly from `ite_bench/results/ite_config_5.csv`) -- this is expected and already the paper's headline ITE-Bench finding (Table `tab:ablation`; McNemar $\chi^2{=}3883$/$2705$, both $p{<}10^{-15}$), not a new result. A flat-1.000 heatmap here was correctly avoided in the existing manuscript by reporting the aggregate per-class recall (Communication/Behavioral/Semantic, Table `tab:ablation`'s predecessor) rather than a 21-family grid of identical values, consistent with this pass's instruction to avoid meaningless heatmaps -- no new figure was built for ITE-Bench per-family data since every value is identical and a heatmap of 21 identical cells would violate the request's own stated constraint.

## What was NOT generated this pass, and why

A grouped bar chart comparing v2.5b and ITE-Bench per-family recall side-by-side was considered and not built: the two benchmarks' family taxonomies do not overlap (v2.5b is semantic-only; ITE-Bench's semantic families are a strict subset used only to validate B3's contribution, already covered by Table `tab:ablation`), so a combined chart would either show 13 disjoint semantic bars next to 21 disjoint crypto/behavioral bars with no meaningful shared axis, or would need fabricated alignment between unrelated categories -- judged not to add real information beyond Fig.~`fig_attack_family_v25b` (v2.5b) and Table `tab:ablation` (ITE-Bench aggregate).
