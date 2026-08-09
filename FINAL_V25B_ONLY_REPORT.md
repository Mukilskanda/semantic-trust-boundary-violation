# Final v2.5b-Only Report

No experiment was rerun, no model was retrained, no benchmark was regenerated, no metric was changed, no equation was modified, and no scientific conclusion was altered. Every edit below is a removal, rewrite, or renumbering of text/table content so the manuscript reads as if STBV-Bench v2.5b was always the sole primary and definitive semantic evaluation benchmark. This supersedes the previous pass's Appendix-relocation approach for STBV-Bench v1 (that appendix has been deleted, not kept) per this pass's explicit "Do NOT create an Appendix" instruction.

## Every removed v1 item

| Location | What was removed |
|---|---|
| Appendix (new `\section{Historical STBV-Bench v1 Evaluation}`, `app:v1`) | **Deleted entirely** — this was added in the immediately preceding pass and is now fully removed, not retained anywhere, per this pass's explicit instruction. |
| Abstract/Introduction, Contributions (i)–(v) | Removed the clause citing STBV-Bench v1 ($n{=}10{,}000$) as the benchmark behind the progressive layer-by-layer ablation; replaced with a clause citing ITE-Bench, which now carries that role. |
| Architecture, "B2 → CP" paragraph | Removed "(as in STBV-Bench v1, by construction of its own generator)" — genericized to "(as in this paper's semantic-attack generator, by construction)," an implementation fact independent of any specific benchmark name. |
| Architecture, "System Assumptions" list item on CP | Removed cross-reference to the old `sec:layervalidation` subsection's v1 discussion; repointed to Section V-C (v2.5b). |
| Methodology | Removed the entire "STBV-Bench v1 ($n{=}10{,}000$) pairs real VeReMi Extension kinematics..." sentence and the "addressing a real limitation of STBV-Bench v1" clause in the ITE-Bench description. |
| Results, roadmap paragraph | Removed "STBV-Bench v1's role in this evaluation is stated once, in full, in Section~Methodology, and not repeated here" — no longer needed since v1 is not mentioned at all; roadmap rewritten around the five RQs as the new request specifies. |
| Results, `sec:layervalidation` subsection ("Layer-wise Architecture Validation") | **Entire subsection deleted** — this was the v1-specific ablation (F1 0.034, F1=1.000/0.995, the 69-escalation fusion trace, the "root causes" paragraph, and the "key numbers" paragraph). ITE-Bench's subsection now stands alone as RQ1's full evidence, retitled "Layer Responsibility — RQ1 (ITE-Bench)." |
| Results, ITE-Bench "Finding" paragraph | Removed "that STBV-Bench v1 never contains" and "the old evaluation protocol" phrasing tied to the deleted v1 subsection. |
| Results, ITE-Bench "Interpretation"/"Implication" paragraphs | The two paragraphs that referred back to "the STBV-Bench v1 ablation numbers above" were removed; replaced with a direct "Answering RQ1" paragraph. |
| Results, Semantic Validation (v2.5b) opening | Removed "STBV-Bench v1's distinct, narrower role is established once, in Section Methodology" and "Its near-ceiling result on v1 has an identified, benchmark-specific leakage-adjacent mechanism." |
| Results, "A second, full-pipeline ablation" paragraph | Removed "like STBV-Bench v1 (Section layervalidation)" comparison; the structural-non-result explanation for B1/B1+B2 configurations is now self-contained, referencing only v2.5b's own scope and ITE-Bench. |
| Results, "Ablation on v2.5b, current checkpoint" paragraph | Removed "consistent with treating v2.5b as this paper's single semantic benchmark rather than repeating STBV-Bench v1's already-established point... a second time" — rewritten as a direct statement that B1/B2/CP-only results are reported once, on ITE-Bench. |
| Results, v2.5b closing sentence | Removed "the identical one-directional pattern already established on STBV-Bench v1" — now reads "already established on the prior v2.5b checkpoint... confirmed on a second measurement" (dropped from "third" to "second," since v1 is no longer one of the two prior confirmations counted). |
| Results, VeReMi (RQ3) opening | Removed "confirming the converse of the STBV-Bench v1 ablation numbers above" — repointed to Section V-C (v2.5b) directly, since the v1 comparison point no longer exists in the manuscript. |
| Discussion, "Strengths"/"Why the architecture works" | Removed "a misreading the STBV-Bench v1 numbers alone would invite" and "consistent with STBV-Bench v1's identical pattern." |
| Discussion, Limitations, item 6 | **Entire item deleted** — "STBV-Bench v1's near-ceiling F1 has a specific mechanism..." (the template-family-exposure leakage-adjacent finding). This was a v1-only caveat with no counterpart claim about v2.5b; removing it required renumbering the remaining "Benchmark and checkpoint caveats" item from 7 to 6. |
| Table `tab:v25b_ablation` | Retitled from "Full-Pipeline Evaluation, Realizable Configurations" to "Architecture-Progression Ablation" and restructured to explicitly list all five requested configurations (B1 only, B1+B2, B3 only, B1+B2+B3, Full STBV Framework), with the two benchmark-inapplicable rows (B1 only, B1+B2) marked "not meaningfully evaluable on this benchmark" with a table note explaining why, rather than fabricated or silently omitted. |

