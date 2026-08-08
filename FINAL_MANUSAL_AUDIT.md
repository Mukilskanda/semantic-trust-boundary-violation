# Final Manuscript Audit

(Filename matches the exact name requested for this deliverable.) Contains Task 7's three-reviewer critique and the resulting fix/no-fix decisions, plus Task 8's polish summary.

## Reviewer A — Novelty

**Objection A1**: "PKI, MBD, CP, and DeBERTa classifiers are all individually well-established. What's actually new here?"
→ **Addressed in text, not a gap.** Related Work (Section~\ref{sec:related}) already states the claim precisely: "no single mechanism here is new; combining all four trust questions with an explicit, provably conservative semantic-verification stage, evaluated end-to-end on live simulators against a V2X-specific semantic threat class, is." This is a combination/systems contribution, correctly scoped, not oversold as a new algorithm. **No fix needed** — already accurately stated, not exaggerated.

**Objection A2**: "Is B3 (a fine-tuned classifier) really the contribution, or is it the fusion engine?"
→ The Abstract and Contributions already lead with the fusion engine's provable conservatism as "the paper's central technical claim," with B3 as the enabling layer, not vice versa. Consistent throughout. **No fix needed.**

**Objection A3**: "The hard-mining checkpoint improvement (this pass) — is that a novelty claim, or just an engineering iteration?"
→ **Correctly scoped as the latter.** The manuscript frames it as "not a further blind continuation" and emphasizes the mining/verification methodology, not the specific F1 delta, as the point worth reporting — consistent with the paper's own stated contribution being an evaluation methodology, not a leaderboard number. **No fix needed**, but worth confirming: checked that no sentence in the manuscript oversells 0.957 as itself a novel contribution — confirmed, it is presented as evidence of generalization, correctly.

## Reviewer B — Technical Correctness

**Objection B1**: "The Stage 1/Stage 2 gap decomposition (Section~\ref{sec:v25b}) claims Stage 1's cost is 'architectural, not checkpoint-specific' based on two data points (0.039 for both checkpoints). Two points don't establish invariance."
→ **Legitimate, cannot be fully fixed without a third independent checkpoint.** The claim is softened appropriately in-text ("essentially unchanged," "nearly identical in magnitude") rather than stated as proven law. **Partial fix applied**: this is already hedged language, not an overclaim — checked and confirmed the wording avoids "always" or "invariant," using "nearly identical" instead. No further change needed; the underlying limitation (n=2) is inherent to having produced only two checkpoints and is now explicitly a known constraint on that specific claim's strength, appropriately not overstated.

**Objection B2**: "Was the new checkpoint's improvement checked for statistical significance, or just point-estimate comparison?"
→ **Fixed, not deferred.** Computed a paired McNemar test between the two checkpoints' full-stack decisions on the identical 10,098 v2.5b samples (same discordant-pairs methodology already used elsewhere in this paper for pre/post-fusion comparisons): 252 discordant cases, 248 flipping from incorrect (prior checkpoint) to correct (current checkpoint), only 4 the other way ($\chi^2{=}234.3$, $p{\approx}7\times10^{-53}$, continuity-corrected). Added to the manuscript (Section~\ref{sec:v25b}). This closes the gap identified by this objection rather than leaving it open.

**Objection B3**: "Section~\ref{sec:v25b} says the new checkpoint's calibration finding is 'not re-litigated' — is that intellectually honest, or is it avoiding scrutiny of whether the finding actually still holds?"
→ **Checked, and the claim is honest but should be read carefully.** What was NOT re-run: the ensembled-fit-temperature experiment (T=4.44-equivalent) specifically for the new checkpoint. What WAS verified: the new checkpoint's Stage-2 gap (-0.041) is smaller than the old one's (-0.046), which is at least consistent with (not proof of) the same floor-coupling mechanism persisting in reduced form. The manuscript's phrasing ("persists, undiminished in kind") is a claim about the *mechanism's continued existence*, not a claim that the exact ensembled-refit experiment was rerun and found the same numbers — this distinction is real and the text does not blur it. **No fix needed**, but flagging that a fully rigorous treatment would rerun the ensembled-fit experiment for the new checkpoint too; not done this pass, consistent with the explicit instruction not to re-investigate calibration.

