# UPDATED_RESULTS_SECTION.md — hard-OOD integration

## Task 6 — Paper selection re-check

With the hard-OOD result now available, the evaluation suite a top venue
would expect is: **main benchmark (STBV-Bench v1) → hard-OOD (new) →
external semantic corpus → adaptive-attack → deployment → ablation**,
exactly the ordering this pass integrated into `stbv_paper.tex`
(Section~\ref{sec:hardood} inserted between the external-corpus subsection
and the adaptive-attack subsection). Re-checked against everything trimmed
in earlier phases: the hard-OOD result does **not** make any previously-kept
table/figure redundant (each answers a different question — v1 = in-
distribution capability, v2 = ambient-traffic realism, external = smaller
independently-authored OOD check, hard-OOD = deliberately hardest OOD
check, adaptive = iterative-mutation robustness, deployment = systems
feasibility, ablation = architectural contribution) and does not itself
duplicate any of them (no other benchmark uses non-grammatical/colloquial
registers or explicit truthful-hard-negative benign messages). No table or
figure was removed this pass; one new table (`tab:hardood`) and two new
figures were added, consistent with "don't add without new value."

## Results-section text added (verbatim, already integrated into `stbv_paper.tex`)

See `stbv_paper.tex` Section~\ref{sec:hardood}, "Hard Out-of-Distribution
Evaluation (Frozen Model, New Benchmark)" — inserted immediately after the
External Semantic Evaluation subsection and before Adaptive Attack
Evaluation. Full text is in the paper itself; summarized:

- Benchmark construction and leakage-check summary (one paragraph).
- Headline finding paragraph: F1=0.446, the hardest benchmark in the paper,
  precision stays 1.000 on every family with any detections, calibration
  degrades sharply (ECE 0.459).
- New table `tab:hardood` (Accuracy/Precision/Recall/F1/ROC-AUC/PR-AUC/ECE/
  Brier).
- Two new figures: per-family recall (`fig_hardood_per_family`),
  cross-benchmark F1 comparison (`fig_hardood_cross_benchmark`).
- Failure-analysis paragraph with four real, unparaphrased example
  messages and their actual model outputs, one per cluster.
- Interpretation and Implication paragraphs connecting this result to the
  paper's other benchmarks and to future work.

## Sections updated beyond Results

- **Abstract**: added one sentence reporting the hard-OOD F1=0.446 finding
  alongside the existing external-corpus sentence, and corrected the
  external-corpus sentence's "weakest result in this paper" claim to
  "weakest among grammatical-text benchmarks" (no longer literally true
  once the hard-OOD number exists).
- **Introduction, Main Contributions**: added a bullet describing the new
  benchmark as a contribution in its own right.
- **Limitations**: two edits — corrected the external-corpus paragraph to
  reference both OOD corpora, and added a new limitation paragraph stating
  the register-specific generalization gap as this paper's most important
  open item, ahead of the narrower per-family weakness already discussed.
- **Conclusion**: added the hard-OOD finding to the results summary
  paragraph and reprioritized the future-work sentence to lead with closing
  this gap.

All edits verified consistent via a fresh `\ref`/`\cite`/`\includegraphics`/
brace-balance check after integration (0 dangling refs, 0 dangling cites,
27/27 figures resolve except the pre-existing `fig1.png`, 13+1
tables balanced) — see `FINAL_CONSISTENCY_REPORT.md`'s addendum.
