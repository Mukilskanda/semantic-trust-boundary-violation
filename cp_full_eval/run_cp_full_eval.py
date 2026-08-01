#!/usr/bin/env python3
"""
run_cp_full_eval.py
=====================
Replays every scene from scenarios/scenes.json statefully (window
accumulates message-by-message, exactly the methodology already used by
stbv_bench/verify_cp_empirical.py for the pre-existing 120-scenario CP
check) through FOUR pipeline configurations:

  1. CP off, B3 off  (diagnostic isolation baseline)
  2. CP on,  B3 off  (diagnostic isolation -- CP's own, unmixed contribution)
  3. CP off, B3 on   (realistic full stack, no CP)
  4. CP on,  B3 on   (realistic full stack, with CP)

No architecture change: same ISCEPipeline, same cp_layer.py, same
Trust Decision Engine, same fusion code as every other result in this
paper. Only the input data (this scenario set) and the enable_cp flag
(already a supported, pre-existing ablation switch) vary.

Does not retrain or modify B3, CP, or any other layer.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

HERE = pathlib.Path(__file__).resolve().parent


def replay_scene(scene, enable_cp, enable_b3):
    p = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=enable_cp, enable_b3=enable_b3)
    window = []
    rows = []
    for m in scene["messages"]:
        window.append(dict(m))
        res = p.run(list(window), context="urban")
        cp_dict = res.get("cp") or {}
        b3_dict = res.get("b3") or {}
        rows.append({
            "station": m["header"]["station_id"],
            "is_attacker": m.get("is_attacker", False),
            "event": m.get("event"),
            "decision": res["decision"],
            "trust_score": res["fusion"]["trust_score"],
            "attack_detected": res["fusion"]["attack_detected"],
            "b3_available": b3_dict.get("available"),
            "b3_label": b3_dict.get("label"),
            "b3_confidence": b3_dict.get("confidence"),
            "cp_num_reports": cp_dict.get("num_reports"),
            "cp_confidence": cp_dict.get("cp_confidence"),
            "cp_spatial": cp_dict.get("spatial_score"),
            "cp_speed": cp_dict.get("speed_score"),
            "cp_heading": cp_dict.get("heading_score"),
            "cp_diversity": cp_dict.get("diversity_score"),
            "cp_observations_available": cp_dict.get("observations_available"),
        })
    return rows


def main():
    scenes = json.loads((HERE / "scenarios" / "scenes.json").read_text())

    all_results = []
    for i, scene in enumerate(scenes):
        entry = {"scene_id": scene["scene_id"], "category": scene["category"],
                 "expected_cp_effect": scene["expected_cp_effect"], "n_messages": len(scene["messages"])}
        entry["cp_off_b3_off"] = replay_scene(scene, enable_cp=False, enable_b3=False)
        entry["cp_on_b3_off"] = replay_scene(scene, enable_cp=True, enable_b3=False)
        entry["cp_off_b3_on"] = replay_scene(scene, enable_cp=False, enable_b3=True)
        entry["cp_on_b3_on"] = replay_scene(scene, enable_cp=True, enable_b3=True)
        all_results.append(entry)
        n_flip_diag = sum(1 for a, b in zip(entry["cp_off_b3_off"], entry["cp_on_b3_off"])
                           if a["decision"] != b["decision"])
        n_flip_full = sum(1 for a, b in zip(entry["cp_off_b3_on"], entry["cp_on_b3_on"])
                           if a["decision"] != b["decision"])
        print(f"[{i+1}/{len(scenes)}] {scene['scene_id']}: diag_flips={n_flip_diag}, full_flips={n_flip_full}")

    out = {
        "manifest": {
            "experiment": "cp_full_evaluation",
            "n_scenes": len(scenes),
            "n_messages": sum(e["n_messages"] for e in all_results),
            "configs": ["cp_off_b3_off", "cp_on_b3_off", "cp_off_b3_on", "cp_on_b3_on"],
            "note": "No retraining/fine-tuning anywhere. CP and B3 both frozen; only enable_cp/enable_b3 flags vary.",
        },
        "scenes": all_results,
    }
    (HERE / "results" / "cp_full_eval_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {HERE / 'results' / 'cp_full_eval_results.json'}")


if __name__ == "__main__":
    main()
