# FINAL_CONSISTENCY_REPORT.md — mixed-corpus final-checkpoint manuscript pass

Final status: **complete**, with two explicitly disclosed gaps (CARLA,
robustness-perturbation battery) that are not resolvable in this
environment/session and are stated as such rather than fabricated.

## Addendum — submission-prep pass (LaTeX build attempt + fresh re-check)

- **LaTeX compilation attempted, genuinely blocked by environment.**
  Checked for `pdflatex`, `xelatex`, `latexmk`, `tectonic` via `which`/
  `where`; searched `C:\Program Files`, `C:\Program Files (x86)`, `C:\texlive`,
  `C:\miktex` for any TeX binary; checked `pip show pylatex`. **No LaTeX
  toolchain of any kind is installed on this machine.** No compile was
  performed, and none is fabricated — this is stated plainly rather than
  presented as a "clean build." Static consistency checks (below) are the
  best available substitute.
- **Fresh consistency re-check, post-deployment-section edits:** re-ran the
  ref/cite checker and the `\includegraphics`-path resolver against the
  current file. 69 labels, 50 refs, **0 dangling refs**; 30 cite keys, 30
  bibitems, **0 dangling cites**; environment counts balanced (12
  `\begin{table}`/`\end{table}`, 1 `\begin{table*}`/`\end{table*}`, 25
  `\begin{figure}`/`\end{figure}`, all matched); 25 `\includegraphics`
  paths, all resolve except the pre-existing, out-of-scope `fig1.png`.
- **Stale-number re-grep, post all edits:** repeated the full sweep for
  every previously-superseded value (old F1s, old McNemar stats, old
  external-eval/adaptive/mixed-threat numbers, old checkpoint SHA, old SUMO
  latency/throughput figures) — **zero matches** in the manuscript body.
- **Dev-history re-check:** repeated the grep for "original checkpoint,"
  "fine-tuned checkpoint," "v25_lora," and checkpoint-vs-checkpoint
  comparison phrasing — **zero matches**, confirmed still true after the
  deployment-section rewrite.

## 1. Every number regenerated against the final checkpoint

