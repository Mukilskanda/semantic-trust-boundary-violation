"""
large_scale/run_large_scale.py
================================
Parts 4, 5, 6, 7 driver for the large-scale evaluation. Composes the frozen
stack (via evaluation.runner / pipeline.ISCEPipeline) with the scale grid
(large_scale.scaling) and semantic attack library
(large_scale.semantic_attacks). Nothing in the architecture is modified.

Per message it records: decision, ground truth, per-layer latency, per-layer
contract conformance (Part 5), final trust_score and belief masses (Part 4).
Semantic-attack scenarios additionally inject a labelled p_malicious into
B3's result on the B3-absent path (clearly tagged synthetic).

Outputs (Part 6) under results/large_scale/<run_id>/:
  manifest.json, per_message.csv, metrics_by_family.csv/.tex,
  sweep_results.csv, resource_usage.json, and plots/ (confusion, ROC, PR,
  latency histogram, throughput, trust-score dist, belief-mass dist,
  attacker-pct and scale curves). Part 7 report: FINAL_REPORT.md.

Usage:
  python3 large_scale/run_large_scale.py --quick
  python3 large_scale/run_large_scale.py --message-target 1000 --seeds 1 2 3
  python3 large_scale/run_large_scale.py --mode sweep --max-scenarios 200
  python3 large_scale/run_large_scale.py --mode scale --message-target 10000
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pipeline.orchestrator as _orch
from evaluation.manifest import build_manifest, write_manifest
from evaluation.runner import _build_pipeline, _verify_contracts
from large_scale import scaling, semantic_attacks as sem
from large_scale.reporting import write_all_outputs
from scenario_generation.generator import HeldOutScenarioGenerator

try:
    import psutil
    _PROC = psutil.Process()
except Exception:
    _PROC = None


def _b3_available() -> bool:
    from pipeline.b3_bridge import preload_classifier, classify_text
    preload_classifier()
    return bool(classify_text("probe").get("available"))


def _patch_semantic_b3(scaled: scaling.ScaledScenario, rng: random.Random):
    """On the B3-absent path, inject a labelled synthetic SemanticResult so
    semantic-attack scenarios exercise the real fusion path. Returns a
    restore fn. When the real model is present this is NOT called."""
    attack = sem.generate(
        rng.choice(sem.malicious_families()) if scaled.base.expected_label == "MALICIOUS"
        else "benign_control", rng)
    # attacker aims to stay under `semantic_confidence`; clamp the sampled p
    p = sem.sample_p_malicious(attack, rng)
    if attack.is_malicious:
        p = min(p, scaled.semantic_confidence + rng.uniform(-0.05, 0.05))
    p = min(max(p, 0.001), 0.999)
    label = "MALICIOUS" if p >= 0.5 else "BENIGN"
    conf = max(p, 1 - p)
    from pipeline.b3_bridge import B3RiskPolicy
    rl = B3RiskPolicy().classify(label, conf)
    result = {"available": True, "label": label, "confidence": conf, "risk_level": rl,
              "status": "SYNTHETIC-LARGE-SCALE", "p_malicious": p}
    original = _orch.classify_text
    _orch.classify_text = lambda text, metadata=None: dict(result)
    return (lambda: setattr(_orch, "classify_text", original)), attack, p


def scenario_level_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse per-message rows to one row per scenario. This is the
    methodologically correct scoring unit: the pipeline emits a decision over
    a WINDOW, so scoring each windowed decision against a single message's
    is_attacker flag conflates 'benign vehicle inside an attack scenario' with
    'benign scenario' -- inflating apparent false positives. At scenario level:
      truth   = the scenario contains an attacker (expected_label == MALICIOUS)
      predict = the stack raised REJECT on ANY message in the scenario
                (an attack detected anywhere in the window is a detection)
    Benign scenarios contribute the false-positive signal correctly (a REJECT
    anywhere in a fully-benign scenario is a genuine FP).
    """
    from collections import defaultdict
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("decision") in ("ACCEPT", "CAUTION", "REJECT"):
            groups[r["scenario_id"]].append(r)
    out = []
    for sid, grp in groups.items():
        family = grp[0]["family"]
        truth = family != "benign"
        any_reject = any(g["decision"] == "REJECT" for g in grp)
        any_flag = any(g["decision"] in ("REJECT", "CAUTION") for g in grp)
        out.append({"scenario_id": sid, "family": family, "truth_attacker": truth,
                     "decision": "REJECT" if any_reject else ("CAUTION" if any_flag else "ACCEPT"),
                     "vehicle_count": grp[0].get("vehicle_count"),
                     "attacker_pct": grp[0].get("attacker_pct"),
                     "density": grp[0].get("density"),
                     "trust_score": min(g.get("trust_score", 1.0) for g in grp)})
    return out


