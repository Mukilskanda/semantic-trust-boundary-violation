"""
figures_generated/scripts/generate_v1_consolidated.py
=========================================================
Consolidates the two separate STBV-Bench v1 figures (confusion matrix,
ROC/PR) into one 3-panel figure, since v1 is now this paper's
supplementary (not primary) benchmark and does not warrant two full
figure slots. Real data only: reuses the same
b3_eval/v25_finetune/ablation_results/final/v1_pmalicious.csv the
original two figures were built from -- no new computation, pure
consolidation for figure-count reduction.
"""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
plt.rcParams.update({"font.size": 8, "figure.dpi": 150})

rows = list(csv.DictReader(open(ROOT / "b3_eval/v25_finetune/ablation_results/final/v1_pmalicious.csv", encoding="utf-8")))
scores = np.array([float(r["p_malicious"]) for r in rows])
labels = np.array([1 if r["is_attacker"] == "True" else 0 for r in rows])

order = np.argsort(-scores)
labels_sorted = labels[order]
P = labels.sum(); N = len(labels) - P
tps = np.cumsum(labels_sorted); fps = np.cumsum(1 - labels_sorted)
tpr = np.concatenate([[0], tps / P]); fpr = np.concatenate([[0], fps / N])
precision = np.concatenate([[1.0], tps / (tps + fps)]); recall = tpr
roc_auc = np.trapezoid(tpr, fpr)
pr_order = np.argsort(recall)
pr_auc = np.trapezoid(precision[pr_order], recall[pr_order])

# real confusion counts from the config-5 rerun (fusion, not raw score) --
# TN=2924 FP=69 FN=0 TP=7007, already published and unchanged
mat = np.array([[2924, 69], [0, 7007]])

fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.4))
im = axes[0].imshow(mat, cmap="Greys", vmin=0)
for i in range(2):
    for j in range(2):
        axes[0].text(j, i, f"{mat[i, j]:,}", ha="center", va="center", fontsize=8,
                      color="white" if mat[i, j] > mat.max() / 2 else "black")
axes[0].set_xticks([0, 1]); axes[0].set_xticklabels(["Accept", "Caution/Reject"], fontsize=6)
axes[0].set_yticks([0, 1]); axes[0].set_yticklabels(["Benign", "Malicious"], fontsize=6)
axes[0].set_title("Confusion (full stack)", fontsize=8)

axes[1].plot(fpr, tpr, color="black", lw=1.3)
axes[1].plot([0, 1], [0, 1], "--", color="0.6", lw=0.8)
axes[1].set_xlabel("FPR", fontsize=7); axes[1].set_ylabel("TPR", fontsize=7)
axes[1].set_title(f"ROC (AUC={roc_auc:.3f})", fontsize=8)

axes[2].plot(recall, precision, color="black", lw=1.3)
axes[2].set_xlabel("Recall", fontsize=7); axes[2].set_ylabel("Precision", fontsize=7)
axes[2].set_title(f"PR (AUC={pr_auc:.4f})", fontsize=8)

fig.suptitle("STBV-Bench v1, Prior (Pass 1) Checkpoint -- Supplementary", fontsize=8, y=1.02)
plt.tight_layout()
plt.savefig(OUT / "fig_v1_consolidated.pdf", bbox_inches="tight")
plt.close()
print(f"[ok] roc_auc={roc_auc:.4f} pr_auc={pr_auc:.4f} (must match 1.000/0.9998)")
