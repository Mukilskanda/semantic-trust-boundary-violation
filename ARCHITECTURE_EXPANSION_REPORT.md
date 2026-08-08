# Architecture Expansion Report

**SUPERSEDED CHECKPOINT NOTICE**: the "actual final checkpoint" referenced below is `semantic_gate_v3_mixed_lora_continued_merged` (SHA-256 `bbae0512...`) — accurate when written, now superseded by `semantic_gate_v3_mixed_lora_hardmine_merged` (SHA-256 `d126cc3...`). The worked-example trust scores this report describes ($T_{Decision}=0.730$/$0.240$) were not regenerated against the new checkpoint this pass (no bug found to justify a rerun of a single illustrative example; the fusion *mechanism* they demonstrate is checkpoint-independent). See `HARDMINE_IMPROVEMENT_REPORT.md`.

Every technical/architectural change made in this pass, and how each was verified. This pass removed the page-budget constraint that shaped every earlier pass in this session, per explicit instruction.

## New content added

1. **Trust Boundary Analysis** (`sec:trustboundary`) — formal statement of what PKI/MBD/CP each verify and what none of them verify, with a running example (Table "Running Example") showing all three conventional checks passing on a real malicious message.
2. **Why Existing Architectures Fail** (`sec:whyfail`) — the conventional PKI→MBD→CP→Decision pipeline walked through explicitly, with a **real, freshly computed** trust score ($T_{Decision}=0.730$, ACCEPT) from running the actual final checkpoint with B1/B2/B3 disabled on the running example's message.
3. **Proposed STBV Trust Architecture** (`sec:whyworks`) — full 9-stage narrative (V2X Messages → PKI → B1 → MBD → B2 → CP → B3 → DS Fusion → Decision Engine → Adapters), each transition stated as "why the next stage is needed," with purpose/inputs/outputs/limitations for B1, MBD, B2, CP, and B3 individually.
4. **Expanded Dempster-Shafer theory** (`sec:dstheory`) — frame of discernment, mass assignment, belief, plausibility, conflict (new Eq. `eq:conflict`), classical Dempster's renormalization failure mode, discounting, Yager's rule, and confidence propagation to the pignistic decision — each concept given its own paragraph immediately preceding its equation, per the request that equations not be isolated.
5. **Why STBV Is Different** (`sec:novelty`) — five idea-level (not component-level) novelty claims: independent trust estimation, orthogonal trust dimensions, confidence-aware fusion, the Semantic Trust Boundary as a first-class design object, and provably (not just empirically) conservative decision making — plus an explicit "why not just add a detector" argument.
6. **Second major figure** (`fig_whyfail`, two-column TikZ) — the same malicious message run through both the conventional pipeline (real output: ACCEPT, $T_{Decision}=0.730$) and the full STBV pipeline (real output: REJECT, $T_{Decision}=0.240$), both numbers freshly computed against the final checkpoint, not asserted.
7. **Updated worked example** (Appendix, `app:worked`) — replaced the prior-checkpoint trace (B3 confidence 0.699, medium risk) with a fresh trace against the **final** checkpoint (B3 confidence 0.984, high risk), including full B1/MBD/B2 detail that was previously only partially shown, plus the new comparison run showing the conventional-pipeline-only ACCEPT result on the identical message.

## How the new numbers were obtained (not fabricated)

Every number in items 2, 6, and 7 above was obtained by directly invoking `pipeline.orchestrator.ISCEPipeline.run()` against the actual final checkpoint (`semantic_gate_v3_mixed_lora_continued_merged`) on a constructed message matching this repository's real CAM schema, run twice: once with the full stack (`enable_mbd=True, enable_cp=True, enable_b3=True`) and once with only PKI/MBD/CP active (`enable_b3=False`, `B1`'s structural checks are unconditional in the code and cannot be disabled independently — noted as such rather than glossed over). Raw JSON output was captured and transcribed into the manuscript without modification. This is a genuinely new evaluation of one message, not a rerun of any existing benchmark, and does not change any previously-reported aggregate metric.

## Verified against the implementation, not assumed

- The 9-stage pipeline order (PKI→B1→MBD→B2→CP→B3→fusion→decision→adapters) was checked against `pipeline/orchestrator.py`'s own numbered execution comments (0 through 7) before being narrated — confirmed exact match.
- CP's event-field limitation, MBD's cold-start blind spot, and B1's structural/fatal-check behavior were all re-stated from, not re-derived independently of, this project's own prior audits (`ABLATION_AUDIT.md`, `FAILURE_ANALYSIS.md`) to avoid introducing a second, possibly inconsistent description of the same mechanisms.

## Full consistency re-verification after all edits

Programmatic check (script run, not eyeballed): zero `\ref`/`\eqref` targets without a matching `\label`; zero `\cite` keys without a matching `\bibitem`; zero `\bibitem` entries never cited. Two labels (`sec:related`, `sec:conclusion`) remain self-unreferenced, unchanged from before this pass and not a new regression — sections do not require self-reference in IEEE style.

## What was explicitly NOT done, and why

- **No new figure regeneration** for existing figures (ROC, ablation summary, CARLA scene, SUMO stage) — no bug was found in any of them this pass; the previously-disclosed staleness note on the ablation summary figure (`fig_ablation`) is unchanged.
- **No rerun of any existing benchmark or aggregate metric.** The new pipeline invocations in this pass are single-message diagnostic runs used only for the worked example and the comparison figure; they do not replace or contradict any n=1,000+ evaluation reported elsewhere in the paper.
- **Page count is now explicitly out of scope** per this turn's instruction ("DO NOT think about page limits anymore"), so no compression was attempted; the manuscript is now ~9,000 words plus 7 figures and 7 tables, which will not compile to 7 pages and is not intended to.
