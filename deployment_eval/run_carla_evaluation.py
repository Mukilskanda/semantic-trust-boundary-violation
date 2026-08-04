#!/usr/bin/env python3
"""
run_carla_evaluation.py
========================
Live-CARLA deployment evaluation of the COMPLETE, frozen trust pipeline
(PKI -> B1/SCSV -> MBD -> B2/Explainability -> Cooperative Perception (CP)
-> Synthesizer -> B3 Semantic Trust Gate -> Trust Decision Engine),
driven by a REAL, running CARLA 0.9.16 server (verified installed at
C:\\Users\\mukil\\Downloads\\CARLA_0.9.16, launched headless via
`CarlaUE4.exe -RenderOffScreen`), not a replayed trace.

Must run under the Python 3.12 interpreter that has both the CARLA
0.9.16 client wheel AND this repo's torch/transformers stack installed
(C:\\Users\\mukil\\anaconda3\\python.exe in this environment -- the
project's default Python 3.13 interpreter cannot import `carla`, whose
wheel is cp312-only).

Does NOT modify B1/MBD/B2/CP/B3/the Trust Decision Engine, and does NOT
retrain B3. Every stage-level timing figure comes from orchestrator.py's
own pre-existing `latencies` dict.
"""
from __future__ import annotations
import gc
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from carla_bridge import CarlaSession, snapshot_vehicle, build_cam_message
from carla_scenarios import SCENARIOS

from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

N_VEHICLES = 8
TICKS_PER_SCENARIO = 40
FIXED_DELTA_SECONDS = 0.1  # 10 Hz CARLA physics/tick, matching ETSI's fastest permitted CAM rate
STATION_BASE = 2000


