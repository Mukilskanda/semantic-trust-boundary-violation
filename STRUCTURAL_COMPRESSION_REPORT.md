# Structural Compression Report

No experiment was rerun, no numerical value was modified, no equation was changed, no figure was invented, and no scientific claim was weakened. Every change below is a structural move (merge, relocate, delete-and-replace-with-cross-reference) or a genuine restructuring edit at a section/subsection boundary.

## Honest headline result

**Word count**: 13,670 → 12,135 words in the `.tex` source (an 11.2% reduction). **Structural footprint**: figure count 11 → 8 (3 fewer floats), subsection count 18 → 7 (11 fewer headed subsections), one full pseudocode `algorithm` environment removed. **No LaTeX compiler is available in this environment to produce a compiled page count** (`pdflatex` is not installed) -- the page-count figures below are estimates from structural/word-count deltas, not a compiled measurement, and are reported as such rather than asserted as fact.

Word-count reduction alone (11%) does not reach the requested ~35-40% (17→10-11 pages) reduction. However, IEEE two-column page count is driven substantially by float and heading overhead, not word count alone: each removed figure recovers roughly a third to half a column (image + caption + surrounding whitespace), each removed subsection heading recovers a smaller but real fixed amount, and the removed `algorithm` environment (a full pseudocode block with its own float placement) recovered space disproportionate to its word count. Combining the 11% word reduction with 3 fewer figure floats, 11 fewer subsection headers, and one removed algorithm float, a realistic estimate is **15-20% total page reduction** -- plausibly 17 pages to approximately **14-15 pages**, not the requested 10-11. This shortfall is stated plainly rather than inflated: reaching 10-11 pages honestly would require either compiling and iterating against a real page count (not possible in this environment) or a further, more aggressive round of prose tightening and/or additional figure/table consolidation beyond what was done here, which risks touching the DS-theory/architecture explanatory text this pass was instructed to compress by ~50% (already done) but not below the point of intuition-plus-equation, or further shortening the per-layer architecture walkthrough explicitly called out as "the strongest part of the paper" and told not to shorten. Recommendation: compile the current version with the actual `IEEEtran` class/venue template to get a real page count before deciding whether further cuts are needed.

## Original section structure (18 subsections, 10 sections + appendices)

```
Introduction
Related Work (one dense paragraph)
Threat Model
Architecture
  Trust Boundary Analysis
  Why Existing Architectures Fail
  Proposed STBV Trust Architecture
  Why Three Trust Layers?
  Dempster-Shafer Evidence Fusion
  Why STBV Is Different
  Semantic Trust Verification Pipeline (+ Algorithm 1 pseudocode)
  System Assumptions
  Computational Complexity
  Known Failure Modes
Methodology
Results
  Layer-wise Architecture Validation (RQ1, RQ2)
  Layer Contribution Within Each Layer's Own Threat Model (ITE-Bench)
  Semantic Validation -- STBV-Bench v2.5b (RQ3)
  Behavioral and Kinematic Validation -- RQ4 (VeReMi)
  Deployment Validation -- RQ5 (Live CARLA)
  SUMO Deployment Replay
  Adaptive Attack Evaluation
Discussion
Conclusion
Appendices (Reproducibility Summary, Worked Fusion Example)
```

## New section structure (7 subsections, 10 sections + appendices)

```
Introduction (compressed ~20%)
Related Work (3 named themes: Cryptographic / Behavioral / Semantic Trust + 1 gap paragraph)
Threat Model (unchanged)
Architecture
  Trust Boundary Analysis
  Proposed STBV Architecture (merges former "Why Existing Architectures Fail" + the per-layer walkthrough)
  Trust Decision Engine (renamed from "Dempster-Shafer Evidence Fusion," explanatory text compressed ~50%)
  Motivation for Multi-Layer Semantic Trust (merges former "Why Three Trust Layers?" + "Why STBV Is Different")
  [Algorithm 1 removed; pipeline execution now one paragraph]
  [Complexity: one table + one paragraph, no subsection heading]
  [Assumptions + Known Failure Modes: one paragraph, no subsection headings]
Methodology (unchanged, with one added transition sentence from a prior pass)
Results
  A. Layer Validation (ITE-Bench, RQ1)
  B. Semantic Validation (STBV-Bench v2.5b, RQ2)
  C. Deployment Validation (VeReMi + CARLA + SUMO + Adaptive Attack, RQ3--RQ4)
Discussion (RQ5; unchanged structurally, already tight from prior passes)
Conclusion (3 paragraphs: contribution, why it matters, future direction -- no benchmark numbers repeated)
Appendices (unchanged: Reproducibility Summary, Worked Fusion Example)
```