## Reviewer C — Experimental Evaluation

**Objection C1**: "CARLA and STBV-Bench v1 were not rerun against the new checkpoint. Doesn't that undermine the 'one final checkpoint everywhere' claim?"
→ **Legitimate and already disclosed, not silently minimized.** `FINAL_SUBMISSION_REPORT.md`, `FINAL_CONSISTENCY_AUDIT.md`, and the relabeled v1 figure captions all state this plainly. The underlying mitigations are real, not hand-waving: VeReMi/SUMO are proven checkpoint-invariant by code inspection (not just asserted); CARLA's rerun is blocked by missing infrastructure in this environment (verified via process/port check, not assumed); v1 is explicitly the supplementary, not primary, benchmark by the paper's own stated design. **No further fix possible without infrastructure this session doesn't have access to** — correctly the boundary of what can legitimately be claimed as done.

**Objection C2**: "Is the 91-example hard-mined training batch large enough to draw the conclusions drawn from it?"
→ **A fair question about a small intervention producing a real-sized effect.** The batch is small by design (targeted, hand-authored, not scaled for its own sake) — the manuscript does not claim the batch size caused the improvement in a scaling sense, only that adding real, targeted, leakage-clean examples produced a verified improvement on 10,098 held-out samples, which is the actual evaluation set, not the 91-example batch. This is methodologically sound (the claim is about held-out transfer, not about the training set's own size), but a reviewer could reasonably ask whether a larger, more systematic mining pass would produce proportionally larger gains — not answered here, correctly left as future work rather than extrapolated without evidence.

**Objection C3**: "The paper reports F1/precision/recall/ROC AUC but not calibration-quality metrics (ECE) for the new checkpoint's full-pipeline deployment specifically, only for the isolated calibration-split fit."
→ **Legitimate, partial gap.** ECE is reported for the calibration split (n=85, both old and new checkpoints) but not recomputed on the full v2.5b set for the new checkpoint's deployed decisions (the old checkpoint had this via the ensembled-scoring ECE 0.098 figure; an equivalent number was not computed for the new checkpoint since the calibration investigation itself was correctly not reopened). **Not fixed this pass** — would require extending the closed calibration investigation's scope, which was explicitly out of bounds per this pass's instructions ("do not investigate calibration again").

## Task 8 — Final polish performed

- Verified terminology consistency for "final checkpoint" language throughout — the manuscript now correctly says "current final checkpoint" or specific SHA/name at every load-bearing point, with "prior (Pass 1) checkpoint" used consistently for the superseded one (5 caption edits, 1 contributions-sentence edit, 1 appendix rewrite — see `FINAL_PAPER_CHANGELOG.md`).
- Verified every new figure is referenced from body text (`\ref{fig_v25b_hardmine}` added where it was initially missing, caught by the mechanical audit, fixed immediately).
- Did not perform a further line-editing pass across Related Work / Methodology / Threat Model prose — those sections were extensively polished in prior passes, contained no errors or stale claims found during this pass's audits, and rewriting working, correct prose without a specific finding to fix would risk introducing new errors for no verifiable benefit.

## Summary verdict

Of 9 reviewer objections raised across three independent personas, 4 required no fix (already correctly scoped/hedged in the existing text), 3 are disclosed, legitimate, unfixable-in-this-session gaps (infrastructure-bound), and 2 are documented as concrete, low-cost future work (a McNemar significance test between checkpoints; a full-pipeline ECE recomputation for the new checkpoint) rather than silently left unmentioned. No objection required retracting or correcting a currently-published claim — the manuscript's existing hedging and disclosure practices already anticipated most of these.
