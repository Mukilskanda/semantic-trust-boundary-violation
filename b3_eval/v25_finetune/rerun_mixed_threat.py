#!/usr/bin/env python3
"""
b3_eval/v25_finetune/rerun_mixed_threat.py
=============================================
Reruns stbv_bench/build_mixed_threat_bench.py (the shared-scene case
study behind stbv_paper.tex Table tab:coverage: "semantic-attacker
recall 70.3%", "kinematic-attacker recall 90.3%", DEPENDENCY_TABLE.md
row 9) with the ONLY change being B3's checkpoint, using the same
isce_config.yaml-override monkeypatch as rerun_paper_ablation.py.

Same determinism argument as rerun_stbv_v2.py: window construction is
seeded (--seed 31) and independent of B3; re-running with the same
--source/--n-windows/--seed/--radius/--min-cluster/--min-buckets as the
committed results/mixed_threat/manifest.json reproduces the identical
windows/compositions, differing only in which checkpoint scores them.

Output goes to a NEW directory (results/mixed_threat_finetuned/) --
results/mixed_threat/ (the original checkpoint's committed result) is
untouched.
"""
from __future__ import annotations
import argparse, importlib, pathlib, sys, tempfile
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

CHECKPOINTS = {
    "original": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3",
    "finetuned": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged",
}


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", choices=["original", "finetuned"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default=str(ROOT / "data" / "veremi_processed" / "ConstPos_1416"))
    ap.add_argument("--n-windows", type=int, default=120)
    ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--radius", type=float, default=100.0)
    ap.add_argument("--min-cluster", type=int, default=3)
    ap.add_argument("--min-buckets", type=int, default=2)
    args = ap.parse_args()

    override_path = make_override_config(CHECKPOINTS[args.checkpoint])
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path

    sys.path.insert(0, str(ROOT / "stbv_bench"))
    if "build_mixed_threat_bench" in sys.modules:
        del sys.modules["build_mixed_threat_bench"]
    mod = importlib.import_module("build_mixed_threat_bench")

    sys.argv = [
        "build_mixed_threat_bench.py",
        "--source", args.source,
        "--n-windows", str(args.n_windows),
        "--radius", str(args.radius),
        "--min-cluster", str(args.min_cluster),
        "--min-buckets", str(args.min_buckets),
        "--seed", str(args.seed),
        "--out", args.out,
    ]
    print(f"[mixed_threat] checkpoint={args.checkpoint} argv={sys.argv[1:]}")
    rc = mod.main()
    print(f"[done] rc={rc}")


if __name__ == "__main__":
    main()