def main():
    import psutil
    import torch

    proc = psutil.Process(os.getpid())
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("Connecting to live CARLA server (127.0.0.1:2000)...")
    sess = CarlaSession(town="Town01", fixed_delta_seconds=FIXED_DELTA_SECONDS)
    sess.connect()
    print(f"Connected. CARLA server version: {sess.client.get_server_version()}, "
          f"map: {sess.world.get_map().name}")

    print(f"Spawning {N_VEHICLES} vehicles under autopilot...")
    vehicles = sess.spawn_traffic(N_VEHICLES, seed=7)
    print(f"Spawned {len(vehicles)} vehicles: {[v.type_id for v in vehicles]}")

    print("Warm-up: 50 ticks to let traffic manager settle before capturing a scene image...")
    for _ in range(50):
        sess.tick()

    scene_path = HERE / "carla_figures" / "fig0_carla_scene.png"
    print(f"Capturing CARLA scene screenshot -> {scene_path}")
    try:
        sess.get_spectator_camera_capture(str(scene_path), actor_to_follow=vehicles[0])
    except Exception as e:
        print(f"  [warn] scene capture failed (non-fatal): {e}")

    print("Constructing ISCEPipeline (loads B3 model)...")
    pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
    b3_load_ms = pipeline.b3_load_ms

    msg_counter: dict = {}
    all_rows = []
    dropped_count = 0
    offered_count = 0

    proc.cpu_percent(interval=None)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()

    eval_t0 = time.perf_counter()

    for scenario in SCENARIOS:
        name = scenario["name"]
        fn = scenario["fn"]
        state: dict = {}
        print(f"\n=== Scenario: {name} — {scenario['description']} ===")
        scenario_t0 = time.perf_counter()
        for tick_i in range(TICKS_PER_SCENARIO):
            sim_time_s = sess.tick()
            window, ground_truth = fn(sess, vehicles, sim_time_s, STATION_BASE, msg_counter, state)
            offered_count += len(window)

            t0 = time.perf_counter()
            res = pipeline.run(list(window), context="urban")
            wall_ms = (time.perf_counter() - t0) * 1000.0

            row = {
                "scenario": name,
                "ground_truth": ground_truth,
                "tick": tick_i,
                "sim_time_s": sim_time_s,
                "decision": res["decision"],
                "reason": res.get("reason"),
                "trust_score": res.get("fusion", {}).get("trust_score"),
                "b3_available": res.get("b3", {}).get("available"),
                "b3_label": res.get("b3", {}).get("label"),
                "b3_confidence": res.get("b3", {}).get("confidence"),
                "wall_ms": wall_ms,
                "window_size": len(window),
                **{k: v for k, v in res["latencies"].items()},
            }
            if tick_i % 10 == 0 or tick_i == TICKS_PER_SCENARIO - 1:
                row["cpu_percent_snapshot"] = proc.cpu_percent(interval=None)
                row["rss_mb_snapshot"] = proc.memory_info().rss / 1e6
                if device.type == "cuda":
                    row["gpu_allocated_mb_snapshot"] = torch.cuda.memory_allocated() / 1e6
                print(f"  [{name} {tick_i}/{TICKS_PER_SCENARIO}] t={sim_time_s:.1f}s "
                      f"wall_ms={wall_ms:.1f} decision={res['decision']} "
                      f"(gt={ground_truth}) cpu%={row.get('cpu_percent_snapshot')} "
                      f"rss_mb={row.get('rss_mb_snapshot', 0):.1f}")
            all_rows.append(row)
        scenario_wall_s = time.perf_counter() - scenario_t0
        print(f"  scenario '{name}' wall time: {scenario_wall_s:.1f}s "
              f"({TICKS_PER_SCENARIO / scenario_wall_s:.2f} msg/s)")

    eval_wall_s = time.perf_counter() - eval_t0
    final_cpu_percent = proc.cpu_percent(interval=None)
    final_rss_mb = proc.memory_info().rss / 1e6
    peak_gpu_mb = (torch.cuda.max_memory_allocated() / 1e6) if device.type == "cuda" else None

    # Synchronous single-consumer architecture: every offered target message
    # IS processed (pipeline.run() blocks until done), so true dropped_count
    # is 0 by construction -- disclosed explicitly, not silently omitted.
    # A separate ANALYTICAL queueing estimate (bounded-queue-at-measured-
    # throughput-vs-offered-load) is computed in the report script, reusing
    # these same measured numbers, and is clearly labeled as an estimate,
    # not a second live measurement.
    manifest = {
        "experiment": "carla_deployment_evaluation",
        "simulator": f"CARLA {sess.client.get_server_version()} (headless, -RenderOffScreen), "
                      f"map={sess.world.get_map().name}",
        "carla_client_version": sess.client.get_client_version(),
        "carla_server_version": sess.client.get_server_version(),
        "n_vehicles": len(vehicles),
        "vehicle_types": [v.type_id for v in vehicles],
        "ticks_per_scenario": TICKS_PER_SCENARIO,
        "fixed_delta_seconds": FIXED_DELTA_SECONDS,
        "n_scenarios": len(SCENARIOS),
        "scenario_names": [s["name"] for s in SCENARIOS],
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "b3_load_ms": b3_load_ms,
        "dropped_messages": dropped_count,
        "offered_messages": offered_count,
        "note": "Single persistent ISCEPipeline instance (enable_mbd/cp/b3=True), "
                "live CARLA vehicle actors under autopilot each tick. No retraining, "
                "no architecture modification. Attack scenarios inject falsified "
                "message CONTENT only, never falsified CARLA physics.",
    }

    out = {
        "manifest": manifest,
        "eval_wall_seconds": eval_wall_s,
        "final_cpu_percent": final_cpu_percent,
        "final_rss_mb": final_rss_mb,
        "peak_gpu_allocated_mb": peak_gpu_mb,
        "per_message": all_rows,
    }
    out_path = HERE / "carla_results" / "carla_deployment_eval_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nEval wall time: {eval_wall_s:.1f}s for {len(all_rows)} messages "
          f"({len(all_rows) / eval_wall_s:.2f} msg/s)")
    print(f"Wrote {out_path}")

    print("Cleaning up CARLA actors...")
    sess.cleanup()
    print("Done.")


if __name__ == "__main__":
    main()
