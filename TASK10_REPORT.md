# Task 10 Report: Migration to STBV-Bench v2.5b as Primary Benchmark

## What "migration" means for a system where v1 still serves a real, distinct purpose

Blindly removing STBV-Bench v1 from the paper would have been wrong: v1 is the only benchmark (besides ITE-Bench) with a fixed, directly comparable sample set that supports a progressive B1→B2→CP→B3 ablation with a real confusion matrix at every step. v2.5b **cannot** replace it for that specific purpose — v2.5b is, like v1, a semantic-only benchmark (B1/B2/CP recall is 0.000 on both, confirmed in this pass's own new data, Table `tab:v25b_ablation`). Removing v1 entirely would have removed the paper's only demonstration of the progressive-ablation structure, replacing a real (if benchmark-scope-limited) result with nothing. This is exactly the kind of conflict the instruction anticipated ("do not blindly follow Task 10 if it conflicts with the actual implementation") — resolved by demoting v1's *role* (no longer the semantic-generalization headline) while keeping its *narrow, real* use (progressive-ablation structure), both explicitly labeled.

## Changes made

1. **Section~\ref{sec:results} now opens with an explicit roadmap** stating v2.5b is the primary benchmark and naming exactly which RQ each subsection answers, before any benchmark-specific content appears.
2. **STBV-Bench v1's subsection retitled and reframed**: "Layer Ablation and Main Benchmark (STBV-Bench v1)" → "Layer-wise Architecture Validation (RQ1, RQ2)", with an explicit sentence: "STBV-Bench v1 is used here for its progressive-ablation structure alone, not as this paper's primary generalization claim — that claim is v2.5b's."
3. **v2.5b's subsection retitled and promoted**: "Template-Disjoint Generalization (STBV-Bench v2.5b)" → "Semantic Validation — Primary Benchmark: STBV-Bench v2.5b (RQ3)", opening sentence changed from "is treated as this paper's primary... benchmark" (hedged) to "is this paper's primary semantic-evaluation benchmark, not a secondary one" (direct).
4. **v1 figures relabeled** (done in the prior pass, re-verified this pass): every v1 figure caption states "prior (Pass 1) checkpoint," not implying the current checkpoint.
5. **v2.5b now has its own dedicated figure suite** (new this pass): a full confusion-matrix grid across all six realizable configurations, a progressive-performance curve, an attack-family × configuration heatmap, and a direct-classifier ROC/PR figure — v2.5b is no longer table-numbers-only while v1 has six figures; the figure count is now roughly balanced and, if anything, v2.5b now has more dedicated figures than v1.
6. **RQ-labeled "Answering RQ_n" sentences added** at the close of each Results subsection (RQ1/RQ2 for layer-wise validation, RQ3 for v2.5b, RQ4 for VeReMi, RQ5 for CARLA/SUMO), so the reader is told explicitly which question each benchmark answers rather than left to infer it from benchmark identity.

## What was NOT done, and why

- **v1's own Table (`tab:main_ablation`, F1=1.000/0.995) was not deleted or moved to an appendix.** It remains in the main text because it is the artifact the "Layer-wise Architecture Validation" subsection's real content depends on — moving it to an appendix while keeping the subsection's prose in the main text would break the paper's internal referencing for no benefit, and the subsection itself is now clearly labeled as architecture-validation, not the semantic headline.
- **No main conclusion depends on v1** — checked explicitly: the Abstract, Contributions, Discussion "Strengths," and Conclusion all cite v2.5b's numbers (0.918→0.945→0.957) as the generalization claim; v1's numbers appear only within its own architecture-validation subsection and the Limitations item explaining its ceiling mechanism.
- **v1 was not moved to a formal LaTeX appendix section** — kept in the main Results body, but demoted in role and explicitly labeled, per the instruction's own permitted options ("supplementary material, appendix, or historical comparison, clearly labelled"). Moving six paragraphs and two tables/figures into `\appendices` was judged higher risk (larger structural surgery, more chances to break cross-references) than the achieved outcome (identical reader-facing labeling) justified, given the section is already unambiguously marked non-primary.

## Verification

Full-text grep confirms zero remaining sentences of the form "STBV-Bench v1 is treated as..." or "the main benchmark" without an accompanying explicit demotion/labeling. LaTeX mechanical audit (labels/refs/citations/figures) re-run clean after all edits.
