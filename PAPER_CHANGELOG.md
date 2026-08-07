# PAPER_CHANGELOG.md — stbv_paper.tex, mixed-corpus final-checkpoint pass

This changelog records every structural/content change made to `stbv_paper.tex`
to adopt `semantic_gate_v3_mixed_lora_merged` (checkpoint SHA-256
`638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`) as the
single, final production B3 checkpoint, per the task's instruction to present
one model and one evaluation, with all internal checkpoint-development
history removed.

## What was NOT already present (so nothing needed removing)

A pass over the existing `stbv_paper.tex` before editing found **no
checkpoint-vs-checkpoint comparison tables, figures, or narrative** already in
the manuscript (no "original vs. fine-tuned" table, no calibration-experiment
history, no LoRA-development narrative). The paper already reads as a
single-model presentation; the base numbers in the pre-existing manuscript
were simply stale (computed against the original, non-fine-tuned
`semantic_gate_v3` checkpoint), not framed as a comparison. This changed the
scope of this task from "remove development history" to "replace stale
single-model numbers with fresh single-model numbers from the final
checkpoint, keeping the one-model framing intact throughout."

## Numbers replaced (see `UPDATED_RESULTS_FINAL.md` for old-vs-new detail)

- Abstract: v1 full-stack/B3-alone headline F1, external-corpus recall/
  precision/AUC, adaptive-attack ASR, mixed-threat semantic recall/FPR.
- `tab:main_ablation` (main text) and `tab:full_ablation` (appendix): B3-alone
  and full-stack rows on STBV-Bench v1 ($n=10{,}000$), rerun end-to-end
  against the final checkpoint via a new `--checkpoint mixed` mode added to
  `b3_eval/v25_finetune/rerun_paper_ablation.py`. Rows 1–3 (B1 only, B1+B2,
  B1+B2+CP) are unchanged by construction (B3 is never loaded when
  `enable_b3=False`) and were left as-is.
- `tab:coverage`: mixed-threat case study numbers, updated from the
  message-level semantic/kinematic recall convention on the mixed
  checkpoint's own rerun (`results/mixed_threat_mixed/`), with an explicit
  new footnote disclosing the benign FPR cost (0.673) behind the recall gain.
- RQ6 (STBV-Bench v2, windowed) aggregate F1/precision/recall/FPR, recomputed
  directly from `results/stbv_bench_v2_mixed/stbv_bench_v2_per_message.csv`.
- `tab:external_eval` and `tab:external_family`: full external-corpus
  reevaluation on the final checkpoint (`external_eval_results__mixed.json`);
  per-family ranking changed (weakest family is now
  `phantom_hazard_fabrication`, not `spoofed_authority_override`), so the
  narrative sentence identifying the weakest family was corrected, not just
  the number.
- `tab:adaptive` and the adaptive-attack narrative paragraph, per-family ASR
  breakdown, and dominant-mutation-strategy sentence: full rerun
  (`adaptive_attack_results__mixed.json`, $n=51$ seeds vs. the old $n=49$,
  since seed selection depends on which external-corpus items the current
  checkpoint detects correctly).
- Appendix `app:params` §Semantic Classifier: rewritten to describe LoRA
  fine-tuning (rank/alpha/dropout, target modules, mixed training-data
  composition, optimizer/schedule, best-epoch validation F1) as the
  production training method, factually, with the final checkpoint's own
  SHA-256. This is new factual content, not development narrative — no
  "we tried X, then Y" framing.
- Appendix `app:external`: confusion counts, per-source accuracy, and the
  calibration-transfer paragraph (rerun result: applying the existing
  post-hoc temperature to the external corpus now slightly **improves** ECE,
  the opposite finding from the paper's previous, differently-checkpointed
  measurement).
- `tab:safety`: adaptive-attacker-evasion risk rating downgraded from HIGH to
  MEDIUM given the large ASR improvement (83.7% → 21.6%), with a retained
  caveat that this is scoped to the tested mutation battery, not a general
  robustness guarantee.

## Numbers verified unchanged (re-derived from fresh mixed-checkpoint
artifacts, not assumed)

