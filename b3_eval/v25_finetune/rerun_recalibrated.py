#!/usr/bin/env python3
"""
b3_eval/v25_finetune/rerun_recalibrated.py
==============================================
Re-runs STBV-Bench v2 (build_stbv_bench_v2.py) and the mixed-threat case
study (build_mixed_threat_bench.py) for the FINE-TUNED checkpoint with
the RECALIBRATED B3 risk-band thresholds and temperature applied --
arm (c) of the three-way comparison, for benchmarks whose per-message
CSVs only store the final fused decision/trust_score (not raw B3
confidence), so a threshold-only Python recompute (as done for v1 and
the external corpus) is not possible; a real rerun is required.

Uses the exact same isce_config.yaml-override monkeypatch as
rerun_stbv_v2.py / rerun_mixed_threat.py (temp copy of isce_config.yaml
with model_path, risk_thresholds.high, risk_thresholds.medium, and
temperature_scaling overridden; every other key copied verbatim; the
real isce_config.yaml on disk is never written to). Window
construction/injection is unaffected (same seed/source/params as the
committed original runs) -- only B3's checkpoint and post-hoc
calibration/threshold config differ from the arm-(b) "finetuned + old
thresholds" runs already on disk.
"""
from __future__ import annotations
import argparse, importlib, json, pathlib, sys, tempfile
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged"


def make_override_config(model_path: str, high: float, medium: float, temperature: float) -> pathlib.Path:
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["b3_semantic_gate"]["model_path"] = model_path
    data["b3_semantic_gate"]["risk_thresholds"]["high"] = high
    data["b3_semantic_gate"]["risk_thresholds"]["medium"] = medium
    data["b3_semantic_gate"]["temperature_scaling"] = temperature
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    print(f"Config override: model_path->{model_path}, high={high}, medium={medium}, "
          f"temperature_scaling={temperature}. All other isce_config.yaml keys unchanged. "
          f"Temp file: {tmp}")
    return tmp


def _force_temperature(b3_bridge, override_path, temperature):
    """SemanticGatePredictor reads temperature_scaling from a HARDCODED
    relative path to the real isce_config.yaml on disk (inference.py
    __init__: os.path.join(dirname(__file__), '../../../isce_config.yaml')),
    NOT from b3_bridge's overridable _DEFAULT_CONFIG_PATH. Overriding
    isce_config.yaml's model_path/risk_thresholds via the temp-file
    monkeypatch (as rerun_paper_ablation.py already does) therefore does
    NOT affect temperature. Rather than edit the real isce_config.yaml on
    disk (forbidden), this forces the classifier singleton's already-loaded
    predictor.temperature attribute directly, post-construction -- the
    same numeric effect as if temperature_scaling had been read from the
    override file, without ever writing to isce_config.yaml."""
    b3_bridge.preload_classifier(override_path)
    inst = b3_bridge._CLASSIFIER_INSTANCE
    if inst is not None and inst.predictor is not None:
        old_t = inst.predictor.temperature
        inst.predictor.temperature = float(temperature)
        print(f"Forced predictor.temperature: {old_t} -> {temperature} "
              f"(inference.py cannot read this from the config override; "
              f"see _force_temperature docstring)")
    else:
        raise RuntimeError("B3 predictor failed to load; cannot force temperature")


def run_v2(override_path, out_dir, temperature, seed=21, n_windows=150):
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path
    _force_temperature(b3_bridge, override_path, temperature)
    sys.path.insert(0, str(ROOT / "stbv_bench"))
    if "build_stbv_bench_v2" in sys.modules:
        del sys.modules["build_stbv_bench_v2"]
    mod = importlib.import_module("build_stbv_bench_v2")
    sys.argv = ["build_stbv_bench_v2.py",
                "--source", str(ROOT / "data" / "veremi_processed" / "ConstPos_1416"),
                "--n-windows", str(n_windows), "--radius", "100.0",
                "--min-cluster", "3", "--min-buckets", "2", "--seed", str(seed),
                "--out", out_dir]
    print(f"[stbv_bench_v2] recalibrated finetuned run argv={sys.argv[1:]}")
    rc = mod.main()
    print(f"[done v2] rc={rc}")


def run_mixed_threat(override_path, out_dir, temperature, seed=31, n_windows=120):
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path
    _force_temperature(b3_bridge, override_path, temperature)
    sys.path.insert(0, str(ROOT / "stbv_bench"))
    if "build_mixed_threat_bench" in sys.modules:
        del sys.modules["build_mixed_threat_bench"]
    mod = importlib.import_module("build_mixed_threat_bench")
    sys.argv = ["build_mixed_threat_bench.py",
                "--source", str(ROOT / "data" / "veremi_processed" / "ConstPos_1416"),
                "--n-windows", str(n_windows), "--radius", "100.0",
                "--min-cluster", "3", "--min-buckets", "2", "--seed", str(seed),
                "--out", out_dir]
    print(f"[mixed_threat] recalibrated finetuned run argv={sys.argv[1:]}")
    rc = mod.main()
    print(f"[done mixed_threat] rc={rc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", choices=["v2", "mixed_threat", "both"], default="both")
    ap.add_argument("--thresholds-json", required=True,
                     help="Path to recalibrated_thresholds.json (must exist by the time this runs)")
    args = ap.parse_args()

    th = json.loads(pathlib.Path(args.thresholds_json).read_text())
    high = th["b3_risk_policy"]["high_confidence"]
    medium = th["b3_risk_policy"]["medium_confidence"]
    temperature = th["temperature_scaling"]["fitted_temperature_new"]

    override_path = make_override_config(MODEL_PATH, high, medium, temperature)

    if args.which in ("v2", "both"):
        run_v2(override_path, str(ROOT / "results" / "stbv_bench_v2_finetuned_recalibrated"), temperature)
    if args.which in ("mixed_threat", "both"):
        run_mixed_threat(override_path, str(ROOT / "results" / "mixed_threat_finetuned_recalibrated"), temperature)


if __name__ == "__main__":
    main()
