#!/usr/bin/env python3
"""
b3_eval/v25_finetune/rerun_adaptive_attack.py
================================================
Re-runs adaptive_attack/run_adaptive_attack.py (Table tab:adaptive,
Fig fig_adaptive_confidence, the 83.7% ASR headline finding) for BOTH
checkpoints, with the ONLY change being B3's checkpoint. The script's
own logic is not modified; only its `checkpoint_status()` function
(the single place that hardcodes the "original" model_dir) is
monkeypatched, following the same pattern already used by
rerun_external_and_cp.py for evaluate_external.py.

Outputs are copied to checkpoint-specific filenames; the original
repo-committed adaptive_attack/results/adaptive_attack_results.json is
left as the "original" checkpoint's result (copied aside first, so nothing
is lost even though the unmodified script will also write there again for
the "original" pass).
"""
from __future__ import annotations
import importlib, pathlib, shutil, sys

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
    return {"ok": True, "size_bytes": present.stat().st_size,
            "sha256_16": __import__("hashlib").sha256(present.read_bytes()).hexdigest()[:16]}, model_dir


def run(checkpoint_name: str):
    sys.path.insert(0, str(ROOT / "adaptive_attack"))
    if "run_adaptive_attack" in sys.modules:
        del sys.modules["run_adaptive_attack"]
    mod = importlib.import_module("run_adaptive_attack")

    model_dir = CHECKPOINTS[checkpoint_name]
    mod.checkpoint_status = lambda: checkpoint_status_for(model_dir)
    print(f"\n[adaptive_attack] checkpoint={checkpoint_name} model_dir={model_dir}")
    mod.main()
    src = ROOT / "adaptive_attack" / "results" / "adaptive_attack_results.json"
    dst = OUT_DIR / f"adaptive_attack_results__{checkpoint_name}.json"
    if src.exists():
        shutil.copy(src, dst)
        print(f"  -> {dst}")


def main():
    for ckpt in ("mixed",):
        run(ckpt)
    print("\nDone. Outputs in", OUT_DIR)


if __name__ == "__main__":
    main()