- `tab:cp_full` (CP's isolated marginal effect): recomputed directly from
  `cp_full_eval_results__mixed.json` — byte-identical to the previously
  reported numbers (33 decision changes, 33 escalations, 11/21 attacker
  messages recovered, fp_off=99/fp_on=121, fn=0/0). This is a genuine,
  checked confirmation, not a reused stale number.
- Deployment latency/throughput/resource figures (`tab:deployment`): stated
  as checkpoint-invariant, since the merged LoRA checkpoint has identical
  architecture and parameter count (141.9M) to every other configuration
  measured on this hardware; this claim is architectural, not re-timed in
  this pass.

## Disclosed gap, not silently carried over

- Live-CARLA per-scenario detection results (`tab:carla_scenarios`, and the
  "B3 returned BENIGN on all 3,585 attack messages" finding) were **not**
  re-collected against the final checkpoint in this pass — no CARLA-capable
  environment was available (same infeasibility already documented in
  `b3_eval/v25_finetune/DEPENDENCY_TABLE.md` row 23). A caveat sentence was
  added to the Deployment Feasibility subsection and to the Discussion's
  CRITICAL-finding paragraph, stating plainly that this specific figure
  characterizes the architecture's live-deployment behavior in general, not
  a claim re-verified against the exact final checkpoint. This is the one
  place in the paper where a pre-existing number is retained without a fresh
  rerun; it is flagged, not hidden.
- The external-corpus reliability-diagram figure (previously
  `fig_ext_calibration`) was removed rather than regenerated with stale
  binned data; the corrected scalar ECE/Brier finding is now stated in text
  instead (Appendix `app:external`).
- The instruction-hiding/role-confusion robustness-perturbation battery
  (100% over-defense rate) and the STBV-Bench v2 threshold-sensitivity sweep
  were **not** rerun against the final checkpoint in this pass (matching the
  same gap already disclosed for the prior fine-tuned checkpoint in
  `DEPENDENCY_TABLE.md` row 13/31) — this remains an open item, stated as
  such in `FINAL_CONSISTENCY_REPORT.md`, not silently carried forward as if
  re-verified.

## Judgment call, not a silent deletion

- `tab:main_ablation`/`tab:full_ablation` (the B1/B1+B2/B1+B2+CP/B3-alone/
  full-stack layer ablation) was **kept**, per the task's explicit
  clarification that layer ablation is an architectural-contribution finding
  (B1+B2+CP+B3 fusion), not checkpoint-development history. Only its
  B3-dependent rows were refreshed against the final checkpoint.

## STBV-Bench v1 full ablation (added after the last save of this file)

The paper's single largest and most central result -- `tab:main_ablation`
(configs 4/5 rows), `tab:full_ablation`, the confusion matrix, per-family
recall, ROC/PR curves, calibration reliability diagram, and the RQ1/RQ2
McNemar/Cohen's-h/three-way-transition statistics -- was rerun end-to-end
against the final checkpoint, $n=10{,}000$, via a new `--checkpoint mixed`
mode added to `rerun_paper_ablation.py`. The result is a large, genuine
qualitative shift, not a small numeric tweak: B3-alone and full-stack F1
both move to near-ceiling (0.9999 / 0.995), every one of the 20 attack
families reaches 100% recall, and fusion's role changes from "meaningfully
improves detection" to "purely conservative escalation on an
already-near-perfect classifier" (84 transitions, all escalations, 0
de-escalations, 0 direct Accept↔Reject reversals). This is consistent with,
not contradicted by, this checkpoint's known weaker external-corpus result
(F1$=0.920$) -- STBV-Bench v1 and the mixed training corpus draw on
overlapping distributional territory (the mixed checkpoint's own training
data includes a disjoint slice of STBV-Bench v1), so a near-ceiling result
here is an in-distribution finding, not evidence of unlimited
generalization, and the manuscript's Results/Discussion/Conclusion text was
rewritten in several places to state this explicitly rather than let the
near-ceiling STBV-Bench number stand unqualified. Correspondingly:
- The baseline-comparison narrative changed materially: B3 no longer trails
  the two trivial bag-of-words baselines "substantially" -- it is now
  essentially tied with them (F1 0.9999 vs. 1.000), which strengthens
  (not weakens) the paper's own benchmark-validity critique of STBV-Bench,
  since even a real neural classifier now also saturates a benchmark whose
  benign class is ten sentences. Rewrote three baseline-section paragraphs
  accordingly.
- The "B3, strict label" row was removed from `tab:baselines` rather than
  recomputed with a stale or estimated number, since the raw per-message
  argmax label needed for that operating point is not retained in this
  rerun's logged CSV artifact -- disclosed via a table footnote, not
  silently dropped.
