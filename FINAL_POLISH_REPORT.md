# Final Polish Report

No experiment, figure, table value, or scientific claim was changed in this pass. Every change below is wording, structure, or cross-reference correction, verified against the mechanical LaTeX audit (0 broken references, before and after every edit).

## 1. Structural improvement: Notation table repositioned

Table II ("Notation Used Throughout This Section") was cut from its previous location (the last subsection of Architecture, after every equation that uses its symbols) and reinserted immediately before Section IV-E (Dempster-Shafer Evidence Fusion), so a reader now sees $\Theta$, $m(\cdot)$, $K$, $m_Y(\cdot)$ defined before encountering them in Eq. 1–3, not after. Its caption was updated from "Notation Used Throughout Section IV" to "Notation Used Throughout This Section" to remain accurate at its new position. The now-empty "Notation" subsection heading was removed.

## 2. Structural improvement: hardcoded subsection letters removed

Every `Section~\ref{sec:results}A` / `...F` style reference (6 occurrences) was replaced with a real, robust cross-reference: two new subsection labels were added (`\label{sec:layervalidation}` for "Layer-wise Architecture Validation," `\label{sec:sumo}` for "SUMO Deployment Replay") and every hardcoded letter now resolves via `\ref` to the actual subsection, or, where a label would be awkward, a descriptive phrase ("the Behavioral Validation subsection below"). This also **found and fixed a real, pre-existing cross-reference bug**: "Section~\ref{sec:results}C validates behavioral/kinematic detection" was verified against the actual subsection order (A=Layer-wise, B=ITE-Bench, C=Semantic Validation/v2.5b, D=Behavioral/VeReMi) and was wrong — subsection C is Semantic Validation, not Behavioral. The corrected version no longer depends on a fragile, manually-counted letter at all.

## 3. Repeated STBV-Bench v1 disclosure paragraphs consolidated

The "STBV-Bench v1 is retained solely for [X], not a semantic-generalization claim" disclosure previously appeared, restated in full or near-full each time, in four places: Methodology, the Results-section roadmap, the opening of Layer-wise Architecture Validation, and the opening of Semantic Validation. **Methodology now holds the one complete statement of v1's role** (kept as-is; it is the natural first point of reference for a reader encountering the benchmark for the first time). The other three were trimmed to short cross-references ("STBV-Bench v1's role here is as established in Section V," "STBV-Bench v1's distinct, narrower role is established once, in Section V," "STBV-Bench v1's role in this evaluation is stated once, in full, in Section V, and not repeated here") — the disclosure itself is not weakened or hedged, only de-duplicated.

## 4. Overclaiming softened

The Abstract's "the architecture behaves **exactly as the theory predicts**" was reworded to "the architecture behaves as the theory predicts **on every property it makes a provable claim about**" — the underlying claim (recall-within-scope, escalation-only fusion, held-out generalization) is unchanged and still fully supported by the results that follow, but the qualifier now correctly scopes the claim to the properties the paper actually proves, rather than reading as an unqualified absolute that a reviewer could set against the Discussion's seven disclosed limitations. Every other use of "proves"/"exactly"/"guarantee" in the manuscript was individually checked against what it actually refers to (a formally proved proposition, e.g. Proposition 1/3's rank-monotonicity, or a literal factual equivalence, e.g. "authenticated by PKI exactly as in any conventional stack") and found to be accurate, precise usage, not overclaiming — none of those needed a change.

## 5. Table V renamed

"Progressive-Layer Ablation, STBV-Bench v2.5b, Current Final Checkpoint" → **"Full-Pipeline Evaluation, Realizable Configurations, STBV-Bench v2.5b, Current Final Checkpoint."** The old title implied a multi-stage build-up (PKI→B1→B2→CP→B3) that the table, after an earlier pass correctly removed its three structurally-zero rows, no longer shows — it now reports three configurations (B3-only, B1+B2+B3 without CP, full stack), not a progression. The new title describes what the table actually contains. (STBV-Bench v1's own Table III is a genuine 4-stage progression and was not renamed — its title remains accurate.)

## 6. Equation introductions reviewed

Checked all three equations (basic belief assignment, conflict mass, Yager combination) against the requested intuition→equation→explanation structure. All three already satisfy it: each is preceded by a plain-language motivation ("This is the property this architecture actually needs...", "this is *conflict*...") and followed immediately by a restatement in the same or next sentence ("A vacuous mass... is used whenever...", "This is the paper's central design choice, stated precisely..."). No change made — already correct.

## 7. Section transitions reviewed

Checked that every Results subsection opens with a sentence stating what question it answers. Six of seven already do, via the "\textbf{What this proves.}" convention; the seventh (Semantic Validation) has one framing sentence before its own "What this proves" paragraph, matching the same pattern one sentence later. No change needed.

## 8. Long paragraphs tightened

- The v2.5b full-pipeline ablation paragraph (previously one ~450-word block covering the F1 gap, the significance test, and both stages of the root-cause mechanism) was split into three paragraphs at its natural argument boundaries: (1) the headline result and its statistical confirmation, (2) the two-stage mechanism breakdown, (3) the calibration-coupling finding and fusion's escalation pattern. No sentence was reworded or removed.
- The Discussion's "Limitations" paragraph (seven items, roman-numeral-labeled, run together as one continuous block) was converted into a proper `enumerate` list — each of the seven limitations is now visually and structurally separate, with identical wording preserved verbatim inside each item.

## 9. Final grammar and readability sweep

Carried forward from the immediately preceding reviewer-simulation pass (verified still correct, not re-broken by this pass's edits): "an averaged-down score" (was "a"), two broken possessives from an earlier mechanical find-replace, an imprecise Notation-table row description, an unexplained "F1 undefined," and an orphan acronym. All six remain fixed; the mechanical LaTeX audit run after every edit in this pass confirms no new issue was introduced (0 broken references, 0 duplicate labels, consistent figure/table counts throughout).

## Confirmation

No scientific claim, number, figure, or table value was altered. Every change in this report is verifiable as a pure wording, ordering, or cross-reference-label edit against the surrounding unchanged content.
