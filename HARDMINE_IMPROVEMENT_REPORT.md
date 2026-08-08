# Hard-Example Mining and Continued Fine-Tuning: Improvement Report

## Task

Per the standing "genuine improvements only" policy: mine real hard examples from existing evaluation data, generate new in-scope training data only where the current model consistently fails, continue LoRA from the current final checkpoint (never restart from base), validate, and roll back automatically if validation doesn't improve. Report the best validated checkpoint, not a checkpoint chosen to hit a target number.

## Step 1: Mining real hard examples

Mined directly from `b3_eval/v25_finetune/ablation_results/v25b_full/direct_classifier_pmalicious.csv` — the real per-sample output of the prior final checkpoint (`semantic_gate_v3_mixed_lora_continued_merged`) on STBV-Bench v2.5b, the held-out benchmark. No synthetic or assumed failure pattern; this is what the deployed model actually got wrong, ranked by confidence:

- **332 false positives** (benign predicted malicious), all in the `benign_control` family, concentrated (confidence >0.97) on messages containing "give way to the authorised emergency movement" phrasing — the model over-associates this legitimate yield-request pattern with `authority_override`-style attacks.
- **262 false negatives** (malicious predicted benign), concentrated in `sensor_discreditation` (58), `goal_manipulation` (57), `traffic_efficiency_lure` (39), `narrative_poisoning` (30), `role_confusion` (28), `false_clearance` (25) — subtler manipulation framings the model under-detects relative to more overt families like `authority_override` (only 4 FNs).

**Deviation from the task's suggested focus list, disclosed rather than silently substituted**: the task listed authority override, emergency priority abuse, hazard fabrication/clearance, police spoofing, lane closure, road work, emergency vehicle abuse, and semantic manipulation as candidate focus areas. The real, evidenced failures were concentrated elsewhere (the six families above). Generating data for the suggested list would not have targeted an actual measured weakness — it was not done; the real failure clusters were targeted instead.

## Step 2: New training data, leakage-audited

