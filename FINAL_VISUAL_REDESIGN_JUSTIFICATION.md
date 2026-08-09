# Final Visual Redesign — Reviewer Justification

Reviewer-style critique of both redesigns, applied after building them, not before, per this task's Part 3.

## Attack-family/category figure (fourth version across this session)

- **Does it occupy justified page space?** Yes -- it is one compact panel (down from two in the immediately preceding version), and it is the only figure in the manuscript showing distribution shape rather than a summary statistic.
- **Does it answer a scientific question?** Yes: "which categories contain individually ambiguous messages, and how many?" -- answerable by eye from the outlier-point density per category, not inferable from Table III's aggregate recall alone.
- **Does it communicate the novelty?** Indirectly but genuinely: it is the concrete evidence for the Trust Decision Engine's floor-rule design (Section IV) -- showing *why* a Caution state is necessary (real, visible per-message ambiguity within otherwise near-ceiling categories), not just asserting it.
- **Can it be simplified further?** Considered and rejected: collapsing to a single number per category (as the two prior versions did) was the exact failure mode this task's third request identified. A boxplot with real outlier points is close to the minimum representation that still shows distribution shape, which is the information this pass established is the only genuinely differentiating signal left in this benchmark's data (`ATTACK_VISUALIZATION_REDESIGN.md`, Step 1).

**Verdict: no further iteration performed. This is the version retained.**

## Related-work table

- **Does it occupy justified page space?** Yes -- a single-column table (7 prior-work rows + 1), narrower than a full-width table, fits without crowding the two-column layout.
- **Does it answer a scientific question?** Yes: "what does each prior direction address, and what is specifically missing that this paper closes?" -- the Primary Limitation column makes this the table's literal content, not an inference left to the reader.
- **Does it communicate the novelty?** This was the primary goal, and is now structurally guaranteed rather than argued in prose: STBV is the only row with all five capability columns fully addressed (\CIRCLE\ in every column), immediately visually distinct from every row above it without needing to read the Primary Limitation text at all -- the text then explains *why* in one glance for a reader who does look.
- **Can it be simplified further?** Considered merging Coop.\ Perception into the MBD row (both behavioral-adjacent) -- rejected: they have genuinely different real limitations (MBD: no cross-layer trust; CP: no semantic reasoning) and Section II's existing prose already treats them as distinct citations, so merging rows would create a table/prose mismatch.

**Verdict: no further iteration performed.**

## What was NOT done, disclosed

- The related-work table is genuinely new (no such table existed before this task; `RELATED_WORK_TABLE_REDESIGN.md` Step 1 states this plainly rather than fabricating a "before" version to critique).
- `\usepackage{wasysym}` was added for the \CIRCLE/\RIGHTcircle/\Circle symbols; this could not be compile-verified in this environment (no `pdflatex` available, a standing constraint throughout this session) -- `wasysym` is a standard, near-universally-available LaTeX package (part of the default TeXLive/MiKTeX collection), a low-risk addition, but flagged here rather than silently assumed to compile cleanly.
- The mechanical label/reference audit (`scratch_latex_audit.py`, which checks labels, references, citations, and figure-file existence but does not compile LaTeX) is clean: 0 broken references, 0 duplicate labels, all 23 citation keys resolve, table count 7 (was 6, +1 for the new related-work table).

## Confirmation

No metric was changed anywhere in either redesign. Every number in the attack-category figure is a real per-message B3 confidence score from `config_5.csv`. Every capability claim in the related-work table is consistent with what Section II's existing prose already says about each cited work; no citation was invented and none of the 12 real prior-work references were misrepresented to make the comparison more favorable.
