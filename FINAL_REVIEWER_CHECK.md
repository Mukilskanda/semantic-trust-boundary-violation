# Final Reviewer Check

## 1. Is the perfect B3 score scientifically defensible?

Yes, as **exactly what it is** — the correct, re-verified output of the final checkpoint on STBV-Bench v1's fixed 10,000-message evaluation set (see `FINAL_FREEZE_AUDIT.md` §2 for the rerun record). It is **not** defensible as a general capability estimate on its own, and the manuscript now says precisely why: `TABLE_II_AUDIT.md` identifies the specific mechanism (template-family exposure via the `rows[10000:]` training slice of the same 100,000-row v1 corpus file the evaluated `rows[0:10000]` are drawn from) rather than leaving the explanation at a generic "in-distribution" hedge.

## 2. Would Reviewer #2 question it?

Yes, immediately — a clean F1=1.000 is the single most reviewer-suspicious number in any ML security paper. This is exactly why the manuscript does not present it in isolation: Table II (v2.5b, template-disjoint, zero training overlap) reports F1=0.945 on the identical checkpoint, and the gap between 1.000 and 0.945 is presented as evidence *for* the template-family-exposure explanation, not smoothed over.

## 3. If yes, how should it be presented?

As done: (a) report it honestly, unmodified; (b) identify the specific leakage-adjacent mechanism rather than a vague caveat; (c) anchor every deployment-relevant claim in the paper's abstract, conclusion, and discussion to the template-disjoint number (0.945), not the in-distribution one (1.000); (d) state explicitly, in the Limitations section, that v1's ceiling should not be read as a capability claim.

## 4. Are B1 and B2 being evaluated fairly?

Yes, and this required real engineering work to achieve honestly, not just better wording: `ABLATION_AUDIT.md` found that the *original* ablation evaluation protocol structurally prevented B1's replay/certificate-rotation checks and MBD's per-sender history from ever firing, regardless of what a benchmark contained (a bug, not a benchmark-design choice). ITE-Bench (Table with per-layer recall) plus the corrected sequential-evaluation protocol give both layers attacks and a protocol capable of exercising them — the result (1.000 recall in-class, 0.000 out-of-class, zero-cost layering, McNemar $p{<}10^{-15}$) is now a fair, direct answer, not an inference from absence.

## 5. Does Table II accurately represent the contribution of each trust layer?

Yes, by design: it is literally structured as three attack-class rows (communication/behavioral/semantic) × three configuration columns (B1-only / B1+B2(+CP) / full stack), so a reader sees each layer's recall inside and outside its own threat class in one table, without needing to cross-reference multiple tables or infer it from prose. No redesign beyond this was needed — Part 3's requested "grouped rows so reviewers immediately understand B1→protocol, B2→behavioral, B3→semantic" was already the table's actual structure.

## 6. Is there any remaining result that appears suspiciously good or suspiciously weak?

Two flagged, both already disclosed rather than hidden:
- **Suspiciously good**: STBV-Bench v1's F1=1.000 (this document, above) — resolved by anchoring claims to v2.5b instead.
- **Suspiciously weak, and left weak rather than improved without evidence**: the adaptive-attack Table's 21.6% ASR is measured against the *prior*, not final, checkpoint — this is disclosed as a real inconsistency in every place the number appears, not quietly presented as current. No other result in the paper showed a similarly unexplained anomaly on inspection.

## 7. Recommended final version of Table II for publication

**No structural change recommended.** Table II (per-layer recall on ITE-Bench) already presents exactly the grouped, attack-category-labeled structure a reviewer needs to see each layer's contribution unambiguously. The one change made this pass was to Table I's surrounding discussion (the F1=1.000 explanation), not to Table II itself, since Table II was already correctly designed. If the target venue's reviewers specifically request it, a natural (but not currently necessary) extension would be adding 95% CIs to Table II's recall cells to match Table I's/Table III's statistical-reporting convention elsewhere in the paper — flagged as a possible future addition, not performed here since ITE-Bench's per-cell recall values are exact 0.000/1.000/0.143 with $n\geq275$ per cell, leaving little room for a CI to change the reading.

## Manuscript changes made as a direct result of this audit

1. Added a precise, mechanism-level explanation of STBV-Bench v1's F1=1.000 ceiling to the Limitations section, citing the exact training-data row-index partition.
2. Produced `TABLE_II_AUDIT.md` documenting the full investigation (five candidate explanations checked, one confirmed, others ruled out with evidence).
3. Added Algorithm 1 (pipeline pseudocode, a direct transcription of the real implementation), a System Assumptions subsection, a Computational Complexity subsection (using real measured per-stage latency from this session's own final-checkpoint SUMO run), a Notation table, and a Known Failure Modes subsection — none of which required changing any previously-reported metric.

## What was NOT changed, and why

No metric, threshold, or reported value was altered anywhere in the manuscript as a result of this pass. Every change was additive (new explanation, new pseudocode, new complexity/notation/assumptions/failure-mode content) or reorganizational (pointing existing content at newly-added sections). This is consistent with the task's own stated objective: maximize scientific credibility, not benchmark scores.
