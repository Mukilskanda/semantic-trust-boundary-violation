"""
b3_eval/v25_finetune/run_full_evaluation.py
==============================================
Runs the ORIGINAL and FINE-TUNED B3 checkpoints through every benchmark
that is architecturally applicable to a text-only semantic classifier, on
IDENTICAL inputs, and writes a single comparison JSON.

Benchmarks run here (Phase 4 of the mission), with justification for each:

1. STBV-Bench v2.5 test split (held-out, template-disjoint)   -- primary
2. STBV-Bench v2.5 val split (for reference / calibration fit set)
3. STBV-Bench v1 (data/stbv_bench/v1/stbv_bench.jsonl)          -- cross-
   generation generalization / forgetting check (this corpus was NOT used
   for LoRA training at all)
4. Robustness suite (paraphrase/typo/homoglyph/instruction-hiding/
   context-poisoning/role-confusion/long-prompt-padding), adapted from
   b3_eval/run_robustness.py's perturbation generator
5. Calibration (temperature refit on v2.5 val, ECE/Brier on v2.5 test)
6. Latency / throughput / GPU memory (CUDA, matching deployment path)

Benchmarks NOT run here, with reasons (see FULL_EVALUATION_REPORT.md for
the complete writeup -- this is not silently skipping them):

- VeReMi (raw): VeReMi Extension is a purely kinematic dataset (position/
  speed/heading/timestamp), no natural-language field. B3 is a text
  classifier; there is nothing for it to score. VeReMi feeds B1/B2
  (kinematic layers), never B3, in this system's architecture
  (b3_eval/_harness.py, stbv_bench/build_and_run_veremi_kinematic_bench.py
  -- grep-verified, zero references to B3 or text rendering).
- Mixed-threat bench: built by stbv_bench/build_mixed_threat_bench.py,
  which requires the FULL multi-layer stack (B1+B2+CP+B3+TrustEngine via
  pipeline.orchestrator.ISCEPipeline) to construct and score -- it is a
  layer-INTERACTION benchmark, not a B3-alone benchmark. Its semantic-
  injection payloads are drawn from the same transformation engine as
  STBV-Bench v1/v2.5 (confirmed in B3_DATA_PROVENANCE_REPORT.md), so B3's
  text-level behavior on that payload distribution is already exercised by
  benchmarks 1 and 3 above.
- Ablation bench (stbv_bench/run_ablation.py): a LAYER ablation study
  (B1-only / B1+B2 / B1+B2+CP / B1+B2+CP+B3-unfused / full stack), not a
  B3-model ablation -- it answers "how much does the B3 layer contribute
  to the fused decision", which is orthogonal to "which B3 checkpoint is
  better" and requires the same full-stack orchestration as mixed-threat.

Run with: python3 b3_eval/v25_finetune/run_full_evaluation.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import torch

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from eval_common import (load_original, load_finetuned, load_jsonl, score_dataset,
                          prf1, roc_pr_auc, ORIGINAL_DIR, LORA_DIR)
from calibration import calibration_report

DATA = HERE / "data"
OUT_DIR = HERE / "results"
OUT_DIR.mkdir(exist_ok=True)

V1_BENCH = ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"
V1_SAMPLE_N = 5000   # fixed reproducible subsample of the 100k-row v1 corpus
V1_SEED = 42


def load_v1_sample():
    """STBV-Bench v1's rows (data/stbv_bench/v1/stbv_bench.jsonl) store a
    structured CAM/DENM `transformed_message` object plus per-window
    metadata (attack_family, expected_decision, severity) -- there is no
    flat natural-language `text` field. B3 only accepts rendered text, and
    that rendering (pipeline/synthesizer.py:synthesize_message) is a
    multi-vehicle WINDOW function (cluster -> text: ego CAM fields + peer
    reports + RSU messages via scene_context, with the target message as
    cluster[-1]), not a per-row pure function -- v1's rows are individual
    messages, not the windowed clusters that function expects. Confirmed by
    direct schema inspection: no 'text'/'rendered_text' key anywhere in a
    sampled row. Reconstructing per-row synthetic windows here would invent
    peer/RSU context that never existed in the original corpus, which would
    make any resulting B3 score meaningless (scoring text B3 never actually
    saw for this benchmark) rather than a genuine cross-generation check --
    so this is skipped with a stated reason instead of fabricated."""
    with open(V1_BENCH, encoding="utf-8") as f:
        first = json.loads(f.readline())
    return None, sorted(first.keys())


def per_family_breakdown(preds, labels, families):
    from collections import defaultdict
    by_fam = defaultdict(lambda: {"preds": [], "labels": []})
    for p, y, fam in zip(preds, labels, families):
        by_fam[fam]["preds"].append(p)
        by_fam[fam]["labels"].append(y)
    out = {}
    for fam, d in by_fam.items():
        out[fam] = prf1(d["preds"], d["labels"])
    return out


def eval_v25_split(model, split_name):
    rows = load_jsonl(DATA / f"{split_name}_split_full.jsonl")
    metrics, preds, labels = score_dataset(model, rows)
    pred_ids = [p["label_id"] for p in preds]
    families = [r["attack_family"] for r in rows]
    fam_metrics = per_family_breakdown(pred_ids, labels, families)
    return metrics, fam_metrics, preds, labels, rows


def eval_robustness(model):
    sys.path.insert(0, str(ROOT / "b3_eval"))
    import run_robustness as rb

    clean = model.predict([t for _, t in rb.SEEDS])
    per_family = {f: {"label_flips": 0, "conf_drift": [], "evasion": 0, "over_defense": 0,
                       "n_benign": 0, "n_malicious": 0} for f in rb.FAMILIES}
    for (truth, seed), c in zip(rb.SEEDS, clean):
        for fam, fn in rb.FAMILIES.items():
            variant = fn(seed)
            pv = model.predict([variant])[0]
            flipped = pv["label_id"] != c["label_id"]
            per_family[fam]["label_flips"] += int(flipped)
            per_family[fam]["conf_drift"].append(abs(pv["confidence"] - c["confidence"]))
            if truth == "BENIGN":
                per_family[fam]["n_benign"] += 1
                if pv["label_id"] == 1:
                    per_family[fam]["over_defense"] += 1
            else:
                per_family[fam]["n_malicious"] += 1
                if pv["label_id"] == 0:
                    per_family[fam]["evasion"] += 1
    n = len(rb.SEEDS)
    summary = {}
    for fam, d in per_family.items():
        summary[fam] = {
            "flip_rate": d["label_flips"] / n,
            "evasion_rate": d["evasion"] / d["n_malicious"] if d["n_malicious"] else None,
            "over_defense_fpr": d["over_defense"] / d["n_benign"] if d["n_benign"] else None,
            "mean_conf_drift": sum(d["conf_drift"]) / len(d["conf_drift"]),
        }
    return summary


def eval_latency(model, n=200):
    sample = ("V2X Scene Report: context=urban. Ego vehicle: station 0x4A2 (type=passengerCar), "
              "speed=82 km/h, heading=145 deg. RSU-7: Toll gate ahead in 1.2km, all lanes "
              "operational. No peer reports contradict this advisory.")
    device = model.device
    # warmup
    for _ in range(10):
        model.predict([sample], batch_size=1)
    if device == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    runs = []
    for _ in range(n):
        t0 = time.perf_counter()
        model.predict([sample], batch_size=1)
        if device == "cuda":
            torch.cuda.synchronize()
        runs.append((time.perf_counter() - t0) * 1000.0)
    s = sorted(runs)
    peak_vram_mb = (torch.cuda.max_memory_allocated() / 1e6) if device == "cuda" else None
    nparams = sum(p.numel() for p in model.model.parameters())
    return {
        "n": n, "p50_ms": s[len(s) // 2], "p90_ms": s[int(len(s) * .90)],
        "p95_ms": s[int(len(s) * .95)], "p99_ms": s[int(len(s) * .99)],
        "mean_ms": sum(runs) / len(runs), "peak_vram_mb": peak_vram_mb,
        "parameters": nparams, "throughput_single_msg_per_sec": 1000.0 / (sum(runs) / len(runs)),
    }


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    manifest = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device": device,
        "original_checkpoint": str(ORIGINAL_DIR),
        "finetuned_checkpoint": str(LORA_DIR),
    }
    print("Loading models...")
    orig = load_original(device=device)
    fine = load_finetuned(device=device)

    results = {"manifest": manifest, "models": {}}

    for model in (orig, fine):
        print(f"\n=== {model.name} ===")
        model_out = {}

        # 1+2. v2.5 test + val
        for split in ("test", "val"):
            metrics, fam_metrics, preds, labels, rows = eval_v25_split(model, split)
            model_out[f"stbv_v25_{split}"] = {"overall": metrics, "per_family": fam_metrics}
            print(f"  v2.5 {split}: F1={metrics['f1']*100:.2f} acc={metrics['accuracy']*100:.2f} "
                  f"P={metrics['precision']*100:.2f} R={metrics['recall']*100:.2f} "
                  f"ROC-AUC={metrics['roc_auc']:.4f}")

        # 3. v1 cross-generation -- see load_v1_sample() docstring for why
        # this is skipped-with-reason rather than run.
        _, v1_keys = load_v1_sample()
        model_out["stbv_v1_sample"] = {
            "status": "SKIPPED: no flat text field in this corpus (structured "
                      "CAM/DENM + window metadata; B3 text rendering is a "
                      "multi-vehicle window function, not reconstructible "
                      "per-row without fabricating peer/RSU context)",
            "row_keys_found": v1_keys}
        print(f"  v1 sample: SKIPPED (structured corpus, no flat text -- see report)")

        # 4. robustness
        rob = eval_robustness(model)
        model_out["robustness"] = rob
        mean_flip = sum(v["flip_rate"] for v in rob.values()) / len(rob)
        print(f"  robustness: mean flip_rate across {len(rob)} families = {mean_flip:.3f}")

        # 6. latency (CUDA path, deployment-relevant)
        lat = eval_latency(model, n=200)
        model_out["latency"] = lat
        print(f"  latency: p50={lat['p50_ms']:.2f}ms p95={lat['p95_ms']:.2f}ms "
              f"params={lat['parameters']/1e6:.1f}M peak_vram={lat['peak_vram_mb']}MB")

        results["models"][model.name] = model_out

        # keep raw logits for calibration (test + val)
        model_out["_raw_for_calibration"] = {}
        for split in ("val", "test"):
            rows = load_jsonl(DATA / f"{split}_split_full.jsonl")
            texts = [r["text"] for r in rows]
            labels = [int(r["label"]) for r in rows]
            preds = model.predict(texts, batch_size=32)
            logits = torch.tensor([p["logits"] for p in preds])
            model_out["_raw_for_calibration"][split] = {
                "logits": logits, "labels": torch.tensor(labels)}

    # Calibration: fit T per model on val, evaluate ECE/Brier pre/post on test
    print("\n=== Calibration ===")
    calib_results = {}
    for model in (orig, fine):
        raw = results["models"][model.name]["_raw_for_calibration"]
        cal = calibration_report(model.name, raw["val"]["logits"], raw["val"]["labels"],
                                  raw["test"]["logits"], raw["test"]["labels"])
        calib_results[model.name] = cal
        print(f"  {model.name}: T={cal['fitted_temperature']:.4f}  "
              f"test ECE {cal['test_set_held_out']['pre']['ece']:.4f} -> "
              f"{cal['test_set_held_out']['post']['ece']:.4f}  "
              f"Brier {cal['test_set_held_out']['pre']['brier']:.4f} -> "
              f"{cal['test_set_held_out']['post']['brier']:.4f}  "
              f"label_flips={cal['argmax_label_flips_on_test']}")
        del results["models"][model.name]["_raw_for_calibration"]
    results["calibration"] = calib_results

    (OUT_DIR / "full_evaluation.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nWritten: {OUT_DIR / 'full_evaluation.json'}")


if __name__ == "__main__":
    main()
