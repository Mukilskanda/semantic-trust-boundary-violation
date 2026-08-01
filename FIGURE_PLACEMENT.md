# Figure Placement Plan

Every figure referenced in `stbv_paper.tex`, its purpose, what it proves,
where it appears, its caption, and whether it exists or must still be
designed. Eleven are real, data-grounded plots already generated and
embedded (`figures_v2/*.pdf`). Four are conceptual/architectural diagrams
that were **not** fabricated as placeholder art, per the standing rule
against manufacturing figures — each is specified precisely enough for a
diagram designer to produce without guessing at content.

A twelfth real, generated plot (`fig_latency_hist.pdf`) exists but is
deliberately not embedded — see the note after the table below.

## Existing, embedded (11)

| # | File | Purpose | What it proves | Location in `stbv_paper.tex` | Caption (as used) |
|---|---|---|---|---|---|
| 1 | `fig1.png` | Motivation / trust evolution | Conceptual evolution from communication trust to decision trust | Introduction, `\label{fig_1}` | "Evolution of V2X trust from communication trust to decision trust..." |
| 2 | `figures_v2/fig_confusion.pdf` | Confusion matrix | Exact TP/FP/FN/TN counts behind Table I's full-stack row | Results §A (RQ1), `\label{fig_confusion}` | "Confusion matrix, full-stack decisions, STBV-Bench v1..." |
| 3 | `figures_v2/fig_per_family_recall.pdf` | Per-family recall bar chart | The 8-family/6-family recall split underlying the "bounded detection gap" claim, at a glance | Results §A (RQ1), `\label{fig_per_family}` | "Per-attack-family recall, full stack, STBV-Bench v1..." |
| 4 | `figures_v2/fig_ablation_summary.pdf` | Ablation F1 with bootstrap CI | Visualizes Table I/Table (full ablation) with uncertainty bars | Results §C (layer ablation), `\label{fig_ablation_summary}` | "Layer-ablation F1 with 95% bootstrap CI..." |
| 5 | `figures_v2/fig_decision_transitions.pdf` | Decision distribution + fusion transitions | The 3-way Accept/Caution/Reject finding central to RQ2 | Results §B (RQ2), `\label{fig_transitions}` | "Full-stack decision distribution... fusion-attributable transitions..." |
| 6 | `figures_v2/fig_threat_coverage.pdf` | B3 vs. MBD recall bar chart | Complementary, non-overlapping threat-class coverage (RQ4/5) | Results §D (RQ4/5), `\label{fig_threat_coverage}` | "B3 vs. MBD recall on the semantic and kinematic threat classes..." |
| 7 | `figures_v2/fig_roc.pdf` | ROC curve | Full-stack discrimination ability across thresholds | Results §F (calibration/robustness), `\label{fig_roc}` | "ROC curve, full-stack fused Decision Trust score..." |
| 8 | `figures_v2/fig_pr.pdf` | Precision-Recall curve | Same, at v1's actual corpus prevalence | Results §F, `\label{fig_pr}` | "Precision-Recall curve... prevalence baseline shown..." |
| 9 | `figures_v2/fig_calibration.pdf` | Reliability diagram | Before/after temperature-scaling calibration improvement | Results §F, `\label{fig_calibration}` | "Calibration reliability diagram before/after temperature scaling..." |
| 10 | `figures_v2/fig_latency.pdf` | Latency percentile chart | End-to-end latency vs. the 10 Hz CAM budget | Results §F, `\label{fig_latency}` | "End-to-end per-message decision latency percentiles..." |
| 11 | `figures_v2/fig_latency_per_stage.pdf` | Per-stage mean latency (log scale) | Where end-to-end latency accumulates across PKI/B1/MBD/B2/CP/synthesizer/B3/fusion | Results §F, immediately after Fig.~\ref{fig_latency}, `\label{fig_latency_per_stage}` | "Per-stage mean latency..., measured on the 120-scenario diagnostic harness, log scale." |

