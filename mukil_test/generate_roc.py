#!/usr/bin/env python3
# =====================================================================
# generate_roc.py  --  ROC curve + AUC + bootstrap CI band  (Fig. F6)
# ---------------------------------------------------------------------
#   results/roc.json        auc + 95% CI
#   figures/F6_roc.pdf
#
# INPUT SCHEMA (results/scores.json):
#   {"y_true":[0/1 ...], "score":[float P(malicious) in 0..1 ...]}
#
# RUN:  python generate_roc.py                         # demo
#       python generate_roc.py --input results/scores.json
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, load_json_or_demo, save_json, savefig,
                         roc_curve, auc_trapz, average_precision, bootstrap_scalar,
                         demo_scores, ACC, NEUTRAL, INK)
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/scores.json")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--nboot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    set_style()

    def demo():
        y, s = demo_scores(seed=args.seed)
        return {"y_true": y.tolist(), "score": s.tolist()}

    d, is_demo = load_json_or_demo(args.input, demo, "ROC")
    y = np.asarray(d["y_true"]); s = np.asarray(d["score"], float)

    fpr, tpr = roc_curve(y, s)
    auc = auc_trapz(fpr, tpr)
    auc_ci = bootstrap_scalar(y, s, lambda a, b: auc_trapz(*roc_curve(a, b)),
                              n=args.nboot, seed=args.seed)

    # bootstrap TPR band on a fixed FPR grid
    grid = np.linspace(0, 1, 101)
    rng = np.random.default_rng(args.seed); n = len(y); curves = []
    for _ in range(args.nboot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        f, t = roc_curve(y[idx], s[idx])
        curves.append(np.interp(grid, f, t))
    curves = np.array(curves)
    lo = np.percentile(curves, 2.5, axis=0); hi = np.percentile(curves, 97.5, axis=0)

    save_json({"demo": is_demo, "auc": auc, "auc_ci95": list(auc_ci),
               "ap": average_precision(y, s)}, os.path.join(args.outdir, "results/roc.json"))

    fig, ax = plt.subplots(figsize=(3.3, 3.1))
    ax.fill_between(grid, lo, hi, color=ACC, alpha=0.18, linewidth=0, label="95% CI")
    ax.plot(fpr, tpr, color=ACC, lw=1.6,
            label=f"ROC (AUC = {auc:.3f})")
    ax.plot([0, 1], [0, 1], color=NEUTRAL, lw=0.8, ls="--", label="chance")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC", loc="left", fontsize=9, fontweight="bold")
    ax.legend(fontsize=6.6, frameon=False, loc="lower right")
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F6_roc.pdf"))
    print(f"  AUC = {auc:.3f}  CI95 = [{auc_ci[0]:.3f}, {auc_ci[1]:.3f}]")


if __name__ == "__main__":
    main()
