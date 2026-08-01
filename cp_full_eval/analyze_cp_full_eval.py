#!/usr/bin/env python3
"""Computes decision/trust/detection/confidence changes and FP/FN rates,
CP-off vs CP-on, for both the diagnostic-isolation (B3 off) and
full-stack (B3 on) arms, overall and per scenario category."""
import json, pathlib
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
data = json.loads((HERE / "results" / "cp_full_eval_results.json").read_text())
scenes = data["scenes"]

ORDER = {"ACCEPT": 0, "CAUTION": 1, "REJECT": 2}


def pair_metrics(off_rows, on_rows, is_attacker_list):
    n = len(off_rows)
    decision_changes = sum(1 for a, b in zip(off_rows, on_rows) if a["decision"] != b["decision"])
    escalations = sum(1 for a, b in zip(off_rows, on_rows) if ORDER[b["decision"]] > ORDER[a["decision"]])
    de_escalations = sum(1 for a, b in zip(off_rows, on_rows) if ORDER[b["decision"]] < ORDER[a["decision"]])
    trust_deltas = [b["trust_score"] - a["trust_score"] for a, b in zip(off_rows, on_rows)]
    mean_trust_delta = sum(trust_deltas) / n if n else 0.0
    detect_changes = sum(1 for a, b in zip(off_rows, on_rows) if a["attack_detected"] != b["attack_detected"])
    conf_pairs = [(a.get("b3_confidence"), b.get("b3_confidence")) for a, b in zip(off_rows, on_rows)]
    conf_deltas = [ (bc - ac) for ac, bc in conf_pairs if ac is not None and bc is not None ]
    mean_conf_delta = (sum(conf_deltas) / len(conf_deltas)) if conf_deltas else None

    def is_fp(row, is_att):
        return (not is_att) and row["decision"] in ("CAUTION", "REJECT")

    def is_fn(row, is_att):
        return is_att and row["decision"] == "ACCEPT"

    fp_off = sum(1 for r, att in zip(off_rows, is_attacker_list) if is_fp(r, att))
    fp_on = sum(1 for r, att in zip(on_rows, is_attacker_list) if is_fp(r, att))
    fn_off = sum(1 for r, att in zip(off_rows, is_attacker_list) if is_fn(r, att))
    fn_on = sum(1 for r, att in zip(on_rows, is_attacker_list) if is_fn(r, att))

    return {
        "n": n, "decision_changes": decision_changes,
        "escalations_toward_caution_reject": escalations,
        "de_escalations_toward_accept": de_escalations,
        "mean_trust_score_delta": mean_trust_delta,
        "attack_detected_flag_changes": detect_changes,
        "mean_b3_confidence_delta": mean_conf_delta,
        "false_positives_off": fp_off, "false_positives_on": fp_on,
        "false_negatives_off": fn_off, "false_negatives_on": fn_on,
    }


def aggregate(scene_list, off_key, on_key):
    all_off, all_on, all_att = [], [], []
    per_scene = []
    for sc in scene_list:
        off_rows, on_rows = sc[off_key], sc[on_key]
        att = [r["is_attacker"] for r in off_rows]
        all_off.extend(off_rows); all_on.extend(on_rows); all_att.extend(att)
        per_scene.append({"scene_id": sc["scene_id"], "category": sc["category"],
                           **pair_metrics(off_rows, on_rows, att)})
    overall = pair_metrics(all_off, all_on, all_att)
    return overall, per_scene


diag_overall, diag_per_scene = aggregate(scenes, "cp_off_b3_off", "cp_on_b3_off")
full_overall, full_per_scene = aggregate(scenes, "cp_off_b3_on", "cp_on_b3_on")

by_cat_diag = defaultdict(list)
by_cat_full = defaultdict(list)
for sc in scenes:
    by_cat_diag[sc["category"]].append(sc)
    by_cat_full[sc["category"]].append(sc)

cat_diag_summary = {}
cat_full_summary = {}
for cat, scs in by_cat_diag.items():
    o, _ = aggregate(scs, "cp_off_b3_off", "cp_on_b3_off")
    cat_diag_summary[cat] = o
for cat, scs in by_cat_full.items():
    o, _ = aggregate(scs, "cp_off_b3_on", "cp_on_b3_on")
    cat_full_summary[cat] = o

# example transitions (for qualitative reporting): first flipping message per category
examples = {}
for sc in scenes:
    cat = sc["category"]
    if cat in examples:
        continue
    for a, b in zip(sc["cp_off_b3_on"], sc["cp_on_b3_on"]):
        if a["decision"] != b["decision"]:
            examples[cat] = {
                "scene_id": sc["scene_id"], "station": a["station"], "is_attacker": a["is_attacker"],
                "decision_cp_off": a["decision"], "decision_cp_on": b["decision"],
                "trust_score_cp_off": a["trust_score"], "trust_score_cp_on": b["trust_score"],
                "cp_spatial_on": b["cp_spatial"], "cp_speed_on": b["cp_speed"],
                "cp_heading_on": b["cp_heading"], "cp_diversity_on": b["cp_diversity"],
                "cp_num_reports_on": b["cp_num_reports"],
            }
            break

out = {
    "diagnostic_isolation_overall_B3_off": diag_overall,
    "full_stack_overall_B3_on": full_overall,
    "per_category_diagnostic": cat_diag_summary,
    "per_category_full_stack": cat_full_summary,
    "example_transitions_full_stack": examples,
    "per_scene_diagnostic": diag_per_scene,
    "per_scene_full_stack": full_per_scene,
}
(HERE / "results" / "cp_full_eval_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if not k.startswith("per_scene")}, indent=2))
print(f"\nWrote {HERE / 'results' / 'cp_full_eval_analysis.json'}")
