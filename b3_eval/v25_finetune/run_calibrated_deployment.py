#!/usr/bin/env python3
"""Rerun deployment_eval (SUMO FCD replay) with the FROZEN calibrated
deployment package (finetuned LoRA-merged checkpoint, T=3.3242247104644775,
high=0.79, medium=0.50). Reuses rerun_deployment_eval.py's iter_fcd_events/
make_flat_message helpers verbatim; builds its own config override (model +
risk_thresholds) and forces predictor.temperature the same way
run_calibrated_cp.py / rerun_recalibrated.py do (inference.py reads
temperature from a hardcoded path, not the override file)."""
from __future__ import annotations
import json, os, pathlib, sys, tempfile, time
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "b3_eval" / "v25_finetune"))
import rerun_deployment_eval as rde

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged"
HIGH, MEDIUM, TEMP = 0.79, 0.5, 3.3242247104644775
FCD_PATH = rde.FCD_PATH
MESSAGE_BUDGET = rde.MESSAGE_BUDGET
WINDOW_SIZE = rde.WINDOW_SIZE

real_config = ROOT / "isce_config.yaml"
data = yaml.safe_load(real_config.read_text(encoding="utf-8"))
data["b3_semantic_gate"]["model_path"] = MODEL_PATH
data["b3_semantic_gate"]["risk_thresholds"]["high"] = HIGH
data["b3_semantic_gate"]["risk_thresholds"]["medium"] = MEDIUM
tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
tmp.write_text(yaml.safe_dump(data), encoding="utf-8")
print(f"Config override: model={MODEL_PATH}, high={HIGH}, medium={MEDIUM}, T(forced)={TEMP}, file={tmp}")

import pipeline.b3_bridge as b3_bridge
b3_bridge._DEFAULT_CONFIG_PATH = tmp
b3_bridge.preload_classifier(tmp)
inst = b3_bridge._CLASSIFIER_INSTANCE
old_t = inst.predictor.temperature
inst.predictor.temperature = float(TEMP)
print(f"Forced predictor.temperature: {old_t} -> {TEMP}")

from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV
import psutil, torch

proc = psutil.Process(os.getpid())
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

concurrency_by_timestep = {}
for t, veh_id, *_ in rde.iter_fcd_events(FCD_PATH):
    concurrency_by_timestep[t] = concurrency_by_timestep.get(t, 0) + 1
max_concurrent = max(concurrency_by_timestep.values())
mean_concurrent = sum(concurrency_by_timestep.values()) / len(concurrency_by_timestep)
n_timesteps_total = len(concurrency_by_timestep)
n_messages_total = sum(concurrency_by_timestep.values())

print(f"Full trace: {n_timesteps_total} timesteps, {n_messages_total} messages, "
      f"max_concurrent={max_concurrent}, mean_concurrent={mean_concurrent:.1f}")
print(f"[checkpoint=calibrated] Replaying first {MESSAGE_BUDGET} messages through the live pipeline...")

pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)

window = []
per_message = []
proc.cpu_percent(interval=None)
if device.type == "cuda":
    torch.cuda.reset_peak_memory_stats()

replay_t0 = time.perf_counter()
for i, (t_sec, veh_id, x, y, speed_mps, angle_deg) in enumerate(rde.iter_fcd_events(FCD_PATH)):
    if i >= MESSAGE_BUDGET:
        break
    msg = rde.make_flat_message(t_sec, veh_id, x, y, speed_mps, angle_deg)
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
        "checkpoint": "calibrated_deployment",
        "model_path": MODEL_PATH,
        "risk_thresholds": {"high": HIGH, "medium": MEDIUM},
        "temperature_scaling_forced": TEMP,
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
        "note": "Rerun of deployment_eval/run_deployment_evaluation.py with the FROZEN calibrated "
                "deployment package (finetuned LoRA-merged checkpoint + recalibrated thresholds/"
                "temperature). Same FCD trace, message budget, window size, pipeline flags as the "
                "original and uncalibrated-finetuned runs. isce_config.yaml on disk untouched.",
    },
    "replay_wall_seconds": replay_wall_s,
    "final_cpu_percent": final_cpu_percent,
    "final_rss_mb": final_rss_mb,
    "peak_gpu_allocated_mb": peak_gpu_mb,
    "per_message": per_message,
}
out_path = ROOT / "deployment_eval" / "results" / "deployment_eval_results_calibrated.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nReplay wall time: {replay_wall_s:.1f}s for {len(per_message)} messages "
      f"({len(per_message)/replay_wall_s:.2f} msg/s)")
print(f"[done] Wrote {out_path}")
