"""
b3_eval/run_latency.py
========================
Part 8: latency and memory profile for B3 in isolation (the stack-level
numbers live in validation/run_c1_c2_latency_throughput.py; this one
isolates the classifier so the bottleneck attribution is unambiguous).

Measures:
  cold start   -- process-fresh model+tokenizer load (the ~150s figure the
                  pipeline's preload_classifier() exists to keep OUT of
                  per-message latency)
  warm start   -- cached predictor retrieval
  single inference  -- batch_size=1, per-call p50/p90/p95/p99
  batch inference   -- sweep batch sizes, report per-item amortized cost
  memory       -- parameter count, peak host RAM delta, peak VRAM (CUDA)

Reports on whatever device is present (CPU if no CUDA) and labels it. Run
on the GPU box for the deployment-relevant numbers.

Run with:  python3 b3_eval/run_latency.py [--n 200] [--max-batch 32]
"""
from __future__ import annotations

import argparse
import pathlib
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from b3_eval._harness import (MODEL_DIR, checkpoint_status, env_manifest,
                                load_predictor, predict_texts, torch_status, write_json)

OUT = ROOT / "b3_eval" / "results"

SAMPLE = ("V2X Scene Report: context=urban. Ego vehicle: station 0x4A2 (type=passengerCar), "
          "speed=82 km/h, heading=145 deg. RSU-7: Toll gate ahead in 1.2km, all lanes "
          "operational. No peer reports contradict this advisory.")


def pctl(data, p):
    if not data:
        return float("nan")
    s = sorted(data)
    k = (len(s) - 1) * p
    f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--max-batch", type=int, default=32)
    args = ap.parse_args()

    manifest = env_manifest("b3_latency")
    ck, tt = checkpoint_status(), torch_status()

    print("=" * 78)
    print("B3 LATENCY & MEMORY PROFILE")
    print("=" * 78)
    if not ck["ok"] or not tt["ok"]:
        reason = ck.get("reason") or tt.get("reason")
        print(f"CANNOT RUN: {reason}")
        print("\nThis harness needs the materialized checkpoint + torch. On the GPU box:")
        print("  git lfs pull && python3 b3_eval/run_latency.py --n 500")
        write_json({"manifest": manifest, "status": "unavailable", "reason": reason},
                   OUT / "latency.json")
        return 0

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}" + (f" ({tt['device_name']})" if device == "cuda" else ""))

    # --- cold start (this process has not loaded it yet) ---
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    predictor, reason = load_predictor()
    cold_ms = (time.perf_counter() - t0) * 1000.0
    if predictor is None:
        print(f"load failed: {reason}")
        return 1
    print(f"Cold start (load + tokenizer): {cold_ms:.1f} ms")

    # --- warm start (cached retrieval) ---
    t0 = time.perf_counter()
    load_predictor()
    warm_ms = (time.perf_counter() - t0) * 1000.0
    print(f"Warm start (cached):           {warm_ms:.3f} ms")

    n_params = sum(p.numel() for p in predictor.model.parameters())
    print(f"Parameters: {n_params:,} ({n_params/1e6:.1f}M)")

    # --- warmup (excluded) ---
    for _ in range(10):
        predict_texts(predictor, [SAMPLE])

    # --- single inference ---
    singles = []
    for _ in range(args.n):
        t0 = time.perf_counter()
        predict_texts(predictor, [SAMPLE], batch_size=1)
        singles.append((time.perf_counter() - t0) * 1000.0)
    print(f"\nSingle inference over {args.n} calls (ms):")
    print(f"  p50={pctl(singles,.5):.2f}  p90={pctl(singles,.9):.2f}  "
          f"p95={pctl(singles,.95):.2f}  p99={pctl(singles,.99):.2f}  "
          f"mean={statistics.mean(singles):.2f}  max={max(singles):.2f}")

    # --- batch sweep ---
    print("\nBatch inference (amortized per item):")
    batch_results = {}
    bs = 1
    while bs <= args.max_batch:
        texts = [SAMPLE] * bs
        runs = []
        for _ in range(20):
            t0 = time.perf_counter()
            predict_texts(predictor, texts, batch_size=bs)
            runs.append((time.perf_counter() - t0) * 1000.0)
        per_item = statistics.mean(runs) / bs
        batch_results[bs] = {"batch_ms_mean": statistics.mean(runs), "per_item_ms": per_item,
                              "throughput_items_per_s": 1000.0 / per_item}
        print(f"  bs={bs:3d}  batch={statistics.mean(runs):7.2f} ms  "
              f"per-item={per_item:6.2f} ms  throughput={1000.0/per_item:8.1f} items/s")
        bs *= 2

    mem = {"parameters": n_params}
    if device == "cuda":
        mem["peak_vram_mb"] = torch.cuda.max_memory_allocated() / 1e6
        print(f"\nPeak VRAM: {mem['peak_vram_mb']:.1f} MB")
    try:
        import resource
        mem["peak_host_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        print(f"Peak host RSS: {mem['peak_host_rss_mb']:.1f} MB")
    except Exception:
        pass

    # ETSI CAM 10 Hz budget context
    p95 = pctl(singles, .95)
    print(f"\nETSI CAM context: at 10 Hz a message arrives every 100 ms. "
          f"B3 single-inference p95 = {p95:.2f} ms "
          f"({'within' if p95 < 100 else 'EXCEEDS'} the per-message budget on this device).")

    write_json({"manifest": manifest, "device": device, "cold_start_ms": cold_ms,
                 "warm_start_ms": warm_ms, "memory": mem,
                 "single_inference_ms": {"p50": pctl(singles, .5), "p90": pctl(singles, .9),
                                          "p95": p95, "p99": pctl(singles, .99),
                                          "mean": statistics.mean(singles), "max": max(singles)},
                 "batch": batch_results}, OUT / "latency.json")
    print(f"\nWritten: {OUT / 'latency.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
