# REGRESSION_REPORT.md — B3 Checkpoint Swap: Manuscript-Wide Impact

**Scope.** This session swapped B3's checkpoint (original `semantic_gate_v3`
→ LoRA-finetuned-and-merged `semantic_gate_v3_v25_lora_merged`, produced by
a prior session's fine-tune on STBV-Bench v2.5) and reran every
Category-A-dependent experiment identified in `b3_eval/v25_finetune/DEPENDENCY_TABLE.md`,
changing nothing else — same datasets, same thresholds, same fusion rule,
same PKI/B1/MBD/B2/CP, same calibration procedure. Full numeric results are
in `UPDATED_TABLES.md`; per-location manuscript edits are in
`MANUSCRIPT_UPDATE_MAP.md`; regenerated figures are in `UPDATED_FIGURES/`.

## Headline finding

**The fine-tuned checkpoint is a large, unambiguous improvement on the
distribution it was fine-tuned on (STBV-Bench v2.5) and a large,
unambiguous regression on every distribution it was not fine-tuned on
(STBV-Bench v1, the v1-derived mixed-threat and STBV-Bench-v2 corpora, and
an independent external corpus).**

| Corpus | Was B3 fine-tuned on this distribution? | Headline metric | Old → New | Verdict |
|---|---|---|---|---|
| STBV-Bench v2.5 test (`FULL_EVALUATION_REPORT.md`, prior session, not rerun here) | **Yes** | F1 | 0.631 → 0.950 | Large **IMPROVEMENT** |
| STBV-Bench v1, n=10,000 (`UPDATED_TABLES.md` §1) | No | F1 (B3 alone / full stack) | 0.715/0.718 → 0.390/0.403 | Large **REGRESSION** |
| Mixed-threat case study (§2) | No | Semantic-attacker recall | 83.8%(msg) → 69.0% | **REGRESSION** |
| STBV-Bench v2 contextual (§3) | No (v2 windowed corpus, distinct from v2.5) | Aggregate Decision-Trust F1 | 0.517 → 0.390 | Large **REGRESSION** |
| External semantic corpus, n=117 (§4) | No | F1 / ROC-AUC | 0.936/0.975 → 0.929/0.952 | Small **REGRESSION** |
| Adaptive-attack ASR, n=51 (§5) | No | ASR | 84.3% → 84.3% | UNCHANGED (already near-ceiling) |
| CP full eval, n=142 (§6) | No | decision changes | byte-identical | UNCHANGED (B3-independent by design) |
| SUMO deployment, n=2,000 (§7) | No | decisions | byte-identical | UNCHANGED (no text field, B3 has nothing to disagree about) |

This is a textbook narrow-distribution-shift outcome, not a bug: LoRA
fine-tuning moved every encoder layer's representation toward STBV-Bench
v2.5's specific 14-family taxonomy and template style. `FULL_EVALUATION_REPORT.md`
(the prior session's own report) already predicted the mechanism —
"a near-chance family cannot be fixed by re-weighting a linear head... the
encoder itself had to move" — and documents this as a deliberate design
choice (full encoder LoRA, not head-only). The cost of that choice, not
visible from the v2.5-only evaluation alone, is exactly what this session's
manuscript-wide rerun surfaces: STBV-Bench v1 uses a **different, 20-family
taxonomy** from v2.5's 14 families (e.g. v1's `semantic_narrative_poisoning`
vs. v2.5's `narrative_poisoning`; v1 has no `role_confusion` or
`priority_manipulation`, families v2.5 explicitly needed to fix), so the
representation shift that fixed v2.5's broken families did not transfer to,
and measurably hurt, v1's.

## The most important nuance: ranking quality vs. calibration

