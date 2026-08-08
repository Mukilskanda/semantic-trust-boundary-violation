import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = pathlib.Path("figures_generated")
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

rows = list(csv.DictReader(open("b3_eval/v25_finetune/ablation_results/final/v1_pmalicious.csv", encoding="utf-8")))
scores = np.array([float(r["p_malicious"]) for r in rows])
labels = np.array([1 if r["is_attacker"] == "True" else 0 for r in rows])

order = np.argsort(-scores)
labels_sorted = labels[order]
P = labels.sum(); N = len(labels) - P
tps = np.cumsum(labels_sorted)
fps = np.cumsum(1 - labels_sorted)
tpr = np.concatenate([[0], tps / P])
fpr = np.concatenate([[0], fps / N])
precision = np.concatenate([[1.0], tps / (tps + fps)])
recall = tpr

roc_auc = np.trapezoid(tpr, fpr)
# sort by recall ascending for a valid PR-AUC integral
pr_order = np.argsort(recall)
pr_auc = np.trapezoid(precision[pr_order], recall[pr_order])

fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8))
axes[0].plot(fpr, tpr, color="black", lw=1.3)
axes[0].plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
axes[0].set_xlabel("False Positive Rate"); axes[0].set_ylabel("True Positive Rate")
axes[0].set_title(f"ROC (AUC={roc_auc:.4f})")
axes[1].plot(recall, precision, color="black", lw=1.3)
axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
axes[1].set_title(f"PR (AUC={pr_auc:.4f})")
plt.tight_layout()
plt.savefig(OUT / "fig_roc_pr_v1_final.pdf")
plt.close()
print("roc_auc", roc_auc, "pr_auc", pr_auc)

fig, ax = plt.subplots(figsize=(4.2, 2.8))
ben = scores[labels == 0]; mal = scores[labels == 1]
bins = np.linspace(0, 1, 31)
ax.hist(ben, bins=bins, alpha=0.55, label=f"Benign (n={len(ben)})", color="0.7", edgecolor="black", linewidth=0.3)
ax.hist(mal, bins=bins, alpha=0.55, label=f"Malicious (n={len(mal)})", color="0.25", edgecolor="black", linewidth=0.3)
ax.set_xlabel("B3 P(malicious)"); ax.set_ylabel("Count")
ax.legend(fontsize=7)
ax.set_title("B3 Score Distribution, STBV v1, Final Checkpoint")
plt.tight_layout()
plt.savefig(OUT / "fig_score_dist_v1_final.pdf")
plt.close()

# Calibration curve (reliability diagram), 15 bins
n_bins = 15
bin_edges = np.linspace(0, 1, n_bins + 1)
bin_acc, bin_conf, bin_n = [], [], []
preds_bin = (scores >= 0.5).astype(int)
conf = np.where(preds_bin == 1, scores, 1 - scores)
correct = (preds_bin == labels).astype(int)
for i in range(n_bins):
    mask = (conf >= bin_edges[i]) & (conf < bin_edges[i + 1] if i < n_bins - 1 else conf <= bin_edges[i + 1])
    if mask.sum() == 0:
        continue
    bin_acc.append(correct[mask].mean())
    bin_conf.append(conf[mask].mean())
    bin_n.append(mask.sum())
ece = sum(n * abs(a - c) for n, a, c in zip(bin_n, bin_acc, bin_conf)) / len(scores)

fig, ax = plt.subplots(figsize=(3.4, 3.0))
ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
ax.plot(bin_conf, bin_acc, "o-", color="black", lw=1.2, markersize=3)
ax.set_xlabel("Mean predicted confidence"); ax.set_ylabel("Empirical accuracy")
ax.set_title(f"Calibration, STBV v1 (ECE={ece:.4f})")
plt.tight_layout()
plt.savefig(OUT / "fig_calibration_v1_final.pdf")
plt.close()
print("ece", ece)
print("[ok] fixed figures written")
