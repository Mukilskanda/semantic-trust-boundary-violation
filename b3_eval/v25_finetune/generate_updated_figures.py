#!/usr/bin/env python3
"""
b3_eval/v25_finetune/generate_updated_figures.py
====================================================
Regenerates every figure in stbv_paper.tex whose underlying data is
B3-checkpoint-dependent (Category A/B rows in DEPENDENCY_TABLE.md),
computed directly from this session's rerun artifacts:

  - b3_eval/v25_finetune/ablation_results/{original,finetuned}/ablation_config_{4,5}.csv
  - b3_eval/v25_finetune/results/paper_reruns/external_eval_results__{ck}.json
  - b3_eval/v25_finetune/results/paper_reruns/adaptive_attack_results__{ck}.json
  - b3_eval/v25_finetune/results/paper_reruns/cp_full_eval_results__{ck}.json
  - results/mixed_threat{,_finetuned}/manifest.json + per-message csv
  - results/stbv_bench_v2{,_finetuned}/...
  - b3_eval/v25_finetune/ablation_results/deployment_eval{,_finetuned}.json

Writes PNG+PDF pairs to UPDATED_FIGURES/ (repo root). This is a NEW,
consolidated script -- it does not reuse the legacy figures_v2/generate_figures.py
pipeline (which reads from a different, older set of intermediate result
files not reproduced verbatim by this session's rerun harnesses); it
computes the same statistics from the new, verified-checkpoint-swapped
artifacts directly. Any figure NOT regenerated here is stated as
unchanged/skipped in REGRESSION_REPORT.md, not silently omitted.
"""
from __future__ import annotations
import csv, json, math, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "UPDATED_FIGURES"
OUT.mkdir(exist_ok=True)
AB = ROOT / "b3_eval" / "v25_finetune" / "ablation_results"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=150)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


def load_cfg(ckpt, cfg):
    with open(AB / ckpt / f"ablation_config_{cfg}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def p_malicious_proxy(rows):
    """rerun_paper_ablation.py's config-4 CSV stores `raw_score` =
    B3's argmax-label confidence (NOT P(malicious)) and no label column,
    so P(malicious) cannot be read back exactly. Reconstructed as a
    disclosed proxy from the (already label-informed) decision4 field:
    decision4 in {CAUTION, REJECT} means B3's own risk_level was
    MEDIUM/HIGH (i.e. its risk assessment leaned toward MALICIOUS), so
    raw_score (confidence) is used directly as the malicious-leaning
    score; decision4 == ACCEPT means risk_level was LOW/NONE (leaned
    BENIGN), so 1-raw_score is used. This is an approximation, not an
    exact P(malicious) recovery -- stated plainly in UPDATED_TABLES.md
    and REGRESSION_REPORT.md; it is monotonic-consistent with B3's own
    3-way risk decision, which is the quantity the paper's Fig
    fig_roc/fig_pr/fig_calibration actually visualize."""
    return [float(r["raw_score"]) if r["decision"] in ("CAUTION", "REJECT") else 1 - float(r["raw_score"])
            for r in rows]


def roc_pr(rows):
    y = [1 if r["is_attacker"] == "True" else 0 for r in rows]
    s = p_malicious_proxy(rows)
    order = sorted(range(len(y)), key=lambda i: -s[i])
    P = sum(y); N = len(y) - P
    tp = fp = 0
    roc_pts, pr_pts = [(0.0, 0.0)], []
    prev_s = None
    for idx in order:
        tp += y[order[idx] if False else idx]
        fp += 1 - y[idx]
        tpr = tp / P if P else 0.0
        fpr = fp / N if N else 0.0
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        roc_pts.append((fpr, tpr))
        pr_pts.append((tpr, prec))
    # AUC via trapezoid on sorted fpr
    roc_pts_sorted = sorted(set(roc_pts))
    auc = np.trapz([p[1] for p in roc_pts_sorted], [p[0] for p in roc_pts_sorted])
    pr_pts_sorted = sorted(set(pr_pts))
    pr_auc = np.trapz([p[1] for p in pr_pts_sorted], [p[0] for p in pr_pts_sorted])
    return roc_pts, auc, pr_pts, pr_auc


def ece_brier(rows, n_bins=15):
    probs = p_malicious_proxy(rows)
    labels = [1 if r["is_attacker"] == "True" else 0 for r in rows]
    conf = [max(p, 1 - p) for p in probs]
    pred = [1 if p >= 0.5 else 0 for p in probs]
    correct = [int(pred[i] == labels[i]) for i in range(len(labels))]
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    bin_stats = []
    n = len(labels)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        idxs = [j for j in range(n) if lo < conf[j] <= hi or (i == 0 and conf[j] == lo)]
        if not idxs:
            bin_stats.append(None)
            continue
        acc_b = sum(correct[j] for j in idxs) / len(idxs)
        conf_b = sum(conf[j] for j in idxs) / len(idxs)
        ece += (len(idxs) / n) * abs(acc_b - conf_b)
        bin_stats.append((conf_b, acc_b, len(idxs)))
    brier = sum((probs[i] - labels[i]) ** 2 for i in range(n)) / n
    return ece, brier, bin_stats


def fig_roc_pr(results):
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.6))
    for ckpt, color in [("original", "#7f7f7f"), ("finetuned", "#d62728")]:
        rows = load_cfg(ckpt, 4)
        roc_pts, auc, pr_pts, pr_auc = roc_pr(rows)
        results.setdefault(ckpt, {})["roc_auc_config4"] = auc
        results[ckpt]["pr_auc_config4"] = pr_auc
        xs = sorted(set(p[0] for p in roc_pts))
        ys_by_x = {}
        for x, y in roc_pts:
            ys_by_x.setdefault(x, []).append(y)
        xs2 = sorted(ys_by_x)
        ys2 = [max(ys_by_x[x]) for x in xs2]
        axes[0].plot(xs2, ys2, color=color, label=f"{ckpt} (AUC={auc:.3f})")
    axes[0].plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR"); axes[0].set_title("ROC — B3 alone (config 4)")
    axes[0].legend(fontsize=8)
    for ckpt, color in [("original", "#7f7f7f"), ("finetuned", "#d62728")]:
        rows = load_cfg(ckpt, 4)
        _, _, pr_pts, pr_auc = roc_pr(rows)
        xs = sorted(set(p[0] for p in pr_pts))
        ys_by_x = {}
        for x, y in pr_pts:
            ys_by_x.setdefault(x, []).append(y)
        xs2 = sorted(ys_by_x)
        ys2 = [np.mean(ys_by_x[x]) for x in xs2]
        axes[1].plot(xs2, ys2, color=color, label=f"{ckpt} (AUC={pr_auc:.3f})")
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].set_title("PR — B3 alone (config 4)")
    axes[1].legend(fontsize=8)
    save(fig, "fig_roc_pr_updated")


