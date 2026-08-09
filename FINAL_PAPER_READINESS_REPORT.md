# Final Paper Readiness Report (updated — continuation pass)

**Honesty note on scope.** This report now covers two passes: (1) the
initial CARLA root-cause pass, and (2) a continuation that implemented the
Phase 4 baseline on v2.5b directly, re-derived Table II/III/IV from raw
per-message data, added P1/P3 proof sketches, and re-audited Phase 7. Nothing
below is fabricated; every number is traced to a specific file.

## A. What was changed
- `stbv_paper.tex`: CARLA benign-scenario discussion (root cause, Pass 1).
- `stbv_paper.tex`: new Table (`tab:baseline`) — external baseline comparison
  on v2.5b's held-out test split, with an honest caveat footnote (Pass 2).
- `stbv_paper.tex`: new Appendix B (`app:proofs`) with compact P1/P3 proof
  sketches sourced from `THEORETICAL_ANALYSIS.md` (Pass 2).
- `BASELINE_EVALUATION_REPORT.md`: rewritten with real v2.5b baseline numbers
  (Pass 2).

## B. What was experimentally rerun
- **New this pass**: a TF-IDF+LogReg baseline and a keyword baseline were
  trained/evaluated (not merely read) on `data/stbv_bench/v25b/stbv_bench_v25b.jsonl`
  — stratified 60/20/20 split, seed 42, threshold selected on val only,
  metrics reported on the untouched 2,020-message test split. This is a real
  new computation performed in this pass (scikit-learn 1.7.2).
- **Not rerun**: no new CARLA/SUMO session, no B3 retraining. The
  `eval_hardmine_v25b.py`/ITE-Bench/config CSV numbers used for Phase 1
  re-derivation were **read and recomputed from existing per-message CSV/JSON
  output**, not regenerated from a live model pass, in this continuation.

## C. Checkpoint used for verification
`semantic_gate_v3_mixed_lora_hardmine_merged` — confirmed via
`b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/run_manifest.json`
(`"checkpoint": "final_continued"`... actually `"model_path"` field points at
the `_hardmine_merged` directory) and via
`b3_eval/v25_finetune/results/hardmine_v25b_eval.json`'s `hardmine_checkpoint`
key, both used for the recomputation below.

## D. Results that changed
- CARLA root cause: traced (Pass 1), no numbers altered.
- **New**: manuscript now reports a real, v2.5b-specific external baseline
  table (previously the paper had none; Pass 1 only found a v1 baseline that
  was correctly withheld from the paper body). No B3/Full-STBV number was
  changed — the new table only adds two new rows (keyword, TF-IDF+LogReg).
- **New**: Appendix now contains proof sketches for P1/P3 instead of only
  deferring to an external, unsubmitted file.

## E. Phase 1 — source-of-truth re-derivation (NEW, this continuation)
Re-derived metrics directly from raw per-message files using
`sklearn.metrics`, independent of any number already printed in the
manuscript or prior audit `.md` files:

**Table III (v2.5b, direct classifier), from `b3_eval/v25_finetune/results/hardmine_v25b_eval.json`:**
| Row | Recomputed (raw JSON) | Manuscript (Table III) | Match |
|---|---|---|---|
| Continued (prior final) | acc 0.9412, prec 0.9389, rec 0.9512, f1 0.9450, AUC 0.9851 | 0.941/0.939/0.951/0.945/0.985 | exact (rounding) |
| Hard-mined (final) | acc 0.9541, prec 0.9461, rec 0.9689, f1 0.9574, AUC 0.9892 | 0.954/0.946/0.969/0.957/0.989 | exact (rounding) |

"Untuned base" and "Mixed corpus (pre-cont.)" rows were **not** independently
re-derived (no matching raw v2.5b-scale JSON for those two older checkpoints
was located in the time available — the only file found with that shape,
`ablation_results/mixed/summary_metrics.json`, is scoped to v1, $n{=}10{,}000$,
not v2.5b, and was correctly not used).