- The Limitations section's "bounded semantic-detection gap" claim was
  rewritten: STBV-Bench itself no longer shows a per-family gap (all 20
  families at 100%), so the claim was relocated to where it is now actually
  supported by fresh data -- the external corpus's per-family breakdown.
- The Discussion's "Failure modes, clustered and root-caused" paragraph's
  third and fourth findings (adaptive-evasion dominant mutation strategy;
  STBV-Bench's specific false-positive score-clustering mechanism) were
  rewritten from the prior checkpoint's specific, no-longer-applicable
  numbers to this checkpoint's own fresh findings, with the FP
  score-clustering claim explicitly marked as not resolved to a single
  mechanism for the final checkpoint (open item), rather than reusing the
  old checkpoint's narrower explanation.
- Figures `fig_confusion`, `fig_per_family_recall`, `fig_roc`, `fig_pr`,
  `fig_calibration`, `fig_ablation_summary`, and `fig_decision_transitions`
  were all regenerated in `FINAL_FIGURES/` from the clean rerun and
  repointed via `\includegraphics`.

## Figures

New, single-model figure set generated to `FINAL_FIGURES/` via the new
script `b3_eval/v25_finetune/generate_final_figures.py`, computed directly
from the same mixed-checkpoint rerun artifacts used for the tables above:
confusion matrix, per-family recall, ROC, PR, reliability diagram, external
corpus ROC and per-family recall, adaptive-attack confidence/detection
curve. `\includegraphics` paths in the affected sections were updated to
point at `FINAL_FIGURES/`. Figures whose underlying data was **not**
refreshed in this pass (CARLA scene photo, CARLA architecture diagram,
per-stage latency diagnostics, multi-run CARLA latency/scenario figures,
decision-transitions figure, ablation-summary bar chart, threat-coverage
figure) were left pointing at their existing `figures_v2/`,
`cp_full_eval/figures/`, or `deployment_eval/` paths, since their underlying
numbers are either checkpoint-invariant (latency/architecture) or were not
re-collected in this pass (CARLA) — consistent with the disclosed gaps above.

## Pass 2 — publication-freeze audit (fabricated-CI fix)

- `tab:baselines`: replaced a fabricated-looking bootstrap CI on B3's
  banded-F1 row (`[0.9997, 1.000]`, never actually computed) with a
  genuinely computed 2,000-resample bootstrap CI (`[0.9998, 1.000]`), found
  via a repo-wide audit cross-checking every table's caption promise
  ("CIs are 2,000-resample percentile bootstrap") against what was actually
  run for that cell. See `PUBLICATION_FREEZE_REPORT.md`.
- Disclosed (not fixed): `isce_config.yaml`'s `model_path` still points at
  the original checkpoint; verified this affects zero published numbers.

## Pass 3 — root-cause validation + real SUMO deployment rerun

- Deep root-cause audit of every benchmark, focused especially on the
  STBV-Bench v1 F1=0.995 jump (checkpoint SHA re-verified, zero
  train/eval overlap re-derived independently, thresholds traced in code,
  row/ID integrity re-confirmed) — result: **PASS**, real, non-buggy,
  explained by the training mixture's inclusion of a same-generator
  disjoint v1 slice. No paper text needed correcting on this point beyond
  what Pass 1 already said.
- Re-verified the CARLA/SUMO environment from scratch (not reused): SUMO
  genuinely available, CARLA genuinely and exhaustively absent (module,
  install dir, executable, Docker image, Docker daemon itself all checked).
- Reran the SUMO deployment evaluation against the final checkpoint,
  confirmed protocol-identical to the paper's original measurement, and
  **replaced** (not merely footnoted) `tab:deployment`'s SUMO column:
  mean 66.8→73.9~ms, $p_{95}/p_{99}$ 78.9/85.0→90.4/100.2~ms, B3 share
  98.6→98.7%, throughput 14.95→13.51~msg/s, RSS 1,081→1,109~MB.
- Real finding requiring a text change: the fresh $p_{99}$ now sits at,
  not comfortably inside, the 100~ms ETSI CAM budget. Rewrote the
  "B3 dominates latency" and "Real-time constraint conclusion" paragraphs
  and the deployment table's caption to state this plainly.
- Added 4 new figures to `FINAL_FIGURES/` (per-stage SUMO latency, latency
  percentiles, resource usage over the replay, SUMO-vs-CARLA throughput
  comparison) and repointed/added the corresponding `\includegraphics`
  blocks, replacing one stale figure (`fig_deploy_latency_stage`, whose
  SUMO half used pre-rerun numbers).
- See `ROOT_CAUSE_REPORT.md` for full evidence.

## Pass 4 — submission-prep (LaTeX build attempt, fresh Reviewer #2, polish)

- Attempted to compile `stbv_paper.tex`: no LaTeX toolchain exists on this
  machine (checked exhaustively); no PDF produced, disclosed rather than
  fabricated. Static consistency checks substituted and pass clean.
- Fresh Reviewer #2 pass on the current (post-Pass-3) text: strengthened
  the Discussion's "Deployment implications" paragraph to tie the new
  $p_{99}=100.2$~ms finding to a sharper claim ("budget already exhausted
  before multi-vehicle contention, not merely tightened by it"). Three
  further reviewer concerns assessed and intentionally left as-is with
  reasoning documented in `REVIEWER2_CHECKLIST.md` (mixed-checkpoint
  deployment table, unCI'd safety-rating downgrade, abstract's CARLA vs.
  SUMO throughput figure).
- Re-verified Tasks 1/2/3/4/6/7/8/9 from prior passes against the current
  file state (not re-executed from scratch): all confirmed still accurate,
  no regression introduced by Pass 3's edits.
- Deliverables consolidated into `FINAL_RESULTS.md`, `FINAL_TABLES.md`,
  `FINAL_REPRODUCIBILITY_REPORT.md`, `REVIEWER2_CHECKLIST.md`,
  `FINAL_SUBMISSION_CHECKLIST.md`, `READY_FOR_SUBMISSION.md`.

## Pass 5 — hard out-of-distribution benchmark (generalization pre-emption)

- Built a new, deliberately hard benchmark ($n=288$, `hard_ood_bench/`):
  12 malicious + 6 benign concepts (3 explicit truthful hard-negatives), 4
  linguistic registers absent from every existing corpus (abbreviated radio
  shorthand, CB-radio slang, plain non-native English, terse telemetry),
  LLM-generated (Mistral 7B, local) directly from concept descriptions —
  never paraphrased from an existing sentence — plus a deterministic
  structural-noise pass on a seeded 32% subsample. Verified zero exact-text
  leakage against all five relevant corpora (STBV-Bench v1's full pool, all
  v2.5 splits, v2's windows, the external corpus, and the exact
  mixed-corpus training data).
- Evaluated the frozen final checkpoint (no retraining) directly via
  `pipeline.b3_bridge.classify_text`: F1 0.446 [95% CI 0.368, 0.520] — the
  hardest benchmark in the paper by a wide margin (next: STBV-Bench v2 at
  0.521, external corpus at 0.920, STBV-Bench v1 at 0.995). Precision
  stays 1.000 wherever the model fires; the failure mode is silence
  (false negatives), not false alarms.
- Real failure-case analysis (four clusters, real unparaphrased message
  text + real model outputs) appended to `FAILURE_ANALYSIS.md`.
- Integrated into `stbv_paper.tex`: new Results subsection
  (`sec:hardood`, inserted between the external-corpus and adaptive-attack
  subsections), new table (`tab:hardood`), two new figures
  (`fig_hardood_per_family`, `fig_hardood_cross_benchmark`), edits to the
  Abstract, Introduction's Main Contributions, Limitations (new paragraph:
  "Real, register-specific generalization gap, not merely a theoretical
  concern"), and Conclusion (future-work reprioritized to lead with closing
  this gap). Corrected the external-corpus section's now-inaccurate
  "B3's weakest result in this paper" claim to "weakest among
  grammatical-text benchmarks."
- Reviewer #2 fresh pass (Task 8) found one real, fixable gap (no CI on the
  hard-OOD F1/recall point estimates) and fixed it with a genuine
  2,000-resample bootstrap (F1 0.446 [0.368, 0.520]); found one further
  gap (single-LLM, single-corpus dependency) that is disclosed as a
  legitimate, currently-unclosable open item rather than chased further.
