# evaluation/ — End-to-End Evaluation Framework

Implements Parts 5–12 of the publication-readiness mandate. One command
produces a complete, manifest-stamped results tree.

## Quick start

```bash
# Smoke run (~4s): 1 seed, benign+replay, all configs+baselines
python3 evaluation/run_experiments.py --quick

# Full run (all 6 families, 7 configurations + 3 baselines, 3 seeds)
python3 evaluation/run_experiments.py

# Sweeps
python3 evaluation/run_experiments.py --seeds 1 2 3 4 5 --families sybil collusion \
    --message-count 20 --window-cap 15
```

Output tree (per run, under `results/<timestamp>/`):

```
manifest.json                 # seeds, config, versions, hardware, dataset SHA fingerprints
per_message_results.csv       # every (seed, scenario, config, message) row incl. errors
metrics_by_config_family.csv  # acc/prec/recall/F1/FPR/FNR/detection/caution/error rates
statistical_tests.json        # McNemar (full vs each ablation), bootstrap CIs — with applicability guards
latency_summary.json          # p50/p95/p99 per stage (full config)
latex/ablation_table.tex      # paste-ready table
plots/                        # confusion matrices, ROC/PR (where scores exist), ablation + latency bars
generated_scenarios/          # the exact seeded scenario data used (fingerprinted in manifest)
logs/
```

## Configurations (Part 8)
`full`, `no_b1`, `no_mbd`, `no_b2`, `no_cp`, `no_b3`, `no_fusion` — all via
harness-side composition/monkey-patching; production code is never modified.

## Baselines (Part 9)
`baseline_pki_only`, `baseline_pki_mbd`, `baseline_threshold` — documented
approximations (see runner.py docstring), not reimplementations of specific
papers.

## Scoring conventions
Positive class = attacker message. REJECT = predicted attack. CAUTION is
**not** a detection claim (confirmed design intent: caution-until-corroborated
for unverified senders); it is reported as `caution_rate`. ERROR rows are
explicit, never silently dropped.

## Honest-limitations behavior
- If B3's real model is unavailable, the manifest + console carry a warning
  and the full-vs-no_b3 comparison is flagged as not meaningful.
- Statistical tests refuse (with reasons) where preconditions fail.
- ROC/PR are only drawn for configurations that emit a continuous score.

## Companion scripts (earlier cycle, still current)
- `validation/run_ablation_table.py` — fixture-based ablation (A4)
- `validation/run_b4_fallback_degradation.py` — B3-down degradation
- `validation/run_c1_c2_latency_throughput.py` — standalone latency
- `validation/run_b3_b6_synthesizer_robustness.py` — leak/determinism/template checks
- `tests/` — regression suites (run all after any change)

## Resolved issue (see CHANGELOG.md)
CP corroboration deficit was previously folded into the validation score as
disbelief, producing FPR up to 0.93 on dense generated traffic. Fixed:
corroboration deficit now routes to DS Theta mass (uncertainty) via the
confidence axis; only genuine shared-event contradiction contributes
disbelief. Measured FPR after fix: 0.00 on both affected families
(regression-tested in tests/test_cp_uncertainty_semantics.py). Numbers from
runs predating the fix should be discarded.
