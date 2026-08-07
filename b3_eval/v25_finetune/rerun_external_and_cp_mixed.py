"""
b3_eval/v25_finetune/rerun_external_and_cp.py
=================================================
Re-runs two more manuscript experiments with the ONLY change being B3's
checkpoint, for both the original and fine-tuned checkpoints:

  - external_semantic_eval/evaluate_external.py  (Table tab:external_eval,
    "Frozen B3" external corpus, n=117)
  - cp_full_eval/run_cp_full_eval.py              (Table tab:cp_full, CP's
    isolated marginal effect, n=142)

Neither script's own logic is modified. For evaluate_external.py (which
calls get_predictor() with a hardcoded model_dir local variable), this
wrapper monkeypatches the module's checkpoint_status() function -- the
single function that determines model_dir -- to point at the requested
checkpoint, then calls the module's unmodified main(). For
run_cp_full_eval.py (which goes through pipeline.orchestrator.ISCEPipeline,
same as rerun_paper_ablation.py), this wrapper uses the identical
isce_config.yaml-override monkeypatch already used there.

Output files are copied to checkpoint-specific names so neither run
overwrites the other, and the original repo-committed result files
(external_eval_results.json, cp_full_eval_results.json) are left
untouched throughout (both are written to first by whichever run happens
to execute, then immediately copied aside -- copy happens before the next
checkpoint's run starts).

Run with: python3 b3_eval/v25_finetune/rerun_external_and_cp.py
"""
from __future__ import annotations

import importlib
import json
import pathlib
import shutil
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

CHECKPOINTS = {
    "original": ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3",
    "finetuned": ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_v25_lora_merged",
    "mixed": ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_merged",
}

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "paper_reruns"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def checkpoint_status_for(model_dir: pathlib.Path):
    import hashlib
    binp = model_dir / "pytorch_model.bin"
    safep = model_dir / "model.safetensors"
    present = safep if safep.exists() else binp
    if not present.exists():
        return {"ok": False, "reason": f"no weight file under {model_dir}"}, model_dir
    size = present.stat().st_size
    return {"ok": True, "size_bytes": size,
            "sha256_16": hashlib.sha256(present.read_bytes()).hexdigest()[:16]}, model_dir


def run_external_eval(checkpoint_name: str):
    sys.path.insert(0, str(ROOT / "external_semantic_eval"))
    sys.path.insert(0, str(ROOT / "b3" / "solution_stb" / "b3_semantic_gate"))
    if "evaluate_external" in sys.modules:
        del sys.modules["evaluate_external"]
    mod = importlib.import_module("evaluate_external")

    model_dir = CHECKPOINTS[checkpoint_name]
    mod.checkpoint_status = lambda: checkpoint_status_for(model_dir)  # only patched function
    print(f"\n[external_semantic_eval] checkpoint={checkpoint_name} model_dir={model_dir}")
    rc = mod.main()
    src = ROOT / "external_semantic_eval" / "external_eval_results.json"
    dst = OUT_DIR / f"external_eval_results__{checkpoint_name}.json"
    if src.exists():
        shutil.copy(src, dst)
        print(f"  -> {dst}")
    return rc


def run_cp_full_eval(checkpoint_name: str):
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["b3_semantic_gate"]["model_path"] = str(CHECKPOINTS[checkpoint_name].relative_to(ROOT)).replace("\\", "/")
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)

    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = tmp
    # Force a fresh predictor load under the new config (the module-level
    # _PREDICTOR_CACHE in inference.py is keyed by resolved model path, so
    # different checkpoints naturally get different cache entries -- no
    # cache-clearing needed, this just documents why that's safe).

    if "run_cp_full_eval" in sys.modules:
        del sys.modules["run_cp_full_eval"]
    sys.path.insert(0, str(ROOT / "cp_full_eval"))
    mod = importlib.import_module("run_cp_full_eval")
    print(f"\n[cp_full_eval] checkpoint={checkpoint_name} model_path={data['b3_semantic_gate']['model_path']}")
    rc = mod.main()
    src = ROOT / "cp_full_eval" / "results" / "cp_full_eval_results.json"
    dst = OUT_DIR / f"cp_full_eval_results__{checkpoint_name}.json"
    if src.exists():
        shutil.copy(src, dst)
        print(f"  -> {dst}")
    return rc


def main():
    for ckpt in ("mixed",):
        run_external_eval(ckpt)
        run_cp_full_eval(ckpt)
    print("\nDone. Outputs in", OUT_DIR)


if __name__ == "__main__":
    main()
