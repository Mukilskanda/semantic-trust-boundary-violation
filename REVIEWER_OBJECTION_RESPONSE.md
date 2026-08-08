# Reviewer Objection Response

Point-by-point responses to the strongest anticipated objections, written as if replying in a rebuttal phase. Each response states what was actually done, not what would be nice to claim.

---

**Objection 1 (Novelty).** "No individual component here is new — PKI, MBD, Dempster-Shafer fusion, and fine-tuned text classifiers all exist elsewhere. What exactly is the contribution?"

**Response.** We do not claim a new fusion rule, a new classifier architecture, or a new communication-trust mechanism. The contribution is the combination, applied to a threat class (semantic manipulation of authenticated V2X content) that, per our literature search, no prior work directly targets end-to-end with a provably conservative decision policy. We make this scoping explicit in §I and §II rather than implying broader novelty. If this framing is judged insufficient for the target venue's novelty bar, the paper's honest fallback claim is the CARLA synthesizer finding (§VI.D): a genuine, previously-undiscovered software defect that silently invalidated a class of live-deployment claims across every prior evaluation of this architecture, found specifically because this evaluation pipeline exists and was run live rather than only against static fixtures.

**Objection 2 (B1/B2 appear to contribute nothing).** "Table I shows B1 and B1+B2 near F1=0 — why include these layers in an architecture paper at all?"

**Response.** This is now addressed directly in §V (the paragraph immediately following Table I): B1's near-zero recall on STBV-Bench is a designed consequence of the benchmark's own threat model, which grants the attacker valid credentials specifically to isolate the semantic layer for evaluation — not evidence B1 fails to detect communication-layer attacks in general. We back this with B1's own unit-test suite (137/137 passing) exercising exactly the certificate-misuse/replay/structural attacks STBV-Bench excludes by construction. We did not construct a new mixed-threat benchmark to give B1 a "fair" F1 number in this pass (that would require new data-generation work outside this pass's scope), and we say so rather than imply the gap is closed.

**Objection 3 (Checkpoint inconsistency).** "Different tables in this paper describe different model checkpoints — how should a reader interpret F1 numbers that aren't from the same model?"

**Response.** This was a real gap, independently flagged by our own internal audit and simulated review. We closed it for Table I by rerunning the exact ablation against the final checkpoint (10,000 samples, ~34 minutes of compute) rather than leaving it as a caveat. We did **not** close it for Table V (adaptive attack), because that rerun requires the full iterative 51-seed/10-round campaign and was out of scope for this pass under the stated freeze policy ("do not rerun unless a real bug requires it" — no bug was found in the adaptive-attack result, only staleness). Table V is explicitly labeled throughout as describing the prior checkpoint. We consider this the single most important remaining action item before a camera-ready submission.

**Objection 4 (DeBERTa-v2 justification is thin / the backbone comparison doesn't actually favor it).** "Your own backbone comparison shows other models scoring higher F1 — why is DeBERTa-v2 still the right choice?"

**Response.** We report the comparison exactly as measured: four candidates scored a nominally higher F1 by predicting the malicious class unconditionally on a 24-sample, class-imbalanced test split, correctly identifying zero benign samples. This is a well-known failure mode of F1 as a summary statistic under class imbalance, not evidence those models understand the task better. Only the incumbent (DeBERTa-v2) discriminated between classes at all on this split. We explicitly do not claim this proves DeBERTa-v2 is optimal — we state "no evidence favoring a switch" and flag the small sample size as a real limitation of this specific check. The architectural argument (disentangled attention suits relational semantic assertions; latency budget rules out LLM-scale classifiers, backed by our own F1=0.267 zero-shot LLM measurement) stands independently of this small-sample check.

**Objection 5 (CARLA results are unstable, so what do they actually show?).** "Two of ten CARLA scenarios show materially different outcomes between runs — how can Table IV's numbers be trusted?"

**Response.** They should be trusted only to the extent disclosed: the six scenarios that are stable across both post-fix runs (`accident`, `emergency_vehicle`, `road_closure`, `replay_attack`, `sybil_attack`, `semantic_manipulation`) and the two headline fixed-scenario outcomes (`authority_override`, `false_hazard_clearance`, both stable and both flipped from ACCEPT to REJECT post-fix) are reproducible findings. `normal_driving` and `goal_manipulation` are explicitly marked "unstable" in Table IV rather than reported as a single number presented as settled. We traced the instability to CARLA's unseeded traffic manager via code-path separation (B1/MBD never consume the text our fix touched), ruling out our fix as the cause, but we did not resolve the instability itself — that requires a multi-seed rerun matching this architecture's own previously-established 15-run CARLA protocol, not attempted in this pass.

**Objection 6 (Page count / formatting not verified).** "You claim a 7-page target but haven't shown a compiled PDF."

**Response.** Correct, and disclosed as such in `FINAL_FREEZE_AUDIT.md` and `READY_FOR_SUBMISSION.md`: no LaTeX compiler is available in this working environment. The word/table/figure count is consistent with the target but is an estimate. This is stated as an open action item, not claimed as verified.
