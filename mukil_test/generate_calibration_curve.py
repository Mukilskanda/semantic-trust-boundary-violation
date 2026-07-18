#!/usr/bin/env python3
# =====================================================================
# generate_calibration_curve.py  --  reliability diagram + temp scaling
#                                     (Fig. F9, Table T9)
# ---------------------------------------------------------------------
#   results/calibration.json    ECE/MCE/Brier pre & post temperature
#   tables/T9_calibration.tex
#   figures/F9_calibration.pdf   reliability diagram (pre vs post)
#
# INPUT SCHEMA (results/scores.json):
#   {"y_true":[0/1...], "score":[float P(malicious)...]}
#   Optional held-out val for fitting T: --val-input results/scores_val.json
#   (best practice: fit T on val, report on test)
#
# RUN:  python generate_calibration_curve.py                # demo
#       python generate_calibration_curve.py --input results/scores.json \
#             --val-input results/scores_val.json
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, load_json_or_demo, save_json,
                         save_latex_table, savefig, ece_mce_brier, fit_temperature,
                         apply_temperature, demo_scores, ACC, THREAT, NEUTRAL, INK)
import matplotlib.pyplot as plt


def reliability_xy(cal):
    xs, ys = [], []
    for b in cal["bins"]:
        if b["n"] > 0:
            xs.append(b["conf"]); ys.append(b["acc"])
    return xs, ys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/scores.json")
    ap.add_argument("--val-input", default=None)
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()
    set_style()

    def demo():
        # mildly mis-calibrated demo scores (direction depends on data;
        # on real overconfident B3 outputs the fitted T will be >1 and soften).
        y, s = demo_scores(seed=args.seed)
        p = np.clip(s, 1e-4, 1 - 1e-4)
        logit = np.log(p / (1 - p))
        s = 1 / (1 + np.exp(-2.2 * logit))
        return {"y_true": y.tolist(), "score": s.tolist()}

    d, is_demo = load_json_or_demo(args.input, demo, "CALIBRATION")
    y = np.asarray(d["y_true"]).astype(int); p = np.asarray(d["score"], float)

    # fit temperature on val if given, else on the same data (warn)
    if args.val_input and os.path.exists(args.val_input):
        import json
        with open(args.val_input) as f:
            v = json.load(f)
        T = fit_temperature(np.asarray(v["y_true"]), np.asarray(v["score"], float))
    else:
        if not is_demo:
            print("  [warn] no --val-input; fitting T on the test data (report as such).")
        T = fit_temperature(y, p)
    p_post = apply_temperature(p, T)

    pre = ece_mce_brier(y, p, bins=args.bins)
    post = ece_mce_brier(y, p_post, bins=args.bins)
    save_json({"demo": is_demo, "temperature": T, "pre": {k: pre[k] for k in ("ece", "mce", "brier")},
               "post": {k: post[k] for k in ("ece", "mce", "brier")}},
              os.path.join(args.outdir, "results/calibration.json"))

    save_latex_table(
        ["Metric", "Pre", "Post ($T{=}%.2f$)" % T],
        [["ECE", f"{pre['ece']:.3f}", f"{post['ece']:.3f}"],
         ["MCE", f"{pre['mce']:.3f}", f"{post['mce']:.3f}"],
         ["Brier", f"{pre['brier']:.3f}", f"{post['brier']:.3f}"]],
        "Calibration before and after post-hoc temperature scaling.",
        "tab:calibration", os.path.join(args.outdir, "tables/T9_calibration.tex"), align="lcc")

    fig, ax = plt.subplots(figsize=(3.3, 3.1))
    ax.plot([0, 1], [0, 1], color=NEUTRAL, lw=0.9, ls="--", label="perfect")
    xs, ys = reliability_xy(pre)
    ax.plot(xs, ys, color=THREAT, marker="o", markersize=3.5, lw=1.4,
            label=f"pre (ECE={pre['ece']:.3f})")
    xs2, ys2 = reliability_xy(post)
    ax.plot(xs2, ys2, color=ACC, marker="s", markersize=3.5, lw=1.4,
            label=f"post (ECE={post['ece']:.3f})")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("Confidence"); ax.set_ylabel("Empirical accuracy")
    ax.set_title("Reliability diagram", loc="left", fontsize=9, fontweight="bold")
    ax.legend(fontsize=6.6, frameon=False, loc="upper left")
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F9_calibration.pdf"))
    print(f"  T={T:.2f}  ECE {pre['ece']:.3f} -> {post['ece']:.3f}  "
          f"Brier {pre['brier']:.3f} -> {post['brier']:.3f}")


if __name__ == "__main__":
    main()
