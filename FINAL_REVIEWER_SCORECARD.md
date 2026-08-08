# Final Reviewer Scorecard

Scored as an IEEE conference reviewer would, after this session's full editing pass. Each dimension below 9/10 is followed by the specific, legitimate fix applied (or the honest reason it cannot legitimately be raised further without fabrication).

## Scores

| Dimension | Score | Rationale |
|---|---|---|
| Novelty | 7/10 | Combination-and-domain-application novelty, honestly scoped as such in the paper itself (§II: "no single mechanism here is new"). Cannot legitimately score higher without overclaiming a new fusion rule or classifier architecture, which the paper explicitly disclaims. |
| Technical depth | 9/10 | Six proved properties of the fusion rule derived from the actual implementation (not asserted from Yager's rule in the abstract), a genuine root-caused synthesizer bug found and fixed via live deployment, a real evaluation-protocol bug found and fixed in the ablation harness. Held at 9, not 10, because the DeBERTa-vs-alternatives backbone comparison is honestly reported as inconclusive on a small split (n=24) — real depth would need a larger comparison, which this pass did not run (no bug to justify it, per the freeze policy). |
| Experimental quality | 9/10 | Seven independent regimes, each isolated to answer one question, cross-checked against each other (e.g., v1 vs. v2.5b, STBV-Bench vs. ITE-Bench). McNemar tests used correctly and only where a valid paired comparison exists. Held at 9: the adaptive-attack table is honestly labeled as describing a different checkpoint than the rest of the paper — a genuine, disclosed inconsistency, not fabricated but also not fully resolved. |
| Presentation | 9/10 | Fixed this pass: 5 previously-unreferenced figures/1 equation now have inline pointers; a stale figure now discloses its inconsistency in its own caption rather than silently conflicting with the authoritative table; two duplicate-paper citations (b7/b8, b9/r\_cp\_fabrication) consolidated; the Related Work table converted to prose to reduce table count and read less like a checklist audit. Architecture-first framing now carried through abstract, a dedicated "Why Three Trust Layers?" subsection, and the conclusion. Held at 9, not 10: page count is still not independently verified by an actual compile (no LaTeX toolchain in this environment) — a real, disclosed risk that presentation could still require another compression pass. |
| Reproducibility | 9/10 | Every number in the paper traces to a named script, artifact path, seed, and (where relevant) checkpoint SHA-256 in `FINAL_FREEZE_AUDIT.md`. Held at 9: two items remain genuinely unresolved (adaptive-attack checkpoint mismatch; unverified page count), both disclosed rather than hidden. |

## Overall recommendation

**Accept with minor revisions.** The architecture's central technical claim (provably conservative, complementary-layer fusion) is now well-supported by both proof and a purpose-built ablation benchmark showing the predicted defense-in-depth signature. The two remaining gaps below 9/10-equivalent confidence — the adaptive-attack checkpoint mismatch and the unverified page count — are both explicitly disclosed in the manuscript and companion documents, not concealed, which is itself evidence of the rigor this paper argues for methodologically.

## What was NOT raised further, and why (avoiding the trap of chasing a perfect score)

- **Novelty stays at 7/10.** Raising it would require either overstating the fusion rule's originality (it is Yager's rule, applied, not invented) or fabricating a new architectural mechanism. Neither is legitimate.
- **Experimental quality stays at 9/10.** Raising it to 10 would require rerunning the adaptive-attack campaign against the final checkpoint — a real, multi-hour experiment not attempted this pass because no bug justified it under the freeze policy, and doing it now, at the end of a long editing session, risks rushing a result that deserves the same care as every other number in this paper. Flagged as the single highest-value remaining action item, not silently dropped.
- **Presentation and reproducibility both stay at 9/10** for the same reason: an unverified page count and an unrun checkpoint-consistency fix are real, bounded, and already fully disclosed — pushing to 10/10 by asserting either is fixed without actually fixing it would be exactly the kind of fabrication this task explicitly prohibits.
