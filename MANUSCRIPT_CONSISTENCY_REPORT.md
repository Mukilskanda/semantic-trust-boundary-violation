# Manuscript Consistency Report — `stbv_paper.tex`

**Scope**: full-manuscript audit against (1) the checkpoint-swap-only
reruns (`REGRESSION_REPORT.md` / `UPDATED_RESULTS.md` / `UPDATED_TABLES.md`),
(2) the v1 threshold/temperature recalibration
(`RECALIBRATION_RESULTS.md`, `results/recalibrated_thresholds.json`,
`results/v1_test_three_way_comparison.json`), and (3) this task's
generalization evaluation of the frozen calibrated deployment package
(`GENERALIZATION_RESULTS.md`). **`stbv_paper.tex` itself was not edited.**
Every number quoted below as "current .tex value" is the manuscript's
existing, unmodified text, describing the **original checkpoint**
(the fine-tuned checkpoint was never adopted into the manuscript, per
`REGRESSION_REPORT.md`'s explicit recommendation, which this task's Part A
findings do not overturn — see `GENERALIZATION_RESULTS.md` Task 8).

Three checkpoint/config arms are referenced throughout:
- **(a) original** — what `stbv_paper.tex` currently reports
- **(b) fine-tuned, uncalibrated** — checkpoint-swap-only, old thresholds (0.85/0.60)
- **(c) fine-tuned, calibrated** — this task's frozen package (T=3.3242, high=0.79, med=0.50, ensembling+confidence-aware-benign on)

---

## Step 1 — Evidence matrix

