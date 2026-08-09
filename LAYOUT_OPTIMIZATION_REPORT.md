# Layout Optimization Report

No experiment was rerun, no numerical value was changed, no equation was removed, and no scientific claim was weakened. Every change below is a float removal (with content preserved as prose), a table merge, an equation-environment consolidation, or a verification that existing float placement is already IEEE-safe. Word count dropped from 12,135 to 11,538 words (a further 4.9% reduction) purely as a side effect of removing float/caption overhead -- no sentence in surviving prose was cut for length alone.

## Starting point

8 figures, 9 tables, 3 separate `equation` environments, 1 `algorithm` environment already removed in the prior pass. Per-turn instruction: get to 6 figures / 4-5 tables through layout optimization, not further sentence compression.

## Final counts (mechanically verified via `scratch_latex_audit.py`)

**6 figures, 5 tables** -- both at the requested targets, confirmed by the audit's `fig labels 6` / `tab labels 5` output.

## Task 1 -- Every figure audited, 2 removed

| Figure | Essential? Unique to a paragraph? | Verdict |
|---|---|---|
| `fig_architecture` | Yes -- the only diagram of the full pipeline structure | **Keep** |
| `fig_boundary_schematic` | No -- a fully abstract, message-independent schematic of the same "traditional accepts / STBV rejects" mechanism that `fig_whyfail` (kept) shows concretely with real trust scores on a real message | **Removed.** Content preserved as one sentence of prose (the two 4-stage chains, written left-to-right in text) immediately before the running example, which already forward-references `fig_whyfail` for the concrete instance. |
| `fig_whyfail` | Yes -- the only figure with a real, traceable trust-score comparison on an actual message; a paragraph cannot show the parallel decision-chain layout as legibly | **Keep** |
| `fig_layer_responsibility` | Yes -- a genuine qualitative synthesis across three separate tables (ITE-Bench, v2.5b, CARLA), not a single table's numbers replotted | **Keep** |
| `fig_v25b_confusion_grid` | Yes -- raw TP/FP/FN/TN counts not present in any surviving table | **Keep** |
| `fig_v25b_roc` | Yes -- a full operating-range curve; a single AUC number in a table cannot show curve shape | **Keep** |
| `fig_sumo_stage` | Yes -- a 3-panel timeline/stage-breakdown/throughput figure with no tabular equivalent | **Keep** |
| `fig_architecture_glance` | No -- its own original caption stated "no new measurement was made to build this summary" and every cell cited a number already in a surviving table; it visualized Table~\ref{tab:ite_ablation}/\ref{tab:v25b}/\ref{tab:veremi} a second time | **Removed.** Content preserved as one closing sentence in Future Work (the four threat-class → layer → evidence → decision mappings, stated as one traceable chain in prose, each fact still individually verifiable in Table~\ref{tab:ite_ablation}). |

Result: 8 → 6 figures.

## Task 2 -- Every table audited, 4 removed via inlining/merge (9 → 5)

| Table | Action | Why safe |
|---|---|---|
| `tab:notation` (12-symbol lookup table) | **Removed, inlined.** Every symbol was already independently defined in the surrounding prose (the table was a pure duplicate index); the notation is now given as one compact inline list ("frame of discernment $\Theta$..., score $s$..., mass function $m(\cdot)$...") at the start of the Trust Decision Engine subsection, per the explicit instruction to inline notation where practical. | No symbol, equation reference, or definition was dropped -- every row's content is now a clause in running text. |
| `tab:trustboundary` (4-row running-example table) | **Removed, inlined.** A 3-column, 4-row table reporting one message's PKI/MBD/CP/B3 results is exactly the "tiny table" the instructions target; the same four facts are now one sentence in the Running Example paragraph. | Same four facts (PKI/B1 valid, MBD consistent, CP vacuous, B3 malicious 0.984), same wording style, zero information loss. |
| `tab:adaptive` (2-row table: ASR, detection probability) | **Removed, inlined.** A 2-row, 1-column-of-data table; the same two numbers are now a clause in the Adaptive Attack Evaluation paragraph. | Both numbers (21.6% ASR; 1.000/0.922/0.784 detection probability) preserved exactly. |
| `tab:v25b_ablation` (5-row pipeline-configuration table) | **Merged into `tab:v25b`.** Both tables report STBV-Bench v2.5b metrics on the identical checkpoint with the same Acc./Prec./Rec./F1 columns; merged into one table with two row-groups (`Checkpoint progression, direct classifier` and `Pipeline configuration, current final checkpoint`), sharing one caption, one float, one dagger-note. | Same benchmark ($n{=}10{,}098$), same checkpoint, structurally compatible columns (only the final column differs: ROC AUC vs. FPR, each kept in its own row-group) -- a legitimate table merge, not a forced one. Every cross-reference to the old `tab:v25b_ablation` label was updated to `tab:v25b`. |