def fig_calibration(results):
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    for ckpt, color in [("original", "#7f7f7f"), ("finetuned", "#d62728")]:
        rows = load_cfg(ckpt, 4)
        ece, brier, bin_stats = ece_brier(rows)
        results.setdefault(ckpt, {})["ece_config4"] = ece
        results[ckpt]["brier_config4"] = brier
        pts = [b for b in bin_stats if b is not None]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=3, color=color,
                 label=f"{ckpt} (ECE={ece:.3f}, Brier={brier:.3f})")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    ax.set_xlabel("Mean predicted confidence"); ax.set_ylabel("Accuracy")
    ax.set_title("Reliability — B3 alone (config 4), STBV-Bench v1")
    ax.legend(fontsize=8)
    save(fig, "fig_calibration_updated")


def fig_confusion(results):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    for ax, ckpt in zip(axes, ("original", "finetuned")):
        rows = load_cfg(ckpt, 5)
        tp = sum(1 for r in rows if r["is_attacker"] == "True" and r["decision"] in ("CAUTION", "REJECT"))
        fp = sum(1 for r in rows if r["is_attacker"] == "False" and r["decision"] in ("CAUTION", "REJECT"))
        fn = sum(1 for r in rows if r["is_attacker"] == "True" and r["decision"] == "ACCEPT")
        tn = sum(1 for r in rows if r["is_attacker"] == "False" and r["decision"] == "ACCEPT")
        mat = np.array([[tn, fp], [fn, tp]])
        im = ax.imshow(mat, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(mat[i, j]), ha="center", va="center")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["Accept", "Caution/Reject"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["Benign", "Attacker"])
        ax.set_title(f"{ckpt} (full stack)")
    save(fig, "fig_confusion_updated")


def fig_per_family(results):
    from collections import defaultdict
    fig, ax = plt.subplots(figsize=(10, 4.2))
    fam_data = {}
    for ckpt in ("original", "finetuned"):
        rows = load_cfg(ckpt, 5)
        fam = defaultdict(lambda: [0, 0])
        for r in rows:
            if r["is_attacker"] != "True":
                continue
            fam[r["attack_family"]][1] += 1
            if r["decision"] in ("CAUTION", "REJECT"):
                fam[r["attack_family"]][0] += 1
        fam_data[ckpt] = {k: v[0] / v[1] if v[1] else None for k, v in fam.items()}
    families = sorted(fam_data["original"].keys())
    x = np.arange(len(families))
    w = 0.38
    ax.bar(x - w / 2, [fam_data["original"][f] or 0 for f in families], w, label="original", color="#7f7f7f")
    ax.bar(x + w / 2, [fam_data["finetuned"][f] or 0 for f in families], w, label="finetuned", color="#d62728")
    ax.set_xticks(x); ax.set_xticklabels(families, rotation=75, ha="right", fontsize=7)
    ax.set_ylabel("Recall (config 5, full stack)")
    ax.set_title("Per-family recall, old vs new checkpoint (STBV-Bench v1)")
    ax.legend()
    save(fig, "fig_per_family_updated")
    results["per_family_recall_config5"] = {"original": fam_data["original"], "finetuned": fam_data["finetuned"]}