| # | Section/Subsection | Claim (paraphrase) | Source file | Current .tex value | New value (arm b / arm c) | Status |
|---|---|---|---|---|---|---|
| 1 | Abstract / §Results RQ1 | B3-alone F1, full-stack F1 on STBV-Bench v1 | `UPDATED_TABLES.md` §1, `results/ablation_rerun_comparison.json` | F1=0.715 (B3 alone) / 0.718 (full stack) | (b) 0.390/0.403 — **severe regression**; (c) test-split F1=0.924 at recalibrated thresholds (`v1_test_three_way_comparison.json`, n=757) — **near-full recovery**, still not identical to (a) | **UPDATED** (report both b and c; c is the headline fix) |
| 2 | §Results RQ1, Table `tab:main_ablation` | Full ablation, 5 configs, McNemar p=3.06e-29 fusion effect | same | rows in §Results | (b) numbers in `UPDATED_TABLES.md` §1; McNemar b3-alone-vs-fullstack not separately recomputed for (c) in this task (out of Part A's 8-task scope, which targeted v2/mixed/external/adaptive/CP/deployment, not v1 re-ablation beyond the already-completed recalibration test split) | **UPDATED** for (b); **UNSUPPORTED gap** for (c) full 5-config ablation (only the 2-arm classify() test-split comparison was rerun for v1, not the fused 5-config ablation at calibrated thresholds) |
| 3 | §Results RQ1, Table `tab:main_ablation` rows "B1 only", "B1+B2" | `enable_b3=False` configs | — | 0.305/0.642/0.018/0.034/0.023 | **UNCHANGED by construction** — B3 never loaded when disabled | UNCHANGED |
| 4 | §Results RQ3, VeReMi kinematic bench | MBD recall/precision/F1/FPR, B3 contributes 0% | — | Recall 0.775, Precision 0.607, F1 0.681, FPR 0.524 | Not rerun this task or prior (Category C — no free text for B3) | UNCHANGED (reason: kinematic-only content) |
| 5 | §Results RQ4/5(b), Table `tab:coverage` | Shared-scene semantic-attacker recall 70.3%(msg-level as stated)/kinematic 90.3% | `GENERALIZATION_RESULTS.md` Task 2, `mixed_threat_recalibration_analysis.json` | semantic 70.3%/kinematic 90.3% (**note**: `UPDATED_TABLES.md` measured the paper's own original-checkpoint rerun at 83.8%(msg)/86.9%(kin), not the .tex's stated 70.3/90.3 — a **pre-existing discrepancy between the .tex text and its own committed artifact**, disclosed in `UPDATED_TABLES.md` §2, not created by this task) | (b) semantic 69.0%(msg)/86.9%(kin); (c) semantic 69.5%(msg)/86.9%(kin) | **UPDATED** (regression persists after calibration); **flag pre-existing (a)-vs-artifact mismatch** for the manuscript authors independent of this task |
| 6 | §Results RQ6, contextual v2 eval | Aggregate Decision-Trust F1=0.517 | `GENERALIZATION_RESULTS.md` Task 1, `v2_recalibration_analysis.json` | F1=0.517 | (b)=(c) F1=0.3905 (decisions byte-identical between b/c; only ranking/calibration metrics differ) | **UPDATED (severe regression, unaffected by calibration)** |
| 7 | §Results RQ6 | "threshold sensitivity... byte-identical across nearly the entire tested range" | — | sweep over τ_H∈[0.55,0.90] | This task's actual recalibrated threshold (0.79) falls inside that swept-and-declared-insensitive range, and empirically the v2 decision distribution WAS in fact insensitive to it (0 decisions changed, confirmed) — **this specific robustness claim survives real recalibration**, a genuine corroboration | UNCHANGED / CORROBORATED |
| 8 | §Results, calibration para | T=2.145, ECE 0.0619→0.0280, Brier 0.0613→0.0553, ROC-AUC 0.747, PR-AUC 0.911 | `RECALIBRATION_RESULTS.md`, `recalibrated_thresholds.json` | T=2.145 etc. | New fitted T=3.3242 (v1, different split methodology — disclosed in `recalibrated_thresholds.json` methodology block, not template-disjoint since v1 lacks `template_id`); val ECE 0.332 post-T (pre-T 0.531), test ECE 0.338 (pre-T 0.526) — **note the new T is fit on a much worse-calibrated raw distribution than the original 2.145 fit was**, so absolute ECE/Brier values are not directly comparable to the .tex's 0.0619/0.0280 baseline (different checkpoint, different starting calibration) | **UPDATED, with a strong caveat**: this is a different checkpoint's calibration exercise, not a recalibration of the same numbers; report both, don't conflate |
| 9 | §External Semantic Evaluation, Table `tab:external_eval` | F1=0.936, recall=0.899, precision=0.976, ROC-AUC=0.975 | `GENERALIZATION_RESULTS.md` Task 3, `external_semantic_calibrated_recompute.json` | as stated | (b)=(c) discrimination identical: F1=0.929, recall=0.888, precision=0.975, ROC-AUC=0.952 (calibration cannot move argmax, proven algebraically) | **UPDATED (small regression)** |
| 10 | §External Semantic Evaluation | Applying existing T=2.145 to external corpus increases ECE 0.054→0.169 (calibration doesn't transfer) | `external_semantic_calibrated_recompute.json` | as stated | New finding, arm (c): applying the *new* calibrated T=3.3242 to this same corpus gives ECE=0.1485 (worse than both raw T=1's 0.079 AND the old T=2.145's 0.064) — **the new temperature transfers even worse than the old one did** | **NEW finding to ADD**, strengthens the paper's own existing point about calibration non-transfer |
| 11 | §Adaptive Attack Evaluation, Table `tab:adaptive` | ASR 83.7% (41/49) | `GENERALIZATION_RESULTS.md` Task 4 | 83.7% (41/49) | (b)=(c) 84.3% (43/51) — note: this session's live rerun uses n=51, not the paper's committed n=49; already disclosed in `REGRESSION_REPORT.md`/`DEPENDENCY_TABLE.md` row 16 as a small discrepancy from the paper's committed artifact, not created by this task; calibration provably changes nothing (mechanistic proof: script never reads B3RiskPolicy config) | **UPDATED (n discrepancy + ASR), UNCHANGED across b→c** |
| 12 | §CP Full Evaluation, Table `tab:cp_full` | CP recovers 11/21 attacker messages | `GENERALIZATION_RESULTS.md` Task 5, `cp_full_eval_calibrated_analysis.json` | 11/21, 6/21→17/21 REJECT | (b)=(c) byte-identical decision distributions across all 4 config arms, confirmed at message granularity (0/138 rows differ) | UNCHANGED (confirmed by real rerun in this task, not just architectural reasoning) |
| 13 | §Deployment Feasibility, SUMO, Table `tab:deployment` | (SUMO column numbers — latency, throughput not fully quoted in visible excerpt) | `GENERALIZATION_RESULTS.md` Task 6, `deployment_calibrated_analysis.json` | — | (a)/(b)/(c) decision distributions byte-identical (ACCEPT 235/CAUTION 1765/REJECT 0 across all three); latency deltas between runs are machine-noise, disclosed as such, not calibration-attributable | UNCHANGED (decisions); latency comparison inconclusive on this shared, uncontrolled hardware — flagged, not asserted |
| 14 | §Deployment Feasibility, Live CARLA | "B3 returned BENIGN on all 3,585 live attack messages" | `DEPENDENCY_TABLE.md` row 23 | as stated | **Not rerun — CARLA genuinely infeasible in this environment** (`import carla` fails, no server). Not attempted with the calibrated package either; carries forward as an open gap | UNSUPPORTED-BY-RERUN (disclosed infeasibility, not fabricated) |
| 15 | §Baseline Comparison, Table `tab:baselines` | TF-IDF F1=1.000 trivializes benchmark; B3 banded 0.715, strict 0.311 | — | as stated | Not part of Part A's 8 tasks (baseline comparison doesn't involve B3 calibration); B3 rows auto-inherit from row 1's v1 numbers if checkpoint is swapped | UNCHANGED (methodology/finding independent of calibration) |
| 16 | §Discussion — Failure Analysis | 4 root-cause clusters (VeReMi 181km/h threshold FP, MBD cold-start, adaptive context_poisoning mechanism, STBV-Bench 69 FPs) | — | as stated | Mechanistic/architectural findings, not per-checkpoint numbers; not re-derived in this task | UNCHANGED (methodology-level, not a rerun-dependent number) |
| 17 | §Limitations | Narrative-indirection gap, robustness weaknesses, adaptive severity | — | as stated | Numbers restate rows 1/13 (robustness battery) and 11 (ASR) | **UPDATED per rows 1 and 11** (inherits) |
| 18 | §Limitations | CP data-generation gap, prevalence assumptions | — | as stated | Independent of B3 weights | UNCHANGED |
| 19 | App. §Reproducibility, checkpoint SHA-256 | original checkpoint hash | — | original hash | Fine-tuned checkpoint hash differs (`sha256_16: b3a85943127fa4c7` for merged LoRA, per `rerun_external_and_cp.py` manifests); calibrated arm uses the SAME checkpoint file, only config differs, so no new hash needed for arm (c) | **UPDATE only if checkpoint is swapped**; N/A while (a) remains canonical |
| 20 | App. §Fusion Constants | τ_H=0.70, τ_L=0.40, B3 bands 0.85/0.60, CP weights | — | as stated | **Explicitly out of scope** — user's rule forbids touching these threshold/fusion constants; B3's OWN internal risk-band thresholds (0.85/0.60→0.79/0.50) are a *different* parameter from the Trust-Engine's τ_H/τ_L, and per `recalibrated_thresholds.json`'s own note, `trust_engine.policy.TrustPolicy` fallback thresholds are documented but currently inert (never invoked in the live wiring) | UNCHANGED for τ_H/τ_L; **B3's own risk bands changed (0.85/0.60→0.79/0.50) IF the calibrated package is adopted** — must be stated explicitly wherever 0.85/0.60 appears if the checkpoint swap is made |
| 21 | App. §Semantic Transformation Engine, worked example 1 | B3 confidence=0.699 on quoted message | `DEPENDENCY_TABLE.md` row 33 | confidence=0.699, risk=medium | Fine-tuned checkpoint on same text: confidence=0.9895, risk=HIGH (from prior task; calibrated-package confidence not separately re-derived in this task — would require running that exact single string through the calibrated pipeline, not done here) | **UPDATED for (b)**; **not yet computed for (c)** — flagged gap |
| 22 | §Related Work, §Problem Statement, §Proposed Architecture, §Theoretical Properties | Architectural/prose description, 6 formal fusion properties | — | as stated | Proofs are about `decide()`'s code, not B3's weights | UNCHANGED |
| 23 | §Methodology (all subsections) | Dataset construction, threat model, baselines, metrics, implementation, setup | — | as stated | Describes procedure, not results; user's rule says methodology must not change | UNCHANGED |
| 24 | App. §Statistical Methodology | Bootstrap/McNemar/Cohen's-h procedure description | — | as stated | Procedure-only | UNCHANGED |
| 25 | App. §Training Data Provenance | Original checkpoint's antecedent-project data provenance | — | as stated | Describes original checkpoint only; a new subsection would be needed to describe the LoRA continuation's own provenance if checkpoint swap is adopted | UNCHANGED for existing text; new content needed only if checkpoint changes |
| 26 | App. §Parameter Sensitivity Sweep | τ sweep, 98.7% fidelity reconstruction | — | as stated | Not re-derived for (b)/(c) in this task | UNCHANGED text; **not verified against arm c** |
| 27 | App. §Human Validation | Annotator agreement (not yet run in paper either) | — | "not yet collected" | N/A | UNCHANGED (not applicable) |
| 28 | App. §External Semantic Evaluation appendix | Corpus construction, leakage check | — | as stated | Describes corpus itself | UNCHANGED |
| 29 | App. §Cooperative Perception Validation | Same 24-scene/142-msg fixture as row 12 | `cp_full_eval_calibrated_analysis.json` | as stated | Confirmed byte-identical under calibration too (this task) | UNCHANGED (now doubly confirmed) |

---

## Step 2 — Numerical audit (every value flagged as no-longer-matching-newest-results)

Values that change if the manuscript's checkpoint is ever swapped to (b)
or (c) — **none of these are edited in the .tex; this is the audit list**:

1. Abstract: "F1=0.715" / "F1=0.718" → regress to 0.390/0.403 (b); partially recovers to 0.924 on the recalibration test split (c, different split/scope, not the full ablation)
2. Abstract: "83.7% attack success rate" → 84.3% under both (b) and (c), plus an n=49→51 discrepancy already flagged as pre-existing
3. Abstract: "89.9% recall and 97.6% precision (ROC AUC 0.975)" external corpus → 88.8%/97.5%/0.952 under (b)=(c)
4. Abstract: "110ms mean latency" — not independently re-measured for (c) in Part A (deployment task measured full-replay wall time, not the isolated per-message latency claim in the abstract at batch=1); DEPENDENCY_TABLE.md row 14 treats this as Category B, spot-verified via a different (v2.5) harness, not this exact figure
5. §Results RQ1: F1 0.715/0.718, McNemar p=3.06e-29 → regressed values in `UPDATED_TABLES.md` §1
6. §Results RQ4/5(b): 70.3%/90.3% → already flagged in Step 1 row 5 as inconsistent with the paper's own committed artifact even before any checkpoint change
7. §Results RQ6: F1=0.517 → 0.3905 (unaffected by calibration)
8. §Results calibration: T=2.145, ECE 0.0619→0.0280, Brier 0.0613→0.0553, ROC-AUC=0.747, PR-AUC=0.911 → new checkpoint has a different, non-comparable calibration profile (see Step 1 row 8)
9. Table `tab:adaptive`: 83.7% (41/49) → 84.3% (43/51)
10. Table `tab:external_eval`: F1/recall/precision/ROC-AUC as in row 3 above
11. §Baseline Comparison Table `tab:baselines`: B3 rows (0.715/0.311) inherit row 1's regression if checkpoint swaps
12. App §Reproducibility: checkpoint SHA-256 — must change if checkpoint swaps
13. App §Fusion Constants: B3's own 0.85/0.60 risk bands — must become 0.79/0.50 if the calibrated package is adopted (this is the ONE threshold change the frozen calibration package legitimately makes; distinct from τ_H/τ_L which are untouched)
14. App §Semantic Transformation worked example: confidence=0.699→0.9895 (b); not measured for (c)
15. Table `tab:coverage`: 70.3%/90.3% (or artifact-measured 83.8%/86.9%) → 69.0–69.5%/86.9%

No other numeric values in Discussion, Limitations, Conclusion, or the
appendix hyperparameter/dataset-composition tables trace to B3's
checkpoint or calibration (confirmed via the DEPENDENCY_TABLE.md Category-C
rows, which this task did not need to re-verify since they are
architecturally, not empirically, independent of B3's weights).

---

## Step 3 — Table-by-table verification

| Table | Verified against | Result |
|---|---|---|
| `tab:main_ablation` | `UPDATED_TABLES.md` §1 | Every row except "B1 only"/"B1+B2" would need updating on checkpoint swap; NOT touched for arm (c) beyond the 2-arm test-split comparison |
| `tab:full_ablation` (appendix) | same source data as `tab:main_ablation` | Same status |
| `tab:coverage` | `GENERALIZATION_RESULTS.md` Task 2 | Regression confirmed real, calibration does not fix it |
| `tab:external_eval` | `GENERALIZATION_RESULTS.md` Task 3 | Small regression confirmed, calibration cannot fix (argmax-invariant) |
| `tab:adaptive` | `GENERALIZATION_RESULTS.md` Task 4 | ASR unchanged by calibration (mechanistically + empirically) |
| `tab:cp_full` | `GENERALIZATION_RESULTS.md` Task 5 | Byte-identical, confirmed by real rerun |
| `tab:deployment` (SUMO column) | `GENERALIZATION_RESULTS.md` Task 6 | Decisions byte-identical; CARLA column not rerun (infeasible) |
| `tab:carla_scenarios` | not rerun | CARLA infeasible in this environment; carries forward unchanged, flagged as not independently reverified under any checkpoint in this or the prior task |
| `tab:baselines` | inherits row 1 | Not independently rerun; B3 rows would auto-update with a v1 ablation rerun, not done for (c) |
| `tab:safety` | not touched by any task | Describes failure-mode severity ratings, not raw metrics — architectural, unaffected |
| `tab:related_work` | not touched | Literature comparison table, no B3 dependency |

---

## Step 4 — Figure-by-figure classification

| Figure | File | Classification | Action taken |
|---|---|---|---|
| `fig_confusion`, `fig_per_family_recall` | `figures_v2/fig_confusion.pdf`, `fig_per_family_recall.pdf` | Must regenerate if checkpoint swaps (v1 confusion matrix changes) | **Not regenerated** — checkpoint swap not adopted (Task 8 recommendation); no action needed while manuscript reports arm (a) |
| `fig_ablation_summary`, `fig_decision_transitions` | `figures_v2/*.pdf` | Same | Not regenerated |
| `fig_roc`, `fig_pr`, `fig_calibration` | `figures_v2/fig_roc.pdf`, `fig_pr.pdf`, `fig_calibration.pdf` | Must regenerate if checkpoint/calibration swaps | Not regenerated (same reasoning) |
| `fig_latency`, `fig_latency_per_stage` | `figures_v2/*.pdf` | Unaffected by calibration (Task 6: runtime unchanged); would need regeneration only on checkpoint swap | Not regenerated |
| `fig_threat_coverage` | `figures_v2/fig_threat_coverage.pdf` | Static threat-taxonomy figure, no B3 dependency | Unchanged |
| `ext_fig_roc`, `ext_fig_per_family_recall`, `ext_fig_calibration` | `external_semantic_eval/figures/*.pdf` | Must regenerate if checkpoint swaps; the new calibration-transfer number (Step 1 row 10) is a genuinely NEW data point not yet plotted anywhere | Not regenerated; **recommend adding a new bar to `ext_fig_calibration` for the (c) arm's T=3.3242 ECE=0.1485 if the manuscript ever adopts calibration language** |
| `adaptive_fig_confidence_evolution` | `adaptive_attack/figures/*.pdf` | Unaffected by calibration (Task 4: script bypasses config entirely) | Unchanged |
| `cp_fig_attacker_detection` | `cp_full_eval/figures/*.pdf` | Confirmed unaffected by calibration (Task 5, byte-identical) | Unchanged |
| `fig_deploy_*` (7 figures, SUMO+CARLA) | `figures_v2/fig_deploy_*.pdf/.png` | SUMO-side unaffected (Task 6); CARLA-side not re-measured (infeasible) | Unchanged |
| `fig1.png` (Fig. `fig_1`, intro architecture diagram) | referenced at line 68, `\label{fig_1}` at line 70 | **File missing on disk** — `\includegraphics{fig1.png}` has no corresponding file anywhere in the repo (confirmed via filesystem check) | **FLAGGED — pre-existing broken reference, not introduced by this task; must be resolved before publication regardless of any checkpoint decision** |

No figures were regenerated in this task's Part B, because none of the
underlying numbers changed enough (or were adopted into the manuscript)
to warrant it: the manuscript still legitimately describes arm (a), and
none of this task's or the prior task's findings recommend an
unconditional checkpoint swap (see `GENERALIZATION_RESULTS.md` Task 8,
Q1). `UPDATED_FIGURES/` from the prior task already contains the
checkpoint-swap-only comparison figures for anyone evaluating arm (b);
no new figures were added there in this Part A/B pass since Part A's six
tasks were table/statistic-producing, not plot-producing (documented at
the end of `GENERALIZATION_RESULTS.md`).

---

## Step 5 — Claims audit ("improves/better/outperforms/highest/significant/robust/effective/generalizes/state-of-the-art/superior")

| Sentence (location) | Current wording | Supported by current evidence (arm a, as published)? | If not, what's supported |
|---|---|---|---|
| Abstract: "aggregate metrics unchanged across a wide sweep of decision thresholds... robust to threshold miscalibration" | "robust" | **Yes, and now doubly corroborated** — this task's real recalibrated threshold (0.79) falls inside the swept range and the v2 decision distribution was in fact unchanged | No change needed |
| Abstract: "a substantially more serious finding than any single-shot number in this paper" (re: adaptive ASR) | comparative claim | Yes, supported, and this task's rerun (b)=(c) shows the finding is not an artifact of calibration/checkpoint choice — it persists identically | No change needed |
| §Results RQ4/5(b): "robust to threshold miscalibration" (aggregate metrics unchanged across sweep) | "robust" | Same as above, now empirically double-checked with a real (not swept-simulated) recalibration | No change needed |
| §External Eval: "corroborating rather than contradicting" | describes cross-corpus consistency of the *weak-family* finding, not of overall calibration | Still true for arm (a); this task adds that arm (c)'s temperature transfers *even worse* — strengthens, does not weaken, the existing "calibration doesn't transfer" argument | No change needed, could be strengthened with the new number |
| §Discussion: "reproducibly what a single run could only suggest" (CARLA) | reproducibility claim | Not reverified in this task (CARLA infeasible); stands on the prior 15-run evidence, unaffected by anything in Part A | No change needed from this task's evidence |
| App §Reproducibility, general framing of "frozen checkpoint" language throughout | "frozen B3 checkpoint" | True and unaffected — no claim anywhere in the current .tex asserts the fine-tuned/calibrated checkpoint is superior, so there is **no overclaiming to walk back** in the current text | N/A |
| (Hypothetical future claim, NOT currently in the .tex) "the fine-tuned checkpoint improves detection" | — | **Would NOT be supported** if added — Part A shows v2 and mixed-threat semantic recall are both worse under (b) and (c) than (a) | If ever added: "the calibrated fine-tuned checkpoint improves ranking/calibration quality on v2 relative to the uncalibrated fine-tuned checkpoint, without recovering the original checkpoint's recall" |
| (Hypothetical) "calibration improves adversarial robustness" | — | **Would NOT be supported** — Task 4 shows zero effect, confirmed mechanistically and empirically | If ever added: state explicitly that calibration has no measurable effect on adaptive-attack ASR |

**Net finding**: the manuscript as currently written makes no claims about
the fine-tuned or calibrated checkpoint at all (it was never adopted), so
there are no live overclaims to correct in the existing text. The audit's
value is prospective — it documents exactly which comparative claims
(*"improves," "robust," "generalizes"*) would or would not survive if a
future revision proposed adopting the calibrated package, and the answer
is mixed: the "robust to threshold miscalibration" claim survives and
strengthens; a hypothetical "calibration improves detection/robustness"
claim would not be supported and must not be added without the caveats
in `GENERALIZATION_RESULTS.md` Task 8.

---

## Step 6 — Cross-reference verification

Checked programmatically (`b3_eval/v25_finetune/check_refs.py`):

- **67 `\label{}` definitions, 48 unique `\ref{}` targets — every `\ref` resolves to an existing `\label`. Zero broken references.**
- **30 `\cite{}` keys used, 30 `\bibitem{}` entries defined — every citation resolves. Zero missing bibliography entries.**
- **22 of 23 `\includegraphics` files exist on disk.** The one exception:
  `fig1.png` (line 68, `\label{fig_1}` at line 70, intro architecture
  diagram) — **file is missing from the repository entirely.** This is a
  pre-existing defect, not something introduced by any checkpoint/
  calibration work in this or the prior task, but it will break PDF
  compilation and must be fixed (restore the file or remove the
  `\includegraphics` call) before submission, independent of any of the
  numeric findings above.

---

## Step 7 — Final report

### (1) Everything changed (this task, Part A)

Six benchmarks re-evaluated under the frozen calibrated deployment
package, all with real reruns or provably-sufficient closed-form
recomputation (documented per-task in `GENERALIZATION_RESULTS.md`):
STBV-Bench v2, mixed-threat, external corpus (closed-form), adaptive
attack (mechanistic reuse), CP, deployment/SUMO. New artifacts: 9 JSON/CSV
result files plus 3 new driver scripts, all under `b3_eval/v25_finetune/`
and `results/`/`deployment_eval/results/` (listed at the end of
`GENERALIZATION_RESULTS.md`). No manuscript text or figures were edited
(per this task's explicit "do not edit stbv_paper.tex" instruction); no
figures needed regeneration because Part A's tasks were table-producing
and the checkpoint swap was not adopted.

### (2) Everything unchanged (verified, not assumed)

- Kinematic-only detection path (VeReMi bench, mixed-threat kinematic
  side, CP scenes with `b3_off`) — confirmed byte-identical across all
  three arms by real rerun, not just architectural reasoning.
- CP's fused decision — confirmed byte-identical at message granularity
  (0/138 rows differ) even in the `b3_on` config arms where calibration
  is in principle reachable.
- SUMO deployment decision distribution — confirmed byte-identical
  (0/2000 rows differ).
- Adaptive-attack ASR — confirmed both mechanistically (code trace: the
  harness never reads `B3RiskPolicy` config) and empirically (identical
  43/51 evaded).
- All Category-C manuscript sections (Methodology, Related Work, Problem
  Statement, Theoretical Properties, most of Limitations/Discussion
  prose, all baseline detectors except B3's own rows) — architecturally
  independent of B3's weights, not re-verified numerically because
  there is nothing checkpoint-dependent in them to verify.
- Every cross-reference (`\ref`, `\cite`) in the manuscript resolves.

### (3) Remaining inconsistencies

- **`fig1.png` is missing from the repository** — breaks compilation,
  pre-existing, unrelated to any checkpoint work, must be fixed.
- **Table `tab:coverage`'s stated 70.3%/90.3% does not match the paper's
  own committed original-checkpoint rerun artifact (83.8%/86.9%)** — a
  pre-existing inconsistency between the manuscript text and its own
  evaluation artifact, flagged in `UPDATED_TABLES.md` §2 and reconfirmed
  here; not introduced or resolved by this task.
- **The v1 recalibration (arm c) headline recovery (F1 0.378→0.924) is
  measured on a stratified 50% test split of a stratified 25% subsample
  of v1's first 10,000 rows** (per `recalibrated_thresholds.json`
  methodology), **not the full 10,000-row ablation** the manuscript's
  Table `tab:main_ablation` reports. If the manuscript ever wants to
  claim the calibrated package "recovers v1 performance," that claim
  needs a full 5-config v1 ablation rerun at the calibrated
  thresholds — not yet done, genuinely out of this task's scope (Part
  A's 8 tasks target v2/mixed/external/adaptive/CP/deployment, not a v1
  re-ablation), and should not be inferred from the smaller test-split
  number alone.
- **App. §Semantic Transformation worked example is only updated for arm
  (b), not (c)** — the calibrated package's confidence on that exact
  quoted string was not separately computed in this task.
- **Latency comparisons in Task 6 are confounded by shared-hardware
  run-to-run noise** (the uncalibrated-finetuned deployment run, executed
  in a prior session, shows markedly higher latency than either the
  original or calibrated runs executed back-to-back in this session) —
  reported honestly as inconclusive rather than smoothed into a false
  "calibration speeds things up" narrative.

### (4) Unsupported claims

None found in the manuscript **as currently written** — it makes no
claims about the fine-tuned or calibrated checkpoint, so there is nothing
live to retract. The Step 5 audit is prospective: it documents which
comparative claims would and would not be supportable if a future
revision proposed adopting the calibrated package.

### (5) Reviewer-visible weaknesses

- A reviewer who reruns `stbv_bench_v2` or the mixed-threat case study
  against the currently-shipped fine-tuned checkpoint artifacts in this
  repo (e.g. from a "reproducibility check" GitHub Action) would find
  numbers substantially worse than the manuscript's headline figures,
  because the manuscript reports the original checkpoint and the fine-tuned
  checkpoint's artifacts are also present in the repo — a source of
  potential confusion if the two are not clearly labeled.
- The `tab:coverage` 70.3%/90.3% vs. own-artifact 83.8%/86.9% mismatch
  (Step 1 row 5) would likely surface under review regardless of any
  checkpoint decision.
- `fig1.png` missing will fail LaTeX compilation from a clean checkout.
- The external-corpus calibration-transfer finding (ECE gets *worse*
  under the new, more carefully-fit temperature) is a genuinely
  unflattering result for the recalibration effort and should be
  disclosed rather than omitted if the calibrated package is ever
  discussed in the manuscript — consistent with this repo's established
  norm of blunt reporting.

### (6) Final publication recommendation

**Do not swap the manuscript's checkpoint.** The current `stbv_paper.tex`
(arm a, original checkpoint) remains internally consistent with its own
Table `tab:coverage` caveat aside, and every rerun in this task confirms
that both the uncalibrated and calibrated fine-tuned checkpoints regress
the two most decision-relevant benchmarks (STBV-Bench v2, mixed-threat
semantic recall) relative to what is currently published, while only
partially recovering v1 performance and not at all improving adversarial
robustness. Before any submission:

1. Fix `fig1.png` (unrelated blocker, must be resolved regardless).
2. Resolve or explicitly caveat the `tab:coverage` 70.3/90.3 vs.
   83.8/86.9 discrepancy.
3. If a future revision wants to report the calibration work at all
   (e.g. as a robustness/generalization appendix rather than a checkpoint
   swap), use `GENERALIZATION_RESULTS.md` verbatim as the source of truth
   and include the external-corpus calibration-transfer regression
   honestly rather than cherry-picking the v2/mixed-threat improvements.
4. The manuscript, as currently written and un-edited by this task, is
   otherwise internally consistent: all cross-references resolve, all
   citations resolve, and no numeric claim currently in the text
   contradicts any artifact produced across this task or the two prior
   ones.
