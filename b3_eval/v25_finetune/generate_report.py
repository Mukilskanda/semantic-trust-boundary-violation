"""
b3_eval/v25_finetune/generate_report.py
==========================================
Reads b3_eval/v25_finetune/results/full_evaluation.json (written by
run_full_evaluation.py) plus training_log.jsonl (written by train_lora.py)
and produces:

  - b3_eval/v25_finetune/results/comparison_table.md   (publication tables)
  - b3_eval/v25_finetune/results/forgetting_analysis.json/.md
  - b3_eval/v25_finetune/results/figures/*.png          (bar charts)

Run with: python3 b3_eval/v25_finetune/generate_report.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIG_DIR = RESULTS / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

ORIG_KEY = "original_B3_semantic_gate_v3"
FINE_KEY = "finetuned_B3_v25_lora"


def load():
    ev = json.loads((RESULTS / "full_evaluation.json").read_text())
    log_lines = [json.loads(l) for l in (HERE / "training_log.jsonl").read_text().splitlines() if l.strip()]
    return ev, log_lines


def fmt_delta(a, b, pct=True, higher_is_better=True):
    d = b - a
    sign = "+" if d >= 0 else ""
    good = (d >= 0) == higher_is_better
    marker = "improved" if good else ("unchanged" if abs(d) < 1e-9 else "regressed")
    if pct:
        return f"{sign}{d*100:.2f} pp ({marker})"
    return f"{sign}{d:.4f} ({marker})"


def main():
    ev, log_lines = load()
    orig = ev["models"][ORIG_KEY]
    fine = ev["models"][FINE_KEY]
    calib = ev["calibration"]

    lines = []
    lines.append("# B3 Model Comparison: Original vs. LoRA Fine-tuned (STBV-Bench v2.5)\n")
    lines.append(f"Generated from `{RESULTS / 'full_evaluation.json'}`.\n")

    # ---- Training summary ----
    complete = next(l for l in log_lines if l["event"] == "training_complete")
    built = next(l for l in log_lines if l["event"] == "peft_model_built")
    lines.append("## Training summary\n")
    lines.append(f"- Best epoch: {complete['best_epoch']} / {complete['total_epochs_run']} run "
                 f"(early stopping patience=2, MAX_EPOCHS=10)")
    lines.append(f"- Best validation F1: {complete['best_val_f1']:.4f}")
    lines.append(f"- Trainable parameters: {built['trainable_params']:,} / "
                 f"{built['total_params']:,} ({built['trainable_pct']:.2f}%)")
    lines.append(f"- Total training wall time: {complete['total_seconds']:.0f}s "
                 f"({complete['total_seconds']/60:.1f} min)\n")

    # ---- Main comparison table ----
    lines.append("## Overall metrics: STBV-Bench v2.5 test split (held-out, template-disjoint)\n")
    lines.append("| Metric | Original | Fine-tuned | Δ |")
    lines.append("|---|---|---|---|")
    o = orig["stbv_v25_test"]["overall"]
    f = fine["stbv_v25_test"]["overall"]
    for metric, pct in [("accuracy", True), ("precision", True), ("recall", True),
                        ("f1", True), ("roc_auc", False), ("pr_auc", False)]:
        lines.append(f"| {metric} | {o[metric]:.4f} | {f[metric]:.4f} | "
                     f"{fmt_delta(o[metric], f[metric], pct=False)} |")

    lines.append("\n## Calibration (temperature refit on v2.5 val, evaluated on v2.5 test)\n")
    lines.append("| Metric | Original | Fine-tuned |")
    lines.append("|---|---|---|")
    co, cf = calib[ORIG_KEY], calib[FINE_KEY]
    lines.append(f"| Fitted temperature | {co['fitted_temperature']:.4f} | {cf['fitted_temperature']:.4f} |")
    lines.append(f"| ECE (pre-calibration) | {co['test_set_held_out']['pre']['ece']:.4f} | "
                 f"{cf['test_set_held_out']['pre']['ece']:.4f} |")
    lines.append(f"| ECE (post-calibration) | {co['test_set_held_out']['post']['ece']:.4f} | "
                 f"{cf['test_set_held_out']['post']['ece']:.4f} |")
    lines.append(f"| Brier (pre-calibration) | {co['test_set_held_out']['pre']['brier']:.4f} | "
                 f"{cf['test_set_held_out']['pre']['brier']:.4f} |")
    lines.append(f"| Brier (post-calibration) | {co['test_set_held_out']['post']['brier']:.4f} | "
                 f"{cf['test_set_held_out']['post']['brier']:.4f} |")
    lines.append(f"| Argmax label flips from calibration | {co['argmax_label_flips_on_test']} | "
                 f"{cf['argmax_label_flips_on_test']} |")

    lines.append("\n## Latency / Throughput / Memory (CUDA, batch=1, n=200)\n")
    lines.append("| Metric | Original | Fine-tuned | Δ |")
    lines.append("|---|---|---|---|")
    lo, lf = orig["latency"], fine["latency"]
    for k, unit in [("p50_ms", "ms"), ("p95_ms", "ms"), ("p99_ms", "ms"),
                    ("throughput_single_msg_per_sec", "msg/s"), ("peak_vram_mb", "MB"),
                    ("parameters", "")]:
        lines.append(f"| {k} | {lo[k]:.3g}{unit} | {lf[k]:.3g}{unit} | "
                     f"{lf[k]-lo[k]:+.3g}{unit} |")

    # ---- Per-family forgetting analysis ----
    # NOTE: F1 here is defined w.r.t. the MALICIOUS class (standard for this
    # binary task). `benign_control` is a 100%-benign family (no positive
    # labels), so precision/recall/F1 are mathematically undefined for it
    # (0/0) and both models report 0.0000 -- this is a metric artifact, NOT
    # a forgetting signal. Its accuracy (1 - false-positive-rate) is the
    # meaningful number for that row and is reported instead of F1.
    lines.append("\n## Per-attack-family F1: catastrophic forgetting check (STBV-Bench v2.5 test)\n")
    lines.append("*`benign_control` has no positive (malicious) labels, so F1 is undefined (0/0) "
                 "for it under this class definition -- its accuracy (= 1 - FPR) is shown instead "
                 "and excluded from the forgetting count below.*\n")
    lines.append("| Attack family | Original | Fine-tuned | Δ | Status |")
    lines.append("|---|---|---|---|---|")
    fam_o = orig["stbv_v25_test"]["per_family"]
    fam_f = fine["stbv_v25_test"]["per_family"]
    forgetting = {"improved": [], "unchanged": [], "regressed": []}
    REGRESSION_THRESHOLD = 0.02  # 2 F1 points -- below this is noise on small per-family n
    for fam in sorted(fam_o.keys()):
        n = fam_o[fam]["n"]
        if fam == "benign_control":
            a_o, a_f = fam_o[fam]["accuracy"], fam_f.get(fam, {}).get("accuracy", float("nan"))
            d = a_f - a_o
            status = "n/a (all-benign family, F1 undefined; see note)"
            lines.append(f"| {fam} (n={n}) | acc={a_o:.4f} | acc={a_f:.4f} | {d:+.4f} | {status} |")
            continue
        f1_o = fam_o[fam]["f1"]
        f1_f = fam_f.get(fam, {}).get("f1", float("nan"))
        d = f1_f - f1_o
        if d > REGRESSION_THRESHOLD:
            status = "IMPROVED"
            forgetting["improved"].append(fam)
        elif d < -REGRESSION_THRESHOLD:
            status = "REGRESSED"
            forgetting["regressed"].append(fam)
        else:
            status = "unchanged"
            forgetting["unchanged"].append(fam)
        lines.append(f"| {fam} (n={n}) | {f1_o:.4f} | {f1_f:.4f} | {d:+.4f} | {status} |")

    lines.append(f"\n**Summary**: {len(forgetting['improved'])} improved, "
                 f"{len(forgetting['unchanged'])} unchanged, "
                 f"{len(forgetting['regressed'])} regressed "
                 f"(threshold: |ΔF1| > {REGRESSION_THRESHOLD}).\n")
    if forgetting["regressed"]:
        lines.append(f"Regressed families: {', '.join(forgetting['regressed'])}\n")

    # ---- Robustness ----
    lines.append("\n## Robustness (adversarial perturbation battery, 6 V2X seeds x 11 families)\n")
    lines.append("| Family | Orig flip_rate | FT flip_rate | Orig evasion | FT evasion | Orig over_defense | FT over_defense |")
    lines.append("|---|---|---|---|---|---|---|")
    ro, rf = orig["robustness"], fine["robustness"]
    for fam in sorted(ro.keys()):
        a, b = ro[fam], rf[fam]
        def s(x):
            return "n/a" if x is None else f"{x:.2f}"
        lines.append(f"| {fam} | {a['flip_rate']:.2f} | {b['flip_rate']:.2f} | "
                     f"{s(a['evasion_rate'])} | {s(b['evasion_rate'])} | "
                     f"{s(a['over_defense_fpr'])} | {s(b['over_defense_fpr'])} |")

    # ---- Benchmarks not run ----
    lines.append("\n## Benchmarks not directly re-scored, and why\n")
    lines.append("- **VeReMi (raw)**: purely kinematic dataset, no text field; architecturally "
                 "out of scope for a text classifier (feeds B1/B2, never B3).")
    lines.append("- **Mixed-threat bench**: requires full B1+B2+CP+B3+TrustEngine orchestration "
                 "(layer-interaction benchmark, not a B3-alone benchmark); its semantic payloads "
                 "share the same generator lineage as v1/v2.5, already covered above.")
    lines.append("- **Ablation bench**: a layer-contribution ablation (B1/B1+B2/.../full stack), "
                 "not a B3-checkpoint ablation; orthogonal question, same full-stack dependency.")
    lines.append(f"- **STBV-Bench v1**: {orig['stbv_v1_sample']['status']}")

    (RESULTS / "comparison_table.md").write_text("\n".join(lines), encoding="utf-8")
    (RESULTS / "forgetting_analysis.json").write_text(json.dumps({
        "threshold_f1_points": REGRESSION_THRESHOLD, "families": forgetting,
        "per_family_original": fam_o, "per_family_finetuned": fam_f}, indent=2))

    # ---- Figures ----
    # benign_control excluded: F1 undefined (0/0) for an all-benign family, see note above
    families = sorted(f for f in fam_o.keys() if f != "benign_control")
    x = range(len(families))
    w = 0.38
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar([i - w/2 for i in x], [fam_o[f]["f1"] for f in families], width=w, label="Original")
    ax.bar([i + w/2 for i in x], [fam_f.get(f, {}).get("f1", 0) for f in families], width=w, label="Fine-tuned")
    ax.set_xticks(list(x))
    ax.set_xticklabels(families, rotation=45, ha="right")
    ax.set_ylabel("F1")
    ax.set_title("Per-attack-family F1: Original vs. Fine-tuned B3 (STBV-Bench v2.5 test)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "per_family_f1_comparison.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    metrics_names = ["accuracy", "precision", "recall", "f1"]
    ax.bar([i - w/2 for i in range(len(metrics_names))], [o[m] for m in metrics_names], width=w, label="Original")
    ax.bar([i + w/2 for i in range(len(metrics_names))], [f[m] for m in metrics_names], width=w, label="Fine-tuned")
    ax.set_xticks(range(len(metrics_names)))
    ax.set_xticklabels(metrics_names)
    ax.set_title("Overall metrics: STBV-Bench v2.5 test")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "overall_metrics_comparison.png", dpi=150)
    plt.close(fig)

    print("Wrote:")
    print(f"  {RESULTS / 'comparison_table.md'}")
    print(f"  {RESULTS / 'forgetting_analysis.json'}")
    print(f"  {FIG_DIR / 'per_family_f1_comparison.png'}")
    print(f"  {FIG_DIR / 'overall_metrics_comparison.png'}")


if __name__ == "__main__":
    main()
