# figures/

TikZ source files for all paper figures.
All figures compile with pdflatex. No external fonts or packages beyond
standard TeX Live are needed.

## Required packages (add to paper preamble if missing)

```latex
\usepackage{tikz}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta, positioning, shapes.geometric, fit, calc, backgrounds}
```

## Files

| File | Fig # | Width | Paper location |
|------|-------|-------|----------------|
| fig1_trust_evolution.tex | Fig 1 | `\textwidth` (figure*) | Section I / Introduction |
| fig2_attack_lifecycle.tex | Fig 2 | `\columnwidth` (figure) | Section III / Threat Model |
| fig3_threat_coverage_matrix.tex | Fig 3 | `\textwidth` (figure*) | Section VI / Results |
| fig5_trust_score_evolution.tex | Fig 5 | `\columnwidth` (figure) | Section VI-A / RQ1 |
| fig6_stbvbench_pipeline.tex | Fig 6 | `\textwidth` (figure*) | Section V / Methodology |
| fig7_perlayer_latency.tex | Fig 7 | `\columnwidth` (figure) | Section VI-G / Latency |
| fig8_failure_analysis.tex | Fig 8 | `\textwidth` (figure*) | Section VI-A / RQ1 |
| fig9_decision_transition.tex | Fig 9 | `\columnwidth` (figure) | Section VI-B / RQ2 |
| fig10_evidence_fusion.tex | Fig 10 | `\textwidth` (figure*) | Section IV-D / Architecture |

## How to preview a single figure

1. Open `standalone_preview.tex`
2. Change the `\input{...}` line to the figure you want
3. Run: `pdflatex standalone_preview.tex`

## How to include in the paper

Full-width figures (figure*):
```latex
\begin{figure*}[t]
  \centering
  \input{figures/figN_name.tex}
  \caption{...}
  \label{fig:...}
\end{figure*}
```

Single-column figures (figure):
```latex
\begin{figure}[t]
  \centering
  \input{figures/figN_name.tex}
  \caption{...}
  \label{fig:...}
\end{figure}
```

## Data sources

All figures use only data already present in the paper:
- Fig 1: layer names and flow from Section IV
- Fig 2: threat model from Section III
- Fig 3: Table III + Section VI recall numbers
- Fig 5: Appendix B worked example (verbatim logged pipeline output)
- Fig 6: Section V dataset construction numbers
- Fig 7: Fig 11 per-stage latency (120-scenario harness)
- Fig 8: Fig 3 per-family recall + Section VI-A failure interpretation
- Fig 9: Section VI-B transition counts (1,585 / 128 / 0)
- Fig 10: Section IV-D equations + Appendix B worked example numbers

No new experiments were run to produce any figure.