- Re-verified full manuscript consistency post-integration: 0 dangling
  refs/cites, 27/27 `\includegraphics` paths resolve except the
  pre-existing `fig1.png`, 14 tables (13+1 `table*`) and 27 figures
  balanced.

## Pass 6 — hard-OOD benchmark scope audit (integrity check on Pass 5's result)

- Audited all 288 hard-OOD messages against the paper's own ETSI CAM/DENM
  threat model (`HARD_OOD_BENCHMARK_AUDIT.md`): 50% in-scope, 25%
  borderline (retained), 25% (`cb_informal`, CB-radio slang) genuinely
  out-of-scope. Reported, before any change was made, that the
  out-of-scope stratum was the *easiest* one (F1=0.633) — restricting to
  only in-scope styles would have made F1 *lower* (0.361), not higher.
- Replaced the 72 out-of-scope messages with 72 freshly-generated,
  fully-grammatical, ETSI-plausible replacements (`HARD_OOD_DATASET.md`'s
  changelog), zero re-verified leakage against all five relevant corpora.
- Re-evaluated the frozen checkpoint (no retraining) on the revised
  corpus: **F1 fell from 0.446 to 0.345** [95% CI 0.267, 0.418] — the
  scope correction made the result worse, not better, confirming the low
  score reflects a real gap, not unrealistic test construction.
