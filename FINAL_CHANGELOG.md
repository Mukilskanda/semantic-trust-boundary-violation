# Final Changelog — Manuscript Integration Pass

Every modification made to produce `stbv_paper.tex` from the prior
scattered documentation, in order.

## 1. Structural reorganization

- Introduced a dedicated **Related Work** section (new Section II),
  condensing `RELATED_WORK.md`'s 10 subsections into flowing IEEE prose
  with inline citations, retaining the comparison table.
- Split the old, combined "Proposed STBV Framework" section into two:
  a new **Problem Statement and Threat Model** section (Section III —
  the Semantic Trust Boundary definition plus the full threat model,
  attacker capabilities, and attack-family taxonomy previously buried in
  the Methodology section) and a **Proposed Architecture** section
  (Section IV — the four trust layers and Trust Decision Engine only).
- Corrected the Introduction's section roadmap paragraph to match this
  new structure (it previously described an outdated section ordering).
- Results (Section VI) reorganized strictly by research question
  (RQ1–RQ6 plus a layer-ablation subsection and a calibration/robustness/
  latency subsection), not chronologically by when each experiment was
  run.

## 2. Content integration (no verbatim duplication)

- `RELATED_WORK.md` → condensed into Section II's prose + Table I
  (comparison table), citations converted to proper `\cite{}`/`\bibitem`
  entries.
- `REPRODUCIBILITY_PARAMETER_APPENDIX.md` → split between inline
  disclosures at each conceptual equation (Section IV) and full detail
  in Appendix A.
- `SEMANTIC_TRANSFORMATION_APPENDIX.md` → summarized in Methodology
  (Section V), full worked examples moved to Appendix B.
- `CP_VALIDATION.md` → summarized in Results (layer-ablation subsection),
  full detail in Appendix C.
- `DISCUSSION_AND_LIMITATIONS.md` → split into Discussion (Section VII,
  the six "why" questions plus trade-offs/deployment/failure-modes/
  research-implications) and Limitations (Section VIII, consolidated,
  each item stated once and cross-referenced from Results/Discussion
  rather than re-explained).
- `MANUSCRIPT_FRAMING.md` → superseded by the integrated Results/
  Discussion; its content is now expressed directly in those sections
  rather than existing as a separate framing document layered on top.
- `THREAT_CLASS_COVERAGE_MATRIX.md` → condensed into Table (Results,
  RQ4/5 subsection).
- `PUBLICATION_PROGRESS.md`, `FINAL_READINESS_REPORT.md` → used as
  source material for what is/is not resolved (Limitations, Conclusion,
  and this changelog/blockers pair); not copied into the manuscript body,
  since they are process-tracking documents, not manuscript content.

## 3. Equation-vs-implementation disclosure moved inline

Previously stated only in `REPRODUCIBILITY_PARAMETER_APPENDIX.md`, now
stated directly beside Eqs. (1), (3), and (4) in Section IV itself (each
equation's own paragraph now says explicitly "this equation is a
conceptual formalization... not a literal computation in the
implementation"), with the full explanation retained in Appendix A. A
reviewer reading Section IV alone, without opening the appendix, now
sees this disclosure.

## 4. Figures

- 11 of 12 real, data-grounded figures from `figures_v2/` embedded with
  `\includegraphics` and matched `\label`/`\ref` pairs. This includes
  `fig_latency_per_stage.pdf` (per-stage latency breakdown), which was
  generated earlier in the project but had not yet been embedded or
  documented until this pass; it is now placed immediately after
  Fig.~\ref{fig_latency} with explicit inline text disclosing that its
  source is the smaller 120-scenario diagnostic harness (the only
  artifact with per-stage timers), not STBV-Bench v1 — and that this
  harness's *accuracy* numbers, but not its *stage timers*, are
  separately flagged as leakage-compromised.
- The twelfth, `fig_latency_hist.pdf`, exists but was judged redundant
  with the embedded `fig_latency.pdf` percentile chart and was not
  embedded, to avoid two near-duplicate latency figures (see
  `FIGURE_PLACEMENT.md`).
- `fig1.png` (trust-evolution diagram) referenced as it was in the
  original manuscript; confirmed this round that the file is **not**
  present in this repository checkout — flagged in `FINAL_BLOCKERS.md`,
  not silently assumed to exist.
- 4 requested architectural/workflow diagrams (`fig_arch` and three
  others) explicitly **not** fabricated; each is specified precisely in
  `FIGURE_PLACEMENT.md` for a deliberate design pass instead.

## 5. Tables restored

The full five-configuration ablation table (`tab:full_ablation`), which
had been dropped when an earlier round collapsed the main-text table to
four rows for readability, was restored as an explicit supplementary
table in Appendix A, per the standing instruction that this table remain
auditable rather than only asserted.

## 6. Consistency audit performed and closed

Automated audit of `stbv_paper.tex` (script used and then removed from
`scratch/`, per this project's scratch-directory convention) found and
fixed:
- 5 broken `\ref`/`\eqref` targets (`fig_arch`, `fig_pr`, `fig_latency`,
  `fig_roc`, `sec:figures`) — either given real figures/labels or
  rewritten to remove the dangling reference.
- 4 unused equation labels (`eq:conflict`, `eq:yager`, `eq:pignistic`,
  `fig_ablation_summary`) — each now referenced from the prose that
  introduces it.
- Citation/bibliography cross-check: zero `\cite` keys without a
  matching `\bibitem`, zero `\bibitem` entries never cited (this was
  already clean).
- `\begin`/`\end` environment balance and overall brace balance
  verified (both clean).
- Every table's row field count manually verified against its column
  specification (one regex false-positive in the automated check, caused
  by the `@{}` column-spec syntax, was caught and confirmed not a real
  defect before being reported as clean).

## 7. Style

Rewrote several transition sentences between sections to avoid abrupt
topic changes (e.g., the end of Section III now explicitly hands off to
Section IV's architecture description; the end of Results explicitly
hands off to Discussion's synthesis framing rather than repeating the
last finding). Removed repeated definitions of STBV/STB (previously
stated near-identically in both the Introduction and the old combined
architecture section; now defined once, in the new Problem Statement
section, and referred back to elsewhere).

## What this changelog does not cover

Two items requested in the original task list were not performed this
round and are not claimed as complete: producing the four architectural
diagrams as real artwork (specified, not drawn — see
`FIGURE_PLACEMENT.md`), and locating or substituting for `fig1.png`,
which is referenced but not present in this repository. Both are listed
in `FINAL_BLOCKERS.md`.
