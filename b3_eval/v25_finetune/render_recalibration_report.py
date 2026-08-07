#!/usr/bin/env python3
"""
b3_eval/v25_finetune/render_recalibration_report.py
========================================================
Renders the numeric sections (fitted parameters, calibration, three-way
comparison tables, statistical tests, verdict) of RECALIBRATION_RESULTS.md
from the JSON artifacts produced by recalibrate_v1_external.py and
analyze_v2_mixed_recalibrated.py. Prints markdown to stdout; the caller
splices it into RECALIBRATION_RESULTS.md by hand (kept as a rendering
helper, not an auto-editor of the narrative sections).
"""
from __future__ import annotations
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"


def load(name):
    return json.loads((RESULTS / name).read_text())


def fmt(x, p=4):
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{x:.{p}f}"


def table_row(name, m):
    return (f"| {name} | {m['n']} | {fmt(m['accuracy'])} | {fmt(m['precision'])} | "
            f"{fmt(m['recall'])} | {fmt(m['f1'])} | {fmt(m['roc_auc'])} | {fmt(m['pr_auc'])} | "
            f"{fmt(m['ece'])} | {fmt(m['brier'])} |")


def main():
    th = load("recalibrated_thresholds.json")
    v1 = load("v1_recalibration_analysis.json")
    ext = load("external_recalibration_analysis.json")

    print("## 2. Fitted parameters\n")
    print("| Parameter | Old (original-checkpoint-fit) | New (recalibrated, fine-tuned checkpoint) |")
    print("|---|---|---|")
    print(f"| Temperature | {th['temperature_scaling']['production_temperature_old']} | "
          f"{th['temperature_scaling']['fitted_temperature_new']:.4f} |")
    print(f"| `high_confidence` | {th['b3_risk_policy']['old_high_confidence']} | "
          f"{th['b3_risk_policy']['high_confidence']:.4f} |")
    print(f"| `medium_confidence` | {th['b3_risk_policy']['old_medium_confidence']} | "
          f"{th['b3_risk_policy']['medium_confidence']:.4f} |")

    print("\n## 3. Calibration (STBV-Bench v1)\n")
    c = v1["calibration"]
    print("| Split | n | ECE pre (T=2.1446) | ECE post (T_new) | Brier pre | Brier post |")
    print("|---|---|---|---|---|---|")
    for split in ("val", "test"):
        s = c[split]
        print(f"| {split} | {s['n']} | {fmt(s['pre_T_old']['ece'])} | {fmt(s['post_T_new']['ece'])} | "
              f"{fmt(s['pre_T_old']['brier'])} | {fmt(s['post_T_new']['brier'])} |")

    print("\n## 4.1 STBV-Bench v1 (test split)\n")
    print("| Arm | n | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | ECE | Brier |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    print(table_row("(a) original + old thresholds", v1["v1_test_arm_a_original_old_thresholds"]))
    print(table_row("(b) finetuned + old thresholds", v1["v1_test_arm_b_finetuned_old_thresholds"]))
    print(table_row("(c) finetuned + recalibrated", v1["v1_test_arm_c_finetuned_recalibrated"]))
    ci = v1["v1_test_arm_c_bootstrap_ci"]
    print(f"\n(c) bootstrap 95% CI: accuracy {ci['accuracy_ci95']}, F1 {ci['f1_ci95']}")
    print(f"\nMcNemar (a vs b): {v1['mcnemar_a_vs_b']}")
    print(f"\nMcNemar (b vs c): {v1['mcnemar_b_vs_c']}")

    print("\n## 4.4 External semantic corpus (n=117, transfer)\n")
    print("| Arm | n | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | ECE | Brier |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    print(table_row("(a) original + old thresholds", ext["arm_a_original_old_thresholds"]))
    print(table_row("(b) finetuned + old thresholds", ext["arm_b_finetuned_old_thresholds"]))
    print(table_row("(c) finetuned + recalibrated (transfer)", ext["arm_c_finetuned_recalibrated_transfer"]))
    print(f"\n(c) bootstrap 95% CI: {ext['arm_c_bootstrap_ci']}")
    print(f"\nMcNemar (a vs b): {ext['mcnemar_a_vs_b']}")
    print(f"\nMcNemar (b vs c): {ext['mcnemar_b_vs_c']}")

    try:
        v2 = load("v2_recalibration_analysis.json")
        print("\n## 4.2 STBV-Bench v2\n")
        print("| Arm | n | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | ECE | Brier |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        print(table_row("(a) original + old thresholds", v2["arm_a_original_old_thresholds"]))
        print(table_row("(b) finetuned + old thresholds", v2["arm_b_finetuned_old_thresholds"]))
        print(table_row("(c) finetuned + recalibrated", v2["arm_c_finetuned_recalibrated"]))
        print(f"\n(c) bootstrap 95% CI: {v2['arm_c_bootstrap_ci']}")
        print(f"\nMcNemar (a vs b): {v2['mcnemar_a_vs_b']}")
        print(f"\nMcNemar (b vs c): {v2['mcnemar_b_vs_c']}")
    except FileNotFoundError:
        print("\n[v2 analysis not yet available]")

    try:
        mt = load("mixed_threat_recalibration_analysis.json")
        print("\n## 4.3 Mixed-threat case study\n")
        print("| Arm | semantic recall (msg) | semantic recall (sender) | kinematic recall (msg) |")
        print("|---|---|---|---|")
        for name in ("arm_a_original_old_thresholds", "arm_b_finetuned_old_thresholds", "arm_c_finetuned_recalibrated"):
            m = mt[name]
            print(f"| {name} | {fmt(m['semantic_recall_message'])} ({m['semantic_flagged_message']}/{m['semantic_n_message']}) "
                  f"| {fmt(m['semantic_recall_sender'])} ({m['semantic_flagged_sender']}/{m['semantic_n_sender']}) "
                  f"| {fmt(m['kinematic_recall_message'])} ({m['kinematic_flagged_message']}/{m['kinematic_n_message']}) |")
        print(f"\nMcNemar (a vs b, semantic detection): {mt['mcnemar_a_vs_b_semantic_detection']}")
        print(f"\nMcNemar (b vs c, semantic detection): {mt['mcnemar_b_vs_c_semantic_detection']}")
    except FileNotFoundError:
        print("\n[mixed-threat analysis not yet available]")


if __name__ == "__main__":
    main()