def fig_ablation_summary(results):
    from collections import defaultdict
    labels = {1: "B1", 2: "B1+B2", 3: "B1+B2+CP", 4: "B3 alone", 5: "Full stack"}
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.arange(5)
    w = 0.38
    for off, ckpt, color in [(-w / 2, "original", "#7f7f7f"), (w / 2, "finetuned", "#d62728")]:
        f1s = []
        for cfg in range(1, 6):
            rows = load_cfg(ckpt, cfg)
            tp = sum(1 for r in rows if r["is_attacker"] == "True" and r["decision"] in ("CAUTION", "REJECT"))
            fp = sum(1 for r in rows if r["is_attacker"] == "False" and r["decision"] in ("CAUTION", "REJECT"))
            fn = sum(1 for r in rows if r["is_attacker"] == "True" and r["decision"] == "ACCEPT")
            prec = tp / (tp + fp) if (tp + fp) else 0
            rec = tp / (tp + fn) if (tp + fn) else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
            f1s.append(f1)
        ax.bar(x + off, f1s, w, label=ckpt, color=color)
    ax.set_xticks(x); ax.set_xticklabels([labels[i + 1] for i in range(5)], rotation=20, ha="right")
    ax.set_ylabel("F1"); ax.set_title("Layer ablation F1, old vs new checkpoint")
    ax.legend()
    save(fig, "fig_ablation_summary_updated")


def fig_ext_roc(results):
    fig, ax = plt.subplots(figsize=(4, 3.6))
    for ckpt, color in [("original", "#7f7f7f"), ("finetuned", "#d62728")]:
        p = ROOT / "b3_eval" / "v25_finetune" / "results" / "paper_reruns" / f"external_eval_results__{ckpt}.json"
        d = json.loads(p.read_text())
        pts = d["roc"]["points_sample"]
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=color,
                 label=f"{ckpt} (AUC={d['roc']['auc']:.3f})")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title("ROC — External Semantic Corpus (n=117)")
    ax.legend(fontsize=8)
    save(fig, "fig_ext_roc_updated")


def fig_adaptive(results):
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    asr = {}
    for ckpt in ("original", "finetuned"):
        p = ROOT / "b3_eval" / "v25_finetune" / "results" / "paper_reruns" / f"adaptive_attack_results__{ckpt}.json"
        d = json.loads(p.read_text())
        res = d["results"]
        n = len(res)
        evaded = sum(1 for r in res if r.get("outcome") == "EVADED")
        asr[ckpt] = evaded / n
    ax.bar(["original", "finetuned"], [asr["original"], asr["finetuned"]], color=["#7f7f7f", "#d62728"])
    for i, ck in enumerate(("original", "finetuned")):
        ax.text(i, asr[ck] + 0.01, f"{asr[ck]*100:.1f}%", ha="center")
    ax.set_ylim(0, 1.05); ax.set_ylabel("Attack Success Rate")
    ax.set_title("Adaptive attack ASR, old vs new checkpoint")
    save(fig, "fig_adaptive_asr_updated")
    results["adaptive_asr"] = asr


def fig_deployment_latency(results):
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    lat = {}
    orig = json.loads((ROOT / "deployment_eval" / "results" / "deployment_eval_results.json").read_text())
    ft = json.loads((AB / "deployment_eval_finetuned.json").read_text())
    for label, d, color in [("original", orig, "#7f7f7f"), ("finetuned", ft, "#d62728")]:
        wall = [r["wall_ms"] for r in d["per_message"]]
        lat[label] = {"mean": float(np.mean(wall)), "p50": float(np.percentile(wall, 50)),
                      "p95": float(np.percentile(wall, 95)), "p99": float(np.percentile(wall, 99))}
        ax.hist(wall, bins=40, alpha=0.5, label=label, color=color, density=True)
    ax.set_xlabel("Per-message wall time (ms)"); ax.set_ylabel("Density")
    ax.set_title("SUMO-replay deployment latency, old vs new checkpoint")
    ax.legend()
    save(fig, "fig_deployment_latency_updated")
    results["deployment_latency_ms"] = lat


def main():
    results = {}
    fig_roc_pr(results)
    fig_calibration(results)
    fig_confusion(results)
    fig_per_family(results)
    fig_ablation_summary(results)
    fig_ext_roc(results)
    fig_adaptive(results)
    fig_deployment_latency(results)
    (OUT / "updated_figures_data.json").write_text(json.dumps(results, indent=2, default=str))
    print("Wrote figures to", OUT)
    print(json.dumps({k: v for k, v in results.items() if not isinstance(v, dict) or len(str(v)) < 500}, indent=2, default=str))


if __name__ == "__main__":
    main()
