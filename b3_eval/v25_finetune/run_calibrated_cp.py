#!/usr/bin/env python3
"""Rerun cp_full_eval/run_cp_full_eval.py with the FROZEN calibrated
deployment package (finetuned LoRA-merged checkpoint, T=3.3242247104644775,
high=0.79, medium=0.50). Reuses rerun_external_and_cp.py's run_cp_full_eval
pattern (isce_config override for model_path, which also carries
risk_thresholds via full-dict copy) plus rerun_recalibrated.py's
_force_temperature hack (inference.py reads temperature from a hardcoded
path, not from the override file)."""
import pathlib, sys, shutil, tempfile
import yaml
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "b3_eval" / "v25_finetune"))

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged"
HIGH, MEDIUM, TEMP = 0.79, 0.5, 3.3242247104644775

real_config = ROOT / "isce_config.yaml"
data = yaml.safe_load(real_config.read_text(encoding="utf-8"))
data["b3_semantic_gate"]["model_path"] = MODEL_PATH
data["b3_semantic_gate"]["risk_thresholds"]["high"] = HIGH
data["b3_semantic_gate"]["risk_thresholds"]["medium"] = MEDIUM
tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
tmp.write_text(yaml.safe_dump(data), encoding="utf-8")
print(f"Config override written: {tmp}, model={MODEL_PATH}, high={HIGH}, medium={MEDIUM}, T(forced)={TEMP}")

import pipeline.b3_bridge as b3_bridge
b3_bridge._DEFAULT_CONFIG_PATH = tmp
b3_bridge.preload_classifier(tmp)
inst = b3_bridge._CLASSIFIER_INSTANCE
old_t = inst.predictor.temperature
inst.predictor.temperature = float(TEMP)
print(f"Forced predictor.temperature: {old_t} -> {TEMP}")

sys.path.insert(0, str(ROOT / "cp_full_eval"))
mod = __import__("run_cp_full_eval")
print("[cp_full_eval] running with calibrated deployment package")
rc = mod.main()
src = ROOT / "cp_full_eval" / "results" / "cp_full_eval_results.json"
dst = ROOT / "b3_eval" / "v25_finetune" / "results" / "paper_reruns" / "cp_full_eval_results__calibrated.json"
if src.exists():
    shutil.copy(src, dst)
    print("->", dst)
print("DONE rc=", rc)