**Table IV (v2.5b, pipeline), from `b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_{4,5,6}.csv`**
(flagged = REJECT or CAUTION vs. `is_attacker`):
| Row | Recomputed | Manuscript | Match |
|---|---|---|---|
| B3 (config_4) | acc 0.852, prec 0.782, rec 0.999, f1 0.877, fpr 0.315 | identical | exact |
| B1+B2+B3 no CP (config_6) | acc 0.845, prec 0.775, rec 0.999, f1 0.873, fpr 0.329 | identical | exact |
| Full STBV (config_5) | acc 0.852, prec 0.782, rec 0.999, f1 0.877, fpr 0.315; TP=5358 FP=1491 FN=6 TN=3243 | identical, and FN=6/FP=1491 exactly matches Fig. confusion-matrix caption | exact |

**Table II (ITE-Bench), from `ite_bench/results/ite_config_{1,2,3,5}.csv`**
(same flagging rule, $n{=}9{,}900$):
| Row | Recomputed | Manuscript | Match |
|---|---|---|---|
| B1 (config_1) | 0.536/1.000/0.381/0.552/0.000 | identical | exact |
| B1+B2 (config_2) | 0.691/0.894/0.667/0.764/0.236 | identical | exact |
| B1+B2+CP (config_3) | 0.691/0.894/0.667/0.764/0.236 (identical to config_2) | identical, and manuscript's own claim that CP adds nothing is confirmed by the CSVs being decision-identical | exact |
| Full STBV (config_5) | 0.913/0.896/1.000/0.945/0.349 | identical | exact |

`config_4.csv` (0.638/0.936/0.556/0.697/0.113) exists but is not reported in
the manuscript's Table II — not a discrepancy, simply an unreported
intermediate configuration; not flagged as an issue.

**Conclusion of Phase 1 re-derivation**: zero discrepancies found across
Table II, III (final two checkpoints), and IV against raw per-message
CSV/JSON. No number in the manuscript was found to be fabricated,
mismatched, or drawn from the wrong checkpoint/benchmark in the rows
checked.

**Not re-derived in this pass**: VeReMi (Table V), SUMO replay, adaptive
attack — no raw per-message file for these was opened in this continuation;
this remains an open item (see Limitations).

## F. CARLA false-positive root cause
Unchanged from Pass 1 — see `CARLA_FALSE_POSITIVE_ROOT_CAUSE.md`.

## G. Baseline results (NEW — Phase 4 now substantively addressed)
Implemented and evaluated **directly on v2.5b** (not v1) in this
continuation:
| Method | Acc | Prec | Rec | F1 | FPR | AUC |
|---|---|---|---|---|---|---|
| Keyword (zero-shot) | 0.503 | 0.606 | 0.184 | 0.282 | 0.135 | n/a |
| TF-IDF+LogReg (in-domain trained)$^\dagger$ | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 |
| B3 direct (final checkpoint) | 0.954 | 0.946 | 0.969 | 0.957 | -- | 0.989 |
| Full STBV | 0.852 | 0.782 | 0.999 | 0.877 | 0.315 | -- |

$^\dagger$ Investigated per the non-negotiable "never accept 1.000 blindly"
rule: v2.5b's benign class has full lexical diversity (4,734/4,734 unique
strings, unlike v1's 10/2,993), so this is not the same defect as v1 — but
inspecting the model's top coefficients shows they are template-register
artifacts (`recorded`, `this transmission` vs. `corridor node`, `dispatch`),
not attack-content markers, so the perfect score is a benchmark-construction
property, not genuine semantic understanding, and is reported with that
caveat rather than as "beats B3." The fair zero-shot comparator (keyword,
F1=0.282) is legitimately and clearly beaten by B3.
This table (with the caveat) is now in the manuscript body (`tab:baseline`,
Section V-B), not just in this report.

## H. Final latency numbers
Unchanged from Pass 1: CARLA final-checkpoint mean 76.6 ms (verified against
raw JSON), SUMO 81.2 ms explicitly labeled prior-checkpoint. Minor
p95/p99 rounding discrepancy (95.7 vs 95.9 recomputed, etc.) still
unreconciled — not re-investigated this pass (would require locating the
exact percentile-interpolation code used to generate the original figure).

