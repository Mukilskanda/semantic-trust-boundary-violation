# Final Changelog

**SUPERSEDED CHECKPOINT NOTICE**: entries below refer to `semantic_gate_v3_mixed_lora_continued_merged` (SHA-256 `bbae0512...`) as "the final checkpoint" — accurate when written, now superseded by `semantic_gate_v3_mixed_lora_hardmine_merged` (SHA-256 `d126cc3...`). See `FINAL_PAPER_CHANGELOG.md` for the changes made when the checkpoint was superseded, and `HARDMINE_IMPROVEMENT_REPORT.md` for the current checkpoint's record.

Chronological record of every substantive change made across this publication-finalization session, in the order performed. Each entry states what changed, why, and how it was verified. This supersedes the prior version of this file, which documented an earlier manuscript-integration pass; that history is preserved in git, not deleted.

## 1. New held-out benchmark: STBV-Bench v2.5b
- Added `benchmark/v25b_compositional.py` (new template bank) and `benchmark/stbv_bench_v25b.py` (generator).
- Generated `data/stbv_bench/v25b/stbv_bench_v25b.jsonl` (n=10,098).
- Verified `TEMPLATE_DISJOINT` against v2.5 (0 exact/template-id overlap, max 4-gram containment 0.53) — after an initial draft was found to contain 10 near-verbatim copied templates from v2.5, manually rewritten and re-verified.

## 2. New training-augmentation corpus: STBV-Bench v2.5c
- Added `benchmark/v25c_compositional.py`, `benchmark/stbv_bench_v25c.py`.
- Generated `data/stbv_bench/v25c/stbv_bench_v25c.jsonl` (n=6,097), verified disjoint from **both** v2.5 and v2.5b.

## 3. True adapter-resume continued fine-tuning
- Added `b3_eval/v25_finetune/build_continued_corpus.py`, `train_lora_continue.py`, `merge_continued_lora.py`, `calibrate_final_checkpoint.py`.
- Resumed (not reinitialized) the `semantic_gate_v3_mixed_lora` adapter on the original mixed corpus + v2.5c. Val F1: 0.9006 → 0.9241 (epoch 5).
- Merged to `semantic_gate_v3_mixed_lora_continued_merged`, SHA-256 `bbae05120439774f724dcce205be71b79d1720e4f0edb47cdb4cc793849a9b1a`.
- Refit calibration temperature: 2.82 (ECE 0.065→0.053).
- Verified genuine generalization: F1 on held-out v2.5b improved 0.918→0.945 (`eval_v25b_final.py`).
- Updated `isce_config.yaml`'s `b3_semantic_gate.model_path` and `temperature_scaling` to the final checkpoint.

## 4. VeReMi evaluation
- Ran `run_veremi_evaluation.py` against ConstPos/DataReplay/DoS (5 seeds each) → `results/veremi_final/`.

## 5. CARLA synthesizer bug: discovery and fix
- Discovered via direct text-capture instrumentation that B3 received no attack content on ego-asserted CARLA attack scenarios.
- Root-caused to `pipeline/synthesizer.py`: `SceneEvidence` never captured the ego vehicle's own `event` field.
- **Fix**: added `ego_event` field to `SceneEvidence`, populated in `_extract_evidence()`, rendered in `_render_default`, `_render_narrative`, `_render_structured`.
- Verified: 188/188 pipeline tests pass post-fix (77/77 in `test_synthesizer_leakage.py`).
- Reran CARLA twice post-fix; confirmed `authority_override`/`false_hazard_clearance` now correctly flagged MALICIOUS by B3 (previously BENIGN); confirmed `sybil_attack`/`semantic_manipulation` remain B3-BENIGN even post-fix (disclosed as an open gap, not hidden).
- Confirmed, by code-path inspection, that observed CARLA run-to-run instability on `normal_driving`/`goal_manipulation` is **not** caused by the fix (B1/MBD never consume synthesized text).

