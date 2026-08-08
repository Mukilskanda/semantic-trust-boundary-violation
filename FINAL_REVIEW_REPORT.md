# Final Review Report

A simulated IEEE-reviewer audit of `stbv_paper.tex` after this pass's rewrite (restructured abstract, DeBERTa-v2 justification, honest B1/CP explanation, final-checkpoint ablation). This supersedes `REVIEWER_SIMULATION.md`'s findings where they've since been addressed, and carries forward what hasn't.

## Issues found and fixed this pass

1. **Weak novelty framing on architecture vs. datasets.** The prior draft's Introduction spent more space enumerating benchmarks than explaining the architecture. Fixed: Architecture (§IV) remains positioned before Methodology/Results, and the abstract now leads with the architecture and its provable-conservatism property rather than a benchmark list.
2. **Unclear justification for DeBERTa-v2.** No prior version explained the backbone choice beyond stating it. Fixed: added a dedicated justification paragraph (§IV) covering disentangled attention's fit for relational semantic attacks, latency constraints ruling out LLM classifiers (with our own zero-shot LLM measurement, F1=0.267, as direct evidence), and an honest report of the five-candidate backbone comparison — which does **not** show a clean DeBERTa-v2 win (the "better" candidates were near-degenerate always-positive classifiers on a 24-sample split). This is reported as "no evidence favoring a switch," not oversold.
3. **B1/B2 appearing weak or broken.** The ablation table's B1-only/B1+B2 rows (F1 undefined/0.034) previously appeared without explanation, inviting the reasonable reader objection "why include a component that does nothing?" Fixed: added an audited explanation, backed by real evidence (B1's own 137/137-passing unit test suite exercising exactly the attack classes STBV-Bench excludes by threat-model construction) rather than a hand-wave. This required checking, not assuming, that B1's low benchmark score doesn't hide an actual defect.
4. **Checkpoint inconsistency across tables.** Table I (ablation) was flagged as stale in the prior pass; it has now been re-run against the final checkpoint ($n{=}10{,}000$: B3-alone F1 1.000, full-stack F1 0.995).
5. **Missing broken-reference and citation issues.** `fig1.png` (referenced, non-existent) and two placeholder/duplicate bibliography entries were found and fixed in the prior pass; still resolved in this version.

## Issues found and NOT fixed (explicitly disclosed, not fabricated fixes)

1. **Adaptive-attack result (Table V) still describes the prior checkpoint.** Rerunning this against the final checkpoint was out of scope for this pass (it requires the full 51-seed, 10-round adaptive campaign, non-trivial compute); the paper explicitly labels this in both the caption and body text rather than presenting it as current.
2. **CARLA run-to-run instability remains unresolved**, not merely undisclosed. Two of ten scenarios (`normal_driving`, `goal_manipulation`) show materially different outcomes between two post-fix runs. We did not add more CARLA seeds this pass; the paper states this as an open limitation rather than picking whichever run looks better.
3. **Page count is not independently verified.** No LaTeX compiler is available in this environment. Word/table/figure-count estimate (~4,600 words, 6 tables, 6 figures) is consistent with approximately 7–7.5 pages in two-column IEEE conference format but has not been compiled and measured directly. This is the single largest remaining formatting risk: if a real compile shows >7 pages, further compression (candidate: trim the DeBERTa backbone-comparison paragraph to 2–3 sentences, or move the Discussion's "why X" paragraphs to a tighter enumerated list) would be needed.
4. **The backbone comparison (n=24) is too small to be a real architecture-selection signal**, and the paper says so explicitly rather than treating it as settled evidence. A reviewer may reasonably ask for a larger-scale rerun; this is left as future work, not attempted here given the freeze-phase "do not fabricate/rerun without cause" constraint.

## Remaining objections a real reviewer would likely raise

See `REVIEWER_OBJECTION_RESPONSE.md` for point-by-point responses to the strongest anticipated objections, framed as if received from a program committee.

## Writing/formatting spot-checks performed

- Acronym-on-first-use: PKI, MBD, CSIA, CP, STB/STBV, ASR, ECE all checked — consistent.
- No orphaned `\ref{}`/`\cite{}` keys (cross-checked against `\label{}`/`\bibitem{}` definitions).
- No duplicate table/figure numbers.
- Table captions state units and CI methodology where applicable (VeReMi table: 5-seed mean, stated in caption).
- Abstract length: the original journal-style abstract (`git show HEAD:stbv_paper.tex` at the start of this session) was 1,222 words in one dense paragraph; the version this pass replaced was already compressed to a conference-length abstract; the current version is 310 words, restructured as Problem → Gap → Architecture → Method → Findings → Impact. The reduction from this pass's immediate predecessor is smaller than 30% by exact count (word counts for the immediately-prior intermediate version were not separately logged), but the structural reformatting and net compression from the original are both substantial and verified by direct word count.
