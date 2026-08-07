#!/usr/bin/env python3
"""
b3_eval/v25_finetune/rerun_deployment_eval.py
================================================
Reruns deployment_eval/run_deployment_evaluation.py (SUMO FCD replay
through the full, live ISCEPipeline) with the ONLY change being B3's
checkpoint, using the exact same monkeypatch technique as
rerun_paper_ablation.py (isce_config.yaml is never written to; a temp
copy with only `model_path` changed is used instead).

NOTE ON A PRIOR SESSION'S CLAIM: DEPENDENCY_TABLE.md (row 22) states
`traci`/`carla` were not importable in this environment and marks SUMO
deployment as infeasible. Re-verified in this session: `import traci`
now succeeds (Eclipse SUMO 1.27.0 is installed, sumo binary on PATH,
`C:\\Program Files (x86)\\Eclipse\\Sumo\\tools\\traci` importable) and the
harness (deployment_eval/run_deployment_evaluation.py) runs the existing
FCD trace (deployment_eval/sumo_scenario/fcd_output.xml) through a live
pipeline -- it does not itself invoke `traci`/`carla` at runtime (the
FCD trace was pre-generated), so SUMO deployment replay IS feasible here.
CARLA remains genuinely infeasible (`import carla` still fails, no
CARLA module installed) -- that part of row 22/23 stands.

Writes to a NEW file (deployment_eval/results/deployment_eval_results_finetuned.json)
-- the original checkpoint's result file
(deployment_eval/results/deployment_eval_results.json) is never touched.
"""
from __future__ import annotations
import argparse, json, os, pathlib, sys, tempfile, time
import xml.etree.ElementTree as ET
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

CHECKPOINTS = {
    "original": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3",
    "finetuned": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged",
    "mixed": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged",
}

HERE = ROOT / "deployment_eval"
FCD_PATH = HERE / "sumo_scenario" / "fcd_output.xml"
MESSAGE_BUDGET = 2000
WINDOW_SIZE = 5


def make_override_config(model_path: str) -> pathlib.Path:
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    original_model_path = data["b3_semantic_gate"]["model_path"]
    data["b3_semantic_gate"]["model_path"] = model_path
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    print(f"Config override: model_path {original_model_path!r} -> {model_path!r}")
    return tmp


def iter_fcd_events(path):
    for event, elem in ET.iterparse(str(path), events=("end",)):
        if elem.tag == "timestep":
            t = float(elem.get("time"))
            for v in elem.findall("vehicle"):
                yield (t, v.get("id"), float(v.get("x")), float(v.get("y")),
                       float(v.get("speed")), float(v.get("angle")))
            elem.clear()


def make_flat_message(t_sec, veh_id, x, y, speed_mps, angle_deg):
    return {
        "sender": int(veh_id) if veh_id.isdigit() else abs(hash(veh_id)) % 100000,
        "x": x, "y": y,
        "speed": speed_mps * 3.6,
        "heading": angle_deg % 360.0,
        "timestamp": t_sec * 1000.0,
        "source": "sumo_replay",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", choices=["original", "finetuned", "mixed"], required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    override_path = make_override_config(CHECKPOINTS[args.checkpoint])
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path

    from pipeline.orchestrator import ISCEPipeline
    from b1_scsv.scsv import SCSV
    import psutil, torch

    proc = psutil.Process(os.getpid())
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    concurrency_by_timestep = {}
    for t, veh_id, *_ in iter_fcd_events(FCD_PATH):
        concurrency_by_timestep[t] = concurrency_by_timestep.get(t, 0) + 1
    max_concurrent = max(concurrency_by_timestep.values())
    mean_concurrent = sum(concurrency_by_timestep.values()) / len(concurrency_by_timestep)
    n_timesteps_total = len(concurrency_by_timestep)
    n_messages_total = sum(concurrency_by_timestep.values())

    print(f"Full trace: {n_timesteps_total} timesteps, {n_messages_total} messages, "
          f"max_concurrent={max_concurrent}, mean_concurrent={mean_concurrent:.1f}")
    print(f"[checkpoint={args.checkpoint}] Replaying first {MESSAGE_BUDGET} messages through the live pipeline...")

    pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)

    window = []
    per_message = []
    proc.cpu_percent(interval=None)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()

    replay_t0 = time.perf_counter()
    for i, (t_sec, veh_id, x, y, speed_mps, angle_deg) in enumerate(iter_fcd_events(FCD_PATH)):
        if i >= MESSAGE_BUDGET:
            break
        msg = make_flat_message(t_sec, veh_id, x, y, speed_mps, angle_deg)
        window.append(msg)
        if len(window) > WINDOW_SIZE:
            window = window[-WINDOW_SIZE:]

        t0 = time.perf_counter()
        res = pipeline.run(list(window), context="urban")
        wall_ms = (time.perf_counter() - t0) * 1000.0

        row = {
            "i": i, "sim_time_s": t_sec, "vehicle_id": veh_id,
            "decision": res["decision"], "wall_ms": wall_ms,
            **{k: v for k, v in res["latencies"].items()},
        }
        if i % 200 == 0 or i == MESSAGE_BUDGET - 1:
            row["cpu_percent_snapshot"] = proc.cpu_percent(interval=None)
            row["rss_mb_snapshot"] = proc.memory_info().rss / 1e6
            if device.type == "cuda":
                row["gpu_allocated_mb_snapshot"] = torch.cuda.memory_allocated() / 1e6
            print(f"  [{i}/{MESSAGE_BUDGET}] t={t_sec:.1f}s wall_ms={wall_ms:.1f} "
                  f"decision={res['decision']} cpu%={row.get('cpu_percent_snapshot')} "
                  f"rss_mb={row.get('rss_mb_snapshot', 0):.1f}")
        per_message.append(row)

    replay_wall_s = time.perf_counter() - replay_t0
    final_cpu_percent = proc.cpu_percent(interval=None)
    final_rss_mb = proc.memory_info().rss / 1e6
    peak_gpu_mb = (torch.cuda.max_memory_allocated() / 1e6) if device.type == "cuda" else None

    out = {
        "manifest": {
            "experiment": "deployment_evaluation",
            "checkpoint": args.checkpoint,
            "model_path": CHECKPOINTS[args.checkpoint],
            "simulator": "SUMO 1.27.0 (headless), FCD replay",
            "simulators_unavailable": {"CARLA": "not installed in this environment (no `carla` module)",
                                        "ROS2": "not installed in this environment (no `ros2` executable)"},
            "message_budget": MESSAGE_BUDGET,
            "window_size": WINDOW_SIZE,
            "full_trace_n_messages": n_messages_total,
            "full_trace_n_timesteps": n_timesteps_total,
            "full_trace_max_concurrent_vehicles": max_concurrent,
            "full_trace_mean_concurrent_vehicles": mean_concurrent,
            "device": str(device),
            "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
            "note": "Rerun of the original deployment_eval/run_deployment_evaluation.py harness "
                     "with ONLY the B3 checkpoint swapped (same FCD trace, same message budget, "
                     "same window size, same pipeline flags). isce_config.yaml on disk untouched.",
        },
        "replay_wall_seconds": replay_wall_s,
        "final_cpu_percent": final_cpu_percent,
        "final_rss_mb": final_rss_mb,
        "peak_gpu_allocated_mb": peak_gpu_mb,
        "per_message": per_message,
    }
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nReplay wall time: {replay_wall_s:.1f}s for {len(per_message)} messages "
          f"({len(per_message)/replay_wall_s:.2f} msg/s)")
    print(f"[done] Wrote {out_path}")


if __name__ == "__main__":
    main()