- Evaluated whether continued fine-tuning was justified (a real,
  addressable register-diversity gap was found in the failure analysis)
  and **explicitly declined to fine-tune this phase**, reasoning
  documented in `FINAL_EVALUATION_REPORT.md`'s addendum: this project's
  own history shows every checkpoint change requires a full multi-hour,
  multi-benchmark re-validation to be trustworthy, and committing to that
  under this phase's time constraints risked exactly the kind of
  under-validated change the task explicitly warned against. Recommended
  as future work instead.
- Updated `stbv_paper.tex` throughout (Abstract, Contributions, Results
  §hardood text/table/figures, Limitations, Conclusion) to the final,
  audit-revised F1=0.345 number, with the scope-audit finding and its
  "made it worse" result stated in the Results text itself. No new
  checkpoint was produced, so the paper's single-checkpoint identity
  (`semantic_gate_v3_mixed_lora_merged`) is unchanged and unambiguous.
- Re-verified consistency post-edit: 0 dangling refs/cites, 27/27 figures
  resolve except `fig1.png`, braces balanced (1255/1255).

## Pass 7 — presentation/structure phase (repositioning, not new claims)

- **Task 1/2**: classified every benchmark A (core)/B (supporting)/C
  (exploratory)/D (future work); no further Results trimming beyond what
  the classification supports (`ROBUSTNESS_EVAL_REPORT.md`'s Task 1/2
  section).
- **Task 3 (new)**: reran the paper's own pre-existing 11-family
  perturbation/robustness battery (`b3_eval/run_robustness.py`, previously
  disclosed as stale) against the final checkpoint via a new wrapper
  `b3_eval/run_robustness_mixed.py` (monkeypatches
  `b3_eval._harness.MODEL_DIR`, writes to `robustness_mixed.json`,
  original `robustness.json` verified untouched). Zero leakage
  re-verified against all corpora. Result: 6/11 families improved, 4
  unchanged, 1 (`contradictory`) regressed to 100% over-defense; aggregate
  accuracy 0.833→0.864, McNemar $p=0.727$ (not significant). Full
  metrics (accuracy/precision/recall/F1/ECE/Brier/bootstrap CI/McNemar):
  `ROBUSTNESS_EVAL_REPORT.md`.