## Every merge performed

| Merged into | Absorbed from | Why safe |
|---|---|---|
| **Proposed STBV Architecture** | "Why Existing Architectures Fail" (full subsection) | Its entire content (the $T_{Decision}{=}0.730$ Accept finding) is now the opening 2 sentences of the architecture walkthrough it directly motivates -- same fact, same number, no longer a separate 5-sentence subsection making the same point before the fix is described. |
| **Trust Decision Engine** (was "Dempster-Shafer Evidence Fusion") | -- (renamed only) | Renamed to match the requested target flow (Threat Boundary → Proposed STBV Architecture → Trust Decision Engine → Novelty); all 3 equations (BBA, conflict, Yager), the notation table, and all 6 propositions are retained verbatim in content. |
| **Motivation for Multi-Layer Semantic Trust** (Novelty) | "Why Three Trust Layers?" + "Why STBV Is Different" | Both asked overlapping "why does this design choice matter" questions from different angles (per-layer question framing vs. architectural-principle framing); merged into one subsection that states each point once. `fig_layer_responsibility` and the DeBERTa-v2 backbone-comparison paragraph (real 5-candidate measurement, unchanged numbers) moved with the Three-Layers content into this merged subsection. |
| **Pipeline paragraph** | Algorithm 1 (full pseudocode block) | The pipeline's control flow (PKI→B1 short-circuit, MBD/B2 crypto-behavioral mass, B3-enabled/disabled branch, Yager fusion, pignistic transform, threshold, floor rules, logging) is now one prose paragraph stating the same execution order and the same two load-bearing branches (B1-fatal short-circuit, vacuous-mass fallback) the pseudocode encoded, with the same grounding claim (direct correspondence to `ISCEPipeline.run()`/`TrustDecisionEngine.decide()`). No algorithmic step was dropped. |
| **Complexity table + 1 paragraph** | "Computational Complexity" subsection (2 paragraphs of prose per-stage complexity + a separate latency paragraph) | Per-stage time complexity, measured latency, and space complexity are identical, real numbers, now in `Table~\ref{tab:complexity}` (Stage / Time / Latency / Memory, exactly as requested) instead of prose; one paragraph retained for the "why B3 dominates" interpretation, which a table cannot state on its own. |
| **1 paragraph (end of Architecture)** | "System Assumptions" (6-item bulleted list) + "Known Failure Modes" (6-item prose list) | Both were reference material -- explicit, stated boundary conditions -- not narrative content; condensing to one paragraph each (still covering every assumption and every failure mode by name) removes two subsection headings and considerable bullet/itemize vertical overhead without dropping a single assumption or failure mode. |
| **Results subsection C (Deployment Validation)** | "Behavioral and Kinematic Validation" (VeReMi) + "Deployment Validation" (CARLA) + "SUMO Deployment Replay" + "Adaptive Attack Evaluation" (4 separate subsections) | All four answer the same two research questions (RQ3: generalization beyond semantic benchmarks; RQ4: realistic deployment) and were sequentially dependent narrative anyway (VeReMi→CARLA→SUMO→adaptive attack, each building on the prior finding). Converted to bold-label paragraphs within one subsection, per the explicit instruction "Reorganize into only four subsections... C. Deployment Validation (VeReMi, CARLA, SUMO)." All tables (`tab:veremi`, `tab:carla`, `tab:adaptive`) and the one figure (`fig_sumo_stage`) are retained unchanged. |

## Every removed subsection (as standalone headings; content relocated, not deleted)

