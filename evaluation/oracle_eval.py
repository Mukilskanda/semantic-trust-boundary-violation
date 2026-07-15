"""
evaluation/oracle_eval.py
===========================
Phase 3/4: end-to-end integration evaluation against the frozen Phase 1
v2 oracle (evaluation/oracle.py). REUSES evaluation/runner.py's real
pipeline construction (_build_pipeline) and scenario generation
(generate_scenarios_for_seed) -- does not reimplement pipeline
execution, per the project's no-duplicate-functionality discipline.

Scope of THIS run (stated honestly, not glossed over):
  - Kinematic families only (replay, sybil, collusion, fabrication,
    manipulation) -- these are what scenario_generation/generator.py
    produces and what runs end-to-end WITHOUT the B3 checkpoint.
  - B3 in this environment is the StubSemanticClassifier fallback
    (available=False) because pytorch_model.bin is a git-lfs pointer,
    not real weights, in this artifact. Every row's b3_available is
    recorded explicitly; no semantic-family or B3-detection claim is
    made from this run. Re-run on the GPU machine with `git lfs pull`
    for real B3 numbers.
  - "full" configuration only in this pass (ablation ×7 configs is a
    trivial sweep once this scoring layer exists -- left as a flag,
    --configs, for a follow-up run once you review these numbers).

Usage:
  python3 evaluation/oracle_eval.py --seeds 1 2 3 4 5 --message-count 20
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.runner import _build_pipeline, generate_scenarios_for_seed
from evaluation.oracle import oracle_for


LAYER_FIRED_EXTRACTORS = {
    "pki": lambda r: (r.get("pki") is not None and bool(r["pki"].get("revoked") or r["pki"].get("compromised"))),
    "b1": lambda r: bool(r["b1"].get("fatal")) or not bool(r["b1"].get("valid", True)),
    "mbd": lambda r: (r.get("mbd") is not None and not bool(r["mbd"].get("passed", True))),
    "cp": lambda r: (r.get("cp") is not None and not bool(r["cp"].get("cp_pass", True))),
    "b3": lambda r: (r.get("b3") is not None and r["b3"].get("available") and
                      str(r["b3"].get("label", "")).lower() not in ("benign", "", "none")),
}

DECISION_MAP = {"ACCEPT": "ACCEPT", "CAUTION": "CAUTION", "REJECT": "REJECT"}


def run_oracle_eval(seeds: List[int], message_count: int, out_dir: pathlib.Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    skipped_no_oracle = 0

    for seed in seeds:
        pairs = generate_scenarios_for_seed(seed, out_dir / "scenarios", message_count=message_count)
        pipe, restore = _build_pipeline("full")
        try:
            for cfg, messages in pairs:
                oracle = oracle_for(cfg.scenario_family, cfg.attack_type)
                if oracle is None:
                    skipped_no_oracle += 1
                    continue
                window: List[Dict[str, Any]] = []
                for i, m in enumerate(messages):
                    window.append(m)
                    truth_attacker = bool(m.get("is_attacker", False))
                    try:
                        r = pipe.run(list(window), context=cfg.road_context)
                    except Exception as e:
                        rows.append({
                            "seed": seed, "scenario_id": cfg.scenario_id,
                            "family": cfg.scenario_family, "attack_type": cfg.attack_type,
                            "msg_index": i, "truth_attacker": truth_attacker,
                            "error": f"{type(e).__name__}: {e}",
                        })
                        continue

                    fired = {layer: bool(fn(r)) for layer, fn in LAYER_FIRED_EXTRACTORS.items()
                              if layer == "b1" or r.get(layer) is not None or layer in ("pki", "b3")}
                    fired = {}
                    for layer, fn in LAYER_FIRED_EXTRACTORS.items():
                        try:
                            fired[layer] = bool(fn(r))
                        except Exception:
                            fired[layer] = False

                    decision = r["decision"].name if hasattr(r["decision"], "name") else str(r["decision"])
                    final_attack_detected = bool(r["fusion"].get("attack_detected", False))

                    earliest_fired = None
                    for layer in ["pki", "b1", "mbd", "cp", "b3"]:
                        if fired.get(layer):
                            earliest_fired = layer
                            break

                    rows.append({
                        "seed": seed, "scenario_id": cfg.scenario_id,
                        "family": cfg.scenario_family, "attack_type": cfg.attack_type,
                        "msg_index": i, "truth_attacker": truth_attacker,
                        "oracle_earliest": oracle.earliest_layer,
                        "oracle_expected_decision": oracle.expected_decision,
                        "fired_pki": fired["pki"], "fired_b1": fired["b1"],
                        "fired_mbd": fired["mbd"], "fired_cp": fired["cp"],
                        "fired_b3": fired["b3"],
                        "b3_available": r["b3"].get("available") if r.get("b3") else None,
                        "earliest_actual": earliest_fired,
                        "decision": decision,
                        "attack_detected": final_attack_detected,
                        "trust_score": r["fusion"].get("trust_score"),
                        "latency_total_ms": r["latencies"].get("total_ms"),
                    })
        finally:
            restore()

    return {"rows": rows, "skipped_no_oracle": skipped_no_oracle}


def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_rows = [r for r in rows if "error" not in r]
    error_rows = [r for r in rows if "error" in r]

    # 1. Per-layer detection accuracy (did the oracle's earliest layer fire
    #    on truth-attacker messages of that family; benign should_not fire)
    per_layer = defaultdict(lambda: {"tp": 0, "fn": 0, "fp_on_benign": 0, "tn": 0})
    for r in valid_rows:
        layer = r["oracle_earliest"]
        if layer == "none":
            continue
        fired = r.get(f"fired_{layer}")
        if fired is None:
            continue
        if r["truth_attacker"]:
            if fired:
                per_layer[layer]["tp"] += 1
            else:
                per_layer[layer]["fn"] += 1
        else:
            if fired:
                per_layer[layer]["fp_on_benign"] += 1
            else:
                per_layer[layer]["tn"] += 1

    # 2. Earliest-correct-detection accuracy: did the FIRST layer to fire
    #    match the oracle's designated earliest layer, on true attacks
    earliest_correct, earliest_total = 0, 0
    for r in valid_rows:
        if not r["truth_attacker"] or r["oracle_earliest"] == "none":
            continue
        earliest_total += 1
        if r["earliest_actual"] == r["oracle_earliest"]:
            earliest_correct += 1

    # 3. Defense-in-depth recovery: oracle's earliest layer MISSED, but a
    #    later layer (any fired_* True after it) or final decision still
    #    caught it (REJECT/CAUTION, not ACCEPT)
    recovered, missed_no_recovery, earliest_hit = 0, 0, 0
    for r in valid_rows:
        if not r["truth_attacker"] or r["oracle_earliest"] == "none":
            continue
        layer = r["oracle_earliest"]
        fired = r.get(f"fired_{layer}")
        if fired:
            earliest_hit += 1
            continue
        # earliest missed -- did final decision still catch it?
        if r["decision"] in ("REJECT", "CAUTION"):
            recovered += 1
        else:
            missed_no_recovery += 1

    # 4. Failure propagation: earliest missed AND final decision ACCEPT
    #    (already counted as missed_no_recovery above; reported explicitly)

    # 5. Fusion effectiveness: on true attacks, is attack_detected True
    #    or decision != ACCEPT
    fusion_catches, fusion_misses = 0, 0
    for r in valid_rows:
        if not r["truth_attacker"]:
            continue
        if r["attack_detected"] or r["decision"] != "ACCEPT":
            fusion_catches += 1
        else:
            fusion_misses += 1

    # 6. Final decision accuracy vs oracle's expected_decision
    decision_correct, decision_total = 0, 0
    confusion = defaultdict(int)  # (expected, actual) -> count
    for r in valid_rows:
        decision_total += 1
        confusion[(r["oracle_expected_decision"], r["decision"])] += 1
        if r["oracle_expected_decision"] == r["decision"]:
            decision_correct += 1

    # 8/9. Latency
    lat_values = [r["latency_total_ms"] for r in valid_rows if r.get("latency_total_ms") is not None]
    lat_summary = {}
    if lat_values:
        s = sorted(lat_values)
        n = len(s)
        lat_summary = {
            "n": n, "mean_ms": sum(s) / n,
            "p50_ms": s[n // 2], "p95_ms": s[int(n * 0.95) if n > 1 else 0],
            "max_ms": s[-1],
        }

    return {
        "n_valid_rows": len(valid_rows),
        "n_error_rows": len(error_rows),
        "per_layer_detection": {
            layer: {**v, "recall": v["tp"] / (v["tp"] + v["fn"]) if (v["tp"] + v["fn"]) else None,
                    "fpr_on_benign": v["fp_on_benign"] / (v["fp_on_benign"] + v["tn"]) if (v["fp_on_benign"] + v["tn"]) else None}
            for layer, v in per_layer.items()
        },
        "earliest_correct_detection_accuracy": earliest_correct / earliest_total if earliest_total else None,
        "earliest_correct_n": earliest_total,
        "defense_in_depth": {
            "earliest_layer_hit": earliest_hit,
            "earliest_missed_but_recovered_downstream": recovered,
            "earliest_missed_no_recovery_failure_propagation": missed_no_recovery,
        },
        "fusion_effectiveness": {
            "catches": fusion_catches, "misses": fusion_misses,
            "rate": fusion_catches / (fusion_catches + fusion_misses) if (fusion_catches + fusion_misses) else None,
        },
        "final_decision_accuracy_vs_oracle": decision_correct / decision_total if decision_total else None,
        "confusion_matrix_expected_vs_actual": {f"{k[0]}->{k[1]}": v for k, v in confusion.items()},
        "latency_ms": lat_summary,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument("--message-count", type=int, default=20)
    ap.add_argument("--out", type=str, default="results/oracle_eval")
    args = ap.parse_args()

    out_dir = ROOT / args.out
    result = run_oracle_eval(args.seeds, args.message_count, out_dir)
    metrics = compute_metrics(result["rows"])

    (out_dir / "per_message_rows.json").write_text(json.dumps(result["rows"], indent=2, default=str))
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))

    print(json.dumps(metrics, indent=2, default=str))
    print(f"\nskipped_no_oracle={result['skipped_no_oracle']}")
    print(f"Full rows: {out_dir / 'per_message_rows.json'}")
    print(f"Metrics:   {out_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()