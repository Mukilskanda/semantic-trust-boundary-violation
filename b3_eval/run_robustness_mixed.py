"""
b3_eval/run_robustness_mixed.py
=================================
Reruns b3_eval/run_robustness.py's adversarial/perturbation battery against
the final production checkpoint (semantic_gate_v3_mixed_lora_merged),
closing the disclosed gap in stbv_paper.tex ("this specific perturbation
battery was not independently re-run against the final production
checkpoint in this evaluation pass"). Monkeypatches b3_eval._harness's
module-level MODEL_DIR constant (process-local only; no file on disk is
touched) so run_robustness.py's own load_predictor()/FAMILIES/SEEDS logic
runs completely unmodified against the new checkpoint.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import b3_eval._harness as harness
harness.MODEL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_merged"

import b3_eval.run_robustness as rob
rob.OUT = ROOT / "b3_eval" / "results"
# Redirect output filename so the original (original-checkpoint) robustness.json is preserved.
_orig_write_json = harness.write_json
def write_json_mixed(obj, path):
    if path.name == "robustness.json":
        path = path.parent / "robustness_mixed.json"
    return _orig_write_json(obj, path)
rob.write_json = write_json_mixed

if __name__ == "__main__":
    sys.exit(rob.main())
