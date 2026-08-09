# Final Coherence Audit

Read start to finish against the 8-point checklist. No experiment, figure, table, or equation was modified — every change below is a transition sentence, added at a section or subsection boundary, that does not alter any measured result, claim, or conclusion.

## 1. Does every research question naturally follow from the previous one?

Mostly yes, with one gap found and fixed. RQ1 (ITE-Bench, layer independence) → RQ2 (v2.5b, semantic validation) → RQ3 (VeReMi, generalization) flow cleanly: each subsection's opening sentence already references the prior one's finding ("confirming the converse of Section~\ref{sec:v25b}'s finding," etc.). RQ3 → RQ4 (CARLA/SUMO, deployment) is explicit ("whether the checkpoint's improved benchmark performance transfers to live deployment"). **Gap found**: the Adaptive Attack Evaluation subsection, which is this paper's RQ5 evidence (robustness/limitations), had no research-question framing at all — it read as a bolted-on extra experiment after RQ4 was already answered. **Fixed**: added one lead sentence connecting it explicitly to RQ5 ("RQ1--RQ4 establish that the architecture works against the single-shot attacks each benchmark and deployment surface poses; this final experiment begins answering RQ5 by testing whether that result holds against an attacker who is not single-shot").

## 2. Does every figure answer the question introduced immediately before it?

Checked all 10. Nine already do (confirmed in an earlier reviewer pass and re-verified here): `fig_architecture` (pipeline), `fig_boundary_schematic` (trust-boundary mechanism), `fig_whyfail` (concrete worked instance), `fig_layer_responsibility` (per-layer coverage), `fig_ite_coverage` (RQ1 table visualized), `fig_v25b_confusion_grid`/`fig_error_analysis`/`fig_v25b_roc` (RQ2 evidence, each preceded by the text establishing what it shows), `fig_sumo_stage` (RQ4 throughput/latency). **Gap found**: `fig_architecture_glance`, the paper's closing summary figure, appeared immediately after the Future Work paragraph with zero lead-in sentence — a reader would hit it with no signal that it is a deliberate closing summary rather than another limitations-adjacent figure. **Fixed**: added one sentence at the end of Future Work pointing to it explicitly as the loop back to the Architecture section's claims.

## 3. Does every table support the surrounding discussion?

Yes for all 8 — checked each against its immediately surrounding paragraph. `tab:trustboundary` (running example), `tab:notation` (equations that follow), `tab:ite_ablation` (RQ1 finding), `tab:v25b_ablation` (RQ2 ablation, now explicitly listing all 5 requested configurations with a stated reason for the 2 not evaluable on this benchmark, from the prior pass), `tab:v25b` (RQ2 checkpoint progression), `tab:veremi` (RQ3), `tab:carla` (RQ4), `tab:adaptive` (RQ5/limitations). No table sits disconnected from its surrounding prose.

## 4. Does the transition from Architecture → Results feel natural?

**Gap found and fixed.** Architecture's last subsection (Known Failure Modes) ended, and Methodology began immediately with reproducibility detail -- no sentence marked the shift from architecture's *proved* properties to the *empirical* evaluation that follows, which is precisely the shift this paper's whole design (Section~\ref{sec:novelty}: "Fusion does what it does with its inputs, not whether the inputs are correct") depends on the reader tracking. **Fixed**: added one bridging sentence at the start of Methodology ("Section~\ref{sec:architecture} proved what the fusion engine can and cannot do given its inputs; the remainder of this paper tests whether those inputs -- and the layers that produce them -- actually behave as designed against real attacks and real deployments").

## 5. Does every experiment have a clear purpose?

Yes. Every Results subsection already opens with a "What this proves" sentence (a house-style convention from an earlier pass, re-verified intact here), and every one now also states which RQ it answers, both at the start (implicitly, via subsection title) and end (explicitly, via "Answering RQ_n").

## 6. Is there any remaining sentence that references historical benchmark development or previous manuscript versions?

**None found.** Re-grepped the full manuscript for "v1," "STBV-Bench v1," "historical," and "previous benchmark" — zero matches outside the one disclosed, deliberate exception already flagged in `FINAL_V25B_ONLY_REPORT.md` (a training-data-provenance fact, not a benchmark discussion). Separately checked for "this pass" / "earlier pass" self-references (8 instances remain, e.g. "Hard-example mining, new in this pass," "an earlier pass caught and corrected a real measurement bug"): these all refer to *this evaluation campaign's own internal work order* (e.g., disclosing that adaptive-attack results weren't rerun against the final checkpoint), not to a prior benchmark generation or a previous version of this manuscript. They are load-bearing scientific-honesty disclosures, not historical-development narration, and are out of scope for this pass's "no experiments/figures/tables/equations modified" constraint — left unchanged.

## 7. Is every evaluation tied back to the central contribution ("Mitigating Inter-Layer Trust Boundary Vulnerabilities")?

Yes, structurally by design: RQ1 validates that the layers *closing* the inter-layer gap each contribute (the mechanism); RQ2 validates the specific layer (B3) that closes the semantic sub-boundary the Introduction and Threat Model define; RQ3 validates the framework doesn't regress on the boundary the existing layers already covered; RQ4 validates the mechanism survives contact with a real deployment; RQ5 is the honest accounting of what's still open. The added transition sentences (items 1 and 4 above) make this chain explicit at the two points where it wasn't previously stated in words, not just structurally implied.

## 8. Does the Conclusion directly answer every research question introduced earlier?

**Partially before this pass — fixed.** The Conclusion's evidence-summary sentence listed four findings (within-scope recall, generalization, kinematic coverage, adaptive-attack degradation) without labeling which research question each answered, and did not explicitly name RQ4 (deployment) as a question being answered at all — a reader would have to infer the CARLA/SUMO sentence was RQ4's answer. **Fixed**: the first Conclusion paragraph was rewritten (transition-only — no finding, number, or claim was added, removed, or altered) to explicitly tag each clause with its RQ number, and to explicitly frame the "what remains open" sentence as RQ5's answer.

## Every transition improved (summary list)

1. Methodology's opening sentence: added, bridging Architecture's proved properties to the empirical evaluation that follows.
2. Adaptive Attack Evaluation's opening sentence: added, framing it explicitly as RQ5 evidence rather than an unlabeled extra experiment.
3. Future Work's closing sentence: added, introducing `fig_architecture_glance` as the deliberate closing summary before the reader reaches it.
4. Conclusion's first paragraph: restructured (no content added/removed) to explicitly tag each evidence clause with the RQ it answers, RQ1 through RQ5.

## Confirmation

No experiment was modified. No figure was modified (no image regenerated, no data-bearing caption sentence changed). No table was modified (no row, column, or value changed). No equation was modified. All four changes above are additions of framing/transition sentences only, verifiable by diff against the pre-audit manuscript. Mechanical LaTeX audit re-run after all edits: 0 broken references, 0 duplicate labels, figure count unchanged (10), table count unchanged (8), all citations resolve.
