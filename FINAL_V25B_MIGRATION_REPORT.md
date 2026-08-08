# Final v2.5b Migration Report

## Task 1 — Audit of every v1 reference (produced before any edit was made)

19 occurrences of "STBV-Bench v1" / "STBV v1" in `stbv_paper.tex` at the start of this pass, classified:

| # | Location | Content | Classification | Action |
|---|---|---|---|---|
| 1 | Contributions (ii) | Lists "STBV-Bench v1 (n=10,000) and ... v2.5b" | **Obsolete ordering** — v1 named first, v2.5b now primary | Reorder: lead with v2.5b |
| 2 | Architecture, B2→CP paragraph | v1 cited as the example of CP's event-field gap | **Still necessary** — minimal, illustrative, not a competing claim | Keep unchanged |
| 3 | System Assumptions | Same CP-zero-contribution example | **Still necessary** — same reason | Keep unchanged |
| 4 | Methodology | Full-paragraph description of v1 (listed before v2.5b) | **Obsolete ordering** | Reorder: lead with v2.5b |
| 5 | Results roadmap | States v1 "retained only where sole source for progressive ablation... not the paper's semantic-generalization claim" | **Already correct** | Keep unchanged (already states the migration policy this report enacts) |
| 6 | Layer-wise Architecture Validation opening | Explains v1's progressive-ablation role in detail | **Necessary** (architectural progression, Task 5's own retained-category example) | Keep unchanged |
| 7 | `fig_decision_dist` caption | v1 decision distribution, prior checkpoint | **Supplementary, no v2.5b equivalent exists or is warranted** — visualizes fusion's escalation-only behavior, a mechanism claim already independently confirmed on v2.5b in prose (Section~\ref{sec:v25b}) | Keep, already labeled supplementary |
| 8 | `fig_score_dist` caption | v1 B3 score histogram | **Redundant once a v2.5b equivalent exists** | **Replaced** — new `fig_v25b_score_dist` built from existing v2.5b inference data; v1 figure removed |
| 9 | `fig_calibration_v1` caption | v1 reliability diagram | **Redundant once a v2.5b equivalent exists** | **Replaced** — new `fig_v25b_calibration` built from existing v2.5b inference data; v1 figure removed |
| 10 | Table III caption | "Layer Contribution, STBV-Bench v1" | **Necessary** — the only benchmark with a fixed, comparable sample set for this specific progressive B1→B2→B3 ablation shape; v2.5b's equivalent table was already trimmed (prior turn) to remove its own dead-zero B1/B2 rows, so it cannot show this same B1-alone-vs-B2-added contrast at all | Keep, with reason restated explicitly in prose |
| 11 | Consolidated `fig_ablation` caption (confusion+ROC/PR) | v1, prior checkpoint, already labeled supplementary | **Necessary as historical/supplementary evidence** — v2.5b has its own confusion matrix (`fig_v25b_confusion_grid`) and ROC/PR (`fig_v25b_roc`) already; v1's is retained specifically as the prior-checkpoint comparison point, not a duplicate primary claim | Keep, already correctly demoted |
| 12–13 | ITE-Bench Finding/Interpretation/Implication paragraphs | v1 cited as contrast (what a benchmark-scope-limited ablation looks like vs. ITE-Bench's purpose-built one) | **Necessary** — this is the direct motivation for why ITE-Bench exists | Keep unchanged |
| 14 | v2.5b subsection opening | Explicitly demotes v1 | **Already correct** | Keep unchanged |
| 15–16 | v2.5b ablation paragraphs | v1 cited only as "identical, already-established reason" cross-reference | **Necessary**, minimal | Keep unchanged |
| 17 | Discussion, Strengths | "every one of 69 fusion-attributable decision changes on STBV-Bench v1 is an escalation" — cited as if the primary evidence for this mechanism claim | **Obsolete as primary evidence** — v2.5b now has the identical, statistically-tested finding (McNemar, Section~\ref{sec:v25b}) | **Reworded**: lead with the v2.5b evidence, cite v1 as corroborating |
| 18 | Limitations (v) | v1's near-ceiling F1 mechanism (`rows[10000:]` template exposure) | **Necessary** — this is precisely why v2.5b was built; removing it would remove the paper's own stated justification for v2.5b's existence | Keep unchanged |
| 19 | (repeat cross-reference within #17/18's paragraph) | — | Covered above | — |

**Summary of the audit**: of 19 occurrences, 3 required action (reorder Contributions, reorder Methodology, reword Discussion Strengths), 2 figures were fully redundant once v2.5b equivalents could be built from already-existing data and were replaced, and the remaining 14 are legitimately necessary — either illustrative/minimal cross-references, or v1's genuine, non-duplicable role as the fixed-sample-set progressive-ablation benchmark and the specific counter-example that motivated ITE-Bench and v2.5b's own construction.

## Task 2–3 — Executed changes

### Removed

- `fig_score_dist_v1_final.pdf` (v1 B3 score-distribution histogram) — no longer referenced from the main manuscript.
- `fig_calibration_v1_final.pdf` (v1 reliability diagram, ECE=0.153) — no longer referenced from the main manuscript.

### Replaced (v1 → v2.5b, using existing figure labels to avoid a wider cross-reference update)

- **Score distribution**: new `fig_v25b_score_dist.pdf`, built from a fresh direct-classifier forward pass on v2.5b (same model/benchmark already scored for `fig_v25b_roc`'s ROC AUC=0.9892 — not a new experiment, an additional plot from the same inference). Real counts: 4,734 benign / 5,364 malicious.
- **Calibration**: new `fig_v25b_calibration.pdf`, reliability diagram at the deployed temperature ($T{=}3.18$) on all 10,098 v2.5b samples. Real result: **ECE$=0.027$**, markedly better calibrated than v1's superseded ECE$=0.153$ (expected — the deployed temperature is fit for and validated against this exact benchmark's decision policy, not v1's).
- **Contributions (item iii)**: reordered to name v2.5b first as the primary benchmark, v1 second with its role stated explicitly (progressive ablation only).
- **Methodology**: reordered to describe v2.5b before v1, with v1's sentence now stating explicitly it is retained "solely as the fixed-sample-set benchmark behind the progressive layer-by-layer ablation... not as a semantic-generalization claim."
- **Discussion, Strengths**: the "fusion is provably conservative and empirically matches" sentence now leads with the v2.5b statistically-confirmed finding (Section~\ref{sec:v25b}'s McNemar result) and cites v1's 69-escalation finding as corroborating, not primary, evidence.
- **A stale cross-reference caught and fixed while replacing the figures**: a sentence in Section~\ref{sec:results}A ("B3's own discriminative quality... confirmed by... the underlying score separation (Fig...), and its calibration behavior (Fig...)") had referenced the v1 figures by their old content; since those figure *labels* now point at v2.5b content (to avoid a wider cross-reference rewrite), the sentence was reworded so it no longer claims v1-specific evidence it no longer contains.

### Retained, with explicit reason (not silently kept)

- **Table III** (`tab:main_ablation`, STBV-Bench v1's 4-row progressive ablation) — the only benchmark in this paper with a fixed, directly comparable sample set across B1-only/B1+B2/B3-alone/full-stack configurations; v2.5b's own ablation table (Table V) was trimmed in an earlier pass to remove its dead-zero B1/B2 rows specifically, so it cannot show this same B1-alone-vs-layers-added numeric contrast at all. Removing Table III would remove the paper's only demonstration of this specific architectural point.
- **Consolidated v1 confusion+ROC/PR figure** (`fig_ablation`) — retained as the explicit prior-checkpoint historical comparison point; v2.5b has its own independent confusion matrix and ROC/PR (`fig_v25b_confusion_grid`, `fig_v25b_roc`), so this is not a duplicate primary claim.
- **v1 decision-distribution figure** (`fig_decision_dist`) — retained; no v2.5b equivalent was built, since the mechanism it illustrates (fusion moves mass Accept→Caution, not Accept→Reject) is already independently confirmed in prose for v2.5b (Section~\ref{sec:v25b}), and building a duplicate figure for the same qualitative point was judged unnecessary per this pass's own "do not regenerate unless required" instruction.
- **ITE-Bench's references to v1** (Finding/Interpretation/Implication paragraphs) — necessary, since v1 is the direct motivating counter-example for why ITE-Bench was built at all; removing these references would leave ITE-Bench's own justification unstated.
- **Limitations item (v)** (v1's near-ceiling F1 mechanism, `rows[10000:]` template exposure) — necessary; this is explicitly the reason v2.5b was constructed, and removing it would remove the paper's own stated justification for v2.5b's existence.
- **Minor illustrative references** (Architecture's B2→CP paragraph, System Assumptions) — single-sentence examples of CP's zero-contribution behavior, not competing benchmark claims; removing them would leave those points unillustrated for no benefit.

## Task 8 — Consistency check performed

Mechanical LaTeX audit (labels/refs/citations/figure-file existence) re-run after every edit in this pass: 0 broken references, 0 duplicate labels, 0 missing citations, 0 missing figure files — clean before and after. Figure count unchanged at 11 (two figures replaced in place using their existing labels, rather than added as new entries, to avoid an unnecessary wider renumbering).

## What was NOT done, and why

- **v1's own ablation table (Table III) was not removed or migrated to v2.5b** — explicitly retained with reason (see above); v2.5b structurally cannot reproduce this table's content since its own B1/B2 rows were already correctly removed as dead-zero content in an earlier pass.
- **No new experiments were run.** Both new figures reuse an inference pass equivalent to one already verified in an earlier pass (same checkpoint, same benchmark, cross-checked ROC AUC), not a new evaluation.
- **The Appendix (worked fusion example) was not touched** — it is already checkpoint-current and was not found to reference v1 in a way requiring migration.

