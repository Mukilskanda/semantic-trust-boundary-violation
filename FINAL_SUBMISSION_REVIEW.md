# Final Submission Review

Reviewed against the 10-point presentation checklist. No experiment, figure, table, metric, equation, or conclusion was changed — every fix below is wording, caption style, or paragraph structure. This paper has already been through several dedicated polishing passes (`FINAL_REVIEWER_PASS.md`, `FINAL_POLISH_REPORT.md`); this pass checks for anything those missed rather than re-litigating what they already fixed.

## Checklist results

**1. Does the Introduction immediately explain the problem?** Yes — paragraph one states the gap (existing V2X trust mechanisms don't check content) before naming the contribution. No change needed.

**2. Does the Architecture section flow naturally?** Yes — each subsection is explicitly chained ("PKI → B1 (why the next stage is needed)", "B1 → MBD...") so the reader is told why the next stage exists before it's described. No change needed.

**3. Does every figure appear before it is discussed?** Checked source order for all 10 figures against their first in-text mention. One case worth noting, not a defect: `fig_boundary_schematic`'s own caption forward-references `fig_whyfail` ("the concrete worked example... follows in Fig.~X") — this is intentional signposting, not a broken reference, since `fig_whyfail` genuinely does appear later and the caption says "follows." No change needed.

**4. Does every table answer a clear question?** Checked all 8 — each has a single, distinct purpose (running example, notation, ITE-Bench recall, v2.5b full-pipeline, v2.5b checkpoint progression, VeReMi, CARLA, adaptive attack). No overlap found. No change needed.

**5. Are captions written as conclusions rather than descriptions?** **Found a real inconsistency and fixed it.** 6 of 9 data-bearing figure captions already opened with a bolded, conclusion-first sentence (e.g., "The architecture almost never misses an attack..."); 3 did not (`fig_boundary_schematic`, `fig_layer_responsibility`, `fig_architecture_glance` — three of the paper's most important explanatory figures, left as plain descriptions from an earlier pass). **Fixed**: added a bolded conclusion-first sentence to each of the 3, matching the house style already established elsewhere. Table captions were deliberately left as concise descriptive titles, matching standard IEEE table convention — conclusion-style captions are a figure-specific convention in this paper's own established style, not a table one, so no table caption was changed.

**6. Are transitions smooth between sections?** Checked all section and subsection boundaries. Already smooth (each Results subsection opens with "What this proves," verified in the immediately preceding pass). No change needed.

**7. Are any paragraphs repetitive?** Already addressed in the preceding pass (four redundant STBV-Bench v1 disclosure paragraphs consolidated to one canonical statement). Re-checked this pass for anything missed — none found.

**8. Are there sentences that are unnecessarily long?** **Found and fixed.** The Conclusion was one continuous ~280-word paragraph running through the architecture claim, the full evidence summary, the CARLA bug narrative, and the closing statement about methodology-as-contribution, with no paragraph break anywhere. **Fixed**: split into three paragraphs at its natural argument boundaries (the architecture claim; the experimental evidence for it; the CARLA-deployment finding and its aftermath; the closing statement) — no sentence was reworded except where noted in item 9 below, and no content was removed.

**9. Are there any claims that sound stronger than the presented evidence?** **Found two and fixed both.** (a) "an architecture's claimed *guarantees* must be tested against live deployment" — reworded to "claimed *properties*," since "guarantees" implies a formal proof claim the live-deployment testing sentence isn't actually about (the formally-proved properties are the fusion propositions, discussed elsewhere and correctly called guarantees there; this sentence is about empirical behavior, which "properties" describes more precisely). (b) "Every experiment in this paper exists to test that design, and every one confirms it" — reworded to "each one supports it," a more precise claim: "confirms" reads as closure (nothing left to find), while the paper's own Limitations section lists seven genuine open items; "supports" is the claim the evidence that follows actually establishes.

**10. Does the paper feel cohesive from start to finish?** After the fixes above (consistent caption style across all explanatory figures, a Conclusion that reads as three connected points rather than one dense block, and evidentiary claims scoped precisely to what was proved vs. what was empirically observed), yes.

## Summary of changes made this pass

1. Added a bolded, conclusion-first lead sentence to 3 figure captions that were missing one (`fig_boundary_schematic`, `fig_layer_responsibility`, `fig_architecture_glance`), bringing all 9 data-bearing figures to the same caption style.
2. Split the Conclusion section's single dense paragraph into three, at its natural argument boundaries.
3. Softened two claims that read stronger than the evidence directly supports ("guarantees" → "properties"; "every one confirms it" → "each one supports it").

## Confirmation

No experiment, figure content, table value, metric, equation, or scientific conclusion was changed. The mechanical LaTeX audit (labels/references/citations/figure files) was re-run after every edit in this pass and remains clean: 0 broken references, 0 duplicate labels, figure count unchanged at 10, table count unchanged at 8.
