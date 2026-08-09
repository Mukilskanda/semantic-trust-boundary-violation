# Manuscript Compression Report

**Honest result up front: this pass achieved a ~2.4% word-count reduction (14,205 → 13,871 words in the `.tex` source), well short of the requested 15–25%.** The reasoning for this shortfall is explained below rather than papered over with an inflated number. No experiment, figure, table value, equation, or scientific conclusion was changed — every edit is a genuine deletion or tightening of redundant prose.

## Why 15–25% was not reachable without violating "preserve all scientific content"

This manuscript has already been through roughly a dozen dedicated editing passes in this session (checkpoint-consistency audits, three figure-redesign passes, a reviewer simulation, two prior polish passes) whose explicit purpose was adding rigor, disclosure, and precision — not padding. Each of those passes specifically added qualifying clauses, cross-references, and disclosed caveats that a reviewer had asked for or that correctness required. The redundancy that remains is concentrated in a small number of specific places (identified and cut below); most of the manuscript's length is load-bearing: per-layer purpose/input/output/limitation specifications, disclosed limitations with their specific evidence, and results paragraphs that trace every number to its source. Cutting a further 12–22% would have required removing content of exactly the kind this session's own standing instructions (repeated across many prior turns) prohibit cutting: disclosed limitations, evidence chains, and reproducibility detail. Rather than hit an arbitrary percentage by thinning those out, this pass cut only what was genuinely restated elsewhere.

## Redundant text found and removed

| Location | What was cut | Why |
|---|---|---|
| Discussion, "Strengths" paragraph | ~150 words (of ~300) | Re-derived numbers (ITE-Bench recall values, McNemar statistics, F1 progression, adaptive-attack ASR) already stated in full, with their own evidence, in the Results section. Rewritten to state the four supporting findings as a compact list with cross-references, rather than re-deriving each number a second time. |
| Conclusion | ~120 words (of ~400, across two edits) | The evidence summary re-listed results already detailed in Results and just-compressed in Discussion. Compressed to a parenthetical summary with a cross-reference; the CARLA-bug narrative and closing methodology statement were kept, since they are the Conclusion's own distinct point, not a restatement. |
| Results, "Why B1's and CP's contributions read as near-zero" paragraph | ~60 words | Its opening two sentences repeated, almost verbatim, the closing sentence of the immediately preceding paragraph ("v1 alone shows B1/B2 as apparently near-useless... not evidence the layers are weak in general" / "A near-zero B1/B2 row invites the wrong reading... They are not"). Removed the second, retained the specific root-cause detail (B1 unit-test evidence, CP's data-generation gap) that was not stated elsewhere. |

## Structural improvement (not primarily a word-count cut)

**Limitations section regrouped into three explicit themes** (Live Deployment; Evaluation Coverage; Benchmark and Checkpoint Caveats), each with its own `\emph{}` heading, per the explicit "group related limitations under broader headings" instruction. All seven items' content is unchanged; grouping makes the section's structure scannable rather than a flat run of seven numbered items with no organizing logic.

## What was reviewed and found NOT to be compressible without loss

- **Related Work** (228 words): already organized by theme (PKI/SCMS, MBD, CP-security, context-aware trust, semantic-channel backdoors, LLM/VLM-in-driving, prompt injection), each sentence establishing a distinct axis of "what's missing that this paper provides." Already matches the requested "organize by themes... end with one clear gap paragraph" structure from an earlier pass. No further cut found without losing a cited comparison point.
- **Architecture's per-layer paragraphs** (PKI→B1, B1→MBD, MBD→B2, B2→CP, CP→B3): each states a distinct Purpose/Inputs/Outputs/Limitation for a distinct component. The repeated phrase structure ("why the next stage is needed") is a deliberate, reviewer-legible convention, not padding — collapsing it would remove the paper's own stated mechanism for explaining why each layer exists (a property this session's much earlier passes were specifically asked to strengthen, not weaken).
- **The v2.5b full-pipeline ablation paragraph** (the single densest paragraph in the paper): reviewed for table/text redundancy specifically. Found to be analysis, not restatement — it explains *why* the Table V numbers are what they are (the two-stage root-cause mechanism, the McNemar significance test), which a table cannot convey on its own. Cutting it would remove the paper's own root-cause finding, not a redundant description of it.

## Confirmation

No experiment, figure, table value, equation, or scientific conclusion was changed. The mechanical LaTeX audit (labels/references/citations/figure files) was re-run after every edit in this pass and remains clean: 0 broken references, 0 duplicate labels, figure count unchanged at 10, table count unchanged at 8.

## Recommendation if a larger cut is still required

A genuine 15–25% reduction is achievable, but not through further sentence-level tightening of a manuscript this dense — it would require a structural decision the user should make explicitly: for example, moving the full per-layer Purpose/Inputs/Outputs/Limitation architecture detail (Section IV-C, several hundred words) to an appendix and leaving only the pipeline diagram and a one-paragraph summary in the main text, or moving STBV-Bench v1's entire architectural-validation subsection to supplementary material now that v2.5b is the primary benchmark. Either would reach the target range, but both remove content a reviewer might specifically want in the main text — not attempted here without that explicit go-ahead, consistent with "preserve all scientific content."
