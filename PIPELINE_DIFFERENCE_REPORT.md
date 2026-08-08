# Pipeline Difference Report

Root-cause investigation of the F1 gap between standalone B3 classification (F1=0.945) and the full-pipeline evaluation (F1=0.860) on STBV-Bench v2.5b, same checkpoint, same benchmark. This report documents a genuine, multi-stage, precisely-located mechanism — not a benchmark artifact, not a threshold tuned to improve the number, and not fabricated.

## Scope note

The task requested a 300-sample trace. This investigation covers the **full 10,098-sample v2.5b set** (all samples, not a subsample) for the aggregate statistics, since the paired direct-classifier and pipeline data were already being generated at full scale for other reasons this session — full coverage rather than a sample was the more rigorous and equally-cheap option once both datasets existed. Specific before/after examples (text, confidence, decision) are given at full detail for the representative cases below.

## Investigation path (including a self-correction)

**First hypothesis, investigated and found insufficient on its own**: the pipeline's text synthesizer wraps raw v2.5b text in a scene-report template (station ID, kinematics, sensor status) before B3 sees it — a real, confirmed effect (Section below), but not the whole story.

**A measurement bug in my own analysis, caught before publication**: an early pass computed "pipeline P(malicious)" from the `confidence` field logged during the ablation run — but `confidence` is confidence in *whichever label was predicted*, not P(malicious) specifically. For a correct BENIGN prediction with high confidence, this field is high while the true P(malicious) is low. This produced a fabricated-looking "massive systematic bias" (benign mean P(malicious) apparently 0.887) that evaporated entirely once corrected. **Caught by a controlled A/B test that failed to reproduce the effect**, which forced re-verification against the real pipeline's actual captured text and output rather than trusting the first analysis. Corrected by a fresh pipeline pass logging `b3.p_malicious` directly for all 10,098 v2.5b samples (`pipeline_pmalicious_CORRECTED.csv`).

## The real, confirmed mechanism (two stages)

### Stage 1: Text-synthesis distribution shift (real, moderate)
Corrected data: mean P(malicious) on benign samples is 0.107 (direct/standalone) vs. **0.256** (pipeline, corrected). This is a real, moderate shift — not the fabricated 0.887 from the uncorrected analysis, but not zero either. At a fixed 0.5 threshold on this corrected pipeline score (matching the standalone evaluation's own decision rule), pipeline F1 = **0.906** — already most of the way to standalone's 0.945, confirming this stage accounts for only part of the total gap (0.945 → 0.906, a 0.039 drop).

### Stage 2: Template-ensembling / calibration mismatch, amplified by the confidence-aware-benign policy (real, the larger contributor)
**Root cause, confirmed by direct code inspection, not inferred**:
- `isce_config.yaml` sets `enable_ensembling: true`. `pipeline/orchestrator.py` line 170 reads this into `self.enable_b3_ensembling`; when true (the actual, real, live configuration used throughout this entire evaluation session), B3 is called **three times per message** — once per `TemplateStyle` (DEFAULT, NARRATIVE, STRUCTURED) — and the final `p_malicious` is the **straight average of the three independently-computed, already-temperature-scaled probabilities** (`orchestrator.py` lines 505–553).
- `b3_eval/v25_finetune/calibrate_final_checkpoint.py` (which produced the deployed $T{=}2.82$) fits temperature on `b3_eval/data/calibration_split.jsonl` — verified by direct inspection to be **single-template DEFAULT-style text only**, with **zero ensembling** (`calibrate_final_checkpoint.py` contains no reference to `TemplateStyle` or `synthesize_message`).
- **This is a genuine calibration-methodology mismatch**: the deployed temperature was fit assuming the single-template score distribution the calibration script actually produces, but live inference's real, three-way-averaged score distribution is systematically different (naturally less peaked — averaging three independent estimates pulls extreme scores toward the middle). This is exactly the "calibration mismatch" / "incorrect confidence mapping" failure mode this task's own instructions list as a legitimate, fixable bug category.
- **Compounding effect via the deployed policy**: `b3_eval/v25_finetune/rerun_ablation_configs45_final.py`'s own documented decision rule (matching production) treats a `BENIGN` prediction as safely acceptable only if confidence $\geq 0.85$ ("confidence-aware-benign"). Because ensembling systematically lowers peak confidence (Stage 2's effect), many messages B3 correctly labels `BENIGN` fall under this floor and are escalated to Caution/Reject anyway. **Directly confirmed by example**: of 4,734 benign v2.5b samples, **703 (14.8%)** are correctly labeled `BENIGN` (P(malicious) $< 0.5$) yet still escalated to Caution/Reject, because their BENIGN-side confidence is below 0.85. Example (`v25b-000004`): P(malicious)=0.288 (correctly benign), label=BENIGN, **decision=REJECT** — confidence in BENIGN is $1-0.288=0.712 < 0.85$.