## 6. First manuscript rewrite (compressed 7-page conference paper)
- Switched `stbv_paper.tex` from `\documentclass[journal]{IEEEtran}` to `\documentclass[conference]{IEEEtran}`.
- Compressed from the original ~1,081-line, ~1,222-word-abstract journal draft to a conference-length paper retaining only: architecture, threat model, layer ablation, STBV-Bench v1, STBV-Bench v2.5b, VeReMi, CARLA (with bug narrative), SUMO, adaptive attack.
- Found and fixed a broken figure reference (`fig1.png`, did not exist) — replaced with `deployment_eval/carla_figures/fig5_architecture.png`.
- Found and fixed two bibliography placeholders (`b7`: "[Citation key to be verified]"; `b9`: flagged duplicate title with `b1`).
- Produced `FINAL_FREEZE_AUDIT.md`, `REVIEWER_SIMULATION.md`, `READY_FOR_SUBMISSION.md`.

## 7. Closed the checkpoint-consistency gap for Table I
- Added `b3_eval/v25_finetune/rerun_ablation_configs45_final.py`.
- Reran STBV-Bench v1's B3-alone/full-stack configs against the final checkpoint (n=10,000, ~34 min).
- Result: B3-alone F1 0.9999→**1.000**; full-stack F1 unchanged at 0.995 (69 discordant decisions, all escalations).
- Updated Table I in `stbv_paper.tex`, `FINAL_FREEZE_AUDIT.md` §2/§5, `READY_FOR_SUBMISSION.md`.

## 8. Second manuscript rewrite (this pass): architecture-forward, DeBERTa justification, B1 explanation
- Rewrote the abstract into the requested Problem→Gap→Architecture→Method→Findings→Impact structure (310 words, down from the original 1,222-word journal abstract).
- Added a DeBERTa-v2 justification paragraph in §IV, citing: (a) latency infeasibility of LLM classifiers (our own F1=0.267 zero-shot measurement), (b) disentangled attention's fit for relational semantic attacks, (c) the real five-candidate backbone comparison from `MANUSCRIPT_RESULTS_DISCUSSION.md` §R9 — reported honestly as inconclusive on a small split (n=24), **not** oversold as a clean win, after an initial draft incorrectly described a different, fabricated comparison (BERT/RoBERTa/ELECTRA/DeBERTa-v2) that was caught and corrected before this document was finalized.
- Added an audited explanation of B1/CP's near-zero ablation contribution, backed by B1's own 137/137-passing unit-test suite (`b1_scsv/test_bad_actors.py` et al.), directly answering why B1/B2 appear "almost useless" in the ablation table without fabricating a new mixed-threat benchmark.
- Produced this document, `FINAL_REVIEW_REPORT.md`, `REVIEWER_OBJECTION_RESPONSE.md`.

## Self-correction logged during this session (transparency)

- **v2.5b template near-duplication**: first draft of `v25b_compositional.py` contained 10 templates too close to v2.5's originals; caught by automated cross-corpus string comparison, rewritten, re-verified before use.
- **DeBERTa backbone comparison fabrication**: first draft of the DeBERTa justification paragraph cited a comparison (BERT-base/RoBERTa-base/ELECTRA-base/DeBERTa-v2) that does not exist in this repository. Caught before finalizing this document by cross-checking against `MANUSCRIPT_RESULTS_DISCUSSION.md`'s actual §R9 experiment, and corrected to describe the real five-candidate comparison and its real, more nuanced (non-clean-win) result.

