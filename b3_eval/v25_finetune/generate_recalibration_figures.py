"""
b3_eval/v25_finetune/generate_recalibration_figures.py
==========================================================
Regenerates reliability diagram (pre/post temperature scaling) and
ROC/PR curves with old vs new operating points marked, for the
recalibration pass, into UPDATED_FIGURES/ with a "recalibrated_" prefix
(distinct from the prior task's un-recalibrated figure set).
"""
from __future__ import annotations
import csv, json, math, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "UPDATED_FIGURES"
OUT.mkdir(exist_ok=True)
HERE = pathlib.Path(__file__).resolve().parent

RAW_CSV = HERE / "results" / "v1_finetuned_recalibration_raw.csv"
THRESH = json.loads((HERE / "results" / "recalibrated_thresholds.json").read_text())


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=150)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


def main():
    rows = list(csv.DictReader(open(RAW_CSV, newline="", encoding="utf-8")))
    test = [r for r in rows if r["split"] == "test"]
    T = THRESH["fitted_temperature"]
    eps = 1e-6

    p_raw, p_post, labels = [], [], []
    for r in test:
        p = min(max(float(r["p_malicious_raw"]), eps), 1 - eps)
        lb, lm = math.log(1 - p), math.log(p)
        p_raw.append(p)
        p_post.append(math.exp(lm / T) / (math.exp(lm / T) + math.exp(lb / T)))
        labels.append(1 if r["is_attacker"] == "True" else 0)

    def reliability(probs, labels, n_bins=10):
        bins = [[] for _ in range(n_bins)]
        for p, l in zip(probs, labels):
            conf = max(p, 1 - p)
            correct = int((p >= 0.5) == bool(l))
            idx = min(int(conf * n_bins), n_bins - 1)
            bins[idx].append((conf, correct))
        xs, accs = [], []
        for i, b in enumerate(bins):
            xs.append((i + 0.5) / n_bins)
            accs.append(sum(c for _, c in b) / len(b) if b else None)
        return xs, accs

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, probs, title in zip(axes, [p_raw, p_post], ["Pre-temperature (T=1.0)", f"Post-temperature (T={T:.3f})"]):
        xs, accs = reliability(probs, labels)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Perfect calibration")
        xs_p = [x for x, a in zip(xs, accs) if a is not None]
        accs_p = [a for a in accs if a is not None]
        ax.bar(xs_p, accs_p, width=0.08, alpha=0.75, color="#4C72B0", edgecolor="black", label="Accuracy")
        ax.set_xlabel("Confidence")
        ax.set_ylabel("Accuracy")
        ax.set_title(title)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=8)
    fig.suptitle("STBV-Bench v1 test split -- reliability diagram (fine-tuned checkpoint)")
    save(fig, "recalibrated_fig_reliability_pre_post")

    order = sorted(range(len(p_post)), key=lambda i: -p_post[i])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    tp = fp = 0
    roc_pts, pr_pts = [(0.0, 0.0)], []
    for i in order:
        if labels[i]:
            tp += 1
        else:
            fp += 1
        tpr = tp / n_pos
        fpr = fp / n_neg
        prec = tp / (tp + fp)
        roc_pts.append((fpr, tpr))
        pr_pts.append((tpr, prec))
    roc_pts.append((1.0, 1.0))

    comp = json.loads((HERE / "results" / "v1_test_three_way_comparison.json").read_text())
    old = comp["arm_b_finetuned_old_thresholds"]
    new = comp["arm_c_finetuned_recalibrated_thresholds"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    ax = axes[0]
    ax.plot([p[0] for p in roc_pts], [p[1] for p in roc_pts], color="#4C72B0", label=f"ROC (AUC={new['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.scatter([old["fpr"]], [old["recall"]], color="#DD8452", marker="x", s=90, label="Old thresholds (0.85/0.60)", zorder=5)
    ax.scatter([new["fpr"]], [new["recall"]], color="#55A868", marker="o", s=90,
               label=f"Recalibrated (high={THRESH['recalibrated_thresholds']['high_confidence']})", zorder=5)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate (Recall)")
    ax.set_title("ROC -- fine-tuned checkpoint, v1 test")
    ax.legend(fontsize=7, loc="lower right")

    ax = axes[1]
    ax.plot([p[0] for p in pr_pts], [p[1] for p in pr_pts], color="#4C72B0", label=f"PR (AUC={new['pr_auc']:.3f})")
    ax.scatter([old["recall"]], [old["precision"]], color="#DD8452", marker="x", s=90, label="Old thresholds", zorder=5)
    ax.scatter([new["recall"]], [new["precision"]], color="#55A868", marker="o", s=90, label="Recalibrated", zorder=5)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("PR -- fine-tuned checkpoint, v1 test")
    ax.legend(fontsize=7, loc="lower left")
    fig.suptitle("STBV-Bench v1 test split -- operating points, old vs recalibrated thresholds")
    save(fig, "recalibrated_fig_roc_pr_operating_points")

    arm_a = json.loads((HERE / "results" / "v1_test_arm_a_original.json").read_text())["config_5"]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    names = ["(a) Original\nckpt+thresholds", "(b) Fine-tuned\n+old thresholds", "(c) Fine-tuned\n+recalibrated"]
    f1s = [arm_a["f1"], old["f1"], new["f1"]]
    colors = ["#8172B2", "#DD8452", "#55A868"]
    bars = ax.bar(names, f1s, color=colors, edgecolor="black")
    for b, f in zip(bars, f1s):
        ax.text(b.get_x() + b.get_width() / 2, f + 0.02, f"{f:.3f}", ha="center", fontsize=10)
    ax.set_ylabel("F1 (STBV-Bench v1, test split, n=757)")
    ax.set_ylim(0, 1.05)
    ax.set_title("Three-way comparison: STBV-Bench v1 test")
    save(fig, "recalibrated_fig_three_way_f1")

    print("Figures written to", OUT)


if __name__ == "__main__":
    main()
