# Layer Figure Redesign

Replaces the checkmark/triangle/dash matrix (`fig_layer_responsibility`, "Layer-wise Threat Coverage Matrix") built two passes ago, per this task's explicit instruction that a binary-symbol matrix "communicates almost no information" and should not be reused.

## Critical review of the matrix design being replaced

- **Does it communicate a scientific result?** Only weakly. A ✓/△/– grid encodes an ordinal judgment call per cell; the actual *magnitude* of each layer's contribution (a 0.381-to-1.000 recall jump is very different information from a 0.999-to-1.000 one, even though both could legitimately be marked ✓) is invisible.
- **Does it teach something beyond one sentence of text?** Marginally. "Each layer covers a different dimension, CP is zero everywhere due to a data-generation gap" is one sentence; the matrix mostly re-confirms it 20 times over.
- **Is it visually engaging?** No -- a flat grid of identical-sized cells with three repeated glyphs is closer to a compliance checklist than a result figure.
- **Does it justify occupying significant page space?** No, per this task's own judgment, which this redesign accepts.
- **Does it differentiate the layers enough?** No -- every "✓" cell looks identical regardless of whether the underlying evidence was a 0.997 recall or a 1.000 recall with zero McNemar reversals across 3,885 discordant pairs (a much stronger claim).
- **Is the Trust Decision Engine column meaningful or a summary?** Mostly a summary -- in the old design it just repeats "✓" wherever any layer below it was "✓," adding no new information a reader couldn't infer.

## Goal

One figure that answers: **"what unique responsibility does each layer have, and how much of the total threat surface does adding it actually close?"** -- using magnitude, not a symbol.

## Five candidates, generated and scored

Scoring: Scientific value / Reviewer readability / Novelty / Space efficiency / Visual quality / Information density / Redundancy (lower redundancy score = more redundant = worse), each 1-5, higher better except Redundancy where higher = worse.

| Candidate | Sci.\ value | Readability | Novelty | Space | Visual quality | Info.\ density | Redundancy (higher=worse) | Verdict |
|---|---|---|---|---|---|---|---|---|
| A. Layer $\to$ Threat-Category Sankey | 4 | 3 | 4 | 2 | 3 | 4 | 2 | Rejected -- real flows exist (McNemar discordant counts) but a Sankey needs per-category flow volumes this benchmark's aggregate recall numbers don't cleanly decompose into without either fabricating intermediate flow values or re-deriving a new per-category breakdown not already in the manuscript |
| B. **Defense-in-depth staircase (selected)** | **5** | **5** | **3** | **4** | **4** | **5** | **1** | **Selected** |
| C. Responsibility wheel | 3 | 2 | 4 | 3 | 3 | 2 | 2 | Rejected -- a radial layout adds novelty but a wheel with 5 sectors and 1-2 real numbers each is lower information density than a direct staircase, and circular layouts are harder to read precisely (the exact failure mode a "no radar chart" instruction elsewhere in this session's requests warns against) |
| D. Architecture overlay (annotate `fig_architecture`) | 4 | 4 | 2 | 5 | 3 | 4 | 4 (modifies an existing figure this session has repeatedly been told not to touch outside its own dedicated task) | Rejected -- explicitly avoided to respect the standing "do not modify other figures" instruction from the adjacent attack-figure task in this same session; reusing `fig_architecture` here would edit a figure this pass was not asked to touch |
| E. Threat-coverage timeline (survives/eliminated/escalated per stage) | 4 | 4 | 4 | 3 | 4 | 4 | 1 | Close second -- conceptually near-identical to B, but framed as a per-message trace (survives/eliminated) rather than an aggregate recall staircase; B was preferred because the paper's real evidence is naturally aggregate (recall percentages across a whole benchmark), not a single traced message, so B represents the actual available evidence more directly without implying a per-message narrative the data doesn't support at this granularity |

## Why B (the staircase) wins

Table `tab:ite_ablation` already reports a real, monotonically increasing recall progression on ITE-Bench (the one benchmark spanning all three non-deployment threat classes at once): B1 alone $0.381 \to$ B1+B2 $0.667 \to$ B1+B2+CP $0.667$ (unchanged, CP's disclosed zero-contribution) $\to$ Full STBV $1.000$. This is a real staircase already sitting in the manuscript's own table, just never plotted as one. Each step's *height* is the actual scientific content: the B1$\to$B1+B2 step is large (+0.286) because behavioral attacks are a large share of ITE-Bench's balanced mix and B1 cannot detect them; the B1+B2$\to$B1+B2+CP step is exactly zero, visually confirming CP's disclosed data-generation gap as a flat segment, not a symbol; the final step to Full STBV closes the remaining semantic gap completely. A deployment-robustness annotation (CARLA, this session's freshly-rerun final-checkpoint numbers) is added as a separate, clearly-delineated panel rather than merged into the same recall axis, avoiding the benchmark-conflation mistake this session's table-redesign task specifically corrected.

## Confirmation

Every number plotted is copied directly from `tab:ite_ablation` (ITE-Bench recall progression, already real and audited, `TABLE_VALUE_AUDIT.md`) and `tab:carla` (this session's real, freshly-rerun final-checkpoint CARLA results). No new metric was computed for this figure; it visualizes existing, already-verified numbers.