- **Task 4**: kept this result as prose in its existing Results location
  (the "Calibration, Robustness, and Latency" paragraph, replacing the
  stale-gap disclosure sentence) rather than promoting it to a new
  headline table — the aggregate delta is not statistically significant,
  so it does not support a standalone claim; the one genuinely reportable
  finding (`contradictory`'s regression) fits the existing narrative
  paragraph's level of detail.
- **Task 5**: moved the hard-OOD benchmark (`sec:hardood`) out of main
  Results entirely, into a new Limitations subsection ("Exploratory
  scope-boundary testing..."), reframed as a deliberate boundary probe
  outside the paper's declared deployment register rather than a headline
  capability result. **All numbers, the audit finding, and the
  failure-cluster analysis are unchanged and fully intact** — F1=0.345
  [0.267, 0.418], accuracy=0.458, the "correcting the benchmark made it
  worse" finding, the register-shift failure examples. Two figures
  (`fig_hardood_per_family`, `fig_hardood_cross_benchmark`) were not
  re-added in the new location (kept as standalone artifacts in
  `FINAL_FIGURES/`, not referenced in-paper) to keep the Limitations
  section's presentation proportionate to its now-exploratory status; a
  compact results table (`tab:hardood`) was retained.
- **Task 6**: updated Abstract, Introduction's Main Contributions,
  Results (the external-corpus paragraph's now-inaccurate
  "weakest-result-in-this-paper" framing), Limitations (new subsection),
  and Conclusion to be consistent with the repositioning. Single
  checkpoint identity unchanged throughout
  (`semantic_gate_v3_mixed_lora_merged`,
  `638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`).
- Re-verified consistency post-edit: 0 dangling refs/cites, 25/25 figures
  resolve except `fig1.png` (figure count dropped from 27 to 25, since the
  two hard-OOD figures are no longer included inline), 14 tables (13+1
  `table*`, unchanged — one table relocated, not added/removed), braces
  balanced (1237/1237).

## Pass 8 — independent in-scope benchmark (new primary generalization evidence)

- Built a new, independent evaluation corpus (`indep_bench/`, $n=216$,
  seed 20260810): the inverse of hard-OOD — fully in-scope (grammatical,
  professional ETSI CAM/DENM register, no register variation) but
  testing genuinely novel scenario content (53 distinct city/road
  combinations across 12 cities/8 roads never referenced anywhere else in
  this project, randomized entity IDs, freshly-generated narratives per
  concept). Same 18-concept taxonomy as hard-OOD for family-level
  comparability.
- Three-method leakage audit against **all six** existing corpora
  (STBV-Bench v1/v2/v2.5, the mixed-corpus training pool, the external
  corpus, hard-OOD both versions): exact-text (0/216 matches against any
  corpus), template/construction independence (verified by generation
  design), embedding-similarity (`all-MiniLM-L6-v2`, thresholds
  0.95/0.90/0.85, reused from `b3_eval/v25_finetune/audit_leakage.py`'s
  established methodology, 2,805-message reference pool) — **0/216 exceed
  even the loosest 0.85 threshold**; highest similarity found: 0.697.
- Evaluated the frozen final checkpoint (no retraining):
  F1=0.352 [95% CI 0.260, 0.440], accuracy=0.472, precision=0.969,
  recall=0.215. Comparably low to hard-OOD despite full in-scope
  compliance.
- **Mandatory root-cause investigation triggered** (same rigor as
  `ROOT_CAUSE_REPORT.md`): checkpoint SHA-256 (confirmed correct via run
  manifest), threshold/config (unmodified production path), message
  truncation (max 405 chars, well under the 256-token limit), character
  encoding (a terminal-display artifact only; the underlying UTF-8 data
  verified correct at the codepoint level), label mapping (verified
  correct by direct inspection), failure-mode shape (uniformly
  high-confidence FNs, mean confidence 0.963; graded 0–66.7% per-family
  recall spread, inconsistent with a uniform pipeline-bug signature).
  **No bug found — the low score is reported as-is.**
- Integrated as a **primary Results subsection** (`sec:indepbench`,
  `tab:indep`, one new figure `fig_indep_per_family`), inserted after
  External Semantic Evaluation and before Adaptive Attack Evaluation —
  not appendix, per this phase's explicit criterion that a scientifically
  sound, leakage-clean, root-caused result earns primary status regardless
  of outcome. Abstract, Main Contributions, and Conclusion updated to cite
  it as converging evidence alongside (structurally different from)
  hard-OOD.
- **Hard-OOD confirmed still correctly positioned** in Limitations/Future
  Work from the prior phase — not re-moved, numbers unchanged.
- Full detail: `INDEPENDENT_BENCHMARK.md` (methodology + leakage audit),
  `INDEPENDENT_BENCHMARK_RESULTS.md` (metrics + investigation).
- Re-verified consistency post-edit: 0 dangling refs/cites, 26/26 figures
  resolve except `fig1.png`, 15 tables (14+1 `table*`) and 26 figures
  balanced, braces balanced (1275/1275).

## Pass 9 — controlled surface-attribute-only confirmatory benchmark

- Built a second independent corpus (`indom_bench/`, $n=216$, seed
  20260811) to test whether the first independent benchmark's low score
  (F1=0.352) was confounded with added narrative complexity rather than
  content novelty alone. Calibrated message length/directness to
  STBV-Bench's own templates (mean 15.2 words vs. 34.4 for the first
  corpus), varying only surface attributes (city, road, entity ID,
  weather, lane) with the same 18-concept taxonomy.
- Leakage-verified against all seven corpora used anywhere in this
  project (the six required + the first independent benchmark itself):
  zero exact-text overlap against all seven; zero near-duplicates at
  embedding-similarity thresholds up to 0.85 (highest found: 0.753,
  reference pool of 3,021 texts).
- Result: F1=0.314 [95% CI 0.224, 0.409] — statistically indistinguishable
  from the first independent benchmark's 0.352 [0.260, 0.440] (CIs
  overlap substantially). Root-cause quality check repeated (checkpoint
  SHA, truncation, encoding, label mapping, failure-mode shape) — no bug
  found.
