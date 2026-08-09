# Final Reviewer Pass

Read as an IEEE Transactions reviewer trying to find grounds for rejection. No experiment, figure, table, or scientific claim was touched — only wording. Findings ranked; Cosmetic and Minor items were fixed automatically (listed at the end with the exact change); Major and Critical items are left as recommendations only, per instruction.

## Critical

None found. No claim in the manuscript is unsupported by its own cited evidence, no result contradicts another, and every disclosed limitation is genuinely disclosed rather than buried.

## Major (recommendations only — not fixed this pass)

**M1. Notation table (Table II) is positioned after every equation that uses its symbols, not before.** A reader encounters $\Theta$, $m(T)$, $K$, $m_Y(\cdot)$ across three equations (Section IV-E) before ever seeing the symbol table, which appears as the last subsection of the Architecture section (Section IV-K). A reviewer skimming for notation on first encounter will not find it where expected. *Recommendation*: move Table II to immediately precede Section IV-E (Dempster-Shafer Evidence Fusion). Not done this pass — moving a table's position is a layout change, out of scope for a wording-only pass.

**M2. The manual section-lettering convention ("Section~\ref{sec:results}A," "...C," "...F") is fragile and was already found to contain one real error** (see Minor fix m3 below — "C" pointed at the wrong subsection). Every other instance was checked and is currently correct, but the convention has no structural protection against drifting out of sync the next time a subsection is added, removed, or reordered. *Recommendation*: replace every hardcoded letter with a named `\label`/`\ref` pair to the specific subsection, eliminating this entire class of bug. Not done wholesale this pass, since touching every occurrence without a fresh compile to verify the result risks introducing new mismatches rather than removing the one found.

**M3. The disclosure "STBV-Bench v1 is retained solely for [X], not a semantic-generalization claim" is restated near-verbatim in at least four separate places** (Methodology, the Results section roadmap, Section VI-A's opening, and Section VI-C's opening). Each individual instance is locally well-motivated (a reader arriving at that paragraph from a citation or a skim needs the context restated), but a reviewer reading start to finish will notice the repetition and may read it as padding. *Recommendation*: state the policy once, in Methodology, and have the other three instances cite it ("as established in Section V") rather than re-explain it. Not done this pass — consolidating four independently-worded, previously-audited disclosure sentences into one carries real risk of accidentally weakening the disclosure somewhere it was needed, and deserves a dedicated pass with fresh eyes rather than a drive-by edit inside a reviewer-simulation pass.

**M4. The Abstract's claim "the architecture behaves exactly as the theory predicts" is a strong absolute** that a skeptical reviewer could read as overclaiming, given that the Discussion later discloses seven real limitations (B3's snake-case blind spot, CARLA non-determinism, an unresolved calibration/floor coupling, among others). The claim is not factually false — the specific properties it refers to (recall-within-scope, fusion's escalation-only behavior) do hold exactly as measured — but "exactly as the theory predicts," stated without qualification in the Abstract, primes a reviewer to expect a cleaner story than the paper actually, honestly, delivers. *Recommendation*: qualify to "behaves as the theory predicts on every property it makes a provable claim about, with the remaining gaps disclosed in Discussion." Not fixed this pass — Abstract wording is the highest-visibility text in the paper and deserves a deliberate edit, not one made in passing during a reviewer simulation.

**M5. Table V's caption, "Progressive-Layer Ablation," overpromises relative to its current 3-row content.** After an earlier pass removed the three structurally-zero B1/B2/CP rows, the table now shows B3-only → B1+B2+B3(no CP) → Full STBV — a real but much shorter progression than "progressive-layer ablation" implies to a reader expecting to see PKI→B1→B2→CP→B3 build up one row at a time. *Recommendation*: retitle to something like "v2.5b Full-Pipeline Configurations" in a future pass. Not fixed this pass — table edits are explicitly out of scope ("No tables").

## Minor (fixed automatically this pass)

**m1. Grammar: "a averaged-down score" should be "an averaged-down score"** (Section IV-F, "Confidence-aware evidence fusion" paragraph). **Fixed.**

**m2. Broken possessive from a prior pass's mechanical find-replace.** When Table III was removed in an earlier pass, every `Table~\ref{tab:main_ablation}` was replaced with the phrase "the STBV-Bench v1 ablation numbers above" — grammatically fine as a noun phrase on its own, but two instances had a possessive `'s` appended directly to "above" ("...ablation numbers above's near-zero B1/B2 rows," "...ablation numbers above's converse"), which is not valid English. **Fixed** by rewording both sentences to avoid the awkward possessive.

**m3. Cross-reference error: "Section~\ref{sec:results}C validates behavioral/kinematic detection independent of semantic content (RQ4)" pointed at the wrong subsection.** Verified against the actual subsection order (A=Layer-wise Architecture Validation, B=ITE-Bench, C=Semantic Validation/v2.5b, D=Behavioral/VeReMi, E=CARLA, F=SUMO): subsection C is Semantic Validation, not Behavioral — the correct letter is D. **Fixed** by replacing the fragile hardcoded letter with a direct description ("the Behavioral Validation subsection") rather than perpetuating the same class of bug with a different letter.

**m4. Notation table imprecision: $\tau_H,\tau_L$ described as "Accept / Reject decision thresholds," omitting Caution** — the actual decision space and the thresholds' own role (Section IV-E) is three-way (Accept/Caution/Reject), and $\tau_H,\tau_L$ are specifically the upper/lower bounds of that three-way split. **Fixed** to "Accept / Caution / Reject decision thresholds (upper/lower)."

**m5. "F1 undefined (0.000 recall)" stated without explaining why F1 is undefined**, which a reader unfamiliar with the precision/recall-undefined-at-zero-positive-predictions convention could misread as a data-quality problem rather than an arithmetic one. **Fixed** by adding a four-word parenthetical: "(no positive predictions to score)."

**m6. Orphan acronym: the Abstract defines "the Semantic Trust Boundary (STB)," but this acronym is never used again anywhere in the paper** — the Introduction separately and properly defines "Semantic Trust Boundary Violation (STBV)," which is the acronym actually used throughout. Having two near-identical acronyms (STB vs. STBV) defined one paragraph apart is a real, avoidable source of first-read confusion. **Fixed** by removing the unused "(STB)" parenthetical from the Abstract, since the term is written out in full there and the acronym is never needed until STBV is properly introduced in the Introduction.

## Cosmetic (fixed automatically this pass)

**c1. Three consecutive blank lines in the LaTeX source** between the error-analysis figure and Table VI (no visual effect on the compiled PDF, but untidy source). **Fixed** — reduced to a single blank line.

## What was explicitly checked and found to be already correct (no issue to report)

- **Equations introduced without intuition**: checked all three (BBA, conflict, Yager combination) — each is immediately followed by a plain-English restatement in the same or next sentence. No fix needed.
- **Architectural steps introduced too late**: checked B3's architecture detail (DeBERTa-v2 specifics) — introduced at the point in the pipeline narrative where B3 itself is introduced (Section IV-C, "CP → B3"), not deferred to Methodology or Results. No fix needed.
- **Figure/table numbering and cross-reference integrity**: re-ran the mechanical LaTeX audit after every fix in this pass — 0 broken references, 0 duplicate labels, both before and after.

## Confirmation

No scientific result, number, figure, or table was changed. Every fix in this report is a wording, grammar, or cross-reference-label correction, verifiable by diffing the six Minor and one Cosmetic edit against the surrounding unchanged text.
