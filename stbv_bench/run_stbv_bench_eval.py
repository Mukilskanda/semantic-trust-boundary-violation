#!/usr/bin/env python3
"""
stbv_bench/run_stbv_bench_eval.py
===================================
Evaluates the REAL, frozen ISCEPipeline (pipeline/orchestrator.py, B1->MBD->
B2->CP->B3->TrustDecisionEngine, unmodified) against a built STBV-Bench
benchmark. This is a deliberately separate step from build_stbv_bench.py so
"what the benchmark contains" and "what a system decides about it" never
get conflated, and so any OTHER system can be scored against the same
benchmark file without regenerating it.

Per the mission's central principle -- "the contribution is the COMPLETE
TRUST ARCHITECTURE, not the semantic classifier" -- this script scores
DECISION TRUST: the pipeline's final ACCEPT/CAUTION/REJECT output vs. each
sample's is_attacker/expected_decision, and records WHICH layer(s)
contributed to that decision (fusion["contributors"]), not merely B3's raw
label. This directly extends (does not replace) the pattern already used by
semantic_evaluation/semantic_attack_evaluation.py and evaluation/runner.py.

Usage:
  python3 stbv_bench/run_stbv_bench_eval.py \
      --bench data/stbv_bench/v1/stbv_bench.jsonl \
      --out results/stbv_bench/v1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV


def _positive(decision: str) -> bool:
    """Positive-class convention (matches evaluation/metrics_and_outputs.py
    and semantic_evaluation/semantic_attack_evaluation.py): REJECT or
    CAUTION both count as "the system raised a concern"; only ACCEPT is a
    clean pass. CAUTION is reported separately too (caution_rate), per this
    repo's established convention that CAUTION is not itself a detection
    claim."""
    return decision in ("REJECT", "CAUTION")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", required=True, help="Path to a stbv_bench.jsonl file")
    ap.add_argument("--out", required=True, help="Output directory for results")
    ap.add_argument("--limit", type=int, default=0, help="Evaluate only the first N samples (0 = all)")
    args = ap.parse_args()

    bench_path = pathlib.Path(args.bench)
    samples = []
    with bench_path.open("r", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))
    if args.limit:
        samples = samples[: args.limit]

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True)

    rows = []
    t_start = time.perf_counter()
    for i, s in enumerate(samples):
        msg = s["transformed_message"]
        res = pipeline.run([msg], context="urban")
        decision = res["decision"]
        contributors = res["fusion"].get("contributors", [])
        b3 = res.get("b3") or {}
        rows.append({
            "sample_id": s["sample_id"],
            "attack_family": s["attack_family"],
            "severity": s["severity"],
            "expected_decision": s["expected_decision"],
            "is_attacker": s["transformed_message"].get("is_attacker", s["attack_family"] != "benign_control"),
            "decision": decision,
            "contributors": ",".join(contributors),
            "b3_available": b3.get("available"),
            "b3_label": b3.get("label"),
            "b3_confidence": b3.get("confidence"),
            "trust_score": res["fusion"].get("trust_score"),
            "total_ms": res["latencies"].get("total_ms"),
            "bridge_ms": res["latencies"].get("bridge_ms"),
        })
        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(samples)} evaluated...")
    total_wall_s = time.perf_counter() - t_start

    # --- Decision Trust metrics (architecture-level, not B3-only) ---
    tp = fp = fn = tn = 0
    caution_n = 0
    by_family = defaultdict(lambda: {"n": 0, "tp": 0, "fp": 0, "fn": 0, "tn": 0, "caution": 0})
    contributor_counts = defaultdict(int)

    for r in rows:
        truth = bool(r["is_attacker"])
        pred_positive = _positive(r["decision"])
        fam = r["attack_family"]
        by_family[fam]["n"] += 1
        if r["decision"] == "CAUTION":
            caution_n += 1
            by_family[fam]["caution"] += 1
        if pred_positive and truth:
            tp += 1; by_family[fam]["tp"] += 1
        elif pred_positive and not truth:
            fp += 1; by_family[fam]["fp"] += 1
        elif not pred_positive and truth:
            fn += 1; by_family[fam]["fn"] += 1
        else:
            tn += 1; by_family[fam]["tn"] += 1
        for c in r["contributors"].split(","):
            if c:
                contributor_counts[c] += 1

    n = len(rows) or 1
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if (precision == precision and recall == recall and precision + recall) else float("nan"))
    accuracy = (tp + tn) / n
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")

    latencies = sorted(r["total_ms"] for r in rows if r["total_ms"] is not None)

    def pct(p):
        if not latencies:
            return None
        idx = min(int(len(latencies) * p), len(latencies) - 1)
        return latencies[idx]

    summary = {
        "benchmark": "STBV-Bench",
        "n_samples": len(rows),
        "wall_clock_seconds": total_wall_s,
        "decision_trust_metrics": {
            "accuracy": accuracy, "precision": precision, "recall": recall,
            "f1": f1, "fpr": fpr, "caution_rate": caution_n / n,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        },
        "per_family": {
            fam: {
                **d,
                "recall": (d["tp"] / (d["tp"] + d["fn"]) if (d["tp"] + d["fn"]) else float("nan")),
                "caution_rate": d["caution"] / d["n"] if d["n"] else float("nan"),
            }
            for fam, d in by_family.items()
        },
        "contributor_counts": dict(contributor_counts),
        "latency_ms": {
            "mean": sum(latencies) / len(latencies) if latencies else None,
            "p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99),
            "max": max(latencies) if latencies else None,
        },
        "scoring_convention": (
            "positive = REJECT or CAUTION (system raised a concern); CAUTION is "
            "reported separately (caution_rate) and is NOT itself counted as a "
            "confident detection claim, matching evaluation/metrics_and_outputs.py's "
            "established convention."
        ),
    }

    (out_dir / "stbv_bench_results.json").write_text(json.dumps(summary, indent=2, default=str))

    import csv
    with (out_dir / "stbv_bench_per_message.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n[done] {len(rows)} samples evaluated in {total_wall_s:.1f}s")
    print(f"Decision Trust: accuracy={accuracy:.3f} precision={precision:.3f} "
          f"recall={recall:.3f} f1={f1:.3f} fpr={fpr:.3f} caution_rate={caution_n/n:.3f}")
    print(f"Contributors observed: {dict(contributor_counts)}")
    print(f"-> {out_dir / 'stbv_bench_results.json'}")
    print(f"-> {out_dir / 'stbv_bench_per_message.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
