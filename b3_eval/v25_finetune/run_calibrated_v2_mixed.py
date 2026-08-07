#!/usr/bin/env python3
"""Driver: run STBV-Bench v2 and mixed-threat bench with the FROZEN
calibrated deployment package (finetuned LoRA-merged checkpoint,
T=3.3242247104644775, high=0.79, medium=0.50; enable_ensembling and
confidence_aware_benign are already true in isce_config.yaml and are
preserved verbatim by the override mechanism). Reuses rerun_recalibrated.py's
run_v2/run_mixed_threat helpers directly (correct thresholds passed in,
bypassing that script's mismatched --thresholds-json schema/main()).
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "b3_eval" / "v25_finetune"))
import rerun_recalibrated as rc

MODEL_PATH = rc.MODEL_PATH
HIGH = 0.79
MEDIUM = 0.5
TEMPERATURE = 3.3242247104644775

override_path = rc.make_override_config(MODEL_PATH, HIGH, MEDIUM, TEMPERATURE)

which = sys.argv[1] if len(sys.argv) > 1 else "both"
if which in ("v2", "both"):
    rc.run_v2(override_path, str(ROOT / "results" / "stbv_bench_v2_finetuned_recalibrated"), TEMPERATURE)
if which in ("mixed_threat", "both"):
    rc.run_mixed_threat(override_path, str(ROOT / "results" / "mixed_threat_finetuned_recalibrated"), TEMPERATURE)
print("DONE", which)