## 9. Ablation redesign: ITE-Bench (this pass)
- Audited why B1/B2 appeared near-useless in the original ablation (`ABLATION_AUDIT.md`). Found two causes, not one: (a) STBV-Bench v1's threat model deliberately grants attackers valid credentials (already known, now backed by B1's 137/137-passing unit-test suite), and (b) a previously-undiscovered evaluation-protocol bug — the ablation harness only ever validated the last message in a window through B1 and explicitly excluded same-sender messages from MBD's history pre-population, so history-dependent checks in either layer could never fire regardless of benchmark content.
- Built `ite_bench/build_ite_bench.py`: a new ~9,900-sample benchmark (Integrated Trust Evaluation Benchmark, ITE-Bench) balanced across real, verified-triggering B1 attacks (invalid certs/coordinates/speed/heading, replay, identity spoofing, cert-rotation churn), B2 attacks (kinematic jumps, Sybil, collusion, temporal replay), and B3 attacks (reusing the existing audited semantic taxonomy).
- Caught and fixed a real bug during construction, before any evaluation: an early draft's benign B2 windows used unrealistic near-zero position deltas, spuriously triggering MBD's "constant position vs. claimed speed" check on legitimate traffic. Fixed with a kinematically-consistent displacement helper; re-verified via smoke test.
- Built `ite_bench/run_ite_ablation.py`: a corrected evaluation protocol (sequential per-message calls on one persistent pipeline per config per sample), verified via direct code inspection and smoke testing to actually exercise B1's and MBD's stateful checks, unlike the original harness.
- Ran the full 5-config ablation (9,900 samples × 5 configs, 5,430s / ~90.5 min). First attempt appeared to hang with zero progress output for over an hour; diagnosed via direct profiling (confirmed GPU was genuinely computing, confirmed `run_all_configs()` worked correctly on isolated samples) before discovering the issue was a monitoring/log-path error, not an actual stall — the run had been progressing normally the whole time.
- Result: clean defense-in-depth signature — each layer reaches 1.000 recall within its own designed threat class and exactly 0.000 outside it; enabling any layer never costs recall elsewhere (McNemar: 3,885 and 2,707 discordant decisions respectively, zero reversals in either comparison, both $p<10^{-15}$).
- Updated `stbv_paper.tex`: new Section~\ref{sec:itebench} with real numbers, updated Discussion "Strengths" paragraph, trimmed the now-partially-redundant original B1/CP explanation paragraph, strengthened Architecture section's defense-in-depth framing, compressed Methodology's benchmark descriptions further, fixed a stale "84" decision-count reference to the already-corrected "69".
- Updated `FINAL_FREEZE_AUDIT.md` (new §8) and `READY_FOR_SUBMISSION.md` to reflect this pass.

## 10. Cross-reference audit (this pass)
- Programmatic check found 5 figures (`fig_pipeline`, `fig_ablation`, `fig_roc`, `fig_carla_scene`, `fig_sumo_stage`) and 1 equation (`eq:bba`) that were captioned/labeled but never pointed to from body text via `\ref`/`\eqref` — a real formatting gap a reviewer would flag ("Figure 3 is never mentioned in the text"). Fixed by adding inline pointers at the relevant discussion points.
- While fixing `fig_ablation`'s pointer, caught that its underlying plot (`FINAL_FIGURES/fig_ablation_summary.pdf`) predates this session's final-checkpoint ablation rerun and shows the old B3-alone F1 (0.9999) rather than the current 1.000 — not regenerated (no plotting infrastructure invoked this pass); disclosed directly in the figure's caption rather than left silently inconsistent with Table I's authoritative value.
- Verified via script: zero `\ref`/`\eqref` targets are undefined; zero figure/equation/table labels remain unreferenced.

## 11. Reviewer #2 audit and architecture-centric rebalancing (this pass)
- Wrote `REVIEWER_2_OBJECTIONS.md`: a pre-edit "try to reject this paper" objection list, each item marked FIXED (this pass), ALREADY ADDRESSED (prior pass), or OPEN (genuine, disclosed limitation) — including an explicit statement of what this pass deliberately did NOT attempt (new experiments without a discovered bug, ITE-Bench expansion without a specific gap to close, new figure generation this environment cannot originate) and why.
- Added a new Architecture subsection, "Why Three Trust Layers?", giving the four-question framing (can I trust the sender / the behavior / the meaning / what is the safest decision) explicitly, rather than leaving it implicit across separate paragraphs.
- Rewrote the abstract to lead with the architecture's four-question decomposition and its provable conservative-fusion property before naming any benchmark, moving specific dataset names into a single supporting clause rather than structuring the abstract around them.
- Rewrote the conclusion with the same architecture-first framing: opens with "This paper's contribution is an architecture, not a benchmark score," restructures every subsequent sentence as "the architecture predicts X, and the experiment confirms it" rather than leading with each benchmark's number.
- Re-verified cross-reference integrity after these edits (zero unresolved refs, zero unreferenced labels).
- **Declined, with reasons stated in `REVIEWER_2_OBJECTIONS.md`**: redesigning/regenerating figures (no diagram-generation tooling used this session; would be fabricated if claimed), expanding ITE-Bench further (already demonstrates the required property cleanly), rerunning CARLA/SUMO/VeReMi (no new bug found this pass to justify it under the standing freeze policy).

