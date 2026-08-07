#!/usr/bin/env python3
"""
b3_eval/v25_finetune/recal_infer_v1.py
=========================================
Recalibration support rerun: re-runs the SAME full-pipeline code path as
rerun_paper_ablation.py's config-4/5 shared call (ISCEPipeline with
enable_mbd=True, enable_cp=True, enable_b3=True) on STBV-Bench v1's first
10,000 samples (identical slice used by the existing ablation CSVs), for
the FINE-TUNED checkpoint only (the original checkpoint's numbers are
untouched -- no recalibration is being applied to it).

Unlike rerun_paper_ablation.py, this script also captures B3's raw
label + confidence + p_malicious (SemanticResult's own exact p_malicious
field: p_malicious = confidence if predicted label is malicious, else
1 - confidence) per message. The existing ablation_config_4/5.csv files
only stored "confidence of whichever label was predicted" plus the
final policy decision, which is NOT sufficient to correctly re-derive
decisions under NEW risk-band thresholds (recovering the predicted label
from (decision, confidence) alone is ambiguous for every CAUTION row,
which is most of them) -- hence this rerun.

Same override mechanism as rerun_paper_ablation.py (temp isce_config.yaml
copy with only model_path changed; real isce_config.yaml on disk never
touched). Threshold values used for the "decision" column in the output
here are still the OLD production thresholds (0.85/0.60) -- purely
informational; recalibrated decisions are recomputed from the saved
label/confidence/p_malicious downstream, in Python, without needing
another rerun.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import tempfile
import time

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged"


def make_override_config(model_path: str) -> pathlib.Path:
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["b3_semantic_gate"]["model_path"] = model_path
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    return tmp


def main():
    out_path = ROOT / "b3_eval" / "v25_finetune" / "results" / "v1_finetuned_p_malicious.csv"
    limit = 10000
    bench = ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"

    override_path = make_override_config(MODEL_PATH)
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path

    from pipeline.orchestrator import ISCEPipeline
    from b1_scsv.scsv import SCSV

    samples = []
    with open(bench, "r", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))
    samples = samples[:limit]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["sample_id", "attack_family", "is_attacker", "b3_label", "b3_confidence",
                  "p_malicious", "decision", "b1_fatal"]
    f = open(out_path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()

    t0 = time.perf_counter()
    for i, s in enumerate(samples):
        msg = s["transformed_message"]
        is_attacker = bool(msg.get("is_attacker", s["attack_family"] != "benign_control"))
        family = s["attack_family"]

        pipeline45 = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
        res45 = pipeline45.run([msg], context="urban")
        b1_dict = res45["b1"]
        b3_result = res45["b3"] or {}
        w.writerow({
            "sample_id": s["sample_id"], "attack_family": family, "is_attacker": is_attacker,
            "b3_label": b3_result.get("label"), "b3_confidence": b3_result.get("confidence"),
            "p_malicious": b3_result.get("p_malicious"),
            "decision": res45["decision"], "b1_fatal": bool(b1_dict.get("fatal")),
        })

        if (i + 1) % 200 == 0:
            elapsed = time.perf_counter() - t0
            rate = (i + 1) / elapsed
            eta = (len(samples) - (i + 1)) / rate if rate > 0 else float("nan")
            print(f"  {i+1}/{len(samples)} ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)", flush=True)

    f.close()
    total = time.perf_counter() - t0
    print(f"[done] {len(samples)} samples in {total:.1f}s -> {out_path}")


if __name__ == "__main__":
    sys.exit(main())