def run(scaled_list: List[scaling.ScaledScenario], b3_available: bool,
        gen_seed: int, cap_messages_per_scenario: int) -> List[Dict[str, Any]]:
    gen = HeldOutScenarioGenerator(seed=gen_seed)
    rows: List[Dict[str, Any]] = []
    for scaled in scaled_list:
        cfg = scaled.base
        try:
            messages = gen.generate_scenario(cfg)
        except Exception as e:
            rows.append({"scenario_id": cfg.scenario_id, "family": cfg.scenario_family,
                          "decision": "GEN_ERROR", "error": f"{type(e).__name__}: {e}",
                          "truth_attacker": cfg.expected_label == "MALICIOUS"})
            continue
        messages = messages[:cap_messages_per_scenario]
        is_semantic = cfg.scenario_family in ("benign",) or True  # every scenario also carries a B3 verdict
        pipe, restore = _build_pipeline("full")
        sem_restore = None
        rng = random.Random(cfg.seed)
        if not b3_available:
            sem_restore, attack, pmal = _patch_semantic_b3(scaled, rng)
        window: List[Dict[str, Any]] = []
        try:
            for i, m in enumerate(messages):
                window.append(m)
                if len(window) > 12:
                    window = window[-12:]   # bounded window for tractability
                truth = bool(m.get("is_attacker", False))
                row = {"scenario_id": cfg.scenario_id, "family": cfg.scenario_family,
                        "vehicle_count": cfg.vehicle_count, "attacker_pct": scaled.attacker_pct,
                        "density": cfg.traffic_density, "context": cfg.road_context,
                        "comm_range_m": scaled.comm_range_m, "frequency_hz": scaled.frequency_hz,
                        "semantic_confidence": scaled.semantic_confidence,
                        "msg_index": i, "truth_attacker": truth, "seed": cfg.seed}
                try:
                    r = pipe.run(list(window), context=cfg.road_context)
                    fd = r["fusion"]
                    row.update({"decision": r["decision"],
                                 "trust_score": fd["trust_score"],
                                 "b3_available": r["b3"]["available"],
                                 "latencies": r["latencies"],
                                 "contract_violations": _verify_contracts(r),
                                 "m_A": fd["details"].get("ds_crypto_mass", {}).get("m_A"),
                                 "m_notA": fd["details"].get("ds_crypto_mass", {}).get("m_not_A"),
                                 "m_theta": fd["details"].get("ds_crypto_mass", {}).get("m_theta"),
                                 "sem_m_notA": fd["details"].get("ds_semantic_mass", {}).get("m_not_A"),
                                 "attack_detected": fd["attack_detected"]})
                except Exception as e:
                    row.update({"decision": "ERROR", "error": f"{type(e).__name__}: {e}",
                                 "latencies": {}, "contract_violations": ["EXCEPTION"]})
                rows.append(row)
        finally:
            restore()
            if sem_restore:
                sem_restore()
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["scale", "sweep"], default="scale")
    ap.add_argument("--message-target", type=int, default=1000,
                    choices=scaling.MESSAGE_TARGETS + [t for t in (200,) ])
    ap.add_argument("--seeds", type=int, nargs="+", default=[101])
    ap.add_argument("--max-scenarios", type=int, default=120,
                    help="cap scenarios per seed for tractability (grids are huge)")
    ap.add_argument("--cap-messages-per-scenario", type=int, default=24)
    ap.add_argument("--out", default=str(ROOT / "results" / "large_scale"))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if args.quick:
        args.seeds = args.seeds[:1]
        args.max_scenarios = 24
        args.message_target = 200
        args.cap_messages_per_scenario = 12

    run_id = time.strftime("%Y%m%d-%H%M%S")
    out_dir = pathlib.Path(args.out) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    b3_available = _b3_available()
    peak_rss_mb = 0.0
    t0 = time.perf_counter()

    all_rows: List[Dict[str, Any]] = []
    for seed in args.seeds:
        if args.mode == "scale":
            grid = scaling.build_scale_grid(seed, args.message_target)
        else:
            grid = scaling.build_sweep_grid(seed, message_target=args.message_target)
        random.Random(seed).shuffle(grid)
        grid = grid[: args.max_scenarios]
        est = scaling.estimate_messages(grid)
        print(f"[seed {seed}] {args.mode}: {len(grid)} scenarios, ~{est} messages "
              f"(capped at {args.cap_messages_per_scenario}/scenario)")
        rows = run(grid, b3_available, gen_seed=seed,
                   cap_messages_per_scenario=args.cap_messages_per_scenario)
        all_rows.extend(rows)
        if _PROC:
            peak_rss_mb = max(peak_rss_mb, _PROC.memory_info().rss / 1e6)
    wall = time.perf_counter() - t0

    n_msgs = sum(1 for r in all_rows if r.get("decision") not in ("GEN_ERROR",))
    throughput = n_msgs / wall if wall > 0 else float("nan")
    resource = {"wall_seconds": wall, "messages_processed": n_msgs,
                "throughput_msgs_per_s": throughput,
                "peak_host_rss_mb": peak_rss_mb,
                "cpu_count": (psutil.cpu_count() if _PROC else None),
                "b3_available": b3_available,
                "note": ("GPU/VRAM metrics require the real B3 model on CUDA hardware; "
                         "unavailable in this run" if not b3_available else "")}
    (out_dir / "resource_usage.json").write_text(json.dumps(resource, indent=2))

    manifest = build_manifest("large_scale_evaluation",
                               config={"mode": args.mode, "message_target": args.message_target,
                                        "seeds": args.seeds, "max_scenarios": args.max_scenarios,
                                        "cap_messages_per_scenario": args.cap_messages_per_scenario,
                                        "b3_available": b3_available,
                                        "b3_note": (None if b3_available else
                                                    "B3 model absent: semantic verdicts are LABELLED "
                                                    "SYNTHETIC (large_scale.semantic_attacks profiles), "
                                                    "not real inference. Kinematic layers are real.")},
                               seeds=args.seeds)
    write_manifest(out_dir, manifest)

    scen_rows = scenario_level_rows(all_rows)
    write_all_outputs(all_rows, resource, out_dir, b3_available, scenario_rows=scen_rows)

    n_err = sum(1 for r in all_rows if r.get("decision") in ("ERROR", "GEN_ERROR"))
    print(f"\nDone in {wall:.1f}s. {n_msgs} messages, {throughput:.0f} msg/s, "
          f"peak RSS {peak_rss_mb:.0f} MB. Errors: {n_err}.")
    print(f"Results: {out_dir}")
    if not b3_available:
        print("NOTE: B3 semantic verdicts are LABELLED SYNTHETIC in this run (no GPU/model). "
              "Kinematic layers (PKI/B1/MBD/B2/CP) are real.")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