## Every rewritten paragraph / transition

1. **Contributions (iii)**: rewritten to cite ITE-Bench instead of STBV-Bench v1 as the benchmark validating per-layer contribution.
2. **Results roadmap**: fully rewritten around the five RQs specified in this pass (RQ1 layer independence → ITE-Bench; RQ2 semantic validation → v2.5b; RQ3 generalization → VeReMi; RQ4 deployment → CARLA/SUMO; RQ5 limitations → Discussion), replacing the prior roadmap's RQ1–RQ5 mapping (which had assigned RQ3–RQ5 to v2.5b/VeReMi/deployment respectively).
3. **"Layer Responsibility — RQ1 (ITE-Bench)"**: this subsection (formerly two subsections, one v1-specific and one ITE-Bench) is now one self-contained subsection ending in an explicit "Answering RQ1" sentence, matching the house style used by every other Results subsection.
4. **All "Answering RQ_n" sentences** in Results were renumbered to match the new mapping: v2.5b section now answers RQ2 (was RQ3), VeReMi answers RQ3 (was RQ4), CARLA/SUMO answers RQ4 (was RQ5). RQ5 (limitations) is answered by the Discussion section as a whole, per this pass's instruction that RQ5's evidence is "Discussion, Future Work."
5. **Discussion "Strengths"** renamed "Why the architecture works" per this pass's requested Discussion flow, and a new paragraph "Why semantic trust is necessary, and why defense-in-depth matters" was added directly beneath it (drawing only from already-reported v2.5b/VeReMi results, no new claims), completing the requested Discussion flow: why the architecture works → why semantic trust is necessary → why defense-in-depth matters → remaining limitations → future work.

## Every updated figure

No figure images were regenerated. No figure in the main body referenced STBV-Bench v1 — this was already true before this pass (v1's only figure content had been converted to inline text in an earlier session pass, and that inline text has now been removed per this pass rather than moved). All 10 figures are unchanged and already exclusively v2.5b/ITE-Bench/VeReMi/CARLA/SUMO-sourced. Figure count confirmed unchanged: 10.

## Every updated table

- `tab:v25b_ablation`: restructured (see above) to explicitly enumerate all 5 requested configurations with a stated reason for the 2 that cannot be meaningfully evaluated on this benchmark, rather than silently reporting only 3 rows as the prior version did.
- No table's underlying values were changed. Table count confirmed unchanged: 8. No table's "primary purpose was v1" — v1 never had its own dedicated table in this manuscript (its numbers were always reported as inline text, both before and during the deleted appendix), so no table removal was required beyond the ablation-table restructuring above.

## Every rewritten caption

No figure or table caption referenced STBV-Bench v1 before this pass began (confirmed by grep before editing), so no caption rewrite was required. `tab:v25b_ablation`'s caption was rewritten as part of the restructuring above (title change only, no data change).

## Every updated discussion

See "Every rewritten paragraph" above — Discussion's Strengths/Limitations sections were the two discussion blocks with genuine v1-only content; both are covered there.

## Confirmation

- ✓ No experiment was rerun.
- ✓ No model was retrained.
- ✓ No benchmark was regenerated.
- ✓ No number was fabricated — the two ablation-table rows that cannot be evaluated on v2.5b are explicitly marked as such, not filled with invented values.
- ✓ No metric, equation, or table value was changed.
- ✓ No scientific conclusion was altered — every remaining claim is identical to its pre-edit form, only its benchmark-comparison scaffolding (v1 as a second reference point) was removed.
- ✓ Mechanical LaTeX audit (`scratch_latex_audit.py`), run after all edits: 0 broken references, 0 duplicate labels, figure count unchanged (10), table count unchanged (8), all citations resolve.
- ✓ No remaining `STBV-Bench v1` / `v1` references in the main manuscript body, Results, Discussion, Conclusion, or Appendix, with one deliberate, disclosed exception below.

## One disclosed exception (not a violation, flagged for transparency)

The Appendix "Reproducibility Summary" (`app:params`) states that Pass 1's training corpus included "the original mixed corpus (v2.5 train split + stratified v1 slice)." This is a factual statement about **what data the deployed checkpoint was trained on**, not a discussion, comparison, or evaluation of STBV-Bench v1 as a benchmark. Removing it would misstate the checkpoint's actual training-data provenance in the reproducibility record — a factual inaccuracy this pass's own rules ("do not fabricate," "do not change any... reported") prohibit more strongly than the instruction to remove v1 discussion. This single word is retained as a provenance fact, not restored discussion.