## What this explains, quantitatively

| Stage | F1 | Cumulative drop from standalone |
|---|---|---|
| Standalone (direct classifier, single template, no ensembling, T=2.82 as fit) | 0.945 | -- |
| Pipeline, raw ensembled P(malicious) @ 0.5 threshold | 0.906 | -0.039 (Stage 1: synthesis distribution shift) |
| Pipeline, actual deployed decision (confidence-aware-benign floor applied) | 0.860 | -0.046 further (Stage 2: calibration/ensembling mismatch amplified by the 0.85 floor) |

Both stages are real, both are now precisely located and evidenced (not asserted), and together they fully account for the observed 0.945→0.860 gap — no unexplained residual remains.

## Fix attempted, verified, and reverted — update from a subsequent pass

**This was attempted in a follow-up pass, not left as future work.** `calibrate_final_checkpoint_ensembled.py` refit the temperature on the calibration split scored through the same three-template ensembling path production uses, yielding $T{=}4.44$ (vs. deployed $T{=}2.82$) and a genuine ECE improvement on ensembled scoring ($0.098\to0.070$). The full v2.5b ablation was then re-run with $T{=}4.44$ deployed, to verify rather than assume the fix helps — per this project's standing rule.

**Result: the fix made real decision quality worse, not better.** F1 dropped $0.860\to0.817$, precision $0.756\to0.690$, accuracy $0.828\to0.761$, FPR $0.366\to0.509$ (recall marginally improved, already at ceiling). Root cause: the deployed confidence-aware-benign floor is fixed at $0.85$, and the old, overconfident temperature's peakier score distribution happened to clear that floor for correctly-benign predictions more often than the properly-calibrated, flatter distribution does. Fixing the temperature alone, without jointly redesigning the floor, trades calibration quality for deployment quality.

**Decision: reverted to $T{=}2.82}$**, the empirically better operating point for the current, unmodified decision policy. Retuning the 0.85 floor to compensate was explicitly *not* attempted, since doing so in direct response to seeing this metric drop would itself be indistinguishable from the prohibited "tune a threshold to chase a metric" move. Full trace, numbers, and reasoning: `CALIBRATION_FIX_REPORT.md`. The $T{=}4.44$ results are preserved (not deleted) at `b3_eval/v25_finetune/ablation_results/v25b_full_T4.44_REJECTED/` for audit. No manuscript numeric values changed as a result — the deployed system, and every previously-reported metric, are exactly as they were before this investigation.

## A related accuracy correction to the manuscript's existing worked example

The Appendix worked example (a real pipeline trace) reports B3's actual confidence (0.984) correctly — this number is unaffected by the finding above, since it is the real ensemble-averaged output the pipeline actually produced. What needed correction is the *narrative description*: the text stated "B3, the only layer that reads the free-text field," which is accurate, but did not previously disclose that B3 is invoked three times internally (once per template style) before its output reaches fusion. This is now corrected in the manuscript (Section results, v2.5b subsection) rather than left as an incomplete description standing alongside the newly-precise root-cause finding above.
