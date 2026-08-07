# FINAL_SUBMISSION_CHECKLIST.md

## Content correctness
- [x] Every number traces to a fresh artifact for the final checkpoint, or
  is explicitly marked checkpoint-invariant / not-rerun (`FINAL_RESULTS.md`,
  `FINAL_REPRODUCIBILITY_REPORT.md`).
- [x] No development-history (checkpoint-vs-checkpoint) narrative anywhere
  in the manuscript body (reconfirmed, zero grep matches, this pass).
- [x] Every disclosed limitation is a real, currently-unfixable gap, not a
  silently-accepted weakness (CARLA, robustness battery, `isce_config.yaml`
  staleness, un-CI'd ASR/safety-rating, missing LaTeX toolchain).
- [x] STBV-Bench v1's F1=0.995 headline number independently root-caused
  and re-verified clean (checkpoint SHA, data leakage, thresholds, row/ID
  integrity, arithmetic consistency) — `ROOT_CAUSE_REPORT.md`.
- [x] One fabricated statistic found and fixed (a placeholder bootstrap CI)
  — `PUBLICATION_FREEZE_REPORT.md`.
- [x] SUMO deployment rerun against the final checkpoint, confirmed
  protocol-identical, table updated to reflect it (not just footnoted).
- [x] CARLA genuinely and exhaustively confirmed unavailable, twice, with
  evidence both times — not assumed or reused uncritically.

## Structural/formatting
- [x] 0 dangling `\ref`s (69 labels, 50 refs).
- [x] 0 dangling `\cite`s (30 keys, 30 bibitems).
- [x] Balanced `\begin`/`\end` for `table` (12), `table*` (1), `figure`
  (25), `threeparttable` (2); balanced braces (verified via character
  count).
- [x] All `\includegraphics` paths resolve except `fig1.png` (pre-existing,
  out of scope, unrelated to B3/checkpoint).
- [ ] **Not done: actual PDF compilation.** No LaTeX toolchain available in
  this environment (exhaustively checked: `pdflatex`/`xelatex`/`latexmk`/
  `tectonic` via `which`/`where`, filesystem search of both `Program Files`
  directories, `pip show pylatex`). This is the single concrete blocking
  item before literal camera-ready submission — someone with local TeX
  Live/MiKTeX access must compile once and fix any real LaTeX-engine-level
  errors (unlikely given the clean static checks, but not verified).

## Statistical rigor
- [x] STBV-Bench v1 fusion effect: McNemar test, real ($\chi^2=67.0$,
  $p<10^{-15}$).
- [x] B3-banded F1 on STBV-Bench v1: real bootstrap CI.
- [x] CARLA per-scenario and aggregate figures: real bootstrap CIs
  (pre-existing, unaffected by this checkpoint).
- [ ] Adaptive-attack ASR ($n=51$): no CI — disclosed limitation, not
  blocking but should be added before camera-ready if time allows.
- [ ] Live-CARLA zero-detection count ($n=3{,}585$): no formal significance
  test — disclosed limitation, same status.

## Presentation quality
- [x] Figures are vector PDF + PNG, consistent color palette across
  `FINAL_FIGURES/` (`#1f77b4` primary, `#d62728` alert, `#2ca02c`
  secondary — colorblind-reasonable, distinguishable in grayscale by
  marker/line style where combined).
- [x] Tables use consistent decimal rounding and bold-best-value convention
  where a genuine best-of comparison exists.
- [x] Reviewer-mode pass completed twice (initial + fresh this cycle);
  findings either fixed or explicitly disclosed with reasoning.

## Bottom line
Content-correct, internally consistent, and honestly self-documented. The
one remaining hard blocker to literal camera-ready submission is PDF
compilation, which requires a LaTeX toolchain this environment does not
have. Everything else that could be checked without one has been checked.