All 5 remaining tables (`tab:ite_ablation`, `tab:v25b` [merged], `tab:veremi`, `tab:carla`, `tab:complexity`) were re-checked against "does this duplicate text nearby" and retained -- each reports a distinct experiment's real per-configuration or per-attack numbers not restated in full elsewhere.

## Task 3 -- Float placement audit

Checked every `\begin{figure}`/`\begin{table}` placement specifier: **all 5 figures and all 5 tables already use `[t]`** (the one `figure*` also uses `[t]`), the IEEE-safe, standard top-of-column/page placement -- no `[h]`, `[!ht]`, or other non-standard override was present or introduced. No margin, font size, or conference-formatting rule was touched, per instruction. No manual `\vspace` spacing hacks were introduced; a scan for consecutive blank lines (a common source of unintended extra vertical space in LaTeX source) found none in the source.

## Task 4 -- Equation compression

The conflict-mass equation (Eq.~\ref{eq:conflict}) and the Yager combination equation (Eq.~\ref{eq:yager}) -- previously two separate `equation` environments with a full paragraph of prose between them -- were combined into a single `align` environment with both labels preserved, eliminating one equation-float's worth of surrounding vertical spacing (IEEE/amsmath-standard `align`, not a spacing hack). The basic-belief-assignment equation (Eq.~\ref{eq:bba}) was left as its own environment: it is introduced and explained as a distinct concept (mass assignment) before conflict/combination are discussed, and merging it in would have required either moving text or displaying an equation before its motivating sentence -- both of which would cost clarity, not just space, in the way the instructions explicitly guard against. Every equation number and every piece of mathematical content is unchanged.

## Task 5 -- Architecture section visual footprint

No additional subsections were removed this pass (already reduced from 10 to 4 in the prior structural-compression pass). The one remaining reduction available without cutting technical content was the `fig_boundary_schematic` removal above (Task 1), which was itself inside the Architecture section and was its second-largest visual element after `fig_architecture`. No diagram's node count, box count, or content was reduced -- `fig_architecture`, `fig_whyfail`, and `fig_layer_responsibility` are pixel-for-pixel unchanged.

## Task 6 -- Results duplication check

Re-verified after the table merge that every result now appears in exactly one place: the `tab:v25b`/`tab:v25b_ablation` merge was the one remaining case where two tables reported overlapping-but-distinct metrics on the same benchmark; after the merge, no metric is reported in two different floats. Cross-references (`Table~\ref{tab:v25b}`'s dagger note, the confusion-matrix figure caption, the ROC/PR figure caption, and all in-text mentions) were updated to point at the merged table and verified via the mechanical audit.

## Task 7 -- Page-savings estimate (honest, not compiled)

No LaTeX compiler is available in this environment (`pdflatex` not installed), so this is a structural estimate, not a compiled measurement, exactly as disclosed in the prior structural-compression pass. This pass removed:
- 2 full figure floats (each typically costs roughly a third to half an IEEE two-column page including caption and surrounding float spacing) → an estimated **0.5-0.8 page**.
- 3 small table floats collapsed into inline prose (each costs less than a figure but still a non-trivial fixed amount: caption line, rule lines, float margins) → an estimated **0.3-0.5 page**.
- 1 table merge (2 floats → 1, removing one full caption + top/bottom rule + float-spacing overhead while keeping every row) → an estimated **0.15-0.25 page**.
- 1 equation-environment merge (2 floats → 1) → a minor amount, well under 0.1 page.
- A 4.9% incidental word-count drop from removed captions/table headers (not from cut prose) → roughly **0.1-0.2 page** at this document's density.

**Combined estimate: roughly 1.0-1.7 additional pages saved this pass**, on top of the prior structural-compression pass's estimated 15-20%. Starting from this pass's stated ~15-page baseline, a realistic estimate is **13-14 pages** after this pass -- real progress toward the 11-page target, but very likely still short of it without either compiling against the actual venue template to confirm, or a further round of float/layout work (e.g., considering whether `fig_v25b_confusion_grid` and `fig_v25b_roc` could be combined into one two-panel figure, which was not done this pass because it was not clearly requested and risks conflating two distinct evaluation questions -- confusion behavior vs. discriminative quality across thresholds -- into one panel). This shortfall is stated plainly rather than inflated, consistent with this project's standing rule never to overstate a reduction.

## Confirmation

No experiment was rerun. No number, equation, or table value was changed. No scientific claim, proposition, or novelty statement was weakened -- every relocated fact is verifiably identical to its pre-edit source. Mechanical LaTeX audit, re-run after all edits: 0 broken references, 0 duplicate labels, 0 missing citations, figure count 6, table count 5, all cross-references resolve to the merged/renamed labels correctly.
