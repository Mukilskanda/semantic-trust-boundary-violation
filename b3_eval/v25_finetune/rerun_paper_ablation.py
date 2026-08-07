"""
b3_eval/v25_finetune/rerun_paper_ablation.py
================================================
Re-runs the manuscript's headline experiment (stbv_paper.tex RQ1/RQ2/
"Layer Ablation", Table tab:main_ablation, Figs fig_confusion/
fig_per_family/fig_ablation_summary/fig_transitions) on STBV-Bench v1
(n=10,000) with the ONLY change being B3's checkpoint.

This is a thin wrapper around stbv_bench/run_ablation.py's exact logic
(same CONFIGS, same b3_only_decision rule, same per-sample fresh-pipeline
construction for configs 1-3, same shared config-4/5 pipeline call) --
duplicated here (not import-and-call) only so the B3 checkpoint override
can be injected without editing isce_config.yaml (which is shared,
production config used by every other script in this repo) or any
pipeline/b1/b2/cp source file.

The override mechanism: pipeline.b3_bridge reads its model_path from
isce_config.yaml via a module-level `_DEFAULT_CONFIG_PATH` constant, read
at CALL time (not import time) by `_load_b3_config()`/`preload_classifier()`.
Monkeypatching that one module attribute to point at a temporary YAML
copy (identical to isce_config.yaml except `model_path`) is therefore
sufficient, and reverts automatically when this process exits -- the real
isce_config.yaml on disk is never written to.

Run with:
  python3 b3_eval/v25_finetune/rerun_paper_ablation.py --checkpoint original --out .../orig
  python3 b3_eval/v25_finetune/rerun_paper_ablation.py --checkpoint finetuned --out .../finetuned
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
import tempfile
import time

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

CHECKPOINTS = {
    "original": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3",
    "finetuned": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged",
    "mixed": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged",
}


def make_override_config(model_path: str) -> pathlib.Path:
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "model_path" in data.get("b3_semantic_gate", {}), "isce_config.yaml schema changed unexpectedly"
    original_model_path = data["b3_semantic_gate"]["model_path"]
    data["b3_semantic_gate"]["model_path"] = model_path
    # Everything else (risk_thresholds, calibration temperature, max_length,
    # ensembling flags, etc.) is copied VERBATIM from the real config --
    # zero other values are touched.
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    print(f"Config override: model_path {original_model_path!r} -> {model_path!r}")
    print(f"All other isce_config.yaml keys copied unchanged. Temp config: {tmp}")
    return tmp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", choices=["original", "finetuned", "mixed"], required=True)
    ap.add_argument("--bench", default=str(ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=10000)
    args = ap.parse_args()

    override_path = make_override_config(CHECKPOINTS[args.checkpoint])
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path
    print(f"pipeline.b3_bridge._DEFAULT_CONFIG_PATH patched (process-local only; "
          f"real isce_config.yaml on disk untouched).")

    from pipeline.orchestrator import ISCEPipeline
    from b1_scsv.scsv import SCSV
    from trust_engine.policy import TrustPolicy
    from trust_engine.models import SemanticRisk

    _POLICY = TrustPolicy()

    def b3_only_decision(b1_dict, b3_result):
        if b1_dict.get("fatal"):
            return "REJECT"
        risk = _POLICY.classify_semantic_risk(b3_result)
        if risk == SemanticRisk.HIGH:
            return "REJECT"
        if risk in (SemanticRisk.MEDIUM, SemanticRisk.LOW):
            return "CAUTION"
        return "ACCEPT"

    CONFIGS = {
        1: dict(enable_mbd=False, enable_cp=False, enable_b3=False, label="B1 only"),
        2: dict(enable_mbd=True, enable_cp=False, enable_b3=False, label="B1+B2"),
        3: dict(enable_mbd=True, enable_cp=True, enable_b3=False, label="B1+B2+CP"),
    }

    samples = []
    with open(args.bench, "r", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))
    samples = samples[: args.limit]

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = ["sample_id", "attack_family", "is_attacker", "decision",
                  "raw_score", "contributors", "decision_source"]
    files, writers = {}, {}
    for cfg_id in (1, 2, 3, 4, 5):
        f = open(out_dir / f"ablation_config_{cfg_id}.csv", "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        files[cfg_id], writers[cfg_id] = f, w

    t_start = time.perf_counter()
    for i, s in enumerate(samples):
        msg = s["transformed_message"]
        is_attacker = bool(msg.get("is_attacker", s["attack_family"] != "benign_control"))
        family = s["attack_family"]

        for cfg_id in (1, 2, 3):
            cfg = CONFIGS[cfg_id]
            pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=cfg["enable_mbd"],
                                     enable_cp=cfg["enable_cp"], enable_b3=cfg["enable_b3"])
            res = pipeline.run([msg], context="urban")
            writers[cfg_id].writerow({
                "sample_id": s["sample_id"], "attack_family": family, "is_attacker": is_attacker,
                "decision": res["decision"], "raw_score": res["fusion"].get("trust_score"),
                "contributors": ",".join(res["fusion"].get("contributors", [])), "decision_source": "fusion"})

        pipeline45 = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
        res45 = pipeline45.run([msg], context="urban")
        b1_dict = res45["b1"]
        b3_result = res45["b3"] or {}
        decision4 = b3_only_decision(b1_dict, b3_result)
        writers[4].writerow({
            "sample_id": s["sample_id"], "attack_family": family, "is_attacker": is_attacker,
            "decision": decision4, "raw_score": b3_result.get("confidence"),
            "contributors": "B3" if b3_result.get("available") else "none", "decision_source": "b3_raw"})
        writers[5].writerow({
            "sample_id": s["sample_id"], "attack_family": family, "is_attacker": is_attacker,
            "decision": res45["decision"], "raw_score": res45["fusion"].get("trust_score"),
            "contributors": ",".join(res45["fusion"].get("contributors", [])), "decision_source": "fusion"})

        if (i + 1) % 200 == 0:
            elapsed = time.perf_counter() - t_start
            rate = (i + 1) / elapsed
            eta_s = (len(samples) - (i + 1)) / rate if rate > 0 else float("nan")
            print(f"  {i + 1}/{len(samples)} ({elapsed:.0f}s elapsed, ~{eta_s:.0f}s remaining)", flush=True)

    for f in files.values():
        f.close()
    total_s = time.perf_counter() - t_start
    print(f"\n[done] checkpoint={args.checkpoint} {len(samples)} samples x 5 configs in {total_s:.1f}s")
    (out_dir / "run_manifest.json").write_text(json.dumps({
        "checkpoint": args.checkpoint, "model_path": CHECKPOINTS[args.checkpoint],
        "bench": args.bench, "n_samples": len(samples), "total_seconds": total_s}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