## 12. Final pre-submission quality pass (this pass)
- Found and fixed two genuine duplicate-citation defects: `b7`/`b8` were the same paper (Yuce, "Misbehavior Detection With Collective Perception in V2X Networks") cited together as if two distinct supporting sources for one claim — consolidated to `b7` alone. `b9`/`r_cp_fabrication` were the same paper (Zhang et al., USENIX Security, data fabrication in collaborative vehicular perception) cited under two different keys in two different sections — consolidated to `r_cp_fabrication` throughout.
- Converted the Related Work comparison table to prose (same comparative content, same citations, no table), reducing the table count from 7 to 6 and freeing space for the paper's actual experimental content, since a qualitative literature checklist is lower-value real estate in a 7-page conference paper than the empirical results it was competing with.
- Verified citation/bibliography integrity programmatically after these edits: zero `\cite{}` keys without a matching `\bibitem{}`, zero `\bibitem{}` entries never cited.
- Wrote `FINAL_REVIEWER_SCORECARD.md`: an explicit /10 rubric (novelty, technical depth, experimental quality, presentation, reproducibility) with a stated overall recommendation and, critically, an explicit explanation of which scores were deliberately NOT pushed to 10/10 and why — to avoid the trap of asserting a fix (e.g., "adaptive-attack rerun done") that was not actually performed just to inflate a self-assessment.

