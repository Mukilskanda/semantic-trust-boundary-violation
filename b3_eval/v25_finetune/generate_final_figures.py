#!/usr/bin/env python3
"""
b3_eval/v25_finetune/generate_final_figures.py
================================================
Generates the FINAL, single-model figure set for stbv_paper.tex, computed
directly from this session's mixed-checkpoint (semantic_gate_v3_mixed_lora_merged)
rerun artifacts:

  - b3_eval/v25_finetune/ablation_results/mixed/ablation_config_{4,5}.csv
  - b3_eval/v25_finetune/results/paper_reruns/external_eval_results__mixed.json
  - b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__mixed.json

Writes PNG+PDF pairs to FINAL_FIGURES/ (repo root). Single-model only (no
checkpoint-vs-checkpoint comparison plots) per the paper's final, one-model
presentation.
"""
from __future__ import annotations
import csv, json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "FINAL_FIGURES"
OUT.mkdir(exist_ok=True)
AB = ROOT / "b3_eval" / "v25_finetune" / "ablation_results" / "mixed"
PR = ROOT / "b3_eval" / "v25_finetune" / "results" / "paper_reruns"

COLOR = "#1f77b4"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=150)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


def load_cfg(cfg):
    with open(AB / f"ablation_config_{cfg}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def p_malicious_proxy(rows):
    return [float(r["raw_score"]) if r["decision"] in ("CAUTION", "REJECT") else 1 - float(r["raw_score"])
            for r in rows]


def roc_pr(rows):
    y = [1 if r["is_attacker"] == "True" else 0 for r in rows]
    s = p_malicious_proxy(rows)
    order = sorted(range(len(y)), key=lambda i: -s[i])
    P = sum(y); N = len(y) - P
    tp = fp = 0
    roc_pts, pr_pts = [(0.0, 0.0)], []
    for idx in order:
        tp += y[idx]; fp += 1 - y[idx]
        tpr = tp / P if P else 0.0
        fpr = fp / N if N else 0.0
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        roc_pts.append((fpr, tpr))
        pr_pts.append((tpr, prec))
    roc_pts_sorted = sorted(set(roc_pts))
    auc = np.trapz([p[1] for p in roc_pts_sorted], [p[0] for p in roc_pts_sorted])
    pr_pts_sorted = sorted(set(pr_pts))
    pr_auc = np.trapz([p[1] for p in pr_pts_sorted], [p[0] for p in pr_pts_sorted])
    return roc_pts, auc, pr_pts, pr_auc


def ece_brier(rows, n_bins=10):
    labels = [1 if r["is_attacker"] == "True" else 0 for r in rows]
    probs = p_malicious_proxy(rows)
    conf = [max(p, 1 - p) for p in probs]
    pred = [1 if p >= 0.5 else 0 for p in probs]
    correct = [1 if pred[i] == labels[i] else 0 for i in range(len(rows))]
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(labels)
    bin_stats = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        idxs = [j for j in range(n) if lo < conf[j] <= hi or (i == 0 and conf[j] == lo)]
        if not idxs:
            bin_stats.append(None); continue
        acc_b = sum(correct[j] for j in idxs) / len(idxs)
        conf_b = sum(conf[j] for j in idxs) / len(idxs)
        ece += (len(idxs) / n) * abs(acc_b - conf_b)
        bin_stats.append((conf_b, acc_b, len(idxs)))
    brier = sum((probs[i] - labels[i]) ** 2 for i in range(n)) / n
    return ece, brier, bin_stats


def fig_confusion():
    rows = load_cfg(5)
    tp = sum(1 for r in rows if r["is_attacker"] == "True" and r["decision"] in ("CAUTION", "REJECT"))
    fp = sum(1 for r in rows if r["is_attacker"] == "False" and r["decision"] in ("CAUTION", "REJECT"))
    fn = sum(1 for r in rows if r["is_attacker"] == "True" and r["decision"] == "ACCEPT")
    tn = sum(1 for r in rows if r["is_attacker"] == "False" and r["decision"] == "ACCEPT")
    mat = np.array([[tn, fp], [fn, tp]])
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    ax.imshow(mat, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(mat[i, j]), ha="center", va="center")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Accept", "Caution/Reject"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Benign", "Attacker"])
    ax.set_title("Confusion matrix, full stack, STBV-Bench v1")
    save(fig, "fig_confusion")
    return dict(tp=tp, fp=fp, fn=fn, tn=tn)


def fig_per_family():
    from collections import defaultdict
    rows = load_cfg(5)
    fam = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["is_attacker"] != "True":
            continue
        fam[r["attack_family"]][1] += 1
        if r["decision"] in ("CAUTION", "REJECT"):
            fam[r["attack_family"]][0] += 1
    families = sorted(fam.keys())
    recalls = [fam[f][0] / fam[f][1] if fam[f][1] else 0 for f in families]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    colors = [("#2ca02c" if r >= 0.99 else ("#d62728" if r <= 0.09 else "#ff7f0e")) for r in recalls]
    ax.bar(families, recalls, color=colors)
    ax.set_xticklabels(families, rotation=75, ha="right", fontsize=7)
    ax.set_ylabel("Recall (full stack)")
    ax.set_title("Per-attack-family recall, STBV-Bench v1")
    save(fig, "fig_per_family_recall")
    return {f: r for f, r in zip(families, recalls)}