On STBV-Bench v1 config-4 (B3 alone), the finetuned checkpoint's **ROC-AUC
improves** (0.747→0.956) and **PR-AUC improves** (0.911→0.985) — meaning its
raw confidence score still separates malicious from benign v1 text better
than the original model does, in a ranking sense. But its **calibration
degrades** (ECE roughly doubles by the proxy measure used in
`UPDATED_TABLES.md` §9), and the production risk-band thresholds
(`semantic_high_confidence=0.85`, `semantic_medium_confidence=0.60` in
`trust_engine/policy.py`) were tuned against the **original** checkpoint's
confidence distribution and were explicitly **not** touched in this pass
(per this task's rules). Applying stale thresholds to a differently-shaped
confidence distribution is the most likely mechanistic explanation for why
recall collapses (55.7%→24.2%) even though discriminative power improved.

**This does not make the regression non-real for the system as currently
configured** — deploying the new checkpoint today, with the current
threshold config, genuinely and severely regresses v1 recall — but it does
mean the fix, if the new checkpoint is ever adopted for v1-style traffic, is
very likely a threshold recalibration exercise (analogous to
`FULL_EVALUATION_REPORT.md`'s own v2.5 recommendation, T=2.1446→3.2778),
not evidence that the encoder itself is worse. Recalibrating v1's
thresholds was out of scope for this pass (the task rules forbid touching
thresholds) and is the natural next step before any v1-facing deployment
decision.

## What is unchanged, and why that matters

Four evaluations are **exactly unchanged**, and each has a clean structural
reason:
- **CP full eval** (byte-identical): confirms the paper's own claim that
  MBD's collusion score already drives CP's outcomes independently of B3.
- **SUMO deployment decisions** (byte-identical): the FCD-replay message
  schema carries no free-text field, so B3 has nothing checkpoint-specific
  to score.
- **Kinematic side of the mixed-threat case study** (byte-identical):
  kinematic detection is MBD-only by architecture.
- **Adaptive-attack ASR** (84.3%→84.3%, aggregate): already near-ceiling
  vulnerability under both checkpoints; 8/51 individual seeds flip which
  specific message evades, but the net rate is identical. The paper's
  single most safety-critical finding (severe adaptive vulnerability) is
  **not resolved** by this fine-tune.

## What could not be measured, and why (disclosed, not fabricated)

- **CARLA-side deployment numbers** (Table `tab:deployment` CARLA column,
  `tab:carla_scenarios`, all CARLA figures): `carla` Python module still not
  installed in this environment; genuinely infeasible here, same as the
  prior session's finding. Not rerun, not fabricated.
- **The paper's exact "70.3%/90.3%" mixed-threat aggregation**: no committed
  analysis script reproduces this exact per-vehicle definition (verified by
  search); this session's own straightforward aggregation does not
  reproduce it even on the unchanged original checkpoint. Relative deltas
  under a consistent, disclosed methodology are reported instead (see
  `UPDATED_TABLES.md` §2).
- **The 11-perturbation-family v1-era robustness battery** (§Results
  "...Latency" prose): deprioritized behind the reruns above within this
  session's time budget; the closest available same-technique measurement
  (v2.5 corpus, `FULL_EVALUATION_REPORT.md` §7) shows a mild aggregate
  improvement (mean flip rate 0.182→0.152), but is not a substitute for the
  paper's specific v1 battery.
- **Worked example 2** (`hazard_suppression`, confidence=0.569): the exact
  message text is paraphrased, not quoted, in the manuscript, so it could
  not be identified and re-run without guessing at wording.

## Recommendation

**Do not replace the checkpoint throughout the paper.** The evidence
supports a narrower, more defensible recommendation:

1. **For any claim scoped to STBV-Bench v2.5** (which does not currently
   exist in `stbv_paper.tex` — v2.5 is this session's and the prior
   session's own held-out evaluation, not yet a manuscript benchmark): the
   fine-tuned checkpoint is a clear, well-documented improvement and should
   be used, with the recalibrated temperature T=3.2778.
2. **For every claim currently in `stbv_paper.tex`** (STBV-Bench v1, its
   mixed-threat/v2 derivatives, the external corpus, the adaptive-attack
   evaluation, the SUMO/CARLA deployment evaluation) — **keep the original
   checkpoint.** The fine-tuned checkpoint would silently and severely
   regress the paper's own headline numbers (F1 0.718→0.403 on the
   benchmark the entire Results section is built around) if substituted
   in-place, for reasons (representation drift toward a disjoint 14-family
   taxonomy, threshold miscalibration) that are understood, disclosed, and
   plausibly fixable but were **not** fixed in this pass, per the
   task's explicit rule against touching thresholds.
3. **If a future revision wants to adopt the fine-tuned checkpoint
   architecture-wide**, the correct sequence is: (a) recalibrate
   `trust_engine/policy.py`'s risk-band thresholds against the new
   checkpoint's confidence distribution on v1 (the same kind of exercise
   `FULL_EVALUATION_REPORT.md` already did for v2.5's temperature), (b)
   re-run this exact audit to confirm whether the ROC-AUC-improvement/
   ECE-regression tension resolves once thresholds are recalibrated, and
   only then consider a manuscript-wide swap. That work is out of scope for
   this task (which explicitly excludes touching thresholds) and is not
   done here.
4. **The adaptive-attack vulnerability (83.7%→84.3% ASR either way) is
   unresolved regardless of which checkpoint is used** and should continue
   to be reported as the paper's most serious open finding, unaffected by
   this checkpoint decision either way.

## Where everything lives

- `UPDATED_RESULTS.md` — every changed metric, repo root.
- `UPDATED_TABLES.md` — full old→new tables, repo root.
- `MANUSCRIPT_UPDATE_MAP.md` — per-`stbv_paper.tex`-location required edits, repo root.
- `UPDATED_FIGURES/` — regenerated figures, repo root.
- `b3_eval/v25_finetune/DEPENDENCY_TABLE.md` — Part 1, updated status column.
- `b3_eval/v25_finetune/results/paper_reruns/` — raw JSON for external eval, adaptive attack, CP full eval (both checkpoints).
- `b3_eval/v25_finetune/results/ablation_rerun_comparison.json` — STBV-Bench v1 stats (McNemar, Cohen's h).
- `b3_eval/v25_finetune/ablation_results/{original,finetuned}/` — raw per-message ablation CSVs, n=10,000, 5 configs each.
- `results/stbv_bench_v2_finetuned/`, `results/mixed_threat_finetuned/`, `b3_eval/v25_finetune/ablation_results/deployment_eval_finetuned.json` — new-checkpoint reruns of the v2/mixed-threat/SUMO harnesses.
