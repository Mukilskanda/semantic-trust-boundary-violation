# Table I Redesign Report

Redesign of `tab:relatedwork` ("Positioning of This Work Relative to Related Literature"), built one pass earlier in this session. No citation was added, removed, or misrepresented; no capability symbol was changed from its previously-verified value (`RELATED_WORK_TABLE_REDESIGN.md` from the prior pass already justified each cell against Section II's prose).

## Step 1: critical review of the version being replaced

- **Every column necessary?** Yes -- C/B/S (the three trust-layer questions), Fus.\ and X-L (two genuinely distinct capabilities: X-L is *this paper's specific formalized gap*, not redundant with Fus., since a work can fuse evidence without ever validating across the inter-layer boundary, e.g.\ Context-Aware Trust).
- **Every row necessary?** Yes, but under-organized -- MBD and Cooperative Perception are both "traditional" V2X mechanisms (the paper's own Architecture section already groups PKI+MBD+CP as "the existing V2X trust stack") but appeared as unrelated flat rows with no visual signal of that shared lineage.
- **Coherent story?** Partially -- readable top to bottom as a rough capability increase, but the *gap* the table is building toward was never stated as its own claim; a reviewer had to infer it from the pattern of empty circles.
- **Communicates WHY novel?** The Primary Limitation column did the real work, but several entries were looser than they needed to be ("No V2X integration or fusion" for LLM-Based Trust conflated two different columns' worth of gap into one clause).
- **Space?** Reasonable, single-column, no overflow risk from the previous version.
- **IEEE TDSC/TIFS/TVT feel?** Close, but the flat, ungrouped row list and generic "Approach"/"Capability" headers read more like a checklist than a Transactions-style comparison table.

## Step 2: header renaming

"Approach" $\to$ "Representative Approaches" (signals these are illustrative citations for a theme, not an exhaustive list -- accurate, since e.g.\ "LLM-Based Trust" represents 4 real citations, not 1). "Capability" $\to$ "Framework Capability" (distinguishes it from "Trust Layer," avoiding the ambiguity of two group headers both implicitly meaning "capability"). "X-L" $\to$ "X-L" retained as the column header (space-constrained) but now spelled out in full ("Cross-Layer Reasoning") in the abbreviations line below the table, per the task's own suggested compromise.

## Step 3: thematic grouping

Traditional Trust (PKI/SCMS, MBD, Cooperative Perception) is now visually grouped under one italic spanning label, with its three member rows indented (`\quad`) -- the only theme with more than one real citation-row, so the only one that benefits from an explicit group header without adding disproportionate height. The other five themes (Context-Aware, Semantic, LLM-Based, Evidence Fusion, plus the new Research Gap and This-Work rows) are each already self-labeled by their own row name, so a separate spanning header for each would have added five extra rows of height for zero new information -- consistent with the task's own conditional instruction ("if grouping improves readability without increasing size").

## Step 4: sharper Primary Limitation column

Every limitation now states specifically why that approach cannot solve the problem STBV solves, tied to the symbol grid rather than restated generically: LLM-Based Trust's limitation is now "No evidence fusion" (directly matching its Fus.\ = \Circle\ cell, not a vaguer "no V2X integration"); Evidence Fusion's is now "No semantic verification" (matching its S = \Circle\ cell). Semantic Trust's is now "No behavioral validation" -- a real, true, and more directly comparable statement than the previous "Trusted-channel assumption" (both are real facts about the cited work; this phrasing was chosen for direct comparability with the other rows' behavioral/semantic framing, per this task's explicit worked example).

## Step 5: the contribution row

Renamed "STBV (This Work)" $\to$ "STBV Framework (This Work)." The claim itself was strengthened from "Unified multi-layer trust validation" to **"First unified comm., behavioral, semantic \& decision-level trust framework for V2X,"** checked against the manuscript before adopting it: Section II's own opening sentence already states "No prior work covers communication, behavioral, semantic, and decision-level trust together," and its closing sentence states "combining all four trust questions with an explicit, provably conservative semantic-verification stage... is [the novel contribution]." The word "First" and the V2X domain-scoping are both therefore already explicit, existing claims in this manuscript's own prose, not new claims introduced by the table -- not an overclaim.

## Step 6: legend

Rewritten from a bare `C=Communication, B=Behavioral, S=Semantic` line into a labeled "Abbreviations:" block spelling out all five columns in full, plus the existing three-symbol legend (\CIRCLE/\RIGHTcircle/\Circle, "Fully/Partially/Not Addressed") retained unchanged -- already grayscale-safe (distinguishable by fill fraction, not color) and already the convention this session's earlier pass selected specifically for that property; no stronger grayscale-safe alternative was found to justify replacing it.

## Step 7: visual hierarchy

Double `\midrule` immediately above the This-Work row (a standard booktabs-compatible way to add emphasis without a new package or color); `\textbf{}` on the entire This-Work row (retained from the prior version); light-gray row shading was considered (`\rowcolor`, via `colortbl`) and **not added**, to avoid stacking a second unverified package addition on top of `wasysym` (added in the prior pass, still not compile-verified in this environment, `FINAL_VISUAL_REDESIGN_JUSTIFICATION.md`) -- bold text plus a double rule already satisfies this task's own "or" framing ("bold row, light gray background, OR thicker separator"), so the lower-risk option was chosen deliberately.

## Step 8: Research Gap row

Added, immediately before This Work, as a `\multicolumn` spanning row with a fixed-width `p{7.6cm}` cell so the sentence wraps rather than overflowing the column: *"No prior framework jointly validates communication, behavioral, and semantic trust while reasoning across the inter-layer boundary itself."* This is one additional row, not a new section -- height cost is one line, and it directly sets up the This-Work row's claim ("First unified... framework") as the row that closes exactly this stated gap, making the table's narrative arc explicit rather than implicit.

## Step 9: self-review

- **Novelty within 5 seconds?** Yes -- a reviewer's eye reaches the double rule, the Research Gap sentence, and the fully-bolded, all-\CIRCLE\ final row in sequence; the pattern (gap stated, then immediately closed) is now structural, not something the reader has to construct themselves.
- **Justifies its space?** Yes -- 12 rows total (3 grouped + 4 standalone + 1 gap + 1 this-work, plus 2 group/header rows), still a single-column table.
- **Cleaner than the previous version?** Yes, per Steps 1-8 above.
- **Every column/row meaningful?** Yes, re-verified in Step 1.
- **Explains WHY this paper exists?** Yes -- the Research Gap row is now that explanation, stated as the table's own content rather than left to the caption or surrounding prose.

No further iteration performed; the redesign is judged complete.

## Honest disclosure: not compile-verified

No LaTeX compiler is available in this environment (a standing constraint throughout this session). The `p{7.6cm}` spanning cell's line-wrapping and the stacked `\midrule\midrule` emphasis rule are both standard, low-risk LaTeX constructs, but neither was rendered to confirm the exact wrap point or vertical spacing looks correct at IEEEtran's actual single-column width. Recommended: compile once against the real venue template and check this table specifically before submission; if the Research Gap sentence wraps awkwardly, shortening it further (e.g., dropping "itself") is the safe fallback, not restructuring the table.

## Why this version is stronger than the previous one

The previous table already had the strongest single element (Primary Limitation column) of this table's several redesigns this session, but read as a static comparison grid. This version keeps every real symbol and citation unchanged and adds exactly two structural things that change how it reads: a visual grouping that matches the paper's own existing "traditional V2X stack" framing (Architecture section), and a stated gap sentence that turns the grid's pattern into an explicit claim, immediately followed by the row that closes it. Nothing was removed to achieve this -- the table communicates more with the same real content, which is the actual objective this task states.
