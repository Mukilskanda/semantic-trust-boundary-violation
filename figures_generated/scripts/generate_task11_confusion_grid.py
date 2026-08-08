"""
figures_generated/scripts/generate_task11_confusion_grid.py
===============================================================
Six confusion matrices (one per realizable ablation configuration),
STBV-Bench v2.5b, current final checkpoint, in one figure grid.
Real counts, no estimation.
"""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"
plt.rcParams.update({"font.size": 8, "figure.dpi": 150})

CONFIG_LABELS = {1: "Traditional (B1)", 2: "+B2", 3: "+CP", 4: "B3 only",
                  6: "B1+B2+B3 (no CP)", 5: "Full STBV Framework"}


def confusion(rows):
    tp = fp = fn = tn = 0
    for r in rows:
        y = r["is_attacker"] == "True"
        p = r["decision"] != "ACCEPT"
        if p and y: tp += 1
        elif p and not y: fp += 1
        elif not p and y: fn += 1
        else: tn += 1
    return np.array([[tn, fp], [fn, tp]])


fig, axes = plt.subplots(2, 3, figsize=(7.0, 4.6))
order = [1, 2, 3, 4, 6, 5]
for ax, cfg in zip(axes.flat, order):
    rows = list(csv.DictReader(open(V25B_HM / f"config_{cfg}.csv", encoding="utf-8")))
    mat = confusion(rows)
    im = ax.imshow(mat, cmap="Greys", vmin=0)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{mat[i, j]:,}", ha="center", va="center", fontsize=8,
                     color="white" if mat[i, j] > mat.max() / 2 else "black")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Accept", "Caution/Reject"], fontsize=6)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Benign", "Malicious"], fontsize=6)
    ax.set_title(CONFIG_LABELS[cfg], fontsize=8)

fig.suptitle("Confusion Matrices, STBV-Bench v2.5b, Current Final Checkpoint ($n{=}10{,}098$ each)", fontsize=9)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUT / "fig_confusion_grid_v25b.pdf")
plt.close()
print("[ok] fig_confusion_grid_v25b.pdf")
