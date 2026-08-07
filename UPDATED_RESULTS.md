# UPDATED_RESULTS.md — B3 LoRA-Finetuned Checkpoint: Manuscript-Wide Impact

**This document supersedes the previous version of `UPDATED_RESULTS.md`**,
which described the *frozen, un-finetuned* checkpoint's poor zero-shot
performance on STBV-Bench v2.5 (a different, earlier finding, now resolved
by fine-tuning — see `b3_eval/v25_finetune/FULL_EVALUATION_REPORT.md`). This
version covers the **LoRA-finetuned-and-merged checkpoint's** impact across
every B3-dependent result in `stbv_paper.tex`, produced by swapping only
B3's checkpoint and rerunning every Category-A experiment in
`b3_eval/v25_finetune/DEPENDENCY_TABLE.md`.

**One-line summary: the fine-tuned checkpoint dramatically improves
performance on the STBV-Bench v2.5 distribution it was fine-tuned on, and
substantially regresses every result currently in the manuscript (which is
built on STBV-Bench v1 and its derivatives, an external corpus, and
adaptive/CP/deployment evaluations). Recommendation: do not swap the
manuscript's checkpoint. Full reasoning in `REGRESSION_REPORT.md`.**

## Every changed metric

### STBV-Bench v1 (n=10,000) — the manuscript's headline benchmark

| Metric | Original | Fine-tuned | Δ |
|---|---|---|---|
| B3-alone F1 | 0.7151 | 0.3896 | **−0.3256** |
| B3-alone recall | 0.5566 | 0.2419 | **−0.3147** |
| B3-alone precision | 1.0000 | 1.0000 | 0 |
| Full-stack F1 | 0.7175 | 0.4032 | **−0.3143** |
| Full-stack recall | 0.5650 | 0.2550 | **−0.3100** |
| Full-stack precision | 0.9829 | 0.9628 | −0.0200 |
| ROC-AUC (config 4) | 0.747 | 0.956 | +0.209 (ranking improves) |
| PR-AUC (config 4) | 0.911 | 0.985 | +0.074 (ranking improves) |
| ECE (argmax-confidence proxy) | 0.365 | 0.539 | +0.174 (worse calibrated) |
| Brier | 0.308 | 0.515 | +0.207 (worse) |
| McNemar (config 4, old vs new) | b01=2355, b10=150 | p≈0 | large, significant, one-directional |
| Cohen's h (recall, config 4) | −0.656 | (large effect) | |
| Configs 1–3 (`enable_b3=False`) | byte-identical | 0/10,000 differ | confirms checkpoint-independence |

### Mixed-threat case study (shared kinematic+semantic scene, n=120 windows / 4,123 messages)

| Metric | Original | Fine-tuned | Δ |
|---|---|---|---|
| Semantic-attacker recall (per-message, n=771) | 83.8% | 69.0% | −14.8pp |
| Semantic-attacker recall (per-sender, n=67) | 94.0% | 92.5% | −1.5pp |
| Kinematic-attacker recall (per-message/sender) | 86.9% / 100% | unchanged | 0 |
| Double-counted attackers | 0 | 0 | 0 |

*Absolute values are not directly comparable to the manuscript's published
70.3%/90.3% (methodology could not be exactly reproduced — see
`UPDATED_TABLES.md` §2); relative deltas above use a consistent methodology
across both checkpoints.*

### STBV-Bench v2 contextual evaluation (n=150 windows / 5,062 messages)

| Metric | Original (reproduces paper exactly) | Fine-tuned | Δ |
|---|---|---|---|
| Aggregate Decision-Trust F1 | **0.5171** (paper: 0.517) | **0.3905** | **−0.1266** |
| Aggregate accuracy | 0.5476 | 0.4739 | −7.37pp |
| Aggregate precision | 0.3654 | 0.2860 | −7.94pp |
| Aggregate recall | 0.8839 | 0.6150 | **−26.89pp** |

