# Handoff Summary — STBV Trust Architecture Evaluation

Written for someone who was not present for this work, to draft the
paper's Methodology/Results/Discussion sections from. Every claim below
is grounded in `git log`/`git show` output and the actual current
contents of files in this repository checkout, gathered directly while
writing this document (not restated from memory). Where a number could
not be verified against a file that currently exists in the repo, that
is stated explicitly.

Scope: this document covers the evaluation effort from commit
`602fae5f0` ("Phase 1: verify real B3 checkpoint...") through `fe5f9351e`
(HEAD at the time of writing), 27 commits. Commits before `602fae5f0` are
pre-evaluation development history and are out of scope (the architecture
was already frozen before this effort began).

---

## 1. Chronological work log

Pulled directly from `git log --reverse --stat 602fae5f0^..HEAD`.

| # | Commit | Description | Files touched |
|---|---|---|---|
| 1 | `602fae5f0` | **Phase 1.** Verified the B3 checkpoint is materialized (real weights, SHA-256 matches README) and ran real GPU inference for the first time in the repo's history. Ran all 5 `b3_eval/` harnesses + the 120-scenario `semantic_evaluation` suite against the real model (every prior stored result had `b3_available=false` or synthetic values). Found: `manual_pipeline_test.py` without `--pipeline` runs a legacy path with no B3 at all. | `PUBLICATION_PROGRESS.md`, `b3_eval/results/{calibration,latency,open_set_analysis,robustness}.json` + plots, `results/semantic/20260801-005121/` and `20260801-005223/` (raw results, plots, LaTeX tables) |
| 2 | `39ca69b16` | **Phase 2.** Found and fixed the Sybil coordinate-frame bug (see §2). Verified Replay, Collusion, Fabrication, and context-fixture detection paths against real fixtures. Also fixed a latent, pre-existing bug in `tests/test_cp_uncertainty_semantics.py` (stale duplicate `main()`). Completed the 5th model-benchmark candidate. Full regression sweep passed except one pre-existing, unrelated failure. | `PUBLICATION_PROGRESS.md`, `b3_eval/results/model_benchmark.json`, `pipeline/orchestrator.py`, `tests/test_cp_uncertainty_semantics.py` |
| 3 | `24021ddac` | Added `PHASE_1_2_VERIFICATION.md`: independently-checkable record of every command, dataset, sample count, metric, and code change from commits 1-2. Includes a manuscript-location mapping and an honest strength assessment (strengthened but not yet sufficient alone for a top-tier venue). Verified reproducibility by re-running `run_calibration.py` and confirming byte-identical output. | `PHASE_1_2_VERIFICATION.md` (new) |
| 4 | `943f7e70e` | **Phase 3 start.** Added the STBV-Bench v1 generation pipeline: `canonical.py` (VeReMi→CAM), `transformations.py` (21 rules across 20 attack families + benign_control), `generator.py`, `build_stbv_bench.py`. `run_stbv_bench_eval.py` scores the real pipeline for Decision Trust, not just B3's label. | `stbv_bench/{__init__,build_stbv_bench,canonical,generator,run_stbv_bench_eval,transformations}.py` (new) |
| 5 | `824557109` | **Bug fix.** `run_stbv_bench_eval.py` reused one `ISCEPipeline` across all samples; fixed to construct a fresh instance per sample (see §2, state-leakage bug). | `stbv_bench/run_stbv_bench_eval.py` |
| 6 | `881336cf8` | Added `DATASET_INTEGRATION.md` documenting the VeReMi→STBV-Bench pipeline step by step. Updated `PUBLICATION_PROGRESS.md` with the v1 100k-sample build parameters and the state-leakage fix's effect. | `DATASET_INTEGRATION.md` (new), `PUBLICATION_PROGRESS.md` |
| 7 | `33b572be4` | Recorded STBV-Bench v1's n=10,000 Decision Trust results (the headline number, see §3). Bootstrap 95% CI on accuracy computed. Per-family recall reported including the weak cluster. | `PUBLICATION_PROGRESS.md`, `results/stbv_bench/v1/{stbv_bench_per_message.csv,stbv_bench_results.json}` (new) |
| 8 | `2f63c43f2` | **Ablation Step 1.** Added `enable_b3` flag to `ISCEPipeline` (real skip, mirrors existing `enable_mbd`/`enable_cp`). Documented the audit of what each ablation config actually can/cannot isolate in `ABLATION_STUDY.md`. | `ABLATION_STUDY.md` (new), `pipeline/orchestrator.py` |
| 9 | `632f9fc25` | **Ablation Step 2.** Added `run_ablation.py`: 5 configs over the identical fixed 10,000-sample slice. | `stbv_bench/run_ablation.py` (new) |
| 10 | `bcd6669f6` | **Ablation Steps 3-5.** Added `analyze_ablation.py`: metrics, bootstrap CI, McNemar/Cohen's h divergence analysis, adjacent-config anomaly check. | `stbv_bench/analyze_ablation.py` (new) |
| 11 | `d1ac048bc` | **Ablation results.** Full n=10,000 ablation run (see §5). Found configs 2 and 3 (B1+B2 vs. B1+B2+CP) are byte-identical — root-caused to CP needing >1 message per window, which STBV-Bench v1 never provides. | `ABLATION_STUDY.md`, `PUBLICATION_PROGRESS.md`, `results/ablation/ablation_config_{1..5}.csv`, `results/ablation/ablation_summary.json` (new) |
| 12 | `f20387bcf` | **Verification addendum**, 5 checks: Cohen's h stated explicitly; 3-way ACCEPT/CAUTION/REJECT flip analysis (found 1,713 real transitions, not 128); STBV-Bench v1 prevalence stated (70.07%/29.93%); empirical CP check on 120 real fixture messages — **found the CP wiring bug** (see §2); flagged that a companion kinematic result was still needed. | `VERIFICATION_ADDENDUM.md` (new), `results/ablation/{ablation_3way_analysis,cp_empirical_verification}.json` (new), `stbv_bench/{analyze_3way_flips,verify_cp_empirical}.py` (new) |
| 13 | `24d62575e` | **Task 2 code.** Added `build_and_run_veremi_kinematic_bench.py`: real VeReMi kinematic attacks (ConstPos/DataReplay/DoS), stateful per-vehicle replay methodology (confirmed necessary by direct example: sender 8193 only triggers MBD's constant-position check with real history). | `stbv_bench/build_and_run_veremi_kinematic_bench.py` (new) |
| 14 | `5a92ef696` | **Task 1 code + design.** Added `STBV_BENCH_V2_DESIGN.md` (multi-message windows) and a working prototype `build_stbv_bench_v2.py`. Smoke-tested at 15 windows; confirmed `cp_confidence` still flatlined at 1.0 (independent 2nd confirmation of the CP bug). | `STBV_BENCH_V2_DESIGN.md` (new), `stbv_bench/build_stbv_bench_v2.py` (new) |
| 15 | `71205e6db` | **Task 3/4 code.** Added `build_mixed_threat_bench.py` (real kinematic + injected semantic attackers in the same scene) and `THREAT_CLASS_COVERAGE_MATRIX.md` skeleton. Not yet run. | `THREAT_CLASS_COVERAGE_MATRIX.md` (new), `stbv_bench/build_mixed_threat_bench.py` (new) |
| 16 | `d252a46fe` | **Task 2 results.** Full kinematic companion bench run: n=13,511 real messages, 360 vehicles (see §3, §4). | `results/veremi_kinematic/{analysis_summary,manifest}.json`, `veremi_kinematic_config_{1..4}.csv` (new), `stbv_bench/analyze_kinematic_bench.py` (new) |
| 17 | `c55cbc2c7` | Filled the coverage matrix with the kinematic bench's real numbers. | `THREAT_CLASS_COVERAGE_MATRIX.md` |
| 18 | `f212e375c` | **Task 1 results.** STBV-Bench v2 at scale: 150 windows, 5,062 messages. Found every v1-weak family improved (up to +75pp), zero regressed. Root-caused by direct text inspection to context-volume in the synthesized scene text. Confirmed CP inert a 3rd time. | `results/stbv_bench_v2/{analysis_summary,manifest}.json`, `stbv_bench_v2_per_message.csv`, `stbv_bench_v2_windows.jsonl` (new), `stbv_bench/analyze_v2_results.py` (new) |
| 19 | `ec5b0916c` | Documented the v1-vs-v2 recall comparison and root cause in the design doc. | `STBV_BENCH_V2_DESIGN.md` |
| 20 | `6c3991391` | **Task 3 results.** Mixed-threat bench: 120 windows, 4,123 messages. Kinematic rows detected 90.3% (MBD), semantic rows 70.3% (B3) in the same shared scene. A ~16pp gap vs. semantic-only control left as an open question at this point (later resolved, see §2/§4). | `results/mixed_threat/{manifest.json,mixed_threat_per_message.csv}` (new) |
| 21 | `27c1eec2c` | Finalized the coverage matrix with v2 + mixed-threat evidence. | `THREAT_CLASS_COVERAGE_MATRIX.md` |
| 22 | `17da80d01` | **Task 5.** Added `MANUSCRIPT_FRAMING.md`: claim-by-claim evidence map + a ready-to-adapt manuscript paragraph. Consolidated `PUBLICATION_PROGRESS.md` into a "Phase 3.5" summary. | `MANUSCRIPT_FRAMING.md` (new), `PUBLICATION_PROGRESS.md` |
| 23 | `b76d52b40` | **Round-2 verification**, 4 follow-ups: confirmed CP bug was diagnosed-only (not fixed) via `git log`; distinguished the two candidate explanations for STBV-Bench v2's improvement (found a direct causal example + 22.7%-of-sequences pattern, but inconsistent correlation direction across 2/6 families); resolved the mixed-threat 90.3%-vs-70.3% gap as a family-mix sampling confound (14 raw `mixed` windows, dominated by 2 vehicles); corrected `MANUSCRIPT_FRAMING.md` accordingly. | `FOLLOWUP_VERIFICATION_2.md` (new), `MANUSCRIPT_FRAMING.md`, `stbv_bench/pull_v2_text_examples.py` (new) |
| 24 | `6dc7df80c` | **Bug fix.** Fixed the CP wiring bug in `_run_cp` (see §2). Verified before applying that it changes zero already-published numbers (no benchmark generator sets an `event` field); verified after applying, on `scenarios/collusion`, that CP's scoring genuinely activates. Full regression suite + CI-equivalent fixture sweep passed. | `pipeline/orchestrator.py`, `results/ablation/cp_empirical_verification.json` |
| 25 | `4860bcd06` | Updated `VERIFICATION_ADDENDUM.md`, `MANUSCRIPT_FRAMING.md`, `THREAT_CLASS_COVERAGE_MATRIX.md`, `PUBLICATION_PROGRESS.md` to reflect the CP fix's precise three-part status (wiring fixed / no reported number changes / still can't score STBV-Bench's own content). | `MANUSCRIPT_FRAMING.md`, `PUBLICATION_PROGRESS.md`, `THREAT_CLASS_COVERAGE_MATRIX.md`, `VERIFICATION_ADDENDUM.md` |
| 26 | `9a2418524` | Added a consolidated "Known Limitations / Future Work" section (L1-L5) to `PUBLICATION_PROGRESS.md`, written to read directly into the paper's Limitations section. | `PUBLICATION_PROGRESS.md` |
| 27 | `fe5f9351e` | Resolved the "multiple full-architecture headline number" conflict (see §3). Investigated dataset-leakage risk in the 120-scenario `semantic_evaluation` corpus and found direct textual evidence. Recorded the previously-incomplete model-benchmark near-degeneracy finding. Added L6/L7 to the limitations list. | `PUBLICATION_PROGRESS.md` |

---

## 2. Every bug found and its current status

### Bug 1: Sybil detection coordinate-frame drift

- **Where:** `pipeline/orchestrator.py`, `_run_mbd`/`_run_cp` (pre-fix).
- **Discovered by:** Phase 2 detector verification (direct instrumentation of MBD/CP signals against `scenarios/sybil/` ground truth), commit `39ca69b16`.
- **Root cause:** `_run_mbd`/`_run_cp` recomputed a fresh `ProjectionOrigin` from the *current target message's own position* on every call. Since a message is always at local `(0,0)` in its own frame, every `VehicleHistoryStore` entry ended up stored as `(0.0, 0.0)` regardless of real position — making the Sybil `dist < 2.0m` co-location check trivially true for every vehicle pair (`sybil_score=1.0` fired for all 16/16 benign background vehicles in `scenarios/sybil/`, not just the 3 real attackers).
- **Status: FIXED AND VERIFIED.** Fix: `ISCEPipeline` now owns one persistent `_projection_origin`, set once from the first message it ever processes, reused for the instance's lifetime.
- **Re-verified how:** Re-ran the same instrumentation — `sybil_score` became discriminative (3 real attackers → 0.87/CAUTION, 16 benign → 0.0/ACCEPT, was 1.0 for all 19 before). Regression suite (`verify_dependency_graph.py`, `test_b2_trust_engine.py`, `test_adapters.py`, `test_pki_mbd_cp_integration.py`) and the CI-equivalent `manual_pipeline_test.py --pipeline` sweep both passed. **Numbers that changed as a result:** Sybil detection went from non-discriminative (100% FPR) to discriminative on `scenarios/sybil/`; this predates and is independent of every headline number reported later in this document (no ablation/STBV-Bench number cited in §3/§5 depends on `scenarios/sybil/`).

### Bug 2: Stale duplicate test in `test_cp_uncertainty_semantics.py`

- **Where:** `tests/test_cp_uncertainty_semantics.py`.
- **Discovered by:** Found incidentally while verifying the Sybil fix caused no regressions, commit `39ca69b16`.
- **Root cause:** A stale duplicate `main()` block missing `event_label=`, silently no-op'ing its own contradiction-channel test.
- **Status: FIXED AND VERIFIED.** Confirmed via `git stash` to predate the Sybil-fix session (i.e. a pre-existing bug, not introduced by this evaluation effort).
- **Re-verified how:** Included in the same regression sweep as Bug 1.

### Bug 3: STBV-Bench eval harness state-leakage across unrelated samples

- **Where:** `stbv_bench/run_stbv_bench_eval.py` (pre-fix, commit `943f7e70e`'s original version).
- **Discovered by:** Investigating an unexpectedly high false-positive rate on `benign_control` samples during the first 500-sample STBV-Bench v1 run.
- **Root cause:** The script constructed ONE `ISCEPipeline` and reused it across all benchmark samples. STBV-Bench samples are independent, unrelated single messages (different real VeReMi vehicles, different times/places), but MBD/CP are stateful (`VehicleHistoryStore`, a projection origin fixed at the first message ever processed). Reusing one instance made unrelated samples look like implausible position "teleports" of the same tracked vehicle.
- **Status: FIXED AND VERIFIED.** Fix (commit `824557109`): construct a fresh `ISCEPipeline` per sample.
- **Re-verified how:** Directly: sample `stbv-000015` (a real, non-attacker VeReMi record) decided ACCEPT on a fresh pipeline but CAUTION when evaluated after 14 unrelated prior samples on a shared instance. **Numbers that changed as a result:** `benign_control` FPR dropped from 92.7% (500-sample pre-fix check) to 2.2% (300-sample post-fix check) — this fix happened before any headline number in §3 was computed, so all headline numbers already reflect the fixed version.

### Bug 4: CP wiring bug — `_run_cp` never passes `event_label` to `cp_layer()`

- **Where:** `pipeline/orchestrator.py`, `_run_cp` method (pre-fix).
- **Discovered by:** An empirical CP check requested as a verification step — replaying 120 real multi-vehicle Phase-2 fixture messages with CP on vs. off and finding 0/120 decision flips despite `num_reports` reaching 20. Commit `f20387bcf`.
- **Root cause:** `_run_cp` never computed or passed an `event_label` argument to `cp_layer()`, unlike `_run_mbd`, which does (`event_str = target_msg.get("event") or _extract_denm_event(target_msg)`). Because `cp_layer()`'s own logic is `observations_available = (event_label is not None) and ...`, `event_label` being permanently `None` meant `observations_available` was permanently `False`, forcing CP into its neutral/vacuous branch (`cp_confidence == 1.0` unconditionally) regardless of window size or sender count.
- **Status: FIXED AND VERIFIED** (commit `6dc7df80c`, after being FOUND, NOT FIXED for two intermediate commits — `f20387bcf` through `b76d52b40` — per an explicit instruction not to alter/re-run already-published ablation numbers until the blast radius was checked).
- **Re-verified how:** Before applying the fix, confirmed by inspection that none of this evaluation's benchmark generators (`canonical.py`, `generator.py`, `build_stbv_bench_v2.py`, `build_mixed_threat_bench.py`, `build_and_run_veremi_kinematic_bench.py`) ever set an `event` key, so the fix is mathematically guaranteed to change nothing about their output. After applying, re-ran `stbv_bench/verify_cp_empirical.py` (the same 120-message check) — `scenarios/collusion` (which DOES carry a real `event` field) now shows genuine varying `cp_confidence` (0.8/0.835/0.879, current values in `results/ablation/cp_empirical_verification.json`) and a real `trust_score` delta between CP-on/CP-off (0.5289 vs. 0.5445 at one step, per commit `6dc7df80c`'s message — not separately saved to a JSON file). Full regression suite + CI-equivalent fixture sweep passed with zero new failures (one pre-existing, unrelated failure in `test_cp_uncertainty_semantics.py` confirmed via `git stash` to predate this fix).
- **Did any previously-reported number change? Explicitly: NO.** Verified, not assumed: none of STBV-Bench v1/v2, the kinematic bench, or the mixed-threat bench's generated content carries an `event` field, so every number in §3/§4/§5 that predates this fix is still accurate after it. **However**, CP still contributes zero to every one of this paper's own benchmarks for a *different*, still-open reason: the fix is necessary but not sufficient — the semantic transformation engine (`stbv_bench/transformations.py`) itself never emits event data for CP to act on. This is tracked as Limitation L1 (§7).

### Bug 5 (found, not a code bug — a mislabeled root-cause explanation)

- **What:** The original ablation study (commit `d1ac048bc`) explained CP's zero contribution as "CP only contributes when a window has >1 message; STBV-Bench v1 evaluates single-message windows only." This was directionally correct but not the actual mechanism — Bug 4 above is the actual, primary mechanism, and it is independent of window size (a window with 20 real reports still produces `cp_confidence==1.0` if `event_label` is never wired through).
- **Status: CORRECTED IN DOCUMENTATION**, not a separate code fix (the underlying issue is Bug 4). `VERIFICATION_ADDENDUM.md` §4 and `ABLATION_STUDY.md`/`PUBLICATION_PROGRESS.md` were updated to state the corrected mechanism.

### Bug 6: Incomplete `model_benchmark.json` write-up (documentation gap, not a code bug)

- **Where:** `PUBLICATION_PROGRESS.md`, Phase 1 section.
- **Discovered by:** Explicit review request in the CP-fix decision follow-up round; the underlying run had actually completed (`b3_eval/results/model_benchmark.json` exists with full results) but the document said "status to be recorded... once it completes" and was never updated.
- **Status: FIXED (documentation).** Real numbers recorded in `PUBLICATION_PROGRESS.md` §Phase 1 item 6, with the near-degenerate-classifier caveat made explicit (see §3/§7, L7). No code was involved; this is a "found an unresolved doc TODO" item, included here because the task explicitly asked not to omit anything found even if minor.

---

## 3. Every headline "full architecture" number found, and which is canonical

| # | Number | Source file | Dataset/harness | Current status |
|---|---|---|---|---|
| 1 | Accuracy 0.983, Precision/Recall/F1 = 0.990 | `results/semantic/20260801-005223/metrics_summary.json` (`configurations.full.confusion_matrix`: tp=104, fp=1, fn=1, tn=14, n=120) | `semantic_evaluation/run_semantic_evaluation.py`, 120-scenario hand-authored corpus (`semantic_evaluation/semantic_attack_dataset.py`), self-generated, NOT external | **SUPERSEDED.** A dataset-leakage risk was investigated and found: the corpus's own docstring states its payloads are "aligned to the phrasing styles of the model's actual training distribution (AF1-AF9 families, Case 1-Case 4...)", and every one of its 120 scenarios' `rationale` fields names the specific B3 training-family template it instantiates (verified by grep; 18+ such lines). That exact `AF1`-`AF9`/`Case 1`-`Case 5` taxonomy is independently confirmed as B3's own internal training/dev vocabulary in `b3/solution_stb/b3_semantic_gate/{error_analysis.py,verify_cases_1_4.py,new_qualitative_test.py}`. Literal string-level duplication against B3's raw training data could NOT be confirmed (that file is not present in this checkout). Full caveat in `PUBLICATION_PROGRESS.md` lines 39-102. |
| 2 | 0.859 | *Not found in current repo state* | *Unknown* | **UNTRACEABLE.** Searched broadly (`.md`/`.py`/`.json`) across the current checkout; found no file containing this exact figure as a headline metric (only unrelated numeric coincidences, e.g. `trust_score` values of 0.859xxx in various CSVs, and noise from `.venv`/`data/veremi` files). May originate outside this repository (e.g. a paper draft, slide deck, or abstract held by a co-author) — this was raised explicitly to the user, who was advised to check any external manuscript file directly, since this repository's own bug-hunting process cannot see outside its own checkout. |
| 3 | 98.8% | *Not found in current repo state* | *Unknown* | **UNTRACEABLE**, same caveat as #2. |
| 4 | Accuracy=0.6883, Precision=0.9829, Recall=0.5650, **F1=0.7175**, FPR=0.0231 | `results/stbv_bench/v1/stbv_bench_results.json` (`decision_trust_metrics`) | `stbv_bench/run_stbv_bench_eval.py` against STBV-Bench v1, n=10,000, real VeReMi Extension kinematics (external, public dataset) + seeded semantic transformation engine | **CANONICAL — recommended primary headline result.** |
| 5 | Full-stack ablation config 5: Accuracy=0.6883, Precision=0.9829, Recall=0.5650, F1=0.7175, FPR=0.0231 | `results/ablation/ablation_summary.json` (`table["5"]`) | Same STBV-Bench v1 n=10,000 slice, re-measured in the ablation harness as a cross-check | **Confirms #4** (numbers match to the digit) — not a competing number, a consistency check. |
| 6 | Accuracy=0.5476, Precision=0.3654, Recall=0.8839, **F1=0.5171**, FPR=0.5793 | `results/stbv_bench_v2/full_corpus_decision_trust_metrics.json` (computed this round, same methodology/convention as #4) | Same real, frozen pipeline against STBV-Bench v2, n=5,062, computed over ALL messages (not just attacker-sender rows) | **CANONICAL — recommended secondary, richer-context headline result, reported honestly alongside #4, NOT as a replacement.** See below — this is WORSE than v1 on the full-corpus metric, for an understood, real reason. |

**Recommendation: report STBV-Bench v1 (F1=0.7175) as the primary, harder-setting headline result, and STBV-Bench v2 (F1=0.5171, computed the same way) as a secondary, richer-context result — both real, both cited, neither hidden, neither replacing the other.**

**Why v1 is primary (not just "most recent"):**
1. **Externally grounded.** Its kinematics come from the public VeReMi Extension dataset, not self-authored text. The 0.990 number's corpus is self-authored and has a confirmed (if not fully quantified) leakage-risk mechanism.
2. **Larger.** n=10,000 vs. n=120.
3. **Stable under adversarial bug-hunting.** The 0.718 figure was independently re-derived twice — once as the direct STBV-Bench v1 evaluation (commit `33b572be4`) and again as ablation config 5 (commit `d1ac048bc`) — and both times produced numbers matching to the fourth decimal place, across a harness rewrite (the ablation harness is a different script than `run_stbv_bench_eval.py`). It also survived the CP wiring-bug fix unchanged (verified, not assumed — see Bug 4 above).
4. **The 0.990 number moved for the wrong reasons when checked.** Its corpus was explicitly authored "aligned to... the model's actual training distribution" per its own docstring — precisely the mechanism that produces suspiciously high, non-generalizing scores.

**Why v2's full-corpus number is lower than v1's, and why that is reported honestly rather than avoided:** computing v2's Decision Trust metrics the identical way v1's are computed (positive=REJECT/CAUTION, ground truth=`is_attacker_sender`, over every message) gives **F1=0.5171, worse than v1's 0.7175** — the opposite of what the already-documented per-family attacker-sender recall improvement (§1, commit `f212e375c`; up to +75pp on specific weak families) might suggest. The two findings are not in tension; they measure different things. Root cause of the lower full-corpus number: 3,675 of v2's 5,062 messages are real, unmodified bystander vehicles incidentally present in each multi-vehicle window — v1 has no equivalent (every v1 sample is a designated `benign_control` or a designated attacker, never an incidental bystander). MBD flags 57.9% of these bystanders as CAUTION (`fp=2129` of 3,675 bystander rows), closely matching the kinematic companion bench's own ~52% baseline per-message FPR (`results/veremi_kinematic/analysis_summary.json`) — the same real MBD behavior, now visible in v2's aggregate metric specifically because v2 is the first STBV-Bench harness to include genuine ambient real traffic. **Both numbers are real and both should be cited**: v2 demonstrates a genuine recall improvement on the specific attacker under richer context, but a genuine, understood increase in aggregate false-positive rate once real ambient traffic (with MBD's baseline sensitivity) is part of the evaluated scene. No methodology, threshold, or scoring logic was changed to produce either number — this is the same convention applied consistently to both benchmarks' full output.

---

## 4. Every dataset/benchmark that currently exists

### STBV-Bench v1
- **Size:** Evaluated at n=10,000 (`results/stbv_bench/v1/`). Built at n=100,000 per the commit message of `33b572be4` and `PUBLICATION_PROGRESS.md` — **this larger build-size claim is NOT independently verifiable from a file in the current checkout**: the actual 100k-sample file (`data/stbv_bench/v1/stbv_bench.jsonl`) is gitignored (`data/` is excluded per `.gitignore`) and not present; only the n=10,000 evaluation slice and its results are committed.
- **Real vs. synthetic:** Kinematics are real (VeReMi Extension, external public dataset — van der Heijden et al. 2018, Kamel et al. 2020). Semantic scene-context text is synthetic (VeReMi has none; injected by `stbv_bench/transformations.py`'s 21 seeded rules).
- **Built to test:** Whether the real, frozen architecture detects purely semantic (STBV) attacks with clean, unaltered kinematics.
- **Known limitations:** `DATASET_INTEGRATION.md` (full pipeline docs); each sample is an independent single message (no multi-vehicle window, no cross-message history) — this is what STBV-Bench v2 was built to address. 6/20 attack families show ≤9% recall (`ABLATION_STUDY.md`, `PUBLICATION_PROGRESS.md` L3).
- **Recommended for the paper?** **Yes — this is the canonical headline benchmark** (§3).

### STBV-Bench v2
- **Size:** 150 windows, 5,062 messages (`results/stbv_bench_v2/`).
- **Real vs. synthetic:** Same real-VeReMi-kinematics-plus-synthetic-text principle as v1, but built from genuine multi-vehicle spatial-temporal clusters (1s time-bucket + 100m-radius clustering; 261 eligible windows found from a single source dataset, `ConstPos_1416`, per `results/stbv_bench_v2/manifest.json`).
- **Built to test:** Whether multi-vehicle context (temporal continuity, real cooperative traffic) changes detection, specifically because CP and MBD's history-dependent checks cannot be exercised on v1's independent single messages.
- **Known limitations:** `STBV_BENCH_V2_DESIGN.md` — narrative-evolution/progressive-poisoning injection strategies are specified but not implemented (L5); CP still cannot be scored on this benchmark's content (no `event` field — L1); the improvement mechanism vs. v1 is only partially understood (context-volume sensitivity confirmed real, but not cleanly separated from a "more realistic traffic" explanation — `FOLLOWUP_VERIFICATION_2.md` §2, L3); not yet ablated (L11, §8); and — computed this round, not previously reported — v2's **full-corpus** Decision Trust F1 (0.5171, `results/stbv_bench_v2/full_corpus_decision_trust_metrics.json`) is WORSE than v1's (0.7175), driven by a 57.9% FPR on the 3,675 real bystander-vehicle messages the multi-vehicle window design introduces (see §3, entry #6, for the full explanation — this is a real, understood MBD-baseline-sensitivity effect, not a benchmark defect).
- **Recommended for the paper?** **Yes, as a secondary/sub-study result reported honestly alongside v1, not as a replacement headline.** The v1→v2 per-family attacker-sender recall comparison (§1, commit `f212e375c`) is a genuinely strong, reproducible finding; the v1→v2 full-corpus comparison (§3, entry #6) is a different, equally real finding showing v2's aggregate FPR is substantially worse. Both should be reported — v2 is not simply "an improved v1," it is a different evaluation regime with its own tradeoffs. It also remains a prototype in scope (one source dataset, 2 of 4 designed injection strategies implemented, no ablation) and should be presented as such.

### VeReMi kinematic companion bench
- **Size:** n=13,511 real messages, 360 vehicles (180 attacker/180 benign) (`results/veremi_kinematic/`).
- **Real vs. synthetic:** Fully real — VeReMi Extension kinematics AND VeReMi's own `is_attacker` ground truth (constant-position falsification/ConstPos, data replay/DataReplay, DoS/flooding), no semantic transformation applied at all, no injected text.
- **Built to test:** Whether MBD/B1 detect the kinematic/behavioral threat class STBV-Bench cannot test (STBV-Bench is semantic-only by design), providing the companion evidence needed before claiming "complementary threat-class coverage."
- **Known limitations:** Per-message FPR is high (52.4% overall, `results/veremi_kinematic/analysis_summary.json`); per-vehicle "ever flagged" policy is unusable (99.4% FPR); replay attacks are the weakest-detected type (60.0% recall vs. 91.2%/80.3% for ConstPos/DoS).
- **Recommended for the paper?** **Yes — required companion evidence**, cited alongside STBV-Bench v1 to support the complementary-coverage claim, not as a competing headline.

### Mixed-threat bench
- **Size:** 120 windows, 4,123 messages, of which 431 messages are in "mixed"-composition windows (`results/mixed_threat/manifest.json`: composition_counts = {"semantic_only": 53, "clean": 38, "mixed": 14, "kinematic_only": 15}).
- **Real vs. synthetic:** Real kinematic attackers (VeReMi's own `is_attacker`) co-present with independently-injected semantic attackers, on different vehicles, in the same real multi-vehicle spatial-temporal window.
- **Built to test:** Whether both detection layers (MBD, B3) continue to function correctly when both threat types are present in the same shared scene.
- **Known limitations:** Only 14 raw `mixed`-composition windows exist in this run — small n, not family-stratified, and the resulting family distribution (89% of mixed-composition semantic-attacker rows drawn from just 3 families, with the lower-recall `semantic_narrative_poisoning` family alone supplying 35.5% of the sample from only 2 real vehicles) is a confirmed confound (`FOLLOWUP_VERIFICATION_2.md` §3, L4) that explains the ~16pp semantic-recall gap vs. the semantic-only control — this is resolved as a sampling artifact, not an open question, as of commit `b76d52b40`.
- **Recommended for the paper?** **Yes, but with the small-n caveat stated explicitly** — a larger, family-stratified re-run is recommended before citing an exact mixed-scene recall percentage as precise.

### 120-scenario `semantic_evaluation` corpus
- **Size:** 120 hand-authored scenarios (`semantic_evaluation/semantic_attack_dataset.py`).
- **Real vs. synthetic:** Fully synthetic/hand-authored text; kinematics are also synthetic (not derived from any real trajectory dataset), per the module's own design (`SemanticAttackScenario` dataclass with hardcoded `payload_text`).
- **Built to test:** Originally, whether B3 detects hand-crafted prompt-injection/semantic attacks; also used for robustness (`b3_eval/run_robustness.py`), calibration, and open-set analysis sub-studies.
- **Known limitations:** Confirmed dataset-leakage risk (§3) — the corpus's own docstring and per-scenario rationale fields explicitly name B3's internal training-family taxonomy.
- **Recommended for the paper?** **Superseded as a headline result; still usable as the underlying corpus for the robustness (L6), calibration, and open-set sub-studies**, which measure B3's own behavior under perturbation/uncertainty rather than making a comparative detection claim, and are unaffected by the leakage concern in the same way a detection-accuracy headline would be.

---

## 5. Ablation and layer-contribution results

Source: `results/ablation/ablation_summary.json` (`table`), current committed content, verified by direct read while writing this document.

### Main-text table (recommended, 3 rows)

Configs "B1+B2" and "B1+B2+CP" in the full 5-config breakdown are
byte-identical (0/10,000 decisions differ — confirmed root cause: the CP
wiring gap, Bug 4/L1, not a benchmark artifact), so merging them into one
row loses no information for the main text. "B1+B2+B3" below is the
**full fused stack** (config 5, the actual deployed decision path — the
no-fusion diagnostic, config 4, is a supplementary/analysis config, not
a deployment configuration, and belongs in the appendix table only).

| Config | n | Accuracy | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|---|
| B1 only | 10,000 | 0.2993 | undefined (0 predicted positive) | 0.0000 | undefined | 0.0000 |
| B1+B2 (= B1+B2+CP; CP contributes 0, see L1) | 10,000 | 0.3048 | 0.6425 | 0.0177 | 0.0344 | 0.0231 |
| B1+B2+B3 (full fused stack) | 10,000 | 0.6883 | 0.9829 | 0.5650 | 0.7175 | 0.0231 |

The CP-inert finding is not removed by this simplification — it still
appears in full in the Limitations section (L1, §7) and
`THREAT_CLASS_COVERAGE_MATRIX.md`; this table just avoids giving a
zero-difference row its own line in the main text.

### Supplementary / appendix table (full 5-config breakdown)

| Config | n | tp | fp | fn | tn | Accuracy | Precision | Recall | F1 | F1 95% CI | FPR | MCC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. B1 only | 10,000 | 0 | 0 | 7,007 | 2,993 | 0.2993 | undefined (0 predicted positive) | 0.0000 | undefined | [0, 0] | 0.0000 | undefined |
| 2. B1+B2 | 10,000 | 124 | 69 | 6,883 | 2,924 | 0.3048 | 0.6425 | 0.0177 | 0.0344 | [0.0290, 0.0410] | 0.0231 | -0.0178 |
| 3. B1+B2+CP | 10,000 | 124 | 69 | 6,883 | 2,924 | 0.3048 | 0.6425 | 0.0177 | 0.0344 | [0.0290, 0.0410] | 0.0231 | -0.0178 |
| 4. B1+B2+CP+B3 (no fusion) | 10,000 | 3,900 | 0 | 3,107 | 2,993 | 0.6893 | 1.0000 | 0.5566 | 0.7151 | [0.7054, 0.7245] | 0.0000 | 0.5226 |
| 5. Full stack | 10,000 | 3,959 | 69 | 3,048 | 2,924 | 0.6883 | 0.9829 | 0.5650 | 0.7175 | [0.7080, 0.7270] | 0.0231 | 0.5060 |

**Configs 2 and 3 are byte-identical** — confirmed at the row level (not just aggregate metrics) in `results/ablation/ablation_3way_analysis.json`/the divergence analysis: 0/10,000 samples differ. Current understanding (post CP-fix, Bug 4 in §2): CP's wiring bug meant it could never contribute regardless of window size; the fix was verified to change zero STBV-Bench numbers because STBV-Bench's own generated content carries no `event` field (a second, independent, still-open reason CP contributes nothing here — see L1).

**Per-layer contribution, current understanding:**
- **B1 alone:** makes zero positive predictions on this benchmark (0/10,000) — accuracy 0.2993 exactly equals the benign fraction of the corpus (2,993/10,000).
- **B2/MBD's real contribution (config 1→2):** small but real and statistically significant — 124 true positives, McNemar comparison shows 193/10,000 flipped, p=1.9e-43, Cohen's h=-0.279 (small-to-moderate). Attributed to MBD occasionally flagging on non-semantic (kinematic/certificate) grounds even though STBV-Bench's ground truth is purely about semantic content.
- **CP (config 2→3):** zero measurable contribution to this benchmark, confirmed root cause = Bug 4 (§2) + the transformation engine never emitting event data (L1). Not evidence CP's algorithm is broken — it is separately verified working on `scenarios/collusion` (§2, Bug 4 verification) and on `scenarios/collusion`-style Phase 2 fixtures generally (§2, Phase 2 detector verification).
- **B3 alone, no fusion (config 3→4):** the dominant detector — F1 jumps from 0.0344 to 0.7151, precision reaches a perfect 1.0000. Confirms B3 does essentially all of the real detection work on this benchmark.
- **DS Fusion's marginal contribution (config 4→5):** binary metric: 128/10,000 flips, McNemar p=3.06e-29, Cohen's h=-0.0262 (negligible effect size despite the significant p-value — n=10,000 gives high power to detect a tiny, real, consistent shift).

### 3-way ACCEPT/CAUTION/REJECT flip analysis (stated precisely)

Source: `results/ablation/ablation_3way_analysis.json`, current committed content.

- Full-stack (config 5) decision distribution over all 10,000 samples: **ACCEPT: 5,972, CAUTION: 1,944, REJECT: 2,084.**
- Config 4→5 transitions: **CAUTION→REJECT: 1,585; ACCEPT→CAUTION: 128. Total: 1,713 real decision-string changes** (not the 128 the binary F1 comparison alone would suggest — binary F1 cannot see CAUTION↔REJECT transitions since both count as "positive").
- **Hard flips (ACCEPT↔REJECT, skipping CAUTION entirely): 0.** Every one of the 1,713 real transitions moves through, or into/out of, CAUTION.
- Interpretation: fusion's real behavior is to escalate already-suspicious (CAUTION) calls to REJECT on genuine attacks (1,585 of the 1,713 transitions, 92.5%), and to add caution to a previously-clean ACCEPT in a smaller number of cases (128, 7.5% — 69/128 of which are false positives on `benign_control`, the remainder real attacks B3 alone missed). This is direct empirical support for the architecture's design intent that fusion routes uncertainty through CAUTION rather than forcing premature binary calls.

---

## 6. Every statistical test run and its result

| Test | What was compared | Result | Source file | Evidence for |
|---|---|---|---|---|
| Bootstrap 95% CI (2,000 resamples) | STBV-Bench v1 accuracy, n=10,000 | [0.679, 0.697] | `PUBLICATION_PROGRESS.md` (computed inline; not saved to a separate JSON) | 10,000 samples is a sufficiently stable sample size for the headline result |
| Bootstrap 95% CI (2,000 resamples) | Ablation F1 per config | Config 4: [0.7054, 0.7245]; Config 5: [0.7080, 0.7270] (others in §5 table) | `results/ablation/ablation_summary.json` | Precision of each config's F1 estimate |
| McNemar's test (continuity-corrected) | Config 5 vs. Config 3 (does B3+fusion change anything over no semantic layer) | n01=0, n10=3,835, χ²=3,833.0, p=0.0 | `results/ablation/ablation_summary.json` (`divergence.config5_vs_config3`) | B3's existence has a large, highly significant effect |
| Cohen's h | Config 5 vs. Config 3 | -1.0964 (large) | same file | Effect size for B3's existence |
| McNemar's test | Config 5 vs. Config 4 (fusion's marginal effect over raw B3) | n01=0, n10=128, χ²=126.0, p=3.06e-29 | same file (`divergence.config5_vs_config4`) | Fusion has a real, statistically significant, but small effect |
| Cohen's h | Config 5 vs. Config 4 | -0.0262 (negligible) | same file | Fusion's effect size is negligible on the binary scale, despite significance |
| McNemar's test | Config 1 vs. Config 2 (B1 only vs. B1+B2/MBD) | n10=193, p=1.918e-43, Cohen's h=-0.2787 | `results/ablation/ablation_summary.json` (`adjacent_config_deltas["1->2"]`) | MBD's marginal contribution is small-to-moderate and real |
| Bootstrap 95% CI on config F1 | Adjacent-config anomaly check | Config 2↔3: ΔF1=0.0000, 0% flipped → flagged LIKELY INERT; Config 4↔5: ΔF1=+0.0024, 1.28% flipped → flagged REAL WEAK CONTRIBUTION | `results/ablation/ablation_summary.json` (`anomalies_flagged`) | Distinguishes an inert code path (CP) from a real-but-small effect (fusion) |
| Expected Calibration Error (ECE) | Raw B3 confidence vs. temperature-scaled | Before: 0.0619; After (T=2.145): 0.0280 (~55% relative reduction) | `b3_eval/results/calibration.json` | Temperature scaling meaningfully improves calibration |
| Brier score | Same | Before: 0.0613; After: 0.0553 | `b3_eval/results/calibration.json` | Same |
| Open-set/OOD analysis | 85 in-distribution + 25 out-of-distribution (unseen attack family) samples | Miss rate on unseen families: 0.000; silent-failure rate: 0.000; dead-zone occupancy: 0.000 | `b3_eval/results/open_set_analysis.json` | B3 fails loudly (low confidence) on unseen families rather than silently; supports "no abstain mechanism needed" |
| AUROC (OOD separation) | MSP vs. energy vs. raw p_malicious as OOD scores | MSP=0.154, energy=0.098, p_malicious=0.994 | `b3_eval/results/open_set_analysis.json` | Raw probability is a far better OOD separator than the standard MSP/energy scores here |
| Selective classification (AURC) | Risk-coverage tradeoff | AURC=0.0082; coverage@risk≤0.01=0.800; coverage@risk≤0.05=0.953 | `b3_eval/results/open_set_analysis.json` | Quantifies the risk/coverage tradeoff for a confidence-based selective policy |

No formal statistical test was run for the STBV-Bench v2 vs. v1 recall comparison (§1, commit `f212e375c`) beyond the direct causal example and the 22.7%-of-sequences observation described in `FOLLOWUP_VERIFICATION_2.md` §2 — this is flagged as a gap, not filled in retroactively here.

---

## 7. Complete limitations list

Pulled **verbatim** from `PUBLICATION_PROGRESS.md`'s "Known Limitations / Future Work" section (lines 299-384 at the time of writing), condensed only by removing the surrounding markdown bolding syntax for readability here — the source file has the full formatting.

> **L1.** CP's semantic transformation engine never emits an `event` field, so Cooperative Perception measurably contributes zero to every benchmark reported in this evaluation, despite its detection logic working correctly. CP's own consistency-scoring code was verified broken (a wiring bug: `pipeline/orchestrator.py::_run_cp` never passed `event_label` to `cp_layer()`) and then fixed and verified working on real event-bearing traffic (`scenarios/collusion` — genuine, varying `cp_confidence` 0.8/0.835/0.879 and a real `trust_score` delta between CP-on/CP-off, commit `6dc7df80c`). But `stbv_bench/canonical.py`, `generator.py`, `build_stbv_bench_v2.py`, and `build_mixed_threat_bench.py` — every message-generation path used in this paper's benchmarks — never attach an `event` key or a `denm.management.event_type.cause_code` structure to their output. So `event_label` is `None` for every message in STBV-Bench v1/v2, the kinematic bench, and the mixed-threat bench, `observations_available` stays `False`, and CP correctly scores zero contribution to every one of this paper's reported numbers — not because CP doesn't work, but because none of the paper's own generated traffic gives it anything to work with. Fix required for future work: add event-label generation to the semantic transformation engine. Unscoped and not started.
>
> **L2.** Collusion detection's real-world coverage is limited to traffic carrying an explicit event/DENM cause-code — a data-availability limitation shared with L1, not an algorithmic defect; deriving a coarse event label from cross-message reasoning for plain CAM traffic would address both L1 and L2 at once.
>
> **L3.** STBV-Bench's B3 detection has a genuine, reproducible weak cluster (6/20 attack families at ≤9% recall in v1: `goal_manipulation`, `traffic_efficiency_lure`, `indirect_prompt_injection`, `multi_message_context_poisoning`, `mixed_semantic_attacks`, `semantic_narrative_poisoning`) — a B3 model-capability limitation, not a fusion defect. STBV-Bench v2 substantially closes this gap in a multi-vehicle-context setting, but the explanation is only partially understood (context-volume sensitivity confirmed as a real, non-negligible factor; real-world representativeness not ruled out).
>
> **L4.** The mixed-threat benchmark's `mixed`-composition sample is small (14 raw windows out of 120) and its family distribution is not stratified, which caused an observed recall gap traced to a sampling confound rather than a real effect. A publication-quality mixed-threat number needs a larger, family-stratified run.
>
> **L5.** Narrative-evolution and progressive multi-message poisoning injection strategies (STBV-Bench v2 design strategies 3-4) are specified but not implemented in the STBV-Bench v2 prototype.
>
> **L6.** B3 shows a 100% over-defense rate on `instruction_hiding` and `role_confusion` robustness perturbations, with a 50% label-flip rate on both. This means benign messages containing trigger-adjacent phrasing are misclassified as malicious every single time this perturbation family was tested — a real, previously-unmeasured robustness gap matching exactly the failure mode the 2024-2026 literature review (`LITERATURE_AND_DATASETS.md`) predicted for generic injection classifiers. This must remain a prominent, explicitly-named item in the manuscript's Limitations section.
>
> **L7.** The B3 model-architecture comparison (`b3_eval/results/model_benchmark.json`) must not be reported as a raw F1 ranking. 4 of 5 candidate architectures scored a higher F1 than the deployed incumbent (0.933 vs. 0.895) purely by predicting MALICIOUS unconditionally on a class-imbalanced 24-sample test split (tn=0 for all four). Only the incumbent has tn>0 and precision=1.000.

**Additional limitations surfacing in this handoff document, not already itemized above:**

- **L8 (new).** Two previously-referenced "full architecture" figures (0.859, 98.8%) could not be traced to any file in the current repository checkout (§3). If they exist in an external manuscript/abstract/slide deck, they require the same correction (replace with STBV-Bench's 0.7175, or remove) but that check is outside what this repository's own audit process can perform.
- **L9 (new).** The STBV-Bench v1 100,000-sample *build* claim (as opposed to the n=10,000 *evaluation* slice, which is fully verifiable) rests on the build script's manifest, which is written to `data/stbv_bench/v1/manifest.json` — a path excluded by `.gitignore` and not present in this checkout. The build is described as reproducible via `build_stbv_bench.py --seed 7` against the same VeReMi source pool, but that reproduction was not re-run to produce this document; the 100k/seed=7/221,125-pool figures are sourced from commit messages and `PUBLICATION_PROGRESS.md` prose only.
- **L10 (new).** No formal statistical significance test (McNemar, bootstrap CI, or otherwise) was computed for the STBV-Bench v2 vs. v1 per-family recall comparison — the finding rests on a direct causal example plus an aggregate 22.7% figure, not a paired hypothesis test (see §6).

---

## 8. Unresolved / open items

| Item | What's needed to resolve it |
|---|---|
| CP cannot score any of this paper's own generated benchmarks (L1) | Add event-label generation to `stbv_bench/transformations.py` (or a wrapper), then re-run STBV-Bench v2's multi-source families (`collaborative_semantic_agreement`, `cross_source_contradiction`) and the mixed-threat bench to see whether CP begins contributing. Unscoped, not started. |
| Collusion detection's data-availability gap (L2) | Same fix as L1 addresses this too — deriving event labels from cross-message reasoning on plain CAM traffic. |
| B3's weak-family cluster (L3) | Requires either improving B3's training data/fine-tuning on the 6 weak families, or accepting and reporting the limitation as-is. The v1→v2 improvement (context-volume effect) is not itself a fix for B3's underlying capability — it's a benchmark-design finding about when B3's existing capability is exercised more effectively. |
| Mixed-threat bench's small-n confound (L4) | Re-run `build_mixed_threat_bench.py` with a larger `--n-windows` and/or add explicit family-stratification logic to guarantee a representative `mixed`-composition sample. |
| Unimplemented v2 injection strategies (L5) | Implement narrative-evolution and progressive multi-message poisoning in `build_stbv_bench_v2.py`, per the design already written in `STBV_BENCH_V2_DESIGN.md`. |
| instruction_hiding/role_confusion 100% over-defense (L6) | Requires B3 model improvement or a policy-level fix (e.g. a dedicated over-defense mitigation); not attempted this session — reported as a finding, not fixed. |
| Model-benchmark near-degeneracy on a 24-sample split (L7) | A larger, better-balanced test split for the architecture comparison would give a less noise-dominated ranking; not re-run this session. |
| Two untraceable headline figures, 0.859 and 98.8% (L8) | Requires a human check of any manuscript/abstract/slide deck held outside this repository — cannot be resolved from inside the checkout. |
| STBV-Bench v1's 100k-sample build is not independently re-verifiable from a committed file (L9) | Re-run `build_stbv_bench.py --seed 7` and inspect the resulting (gitignored) `manifest.json` directly, or commit a copy of that manifest (not the full 179MB dataset) for future auditability. |
| No formal significance test for the v2 recall improvement (L10) | Compute a paired test (e.g. McNemar per family, or an aggregate test across the whole v1-vs-v2 comparison) on matched samples, if v1/v2 sample identity can be aligned; not attempted this session. |
| STBV-Bench v2 has not been ablated (L11, new) | Only the full-stack configuration (`enable_mbd=True, enable_cp=True, enable_b3=True`) was ever run against v2's windows (`stbv_bench/build_stbv_bench_v2.py:241`) — verified by inspection, not assumed. `results/ablation/` contains only STBV-Bench v1's 5-config ablation; there is no `results/ablation_v2/` or equivalent. A 5-config ablation on v2 would require adapting `run_ablation.py` for windowed/multi-message data (it currently assumes one independent message per sample, matching v1's design, not v2's), not yet done. |
| `tests/test_large_scale_framework.py` fails (`AttributeError: 'ScaledScenario' object has no attribute 'vehicle_count'`) | Confirmed via `git stash` (commit `39ca69b16`'s message) to be a pre-existing, unrelated `large_scale/scaling.py` API-drift bug, predating this evaluation effort entirely. Not fixed; does not block anything reported in this document (STBV-Bench's own scale-up does not depend on `large_scale/`). |
| `test_cp_uncertainty_semantics.py`'s "Contradictory reports commit significant disbelief mass" assertion fails | Confirmed via `git stash` (commit `6dc7df80c`'s message) to be a pre-existing failure unrelated to the CP wiring fix (that test stubs `_run_cp` entirely, bypassing the fixed code path). Not fixed this session. |

---

## 9. File index

| If you need... | Look at |
|---|---|
| The canonical headline "full architecture" numbers (F1=0.7175) | `results/stbv_bench/v1/stbv_bench_results.json` |
| Per-family recall for STBV-Bench v1 | `results/stbv_bench/v1/stbv_bench_results.json` (`per_family`), or the summary table in `PUBLICATION_PROGRESS.md` §Phase 3 |
| STBV-Bench v2's full-corpus Decision Trust metrics (F1=0.5171, the secondary headline) | `results/stbv_bench_v2/full_corpus_decision_trust_metrics.json` |
| STBV-Bench v2's per-family attacker-sender recall (the separate +75pp-style improvement finding) | `results/stbv_bench_v2/analysis_summary.json` (`per_family_recall`) |
| The superseded 0.990 number and its full leakage caveat | `results/semantic/20260801-005223/metrics_summary.json` (raw number); `PUBLICATION_PROGRESS.md` lines 30-102 (caveat) |
| Every ablation config's metrics, McNemar/Cohen's h, and the anomaly check | `results/ablation/ablation_summary.json` |
| The 3-way ACCEPT/CAUTION/REJECT flip analysis | `results/ablation/ablation_3way_analysis.json` |
| Raw per-sample ablation decisions (for independent re-verification) | `results/ablation/ablation_config_{1..5}.csv` |
| The CP wiring bug's root cause and fix verification | `VERIFICATION_ADDENDUM.md` §4; the code fix itself is `pipeline/orchestrator.py`'s `_run_cp` method; the post-fix empirical check is `results/ablation/cp_empirical_verification.json` |
| The Sybil coordinate-frame bug | `PUBLICATION_PROGRESS.md` §Phase 2 ("Sybil" row); fix in `pipeline/orchestrator.py` (`_projection_origin`, `_get_or_create_projection_origin`) |
| The STBV-Bench eval state-leakage bug | Commit `824557109`; fix in `stbv_bench/run_stbv_bench_eval.py` |
| STBV-Bench v1's build pipeline and honesty contract | `DATASET_INTEGRATION.md` |
| STBV-Bench v2's design and prototype results | `STBV_BENCH_V2_DESIGN.md`; results in `results/stbv_bench_v2/` |
| The VeReMi kinematic companion bench's methodology and results | `stbv_bench/build_and_run_veremi_kinematic_bench.py`'s module docstring; `results/veremi_kinematic/analysis_summary.json` |
| The mixed-threat bench's methodology and results | `stbv_bench/build_mixed_threat_bench.py`'s module docstring; `results/mixed_threat/manifest.json`, `mixed_threat_per_message.csv` |
| Every attack family mapped to its detecting layer | `THREAT_CLASS_COVERAGE_MATRIX.md` |
| Ready-to-adapt manuscript prose + the claim-by-claim evidence map | `MANUSCRIPT_FRAMING.md` |
| The full round-2 verification investigation (v2 explanation, mixed-threat gap resolution) | `FOLLOWUP_VERIFICATION_2.md` |
| Robustness (instruction_hiding/role_confusion over-defense) | `b3_eval/results/robustness.json`; summarized in `PUBLICATION_PROGRESS.md` §Phase 1 item 2 |
| Calibration (ECE/Brier/temperature scaling) | `b3_eval/results/calibration.json` |
| Open-set/OOD analysis | `b3_eval/results/open_set_analysis.json` |
| Latency measurements | `b3_eval/results/latency.json` |
| The model-architecture comparison and its near-degeneracy caveat | `b3_eval/results/model_benchmark.json`; caveat in `PUBLICATION_PROGRESS.md` §Phase 1 item 6 / L7 |
| The full consolidated limitations list | `PUBLICATION_PROGRESS.md`, "Known Limitations / Future Work" section |
| The complete chronological narrative of Phase 1/2 work with exact commands | `PHASE_1_2_VERIFICATION.md` |
| The Step-1 audit of what each ablation config can/cannot actually isolate | `ABLATION_STUDY.md` §Step 1 |

---

## Honest summary

**Solid enough to write into a paper today:** STBV-Bench v1's F1=0.7175 (n=10,000, real VeReMi kinematics, externally grounded) as the primary headline full-architecture result, reported alongside its precision/recall/FPR breakdown and its 6/20-family weak cluster (L3) stated honestly. STBV-Bench v2's two real, complementary findings — the per-family attacker-sender recall improvement (up to +75pp on previously-weak families) AND the full-corpus F1=0.5171 (worse than v1, driven by a real, understood 57.9% bystander FPR) — are both solid enough to report side by side as a secondary result, provided both are stated together rather than either alone. The collapsed 3-row main-text ablation table (B1 / B1+B2 / B1+B2+B3) plus the full 5-row appendix table are both ready to use. The ablation study's layer-contribution findings (B3 dominates STBV detection; MBD/CP are near-inert on STBV-Bench specifically, for now-understood, distinct reasons; fusion's small-but-real CAUTION-routing behavior, backed by McNemar/Cohen's h/a 3-way transition analysis) are reproducible, internally consistent (the same number was independently re-derived twice, in two different harnesses, to four decimal places), and survived a real bug (the CP wiring fix) without moving. The VeReMi kinematic companion bench provides genuine, real-attack evidence that MBD works on the threat class it was designed for — and its ~52% baseline per-message FPR finding is exactly what explains v2's full-corpus number, a nice internal-consistency check across two independently-built benchmarks. The calibration, robustness, and open-set sub-studies are real, reproducible measurements of B3's own behavior and can be cited on their own terms regardless of the 0.990 headline-number issue.

**Still needs work before being cited as a settled result:** the STBV-Bench v2 multi-vehicle-context improvement's causal explanation (real and reproducible in its raw numbers, but only partially resolved, and no formal significance test has been run — L10); v2's ablation, which has never been run (only the full-stack configuration exists for v2 — L11); the mixed-threat benchmark's exact recall percentages (real signal, but drawn from a small, non-stratified 14-window sample — L4); CP as a functioning, evaluated component of this paper's own results (the wiring bug is fixed and verified on hand-authored fixtures, but CP still cannot be scored on any of this paper's own generated content until event-label generation is added — L1); and the two untraceable prior figures (0.859, 98.8%), which need a human check outside this repository before anyone can be certain they don't still appear in a live manuscript draft somewhere.