- **Decision: both independent corpora kept in main Results; neither
  replaces the other.** Their agreement rules out narrative complexity as
  an alternative explanation for either result — integrated as a
  confirmatory paragraph within the existing `sec:indepbench` subsection
  (no new standalone table, avoiding redundant proliferation for a
  confirmatory-only finding).
- Full detail: `INDOMAIN_BENCHMARK.md`, `INDOMAIN_BENCHMARK_RESULTS.md`.
- Re-verified consistency post-edit: 0 dangling refs/cites, 26/26 figures
  resolve except `fig1.png`, braces balanced (1281/1281), table/figure
  counts unchanged (15 tables, 26 figures — no new table/figure added,
  confirmatory prose only).

## Pass 10 — six-part quality audit of the in-domain confirmatory benchmark

- Full audit-before-modification pass on `indom_bench/indomain_corpus.jsonl`
  (all 216 messages read in full): Part A scope classification (194
  clearly in-scope, 10 borderline/retained, 12 out-of-scope), Part B
  difficulty leveling (0% Level-4, no redesign triggered), Part C
  simulated inter-annotator agreement (12/216 flagged <80%, same 12 as
  Part A), Part D ETSI realism audit (12 messages contained unrealistic
  self-narrating meta-commentary, e.g. literal parenthetical text like
  "(Manipulates safe situation as dangerous...)" or "No manipulation
  intent." baked into the message — a generation artifact no real V2X
  broadcast would produce, and a validity defect since it embeds the
  label in the input), Part E distributional comparison (this benchmark's
  messages are ~half the length of STBV-Bench v1/v2.5/external/the mixed
  training pool — a real, disclosed, **not corrected** limitation, since
  fixing it would require a corpus-wide rebuild outside this audit's
  targeted-fix mandate), Part F vehicle-solvability (10 of the 12 flagged
  messages were only "solvable" because they leaked their own answer).
- **12 of 216 messages (5.6%) rewritten** via the same LLM-generation
  mechanism, corrected prompts forbidding self-labeling/meta-commentary
  while preserving or strengthening the underlying attack content (no
  simplification). Leakage re-verified on all 12 against all seven
  corpora used anywhere in this project (STBV-Bench v1/v2/v2.5, the
  mixed-corpus training pool, the external corpus, hard-OOD, the prior
  independent benchmark) plus the unchanged 204 items within this same
  corpus — **zero overlap on all counts**.
- Reran the frozen final checkpoint on the corrected corpus
  (`indom_bench/indomain_corpus_v2.jsonl`): F1=0.294 [95% CI 0.204,
  0.384], vs. 0.314 [0.224, 0.409] pre-audit — **not a meaningful
  difference** (CIs overlap almost entirely). The audit confirmed rather
  than manufactured the benchmark's soundness.
- Updated `stbv_paper.tex`'s confirmatory paragraph in `sec:indepbench`
  to report the post-audit F1=0.294 as the final number, with the audit
  methodology and the disclosed-but-uncorrected length-shift limitation
  both cited in-text.
- Full detail: `INDOMAIN_BENCHMARK_AUDIT.md` (new), `INDOMAIN_BENCHMARK.md`
  and `INDOMAIN_BENCHMARK_RESULTS.md` (both updated with addenda,
  original pre-audit content retained for traceability).
- Re-verified consistency post-edit: 0 dangling refs/cites, 26/26 figures
  resolve except `fig1.png`, braces balanced (1284/1284), no
  table/figure count change (audit result integrated as prose only).
