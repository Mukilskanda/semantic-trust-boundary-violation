#!/usr/bin/env python3
"""
deployment_eval/run_carla_multirun.py
======================================
Statistically rigorous replacement for the single-seed / single-town live
CARLA deployment evaluation.

Design:
  * 3 CARLA towns  x  5 random seeds  =  15 independent runs
  * every run replays ALL 10 scenarios (40 ticks each) => 400 messages/run
  * 6,000 pipeline invocations total
  * NOTHING in the frozen pipeline is changed: same ISCEPipeline, same
    B1/MBD/B2/CP/B3/TrustDecisionEngine, same scenario definitions. Only
    the town and the traffic-spawn seed vary.

Never cherry-picks: every run is written to disk and the aggregate step
averages over ALL runs, reporting 95% CIs. There is no "best run" concept
anywhere in this file.

Must run under the CARLA-compatible interpreter (Python 3.12 + carla wheel):
    C:\\Users\\mukil\\anaconda3\\python.exe deployment_eval/run_carla_multirun.py
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from carla_bridge import CarlaSession
from carla_scenarios import SCENARIOS

from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

# Town03 was the originally-intended third town but crashes the 0.9.16 server
# reproducibly during load_world() on this hardware, with the full 5,920 MiB
# of VRAM free (verified twice, once with an empty GPU). Town02 and Town05
# both load to ~2.1 GiB and run normally, so the town set is Town01/02/05.
# This substitution is a documented hardware/simulator limitation, not a
# selection made after seeing any result.
TOWNS = ["Town01", "Town02", "Town05"]
SEEDS = [1, 2, 3, 4, 5]
N_VEHICLES = 8
TICKS_PER_SCENARIO = 40
FIXED_DELTA = 0.1
STATION_BASE = 2000

OUT = HERE / "carla_multirun"
OUT.mkdir(parents=True, exist_ok=True)


class GPUSampler(threading.Thread):
    """Background nvidia-smi sampler -- utilization % and MiB used."""

    def __init__(self, period=1.0):
        super().__init__(daemon=True)
        self.period, self.samples = period, []
        self._stop_evt = threading.Event()

    def run(self):
        while not self._stop_evt.is_set():
            try:
                r = subprocess.run(
                    ["nvidia-smi",
                     "--query-gpu=utilization.gpu,memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5)
                u, m = r.stdout.strip().split("\n")[0].split(",")
                self.samples.append((float(u), float(m)))
            except Exception:
                pass
            self._stop_evt.wait(self.period)

    def stop(self):
        self._stop_evt.set()

    def stats(self):
        if not self.samples:
            return {}
        u = [s[0] for s in self.samples]
        m = [s[1] for s in self.samples]
        return {"gpu_util_mean": sum(u) / len(u), "gpu_util_max": max(u),
                "gpu_mem_used_mean_mib": sum(m) / len(m),
                "gpu_mem_used_max_mib": max(m), "n_gpu_samples": len(u)}


def run_one(sess, pipeline, town, seed, proc, torch):
    """One (town, seed) run: all 10 scenarios, 400 messages."""
    vehicles = sess.spawn_traffic(N_VEHICLES, seed=seed)
    for _ in range(50):                      # let traffic manager settle
        sess.tick()

    msg_counter, rows = {}, []
    dropped = offered = 0
    proc.cpu_percent(interval=None)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    t0 = time.perf_counter()
    for scenario in SCENARIOS:
        state = {}
        for tick_i in range(TICKS_PER_SCENARIO):
            sim_t = sess.tick()
            window, gt = scenario["fn"](sess, vehicles, sim_t, STATION_BASE,
                                        msg_counter, state)
            offered += len(window)
            t_msg = time.perf_counter()
            res = pipeline.run(list(window), context="urban")
            wall = (time.perf_counter() - t_msg) * 1000.0
            rows.append({
                "town": town, "seed": seed, "scenario": scenario["name"],
                "ground_truth": gt, "tick": tick_i, "decision": res["decision"],
                "trust_score": res.get("fusion", {}).get("trust_score"),
                "b3_label": res.get("b3", {}).get("label"),
                "b3_available": res.get("b3", {}).get("available"),
                "wall_ms": wall,
                **{k: v for k, v in res["latencies"].items()},
            })
    wall_s = time.perf_counter() - t0

    run = {
        "town": town, "seed": seed,
        "n_messages": len(rows), "wall_seconds": wall_s,
        "throughput_msg_s": len(rows) / wall_s,
        "cpu_percent": proc.cpu_percent(interval=None),
        "rss_mb": proc.memory_info().rss / 1e6,
        "peak_gpu_alloc_mb": (torch.cuda.max_memory_allocated() / 1e6
                              if torch.cuda.is_available() else None),
        "offered_messages": offered, "dropped_messages": dropped,
        "n_vehicles_spawned": len(vehicles),
        "per_message": rows,
    }
    # release actors so the next seed starts from a clean world
    for a in list(sess.actors):
        try:
            if a.is_alive:
                a.destroy()
        except Exception:
            pass
    sess.actors.clear()
    return run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--towns", nargs="*", default=TOWNS)
    ap.add_argument("--seeds", nargs="*", type=int, default=SEEDS)
    args = ap.parse_args()

    import psutil
    import torch
    proc = psutil.Process(os.getpid())

    print(f"Plan: {len(args.towns)} towns x {len(args.seeds)} seeds = "
          f"{len(args.towns)*len(args.seeds)} runs, "
          f"{len(args.towns)*len(args.seeds)*len(SCENARIOS)*TICKS_PER_SCENARIO} messages")

    print("Constructing ISCEPipeline once (B3 loaded once, reused across all runs)")
    pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True,
                            enable_b3=True)

    manifest = {
        "experiment": "carla_multirun_deployment",
        "towns": args.towns, "seeds": args.seeds,
        "n_vehicles": N_VEHICLES, "ticks_per_scenario": TICKS_PER_SCENARIO,
        "fixed_delta_seconds": FIXED_DELTA,
        "scenarios": [s["name"] for s in SCENARIOS],
        "b3_load_ms": pipeline.b3_load_ms,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "note": "Frozen pipeline unchanged; only town and spawn seed vary. "
                "All runs retained; aggregate averages over every run.",
        "runs_completed": [], "runs_failed": [],
    }

    for town in args.towns:
        print(f"\n{'='*62}\n=== TOWN {town} ===\n{'='*62}")
        sess = None
        try:
            sess = CarlaSession(town=town, fixed_delta_seconds=FIXED_DELTA)
            sess.connect()
            print(f"  loaded: {sess.world.get_map().name}")
        except Exception as e:
            print(f"  [FAIL] cannot load {town}: {e}")
            manifest["runs_failed"].append({"town": town, "seed": None,
                                            "error": f"town load failed: {e}"})
            continue

        for seed in args.seeds:
            tag = f"{town}_seed{seed}"
            path = OUT / f"run_{tag}.json"
            if path.exists():
                print(f"  [skip] {tag} already present")
                manifest["runs_completed"].append(tag)
                continue
            print(f"  --- {tag} ---")
            gpu = GPUSampler(); gpu.start()
            try:
                run = run_one(sess, pipeline, town, seed, proc, torch)
                gpu.stop(); gpu.join(timeout=3)
                run["gpu"] = gpu.stats()
                path.write_text(json.dumps(run), encoding="utf-8")
                manifest["runs_completed"].append(tag)
                print(f"      {run['n_messages']} msgs, "
                      f"{run['throughput_msg_s']:.2f} msg/s, "
                      f"gpu_util={run['gpu'].get('gpu_util_mean', float('nan')):.0f}%, "
                      f"rss={run['rss_mb']:.0f}MB")
            except Exception as e:
                gpu.stop()
                print(f"      [FAIL] {tag}: {e}")
                manifest["runs_failed"].append({"town": town, "seed": seed,
                                                "error": str(e)})
        try:
            sess.cleanup()
        except Exception:
            pass

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    print(f"\nCompleted {len(manifest['runs_completed'])} runs, "
          f"{len(manifest['runs_failed'])} failed -> {OUT}")


if __name__ == "__main__":
    main()