Generation code and exact source-file provenance for all eleven:
`figures_v2/generate_figures.py`. Note that #11's source is explicitly
the 120-scenario `semantic_evaluation` diagnostic harness, not
STBV-Bench v1 — its per-message CSV logs only total latency, not a
per-stage breakdown. That harness's *accuracy* numbers are separately
flagged as leakage-compromised (Section~\ref{sec:limitations}), but its
*stage timers* are unaffected by that concern and are reported as a
diagnostic indicator, with the source explicitly disclosed in the
caption and surrounding text rather than presented as a STBV-Bench v1
result.

## Real, generated, but not embedded

`figures_v2/fig_latency_hist.pdf` — a histogram of full-stack per-message
latency (STBV-Bench v1, same source as `fig_latency.pdf`). Generated but
not embedded: it is redundant with the percentile chart already embedded
as `fig_latency.pdf`, which conveys the same distribution more precisely
(exact $p_{50}$/$p_{95}$/$p_{99}$ values vs. a binned histogram). Not
embedding it avoids two near-duplicate latency figures in the same
subsection.

## Not yet produced — specified, not fabricated (4)

| # | Working name | Purpose | What it proves | Intended location | Status |
|---|---|---|---|---|---|
| 11 | Vertical Architecture Diagram | Show the full B1→B2→CP→B3→Trust Decision Engine pipeline as connected blocks, with the Semantic Trust Boundary marked | Gives a reader a single-glance map of the layered architecture described in prose across Section IV | Section IV (Proposed Architecture), opening paragraph — currently has explicit prose noting this diagram is planned, not a silent gap | **Not produced.** Requires deliberate diagram design (boxes/arrows/layer labels matching Section IV's subsection structure exactly: PKI→SCSV→MBD→CSIA→CP→B3→Trust Decision Engine), not a data plot. Fabricating placeholder art was explicitly avoided. |
| 12 | STBV-Bench Generation Pipeline Diagram | Show VeReMi record → canonical CAM → semantic transformation → validated STBV-Bench sample as a linear pipeline | Visually anchors the Methodology section's dataset-construction description and Appendix B's worked example | Methodology (Section V), Dataset Construction subsection, or Appendix B alongside the worked example | **Not produced.** Content is fully specified in `SEMANTIC_TRANSFORMATION_APPENDIX.md`/Appendix B's prose; needs the same deliberate diagram treatment as #11. |
| 13 | Experimental Workflow Diagram | Show the relationship between STBV-Bench v1, STBV-Bench v2, the VeReMi kinematic companion bench, and the mixed-threat case study as a single workflow/decision tree (which benchmark answers which RQ) | Prevents a reader from conflating the four benchmarks' different purposes — directly supports this manuscript's core "never compare experiments answering different questions" rule | Methodology (Section V), before or after Dataset Construction | **Not produced.** The relationships are fully specified in Results §A–E's RQ structure and Section~\ref{sec:methodology}'s dataset descriptions; a diagram would be a visual summary of already-written text, not new content. |
| 14 | Threat-Class Coverage Matrix (as a rendered figure, distinct from Table II) | A visual matrix (attack family × layer) analogous to `THREAT_CLASS_COVERAGE_MATRIX.md`'s table, rendered as a heatmap or grid rather than prose table | Alternative, more scannable presentation of the same coverage information already in Table~\ref{tab:coverage} | Results §D (RQ4/5), as an alternative/complement to Table~\ref{tab:coverage} | **Not produced — arguably redundant with Table~\ref{tab:coverage}, which already exists and is populated with real numbers.** Recommend only producing this if a reviewer specifically requests a visual alternative to the existing table; otherwise the table is sufficient and this figure would not add new information. |

## Why these four were not designed as placeholder art

Producing #11–13 with fabricated boxes/arrows and no real underlying
diagram-design decision (layout, exact block contents, what visually
distinguishes a "conceptual" equation box from an "implemented" one per
the equation-vs-implementation finding) would not meet the same
evidentiary standard as the ten real data plots, and risks looking more
finished than it is. Each is specified above precisely enough that a
diagram designer — human or a dedicated diagramming pass — can produce
it directly from this document and the cited source sections, without
inventing content.