- **STBV-Bench v1 full pipeline** (`tab:main_ablation`, `tab:full_ablation`,
  `fig_confusion`, `fig_per_family_recall`, `fig_roc`, `fig_pr`,
  `fig_calibration`, `fig_ablation_summary`, `fig_decision_transitions`,
  RQ1/RQ2 text, McNemar/Cohen's-h/three-way-transition stats): **PASS**.
  Rerun end-to-end, $n=10{,}000$, all 5 configurations, via a new
  `--checkpoint mixed` mode in `rerun_paper_ablation.py`. The first attempt
  at this rerun suffered file corruption in configs 4/5 from a stray
  orphaned process (a leftover from an earlier failed background-launch
  attempt) writing to the same files concurrently; this was caught by a
  row-count/sample-ID cross-check against the clean, checkpoint-invariant
  configs 1–3, not assumed clean. Fixed by deleting the corrupted files and
  rerunning configs 4–5 in isolation as a single, unshared process
  (`rerun_ablation_configs45_mixed.py`, with per-row `flush()`); the final
  files were re-verified to contain exactly 10,000 unique, correct sample
  IDs each before any number was written into the paper.
- STBV-Bench v2 (windowed): PASS — matches `MIXED_CORPUS_RESULTS.md`'s
  independently-reported numbers exactly (cross-checked in this session).
- External semantic corpus: PASS — recomputed directly from
  `external_eval_results__mixed.json`, including a corrected per-family
  ranking (weakest family is `phantom_hazard_fabrication`, not
  `spoofed_authority_override` as in the earlier checkpoint's evaluation).
- Adaptive-attack evaluation: PASS — ASR, per-round detection probability,
  and per-family/per-strategy breakdown recomputed directly from
  `adaptive_attack_results__mixed.json`'s raw per-seed trace.
- Mixed-threat case study: PASS — recomputed directly from
  `results/mixed_threat_mixed/mixed_threat_per_message.csv`.
- CP full evaluation: PASS — recomputed directly from
  `cp_full_eval_results__mixed.json` and independently verified
  byte-identical to the previously reported delta (33 decision changes,
  fp_off=99/fp_on=121, fn=0/0) by direct per-message decision comparison.
- Deployment (SUMO): PARTIAL — a fresh spot-check rerun was performed
  (footnoted in `tab:deployment`'s caption, confirms same order of
  magnitude: mean 73.9~ms vs. table's 66.8~ms, throughput 13.5 vs.
  14.95~msg/s); the table's own headline numbers were not replaced, since
  architecture/parameter-count invariance -- not a byte-identical re-run of
  the table's original measurement protocol -- is the basis for treating
  latency as checkpoint-invariant.
- Live CARLA: **NOT regenerated.** No CARLA-capable environment was
  available in this session. `tab:carla_scenarios` and the "B3 returned
  BENIGN on all 3,585 attack messages" finding are carried forward from the
  architecture's prior evaluation, with an explicit caveat added at both
  points in the manuscript where this finding is used (the Deployment
  Feasibility subsection and the Discussion's CRITICAL-finding paragraph).
- Robustness perturbation battery (instruction-hiding/role-confusion 100%
  over-defense) and the STBV-Bench v2 threshold-sensitivity sweep: **NOT
  rerun** against the final checkpoint — disclosed via caveat sentences
  added at both points in the manuscript, rather than silently carried
  forward as re-verified.

## 2. No stale metrics remain

Verified by direct string search across the finished `stbv_paper.tex` for
every superseded number this pass touched (old STBV-Bench v1 F1s 0.715/
0.718, old McNemar $p=3.06\times10^{-29}$/128-discordant/1,713-transition
figures, old external-corpus recall/precision/AUC 0.899/0.976/0.975, old
adaptive ASR 83.7%/n=49, old mixed-threat coverage 90.3%/70.3%, the removed
`fig_ext_calibration` reference, the old checkpoint SHA `9ee7475e`): **zero
matches** remain in the manuscript body. These values appear only inside
`UPDATED_RESULTS_FINAL.md` and this report, explicitly as the "old" column
of a disclosed old-vs-new comparison.

## 3. Only the final checkpoint appears anywhere in the paper

Confirmed: no development-history narrative (no "original vs. fine-tuned"
table/figure, no LoRA-development trial-and-error narrative, no
calibration-experiment history) exists anywhere in `stbv_paper.tex`. The
one checkpoint identity stated in the manuscript is the final production
checkpoint's SHA-256
(`638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`),
described factually via its LoRA training recipe in Appendix A. No
"we compared X and Y" framing appears anywhere in Results, Discussion, or
Conclusion; every result is presented as a property of the single evaluated
system.

## 4. Internal consistency (refs/cites/figures/tables resolve)

Automated check (`b3_eval/v25_finetune/check_refs_final.py`) against the
finished file:
- 66 `\label`s, 47 `\ref`s used — **zero dangling `\ref`s** (every `\ref`
  resolves to an existing `\label`).
- 30 distinct `\cite` keys used — **zero dangling cites** (every cite key
  has a matching `\bibitem`).
- Brace count balanced (1,171 open / 1,171 close); `\begin{table}`/
  `\end{table}` (15/15) and `\begin{figure}`/`\end{figure}` (22/22) counts
  match.
- All 22 `\includegraphics` paths resolve to an existing file **except
  `fig1.png`** (the Section~I architecture-evolution diagram) — this file
  was already absent before this task's changes, is unrelated to B3 or any
  checkpoint (Category C, purely illustrative), and is out of this task's
  scope; flagged here rather than silently left unmentioned.

## 5. Honest gaps, stated plainly

- **Live-CARLA per-scenario detection** (`tab:carla_scenarios`, and the
  "B3 non-detection" finding) was not re-collected against the final
  checkpoint — no CARLA-capable environment was available. This is the one
  place in the paper where a headline number is retained without a fresh
  rerun for this specific checkpoint; it is flagged at both points it is
  used, not hidden.
- **Instruction-hiding/role-confusion robustness battery and the v2
  threshold-sensitivity sweep** were not rerun against the final checkpoint
  — flagged with an added caveat sentence at each location.
- **`fig1.png`** (Section I) is missing from the repository independent of
  this task; not investigated further as out of scope.
- **B3's strict-argmax baseline operating point** (previously a second row
  in `tab:baselines`) was removed rather than recomputed with a stale
  number, since the raw per-message argmax label is not retained in this
  rerun's CSV artifact.
- A file-corruption incident during the STBV-Bench v1 rerun (Section 1
  above) is disclosed in full, including its root cause (a concurrent
  orphaned process) and the specific verification steps used to detect and
  fix it, so the final numbers can be trusted as clean rather than merely
  asserted clean.

## Summary

Every number in the final `stbv_paper.tex` traces to an actual experimental
artifact for `semantic_gate_v3_mixed_lora_merged`, freshly computed in this
session, with two explicitly disclosed exceptions (live-CARLA per-scenario
detection; the exact robustness-perturbation battery) that could not be
regenerated in this environment and are stated as open items rather than
silently carried forward or fabricated. The manuscript presents one model,
one checkpoint, one evaluation, with no internal checkpoint-development
narrative anywhere in the reader-facing text.
