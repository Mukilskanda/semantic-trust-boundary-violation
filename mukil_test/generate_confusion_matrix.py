#!/usr/bin/env python3
# =====================================================================
# generate_confusion_matrix.py  --  confusion matrix heatmap  (Fig. F8)
# ---------------------------------------------------------------------
#   results/confusion.json   TP/FP/TN/FN + derived metrics
#   figures/F8_confusion.pdf
#
# INPUT SCHEMA — either:
#   {"y_true":[0/1...], "y_pred":[0/1...]}                    (hard labels)
#   {"y_true":[0/1...], "score":[float...]}  + --threshold    (scores)
#
# RUN:  python generate_confusion_matrix.py                  # demo
#       python generate_confusion_matrix.py --input results/scores.json --threshold 0.5
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, load_json_or_demo, save_json, savefig,
                         binary_metrics, demo_scores, ACC, THREAT, INK)
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/scores.json")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    set_style()

    def demo():
        y, s = demo_scores(seed=args.seed)
        return {"y_true": y.tolist(), "score": s.tolist()}

    d, is_demo = load_json_or_demo(args.input, demo, "CONFUSION")
    y = np.asarray(d["y_true"]).astype(int)
    if "y_pred" in d:
        yp = np.asarray(d["y_pred"]).astype(int)
    else:
        yp = (np.asarray(d["score"], float) >= args.threshold).astype(int)

    m = binary_metrics(y, yp)
    save_json({"demo": is_demo, "threshold": args.threshold, **m},
              os.path.join(args.outdir, "results/confusion.json"))

    # 2x2 matrix: rows = actual (Malicious, Benign), cols = predicted (Malicious, Benign)
    M = np.array([[m["tp"], m["fn"]],
                  [m["fp"], m["tn"]]], float)
    total = M.sum()
    fig, ax = plt.subplots(figsize=(3.2, 3.0))
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=M.max())
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Malicious", "Benign"], fontsize=8)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Malicious", "Benign"], fontsize=8)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title(f"Confusion matrix (\u03c4={args.threshold:g})",
                 loc="left", fontsize=9, fontweight="bold")
    names = [["TP", "FN"], ["FP", "TN"]]
    for i in range(2):
        for j in range(2):
            v = int(M[i, j]); pct = 100 * v / total if total else 0
            txt = ax.text(j, i, f"{names[i][j]}\n{v}\n{pct:.1f}%",
                          ha="center", va="center", fontsize=8,
                          color="white" if M[i, j] > M.max() * 0.5 else INK)
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F8_confusion.pdf"))
    print(f"  TP={m['tp']} FP={m['fp']} TN={m['tn']} FN={m['fn']} | "
          f"P={m['prec']:.3f} R={m['rec']:.3f} F1={m['f1']:.3f} FPR={m['fpr']:.3f}")


if __name__ == "__main__":
    main()
