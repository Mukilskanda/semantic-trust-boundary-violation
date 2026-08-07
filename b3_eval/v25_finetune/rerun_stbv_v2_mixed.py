#!/usr/bin/env python3
"""
b3_eval/v25_finetune/rerun_stbv_v2.py
========================================
Reruns stbv_bench/build_stbv_bench_v2.py (STBV-Bench v2 windowed,
multi-message corpus + full-pipeline evaluation; source of §Results RQ6:
attacker-sender recall, aggregate Decision Trust F1=0.517, threshold
sweep) with the ONLY change being B3's checkpoint.

build_stbv_bench_v2.py combines window CONSTRUCTION (deterministic given
--source/--seed/--radius/--min-cluster/--min-buckets -- confirmed by
reading the script: numpy/random seeded once at top from --seed, source
VeReMi files never touched) with pipeline EVALUATION (ISCEPipeline with
enable_b3=True) in one script. Re-running it with the same
--source/--n-windows/--seed/--radius/--min-cluster/--min-buckets as the
original run (results/stbv_bench_v2/manifest.json: n_windows=150,
seed=21, radius=100.0, min_cluster=3, min_buckets=2; source per the
script's own documented usage example, data/veremi_processed/ConstPos_1416,
the only source referenced anywhere in this repo's v2 docs) regenerates
BYTE-IDENTICAL windows and attack injections, differing only in which B3
checkpoint scores them -- verified after the fact by diffing
n_eligible_windows_found and attack_family_counts against the committed
manifest.json.

Uses the same isce_config.yaml-override monkeypatch as
rerun_paper_ablation.py. Output goes to a NEW directory
(results/stbv_bench_v2_finetuned/) -- the original, repo-committed
results/stbv_bench_v2/ (implicitly the "original" checkpoint's result) is
never touched.
"""
from __future__ import annotations
import importlib, pathlib, sys, tempfile
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
    original_model_path = data["b3_semantic_gate"]["model_path"]
    data["b3_semantic_gate"]["model_path"] = model_path
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    print(f"Config override: model_path {original_model_path!r} -> {model_path!r}")
    return tmp


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", choices=["original", "finetuned", "mixed"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default=str(ROOT / "data" / "veremi_processed" / "ConstPos_1416"))
    ap.add_argument("--n-windows", type=int, default=150)
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--radius", type=float, default=100.0)
    ap.add_argument("--min-cluster", type=int, default=3)
    ap.add_argument("--min-buckets", type=int, default=2)
    args = ap.parse_args()

    override_path = make_override_config(CHECKPOINTS[args.checkpoint])
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path

    sys.path.insert(0, str(ROOT / "stbv_bench"))
    if "build_stbv_bench_v2" in sys.modules:
        del sys.modules["build_stbv_bench_v2"]
    mod = importlib.import_module("build_stbv_bench_v2")

    sys.argv = [
        "build_stbv_bench_v2.py",
        "--source", args.source,
        "--n-windows", str(args.n_windows),
        "--radius", str(args.radius),
        "--min-cluster", str(args.min_cluster),
        "--min-buckets", str(args.min_buckets),
        "--seed", str(args.seed),
        "--out", args.out,
    ]
    print(f"[stbv_bench_v2] checkpoint={args.checkpoint} argv={sys.argv[1:]}")
    rc = mod.main()
    print(f"[done] rc={rc}")


if __name__ == "__main__":
    main()