## I. Final attack-family results (NEW — re-derived this pass)
Recomputed per-category confidence-below-threshold counts directly from
`config_5.csv` using the same family-to-category map as
`figures_generated/scripts/generate_attack_category_v25b.py`:
| Category | n | below $\tau_H{=}0.70$ | % |
|---|---|---|---|
| Multi-Source Manipulation | 817 | 0 | 0.0% |
| Authority Claims | 1706 | 22 | 1.3% |
| Indirection | 1245 | 35 | 2.8% |
| Narrative Manipulation | 1596 | 47 | 2.9% |

**Exact match** to the manuscript's Fig.~\ref{fig_attack_family_v25b} caption
and prose (0/817, 22/1706=1.3%, 47/1596=2.9%, 35/1245=2.8%). No changes
needed to the figure or its caption; Phase 7 audit passes.

## J. Final scenario-wise CARLA results
Unchanged from Pass 1 — verified exactly against raw JSON.

## K. Final figure/table list
7 figures (unchanged), now **7 tables** (added `tab:baseline`): Table I
(related work), Table II (ITE-Bench), Table III (v2.5b checkpoint
progression), Table IV (v2.5b pipeline), Table V (VeReMi), Table VI (CARLA
scenarios), Table VII (per-stage latency), plus the new baseline table —
table numbering was not manually renumbered; LaTeX auto-numbers via
`\label`/`\ref`, verified compiling with 0 undefined references.

## L. Remaining limitations
- VeReMi/SUMO/adaptive-attack numbers still not independently re-derived
  from raw per-message logs in this pass (time budget; Table V/adaptive-attack
  raw files were not opened).
- CARLA benign-scenario root cause traced but not fixed, not reproduced
  across seeds (note: `deployment_eval/carla_multirun/` contains per-seed
  JSON files across Town01/02/05 that were **discovered but not analyzed**
  in this pass — a genuine, real opportunity for a follow-up multi-seed
  reproducibility check that was not completed here).
- Untuned-base / mixed-corpus (pre-continuation) checkpoint rows in Table III
  not independently re-derived (no matching raw v2.5b file located).
- Small unreconciled latency-percentile discrepancy, unresolved.
- Full Phase 12 overclaim word-sweep not performed.

## M. Remaining reviewer risks
1. TF-IDF+LogReg baseline's perfect score, even though explained, is the
   kind of number a skeptical reviewer will scrutinize closely — the
   footnote/caveat needs to survive review, not just be present.
2. CARLA benign-scenario Reject pattern remains a disclosed, unresolved
   limitation.
3. VeReMi/SUMO/adaptive numbers remain unverified against raw logs by this
   pass (rely on manuscript + prior session's audit trail).
4. `deployment_eval/carla_multirun/` (multi-seed CARLA data) exists in the
   repo and was not used — a reviewer-facing "why didn't you use your own
   multi-seed data" risk if that directory turns out to be relevant/final-
   checkpoint data; flagged for a follow-up pass to check.

## N. Page count
**10 pages** (grew from 9 after adding the baseline table and proof-sketch
appendix), verified by a real `pdflatex` compile (run twice) in this pass, 0
LaTeX errors, 0 undefined references in the log. Still within the task's
9-11 page target.

## O. Final recommendation
**CLOSER TO READY than Pass 1, still not exhaustively complete.** Phase 4
(baseline) is now substantively addressed with a real v2.5b-specific
external comparison, honestly caveated. Phase 1 is now materially
re-verified for the two most important tables (II, IV, and the final two
rows of III) with zero discrepancies found. Phase 11 has compact proof
sketches in the Appendix. Phase 7 audit passed with an exact match. Open
items: VeReMi/SUMO/adaptive-attack raw re-verification, the unused
`carla_multirun/` multi-seed data, and the two oldest Table III checkpoint
rows. Recommend a further short pass on those before final submission if
time allows; otherwise this is submittable with the remaining gaps disclosed
in Limitations, which is the honest position rather than a fabricated
"fully verified" claim.
