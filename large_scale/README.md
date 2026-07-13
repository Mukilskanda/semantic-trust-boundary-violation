# large_scale/ — Publication-Scale Evaluation Framework

Parts 1–7 of the large-scale evaluation mandate. Composes the **frozen** stack
(`pipeline.ISCEPipeline` via `evaluation.runner`), the existing scenario
generator (`scenario_generation`), and a semantic attack library
(`large_scale/semantic_attacks.py`). No layer or model is modified.

## Quick start

```bash
python3 large_scale/run_large_scale.py --quick                       # ~1s smoke
python3 large_scale/run_large_scale.py --mode scale --message-target 1000
python3 large_scale/run_large_scale.py --mode sweep  --max-scenarios 200
python3 large_scale/run_large_scale.py --mode scale --message-target 10000 --seeds 1 2 3
```

## What it produces (`results/large_scale/<timestamp>/`)

| File | Part |
|---|---|
| `manifest.json` | 11 — seeds, versions, hardware, B3-availability |
| `per_message.csv` | 4/5 — every message: decision, masses, latencies, contract violations |
| `per_scenario.csv` | 4 — scenario-level scoring (the primary metric unit) |
| `metrics_by_family.csv` / `.tex` | 4/6 — acc/P/R/F1/FPR/FNR/detection/caution |
| `sweep_results.csv` | 3 — metrics per (vehicle_count × attacker_pct) |
| `resource_usage.json` | 4 — throughput, peak RSS, CPU count |
| `plots/` | 6 — confusion, ROC, PR, latency hist, throughput, trust-score dist, belief-mass dist, detection-vs-attacker-% |
| `FINAL_REPORT.md` | 7 — best config, largest weakness/bottleneck/FP source/FN source, pub recommendations — all auto-computed |

## Scale targets (Part 1)

- message counts: 100 / 500 / 1000 / 5000 / 10000 / 50000 (`--message-target`)
- vehicle counts: 5 / 10 / 25 / 50 / 100 / 250 / 500 / 1000 (swept)
- attacker %: 1 / 5 / 10 / 20 / 40 (swept)

Grids are combinatorially huge; `--max-scenarios` caps scenarios per seed and
`--cap-messages-per-scenario` bounds each window for tractable local runs.
Remove/raise the caps on a cluster for the full volumes.

## Two important methodology notes (read before citing numbers)

**1. Scenario-level scoring is primary.** The pipeline emits a decision over a
*window*, so scoring each windowed decision against a single message's
`is_attacker` flag miscounts honest vehicles inside an attack scenario as false
positives (an early version of this harness reported a spurious FPR of 0.71
exactly this way). The framework therefore scores at **scenario level**: truth =
"scenario contains an attacker"; prediction = "REJECT raised anywhere in the
scenario". Benign scenarios still contribute genuine false positives (a REJECT
in a fully-benign scenario). Locked by `tests/test_large_scale_framework.py`.

**2. Semantic verdicts are synthetic without the model.** When the B3 checkpoint
/ GPU are absent (as in this sandbox), semantic-attack scenarios inject a
**labelled synthetic** `p_malicious` from seeded profiles in
`semantic_attacks.py` — clearly tagged in the manifest, the report, and console.
The kinematic layers (PKI/B1/MBD/B2/CP) and the entire fusion/decision path are
real. Re-run on GPU with the materialized checkpoint to replace the semantic
column with measured values before citing any semantic-attack number. GPU/VRAM
utilization metrics likewise require that run.
```
```