def fig_roc_pr():
    rows = load_cfg(4)
    roc_pts, auc, pr_pts, pr_auc = roc_pr(rows)
    fig, ax = plt.subplots(figsize=(4, 3.6))
    xs = sorted(set(p[0] for p in roc_pts))
    ys_by_x = {}
    for x, y in roc_pts:
        ys_by_x.setdefault(x, []).append(y)
    xs2 = sorted(ys_by_x)
    ys2 = [max(ys_by_x[x]) for x in xs2]
    ax.plot(xs2, ys2, color=COLOR, label=f"AUC={auc:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title("ROC, full-stack fused score, STBV-Bench v1")
    ax.legend(fontsize=8)
    save(fig, "fig_roc")

    fig, ax = plt.subplots(figsize=(4, 3.6))
    xs = sorted(set(p[0] for p in pr_pts))
    ys_by_x = {}
    for x, y in pr_pts:
        ys_by_x.setdefault(x, []).append(y)
    xs2 = sorted(ys_by_x)
    ys2 = [np.mean(ys_by_x[x]) for x in xs2]
    ax.plot(xs2, ys2, color=COLOR, label=f"AUC={pr_auc:.3f}")
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.set_title("PR curve, full-stack fused score, STBV-Bench v1")
    ax.legend(fontsize=8)
    save(fig, "fig_pr")
    return dict(roc_auc=auc, pr_auc=pr_auc)


def fig_calibration():
    rows = load_cfg(4)
    ece, brier, bin_stats = ece_brier(rows)
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    pts = [b for b in bin_stats if b is not None]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=3, color=COLOR,
             label=f"ECE={ece:.3f}, Brier={brier:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    ax.set_xlabel("Mean predicted confidence"); ax.set_ylabel("Accuracy")
    ax.set_title("Reliability diagram, B3, STBV-Bench v1")
    ax.legend(fontsize=8)
    save(fig, "fig_calibration")
    return dict(ece=ece, brier=brier)


def fig_ext_roc():
    d = json.loads((PR / "external_eval_results__mixed.json").read_text())
    pts = d["roc"]["points_sample"]
    fig, ax = plt.subplots(figsize=(4, 3.6))
    ax.plot([q[0] for q in pts], [q[1] for q in pts], color=COLOR, label=f"AUC={d['roc']['auc']:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title("ROC, external semantic corpus (n=117)")
    ax.legend(fontsize=8)
    save(fig, "fig_ext_roc")


def fig_ext_per_family():
    d = json.loads((PR / "external_eval_results__mixed.json").read_text())
    fam = d["per_family_recall"]
    families = sorted(fam.keys(), key=lambda f: fam[f]["recall"])
    recalls = [fam[f]["recall"] for f in families]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    colors = ["#d62728" if r < 0.8 else ("#ff7f0e" if r < 1.0 else "#2ca02c") for r in recalls]
    ax.bar(families, recalls, color=colors)
    ax.set_xticks(range(len(families))); ax.set_xticklabels(families, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("Recall")
    ax.set_ylim(0, 1.05)
    ax.set_title("Per-family recall, external semantic corpus (n=117)")
    save(fig, "fig_ext_per_family_recall")


def fig_adaptive_confidence():
    d = json.loads((PR / "adaptive_attack_results__mixed.json").read_text())
    res = d["results"]
    max_r = max(len(r["trace"]) for r in res)
    mean_conf = []
    detect_prob = []
    for round_idx in range(max_r):
        vals, dets = [], []
        for r in res:
            tr = r["trace"]
            entry = next((e for e in tr if e["iteration"] == round_idx), tr[-1])
            vals.append(entry["p_malicious"])
            dets.append(1 if entry["detected"] else 0)
        mean_conf.append(np.mean(vals))
        detect_prob.append(np.mean(dets))
    fig, ax = plt.subplots(figsize=(5, 3.6))
    ax.plot(range(max_r), mean_conf, marker="o", ms=3, color=COLOR, label="Mean P(malicious)")
    ax.plot(range(max_r), detect_prob, marker="s", ms=3, color="#d62728", label="Detection probability")
    ax.set_xlabel("Adaptive mutation round"); ax.set_ylabel("Value")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Adaptive-attack confidence/detection, n={len(res)} seeds")
    ax.legend(fontsize=8)
    save(fig, "fig_adaptive_confidence")


def main():
    results = {}
    results["confusion"] = fig_confusion()
    results["per_family_recall"] = fig_per_family()
    results["roc_pr"] = fig_roc_pr()
    results["calibration"] = fig_calibration()
    fig_ext_roc()
    fig_ext_per_family()
    fig_adaptive_confidence()
    (OUT / "final_figures_manifest.json").write_text(json.dumps(results, indent=2, default=str))
    print("Wrote figures to", OUT)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
