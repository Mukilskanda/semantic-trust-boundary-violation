# Related Work Table Redesign

## Step 1: honest correction before redesigning anything

**No "Positioning of This Work Relative to Related Literature" table currently exists in the manuscript.** Related Work (Section II) is prose-only, three thematic paragraphs (Cryptographic/Behavioral/Semantic Trust), a deliberate design from an earlier compression pass in this session. There is nothing to critique for redundant columns/rows/wasted space, because there is no existing table. This is stated plainly rather than inventing a fictitious "current table" to critique, per this project's standing rule against fabrication. The redesign below is therefore a **new** table, built from scratch, using only the 12 real, already-cited related-work references in the bibliography (`r_pki_survey`, `r_pki_compare`, `r_mbd_survey1`, `r_mbd_survey2`, `r_cp_fabrication`, `r_context_aware`, `r_cares`, `r_semcom_backdoor`, `r_llm4drive`, `r_llm_survey`, `r_prompt_robot`/`r_prompt_vla`, `r_ds_improved1`/`r_ds_improved2`) -- no new citation was invented, and no capability claim about a cited work goes beyond what Section II's existing prose already says about it.

## Step 2: capability grouping chosen

Three grouped column headers, matching the paper's own architecture vocabulary rather than a generic feature list:

- **Trust Layers**: Communication / Behavioral / Semantic -- directly the three trust questions Section IV's architecture answers.
- **Framework Capability**: Fusion (explicit evidence fusion across layers, as opposed to a single-stage detector) / Cross-Layer (validates trust *across* an inter-layer boundary, this paper's specific formalized gap, not just within one layer).
- **Primary Limitation** (free text, one line): the specific gap that motivates this paper's next section, per the "novelty row" refinement -- applied to every row, not only the last, per the explicit follow-up preference this task's second message adds.

## Step 3: width reduction techniques used

Multi-line grouped headers (`\multicolumn` spanning "Trust Layers" over 3 sub-columns); single-letter-plus-symbol sub-headers under the group (C/B/S instead of "Communication"/"Behavioral"/"Semantic" spelled out per column); category names abbreviated to their shortest unambiguous form (e.g., "LLM/Prompt Inj." not "Large Language Model and Prompt Injection Literature"); the Primary Limitation column uses a single-clause phrase (matching this task's own worked example's style), not a full sentence.

## Step 4: "This Work" row highlighting

Bold row text, a thicker rule (`\midrule` reused as a bold separator) immediately above it separating it from all prior work, and light gray shading (`\rowcolor{black!8}`, grayscale-safe -- renders as a pale gray in print, not a color-dependent cue) -- avoiding the "excessive colours" this task warns against; no green (a color-vision-deficiency-risk choice for a "this is good" signal was deliberately avoided).

## Step 5: legend

Adopted per this task's own suggested scheme: **\fullcirc\ Fully Addressed, \halfcirc\ Partially Addressed, \opencirc\ Not Addressed** -- three symbols, distinguishable by fill fraction alone (grayscale-safe, unlike a color-coded checkmark/cross scheme), more compact than the ✓/△/– glyph set used elsewhere in this paper's figures (kept distinct on purpose, since a table legend and a figure legend serving different data types being visually distinct is itself a readability aid, not an inconsistency).

## Step 6: grouping of the literature itself

Six rows, each a real theme with real citations, in the same order Section II's existing prose already introduces them (no reordering needed, since that prose was already organized by theme in an earlier pass): Cryptographic Trust (PKI/SCMS), Behavioral Trust (MBD), Cooperative Perception, Context-Aware Trust, Semantic-Channel Security, LLM/Prompt-Injection Literature, Evidence Fusion (Dempster-Shafer literature specifically, since this paper's fusion mechanism itself is grounded in cited DS-theory work, `r_ds_improved1`/`r_ds_improved2`, not just V2X literature) -- 7 prior-work rows, then This Work.

## Step 7-8: novelty made obvious via the Primary Limitation column, applied to every row (per the explicit follow-up refinement)

Rather than a flat feature checklist ending in an unlabeled "This Paper: all ✓" row (which this task's own framing identifies as less memorable), every row states its real limitation, so the progression from row 1 to row 8 reads as an argument, not a table:

| Approach | Comm. | Behav. | Semantic | Fusion | Cross-Layer | Primary Limitation |
|---|---|---|---|---|---|---|
| PKI / SCMS | Full | -- | -- | -- | -- | No semantic reasoning |
| MBD | -- | Full | -- | -- | -- | No cross-layer trust |
| Cooperative Perception | -- | Partial | -- | -- | -- | No semantic reasoning |
| Context-Aware Trust | -- | Full | Partial | Partial | Partial | No content-coherence check |
| Semantic-Channel Security | -- | -- | Partial | -- | -- | Trusted-channel assumption; no manipulative-content model |
| LLM/Prompt-Injection Lit. | -- | -- | Full | -- | -- | No V2X integration or fusion |
| Evidence Fusion (DS theory) | -- | -- | -- | Full | -- | Domain-general; no V2X trust-layer grounding |
| **STBV (This Work)** | **Full** | **Full** | **Full** | **Full** | **Full** | **Unified multi-layer trust validation** |

This table is the real one inserted into the manuscript (Section II), with the symbol legend replacing the "Full/Partial/--" text used here for readability in this Markdown report.

## Step 9: comparison against top-tier IEEE Transactions conventions

Checked against the structural conventions common in recent IEEE TDSC/TIFS/TVT/TMC related-work comparison tables: grouped multi-column headers under a bold group label (yes), a compact symbol legend rather than spelled-out cell text (yes), the proposed method's row visually distinguished without excessive color (yes, grayscale-shaded), one row per real cited theme rather than one row per individual paper (yes -- matches this paper's own existing "themes, not paper-by-paper" Related Work convention, avoiding a table that contradicts the prose immediately next to it), and a stated gap/limitation column rather than a bare feature grid (a stronger convention than the checkmark-only tables common in the literature, directly answering this task's "why is this needed" requirement). Judged to meet the bar; no further iteration performed.