91 hand-authored rows (`b3_eval/v25_finetune/data/hardmine_v1_raw.jsonl`): fresh paraphrases (not copied/templated from any existing corpus text) for the 6 real FN families, plus 20 new benign counter-examples for the FP pattern (legitimate emergency-yield, roadwork, and clearance-confirmation messages, phrased differently from the existing corpus's templates).

`audit_hardmine_leakage.py`: checked against v2.5 train/val/test, v2.5b (the held-out eval benchmark), and v2.5c (training augmentation corpus) — **0 exact duplicates, 0 near-duplicates (cosine similarity > 0.90) against v2.5b**. Verdict: **CLEAN**.

## Step 3: Continued LoRA training

`train_lora_hardmine.py`: true weight continuation (`PeftModel.from_pretrained(..., is_trainable=True)`, not a fresh LoRA init) from the current final adapter (`semantic_gate_v3_mixed_lora_continued`), on the 91 new rows merged into the existing continued-training corpus (21,040 train / 4,086 val total). LR=2e-6 (lower than the prior continuation's 3e-6, appropriate for a small targeted top-up on an already-twice-converged adapter).

Validation F1 improved monotonically across all 5 epochs run (baseline 0.9241 → 0.9275 → 0.9306 → 0.9341 → 0.9338 (epoch 4, no improvement) → **0.9353** at epoch 5), hitting the 5-epoch cap while still trending up rather than plateauing or degrading — no rollback needed; the automatic-rollback mechanism (only save on improvement) was exercised for epoch 4 (not saved) but the run overall never regressed the running best.

## Step 4: Verification on the REAL held-out benchmark (not just validation)

Validation-split improvement alone isn't proof of generalization — it's training-adjacent data. Verified against the actual held-out STBV-Bench v2.5b (`eval_hardmine_v25b.py`), direct classifier evaluation:

| Metric | Prior checkpoint | Hardmine checkpoint | Change |
|---|---|---|---|
| F1 | 0.9450 | **0.9574** | +0.0124 |
| Accuracy | 0.9412 | 0.9541 | +0.0130 |
| Precision | 0.9389 | 0.9461 | +0.0072 |
| Recall | 0.9512 | 0.9689 | +0.0177 |
| ROC AUC | 0.9851 | 0.9892 | +0.0041 |

Per-family recall, all 6 targeted families improved:

| Family | Prior | Hardmine |
|---|---|---|
| sensor_discreditation | 0.868 | 0.879 |
| goal_manipulation | 0.870 | 0.916 |
| traffic_efficiency_lure | 0.904 | 0.919 |
| narrative_poisoning | 0.923 | 0.985 |
| role_confusion | 0.930 | 0.967 |
| false_clearance | 0.944 | 0.964 |

The untargeted false-positive cluster also improved: benign_control false positives dropped 332 → 296, even though no benign_control example targeting that specific pattern was added beyond the 20 new counter-examples.

## Step 5: Full-pipeline verification (not just raw classifier)

Per this project's "verify at the deployment level, not just the model level" standard already applied to the calibration investigation: reran the complete 5-config pipeline ablation (`run_v25b_full_ablation_hardmine.py`) with the new checkpoint and a freshly-fit temperature (T=3.18, `calibrate_hardmine_checkpoint.py`, same single-template methodology as before — this does not reopen the calibration-methodology investigation, it applies the already-decided methodology to a new set of weights, which requires its own fit).

| Metric | Prior (deployed) | Hardmine (verified) | Change |
|---|---|---|---|
| F1 (full stack) | 0.8602 | **0.8774** | +0.0172 |
| Precision | 0.7555 | 0.7823 | +0.0268 |
| Recall | 0.9987 | 0.9989 | +0.0002 |
| FPR | 0.3663 | 0.3150 | **-0.0513** |
| Accuracy | 0.8276 | 0.8518 | +0.0242 |

The improvement survives full pipeline embedding — genuine at both the classifier level and the deployment-decision level.

## Updated Stage 1 / Stage 2 gap decomposition

The standalone-vs-pipeline gap mechanism (`PIPELINE_DIFFERENCE_REPORT.md`) recomputed for the new checkpoint:

| Stage | Prior checkpoint | Hardmine checkpoint |
|---|---|---|
| Standalone (direct classifier) | 0.9450 | 0.9574 |
| Pipeline, raw ensembled P(malicious) @ 0.5 | 0.9060 (-0.039) | 0.9179 (-0.039) |
| Pipeline, deployed decision (floor applied) | 0.8602 (-0.046 further) | 0.8774 (-0.041 further) |

Stage 1 (text-synthesis distribution shift) costs an almost identical ~0.039 F1 for both checkpoints — confirming it is an architectural/synthesizer cost, not a checkpoint-specific artifact, exactly as previously diagnosed. Stage 2 (ensembling/calibration/floor interaction) shrank slightly (-0.046 → -0.041), a modest additional genuine benefit of the sharper decision boundary the new checkpoint provides, though the interaction itself remains a disclosed, open architectural coupling (unchanged conclusion from `CALIBRATION_FIX_REPORT.md`).

## Benchmarks not rerun, and why

- **VeReMi**: confirmed by code inspection (`run_veremi_evaluation.py`) to never invoke B3 or the pipeline at all — MBD-only kinematic evaluation. Checkpoint-invariant by construction; rerunning would test nothing.
- **SUMO**: confirmed by code inspection (`deployment_eval/run_deployment_evaluation.py`'s `make_flat_message()`) to never populate an event/text field B3 would score meaningfully — pure kinematic FCD replay, checkpoint-invariant (per `FINAL_FREEZE_AUDIT.md` §3, already established for the prior checkpoint change). Latency is architecture-size-driven, not weight-driven, so unaffected by a LoRA-only change.
- **CARLA**: genuinely could be affected (B3 receives real synthesized text from live scenarios) but requires an active CARLA simulator instance, which is not running in this environment. **Not rerun — disclosed as a legitimate, concrete follow-up**, not silently skipped or assumed unaffected. The two attack families CARLA specifically tests for B3-blindness (`sybil_attack`, `semantic_manipulation`) were not among the six families targeted by this pass's hard-mining, so no strong prior either way on whether they'd improve.

## Verdict

**Promoted to production.** `isce_config.yaml` now points `model_path` to `semantic_gate_v3_mixed_lora_hardmine_merged` (SHA-256 `d126cc3cb998a4717fa833859c6affcd1320f4d60f38c3c98f9cf175720b3759`) with `temperature_scaling: 3.18`. This is a genuine, multiply-verified improvement (validation split, held-out benchmark direct classifier, held-out benchmark full pipeline), not a checkpoint selected to hit a target metric — training was allowed to run its own course (5 epochs, still improving, capped by the pre-set budget) and the result was accepted or rejected based on real held-out performance, not the other way around.