1. Why Existing Architectures Fail → folded into Proposed STBV Architecture (2 sentences)
2. Why Three Trust Layers? → folded into Motivation for Multi-Layer Semantic Trust
3. Why STBV Is Different → folded into Motivation for Multi-Layer Semantic Trust
4. Semantic Trust Verification Pipeline (Algorithm 1) → one paragraph, no heading
5. System Assumptions → part of one combined paragraph, no heading
6. Computational Complexity → one table + one paragraph, no heading
7. Known Failure Modes → part of the same combined paragraph, no heading
8. Layer-wise Architecture Validation (RQ1, RQ2) → already removed in the prior (v2.5b-only) pass; not reintroduced
9. Behavioral and Kinematic Validation (VeReMi) → paragraph inside Results-C
10. Deployment Validation / Live CARLA → paragraph inside Results-C
11. SUMO Deployment Replay → paragraph inside Results-C
12. Adaptive Attack Evaluation → paragraph inside Results-C

## Every removed paragraph (content, not just heading, cut -- because it was a genuine duplicate)

- The original "Why STBV Is Different" subsection's 5 labeled paragraphs (Independent trust estimation / Orthogonal trust dimensions / Confidence-aware evidence fusion / Semantic Trust Boundary as first-class design object / Conservative decision making / Why simply adding another detector) restated, near-verbatim in places, points the merged Novelty section now states once each. This was the single largest genuine duplication found: the "independent trust estimation," "orthogonal dimensions," and "conservative by construction" arguments were each stated twice in the original (once in "Why Three Trust Layers?," once in "Why STBV Is Different") using different phrasing for the same claim.

## Figures removed (2, both explicitly redundant with an adjacent table/figure by their own original captions)

- `fig_ite_coverage`: its own caption stated it showed "the same values as Table~\ref{tab:ite_ablation}, visualized" -- a pure table visualization with no unique information, matching the explicit instruction to remove exactly this class of figure.
- `fig_error_analysis`: its own caption stated it showed "the same FN=6/FP=1,491 split as Fig.~\ref{fig_v25b_confusion_grid}" -- the one unique fact it conveyed (99.6% of errors are false positives) was folded as one clause into `fig_v25b_confusion_grid`'s caption, so no information was lost, only the redundant second chart.
- All 8 remaining figures were re-checked against "what information does this provide that no table can?" and retained: `fig_architecture` (pipeline structure), `fig_boundary_schematic` (mechanism diagram), `fig_whyfail` (a concrete real trace, not a table row), `fig_layer_responsibility` (cross-benchmark qualitative synthesis, not one table's numbers), `fig_v25b_confusion_grid` (raw TP/FP/FN/TN counts not in any table), `fig_v25b_roc` (full operating-range curve, not a single AUC number), `fig_sumo_stage` (3-panel timeline/breakdown/throughput, not table-representable), `fig_architecture_glance` (end-to-end synthesis figure).

## Tables

No table was removed. All 9 tables (`tab:notation`, `tab:trustboundary`, `tab:ite_ablation`, `tab:v25b_ablation`, `tab:v25b`, `tab:veremi`, `tab:carla`, `tab:adaptive`, and the new `tab:complexity`) carry information not otherwise stated in full elsewhere in the main text -- each was checked against "does this duplicate text nearby" and retained.

## Reviewer test (self-applied)

- **Can the contribution be understood in under 15 minutes?** The Introduction (compressed ~20%), Architecture's 4-subsection flow (Trust Boundary → Proposed Architecture → Trust Decision Engine → Novelty), and Results' 3-subsection flow (A/B/C) now form a single, shorter read-path with no repeated explanations of the same idea.
- **Does every remaining section justify its existence?** Yes -- every remaining subsection heading corresponds to a distinct question (a threat, a component, a proof, a motivation, a research question), not a restatement of an adjacent one.
- **Does every figure teach something unique?** Yes, re-verified above; 2 that did not were removed.
- **Does every table provide unique information?** Yes, re-verified above; none removed because none were found duplicative.

## Confirmation

No experiment was rerun. No number, table value, equation, or figure content was changed. No scientific claim, proposition, or novelty statement was weakened -- each was relocated or restated once instead of two-to-three times. Mechanical LaTeX audit (`scratch_latex_audit.py`), re-run after all edits: 0 broken references, 0 duplicate labels, 0 missing citations, figure count 8 (down from 11, both removals justified above), table count 9 (unchanged, 1 net addition offsetting structural consolidation), all cross-references resolve.
