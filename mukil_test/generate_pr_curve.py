#!/usr/bin/env python3
# =====================================================================
# generate_pr_curve.py  --  Precision-Recall + AP + CI band  (Fig. F7)
# ---------------------------------------------------------------------
#   results/pr.json         average precision + 95% CI
#   figures/F7_pr.pdf
#
# INPUT SCHEMA (results/scores.json):
#   {"y_true":[0/1 ...], "score":[float P(malicious) ...]}
#
# RUN:  python generate_pr_curve.py                    # demo
#       python generate_pr_curve.py --input results/scores.json
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, load_json_or_demo, save_json, savefig,
                         pr_curve, average_precision, bootstrap_scalar,
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

    d, is_demo = load_json_or_demo(args.input, demo, "PR")
    y = np.asarray(d["y_true"]); s = np.asarray(d["score"], float)
    prevalence = float(y.mean())

    recall, precision = pr_curve(y, s)
    ap_val = average_precision(y, s)
    ap_ci = bootstrap_scalar(y, s, average_precision, n=args.nboot, seed=args.seed)

    grid = np.linspace(0, 1, 101)
    rng = np.random.default_rng(args.seed); n = len(y); curves = []
    for _ in range(args.nboot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        r, p = pr_curve(y[idx], s[idx])
        # interpolate precision on recall grid (recall is nondecreasing)
        curves.append(np.interp(grid, r, p))
    curves = np.array(curves)
    lo = np.percentile(curves, 2.5, axis=0); hi = np.percentile(curves, 97.5, axis=0)

    save_json({"demo": is_demo, "ap": ap_val, "ap_ci95": list(ap_ci),
               "prevalence": prevalence}, os.path.join(args.outdir, "results/pr.json"))

    fig, ax = plt.subplots(figsize=(3.3, 3.1))
    ax.fill_between(grid, lo, hi, color=ACC, alpha=0.18, linewidth=0, label="95% CI")
    ax.plot(recall, precision, color=ACC, lw=1.6, label=f"PR (AP = {ap_val:.3f})")
    ax.axhline(prevalence, color=NEUTRAL, lw=0.8, ls="--",
               label=f"no-skill ({prevalence:.2f})")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall", loc="left", fontsize=9, fontweight="bold")
    ax.legend(fontsize=6.6, frameon=False, loc="lower left")
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F7_pr.pdf"))
    print(f"  AP = {ap_val:.3f}  CI95 = [{ap_ci[0]:.3f}, {ap_ci[1]:.3f}]  prevalence={prevalence:.3f}")


if __name__ == "__main__":
    main()