## 13. Architecture-completion pass (this pass) — scoped against the standing 7-page budget
- Added an honest "why existing pipelines admit this attack" paragraph to the Threat Model, explaining that PKI/MBD/CP are each individually correct but blind between stages, pointing to a real worked example rather than asserting the claim abstractly.
- Restored a real, previously-cut worked fusion example (new Appendix~B, `app:worked`) from the original pre-compression manuscript: an unedited pipeline trace showing B1/MBD/B3's actual per-layer output and the Trust Decision Engine's verbatim logged Dempster-Shafer/Yager reasoning on one message, step by step. Explicitly disclosed that this trace predates the final checkpoint and was not regenerated against it (no bug found to justify a rerun) — the fusion *mechanism* it demonstrates is checkpoint-independent (a property of the decision engine, not B3's weights), but B3's specific confidence value is not re-verified.
- Added explicit answers to two reviewer questions not previously addressed head-on: "why not one model reading everything" (no equivalent to the conservative floor-rule guarantee; each layer's logic doesn't need training data) and "why not semantic detection alone" (Table~III already shows B3 contributes zero to real kinematic-attack detection — semantic-only is blind to an entire real attack class).
- Re-verified full manuscript consistency after these additions: zero unresolved refs/cites, zero unreferenced labels.

**Scope decision, stated explicitly**: this request's Parts 1, 3, 4, and 5 asked for a much larger expansion (full traditional-pipeline exposition with per-component math, per-layer purpose/inputs/outputs/mathematics/failure-case breakdowns for B1/B2/B3/fusion individually, an expanded belief/plausibility/discounting treatment of Dempster-Shafer theory) that directly conflicts with this same project's standing instruction, repeated across multiple earlier passes in this session, to compress the manuscript to approximately 7 pages. Rather than silently picking one side, this pass added the highest-value new content (the attack-flow motivation, the restored worked example, the two remaining FAQ answers) within the existing budget and left the larger structural expansion undone — flagged here for the user to explicitly resolve (either accept the 7-page framing as final, or lift the page constraint and request the fuller expansion as a deliberate, budget-aware follow-up).

## 14. Architecture figure redesign (this pass)
- Replaced the raster architecture figure (`deployment_eval/carla_figures/fig5_architecture.png`) with a native vector TikZ diagram embedded directly in `stbv_paper.tex`, added `\usepackage{tikz}` + `\usetikzlibrary{arrows.meta,positioning,fit,backgrounds}` to the preamble.
- Diagram distinguishes the existing V2X trust stack (PKI, MBD, CP -- light solid boxes) from this paper's additions (B1, B2, B3, Dempster-Shafer/Yager fusion, Trust Decision Engine -- shaded boxes inside a dashed "Proposed STBV Trust Framework" region), with small italic per-stage labels (Identity Trust, Cryptographic Trust, Behaviour Observation, Behaviour Explainability, Cooperative Scene Fusion, Semantic Trust, Evidence Fusion, Final Risk Decision).
- **Verified the requested stage order (PKI→B1→MBD→B2→CP→B3→fusion→decision) against `pipeline/orchestrator.py`'s actual numbered execution comments (0. PKI, 1. B1, 2. MBD, 3. B2, 4. CP, 5/6. B3, 7. Trust Decision Engine) before drawing it** — confirmed exact match, not assumed.
- **Corrected one inaccuracy in the requested diagram text**: the user's draft labeled B3 as "DeBERTa-v3 Semantic Analysis"; the actual deployed model, throughout this paper and its checkpoint provenance, is DeBERTa-v2 (v3 was one of the *rejected* candidates in the backbone comparison, Appendix~A). Kept as DeBERTa-v2 in the figure rather than silently propagating the inaccuracy.
- Also produced two standalone deliverables per the request's explicit "PDF and SVG" export ask: `figures_src/fig_architecture.svg` (hand-authored vector SVG, validated as well-formed XML) and `figures_src/fig_architecture_standalone.tex` (a `standalone`-class TikZ source, same diagram body as the in-paper figure, compiles independently via `pdflatex` to a native vector PDF).
- **Disclosed limitation**: no LaTeX toolchain is available in this environment (consistent with every earlier pass in this session), so neither the standalone PDF nor a rendered preview of the in-paper TikZ figure was actually produced/verified by compilation here -- the source is syntactically standard TikZ (simple rectangle/arrow flowchart, no exotic packages beyond the three listed libraries) but has not been compile-tested. The attack-flow comparison diagram (traditional pipeline ACCEPTs vs.\ STBV pipeline REJECTs the same message) requested in the same turn was not built this pass, given the page-budget tension already flagged in changelog entry 13 and the added weight of an already-large new figure; noted here as an open item pending the user's page-budget decision.

## 15. Full architecture expansion pass, page limit lifted (this pass)
- Per explicit instruction, the ~7-page budget that shaped every earlier pass in this session no longer applies to this pass.
- Added six new subsections/sections (Trust Boundary Analysis, Why Existing Architectures Fail, Proposed STBV Trust Architecture, expanded Dempster-Shafer theory with frame of discernment/belief/plausibility/conflict/discounting, Why STBV Is Different) and a second major two-column TikZ figure (`fig_whyfail`) comparing the conventional and STBV pipelines on the identical message.
- **Generated genuinely new evidence for this pass**: ran the actual final checkpoint twice on a real constructed message (once full-stack, once with only PKI/MBD/CP active) via direct `ISCEPipeline.run()` invocation, capturing real JSON output used verbatim in the new running example, the new comparison figure, and the rewritten Appendix worked example (which previously used a prior-checkpoint trace — the user explicitly asked for the final implementation, so it was regenerated, not merely relabeled).
- Verified the 9-stage pipeline narrative against `pipeline/orchestrator.py`'s own numbered execution order before writing it (0–7 exact match), not assumed from memory of an earlier pass.
- Full manuscript now ~9,000 words, 7 figures, 7 tables — page count is explicitly out of scope for this pass per instruction, not tracked.
- Produced `ARCHITECTURE_EXPANSION_REPORT.md` documenting every change and how each new number was obtained.

## 16. Reviewer-proofing pass: Table I audit and new architecture sections (this pass)
- **Investigated, rather than assumed, why B3-alone F1=1.000 on STBV-Bench v1.** Checked five candidate explanations (exact-duplicate leakage, template-family leakage, threshold effects, calibration, benchmark separability) against direct evidence in the repository. Confirmed the real mechanism: the final checkpoint's training data includes a stratified slice of the same 100,000-row v1 corpus file, drawn from `rows[10000:]` (`build_mixed_corpus.py` line 57), disjoint by row index from the evaluated `rows[0:10000]` but built from the same finite, seeded template bank — template-family exposure, not sample-level leakage. Wrote `TABLE_II_AUDIT.md` documenting the full investigation and ruling out the other four candidates with specific evidence.
- Added one precise sentence to the manuscript's Limitations section citing this exact mechanism, replacing the previous, less specific "same generator family" hedge — the reported F1=1.000 value itself was **not** changed, since it is the correct, real output of the final checkpoint.
- Verified Table II (ITE-Bench per-layer recall) already satisfies the requested "grouped by attack category so B1/B2/B3's roles are immediately clear" design — no table redesign was needed, confirmed and documented rather than redesigned for its own sake.
- Added Algorithm 1 (pipeline pseudocode, a direct transcription of `ISCEPipeline.run()`/`TrustDecisionEngine.decide()`, verified line-correspondence), a System Assumptions subsection, a Computational Complexity subsection (Big-O per layer plus **real measured per-stage latency figures pulled directly from this session's own final-checkpoint SUMO run** — PKI 0.001ms, B1 0.223ms, MBD 0.202ms, B2 0.059ms, CP 0.034ms, synthesizer 0.344ms, B3 80.20ms, fusion 0.089ms — not estimated, not from an older run), a Notation table, and a Known Failure Modes subsection.
- Wrote `FINAL_REVIEWER_CHECK.md` answering all ten requested questions explicitly.
- Re-verified full manuscript consistency after all edits: zero broken refs/cites/labels.
- **No metric, threshold, or previously-reported value was changed anywhere in this pass** — every change was additive explanation or new architectural content, consistent with the task's explicit "not to maximize numbers" objective.

## 17. Final publication pass: v2.5b as primary benchmark, real figure generation (this pass)
- **Corrected a checkpoint-identity error in the request**: it named `semantic_gate_v3_mixed_lora_merged` (the pre-continuation checkpoint) as final. Used the actual final checkpoint (`semantic_gate_v3_mixed_lora_continued_merged`) throughout instead of silently complying.
- **Made STBV-Bench v2.5b the primary semantic benchmark**, repositioning STBV-Bench v1 as historical/supplementary, per explicit instruction.
- **Ran a genuinely new experiment**: full 5-config ablation (B1/B1+B2/B1+B2+CP/B3-alone/full-stack) on v2.5b against the final checkpoint, 10,098 samples, ~67 minutes.
- **Found and investigated a real discrepancy** rather than reporting only the favorable number: the new full-pipeline F1 on v2.5b (0.860) is notably lower than the existing direct-classifier F1 (0.945) on the identical checkpoint and benchmark. Traced the cause by instrumenting the actual text B3 receives inside the full pipeline — confirmed it is a synthesized scene report wrapping the raw v2.5b text in a telemetry/sensor-status preamble, not the raw text itself. Reported both numbers with the mechanism explained, not reconciled by assumption.
- **Discovered matplotlib was available** in this environment (previously undetermined) and generated 6 new/regenerated real PDF figures from real per-sample data already on disk: confusion matrix, ROC+PR, score distribution, calibration curve, decision-transition bar chart, per-family recall heatmap.
- **Caught and fixed a real bug while building the ROC/PR figure**: the first attempt plotted the classifier's raw "confidence" field (confidence in whichever label was predicted) instead of P(malicious) specifically, producing a corrupted AUC of 0.893 and a negative PR-AUC from an integration sign error. Fixed by computing P(malicious) via a fresh forward pass; corrected AUC=1.000 matches the previously-reported value exactly.
- **Removed a false claim caught during figure integration**: a calibration figure caption initially asserted "a previously-reported ECE of 0.017" for comparison — checked and found this number does not actually appear anywhere else in the current (compressed) manuscript, only in an earlier pre-compression draft. Corrected the caption to compare against the actually-present fitting-time ECE figure (0.053) instead.
- Declined to build several requested figures (Sankey diagram, DS evidence-flow diagram, multi-axis radar chart) with explicit reasoning in `FINAL_FIGURES_REPORT.md` — the radar chart specifically was declined because combining unlike-unit metrics (F1, milliseconds, qualitative judgments) into one chart would require inventing an unjustified scoring rubric.
- Produced/updated `FINAL_RESULTS.md`, `FINAL_FIGURES_REPORT.md`, `FINAL_CONSISTENCY_AUDIT.md`, `FINAL_SUBMISSION_CHECKLIST.md` (the latter two superseding stale versions from an earlier work phase that itself carried the same incorrect checkpoint-identity premise this request repeated — confirming the correction was warranted).
- Full manuscript re-verified after all edits: zero broken refs/cites/labels, zero duplicate labels.

## Items explicitly NOT done this session (disclosed as open, not silently skipped)

- Adaptive-attack campaign (Table V) not rerun against the final checkpoint.
- CARLA run-to-run instability not resolved (would require a multi-seed rerun).
- LaTeX not compiled; page count not independently verified (now more likely to exceed 7 pages given the ablation redesign's added content — see `READY_FOR_SUBMISSION.md`).
- b7/b9 bibliography substitutions not verified against real published sources.
- ITE-Bench's B2 windows are synthetic, not drawn from real vehicular trajectory data (disclosed in `ABLATION_AUDIT.md` §5).
- No git commit was made of any change in this session — all changes are in the working tree only.