### External semantic evaluation corpus (n=117, frozen checkpoint)

| Metric | Original | Fine-tuned | Δ |
|---|---|---|---|
| F1 | 0.9357 | 0.9294 | −0.0063 |
| Recall | 0.8989 | 0.8876 | −1.12pp |
| Precision | 0.9756 | 0.9753 | −0.03pp |
| ROC-AUC | 0.9747 | 0.9522 | −0.0225 |
| Confusion (TP/FP/FN/TN) | 80/2/9/26 | 79/2/10/26 | +1 FN |

### Adaptive attack evaluation (n=51 seeds)

| Metric | Original (live rerun) | Fine-tuned | Δ |
|---|---|---|---|
| Attack Success Rate | 84.3% (43/51) | 84.3% (43/51) | **0 (unchanged)** |

Manuscript states 83.7% (41/49); this session's live rerun of the
**unchanged original checkpoint** gives 84.3% (43/51) — a small,
disclosed discrepancy from the committed artifact (see
`UPDATED_TABLES.md` §5), not attributable to the checkpoint swap.

### CP full evaluation (n=142, 24 scenes)

**Byte-identical** between checkpoints on every metric (decision changes,
escalations, false positives/negatives, per-category and per-scene
breakdowns) — confirms the manuscript's own claim that CP's outcomes here
are driven by MBD, not B3.

### Deployment feasibility — SUMO replay (n=2,000)

**Decisions byte-identical** between checkpoints (1765 CAUTION / 235 ACCEPT
both). Latency **not comparable** in this pass — the finetuned run executed
under GPU contention from concurrent reruns; use
`FULL_EVALUATION_REPORT.md`'s isolated batch=1 benchmark instead (p50
23.4ms→21.7ms, unchanged).

**SUMO/CARLA feasibility correction**: `traci`/`sumo` ARE available in this
environment (re-verified; the prior session's infeasibility claim for SUMO
was stale/incorrect). CARLA remains genuinely infeasible (`carla` module not
installed) — not rerun.

### Worked example (App. §Semantic Transformation Engine)

Exact quoted text run through the finetuned checkpoint directly:
label=MALICIOUS, confidence **0.699→0.9895**, risk_level **medium→high**.
Requires a prose rewrite of the Dempster-Shafer fusion-mass walkthrough
(the mass split is downstream of the confidence band) — see
`MANUSCRIPT_UPDATE_MAP.md`.

### Latency (unchanged, checked explicitly)

Not re-benchmarked end-to-end in this pass (Category B, low priority given
the reruns above cover every Category A row). `FULL_EVALUATION_REPORT.md`'s
existing isolated measurement stands: p50/p95/p99/throughput/VRAM/param-count
all within noise or exactly identical post-LoRA-merge.

## What regressed, what improved, what's unchanged — one table

See `UPDATED_TABLES.md` §"Summary of every metric touched in this pass" for
the consolidated view, and `REGRESSION_REPORT.md` for the full
interpretation and recommendation (**do not swap the manuscript's checkpoint
without also recalibrating v1's risk-band thresholds, which was out of
scope for this task**).

## Deliverables from this pass

- `UPDATED_RESULTS.md` (this file)
- `MANUSCRIPT_UPDATE_MAP.md` — every `stbv_paper.tex` location needing an edit, old text → new values, no `.tex` edits made
- `UPDATED_TABLES.md` — full numeric tables
- `UPDATED_FIGURES/` — regenerated figures + `updated_figures_data.json`
- `REGRESSION_REPORT.md` — summary + explicit recommendation
- `b3_eval/v25_finetune/DEPENDENCY_TABLE.md` — Part 1, status column updated to reflect what was actually run
- New reusable rerun scripts: `b3_eval/v25_finetune/rerun_deployment_eval.py`, `rerun_adaptive_attack.py`, `rerun_stbv_v2.py`, `rerun_mixed_threat.py`, `generate_updated_figures.py`
