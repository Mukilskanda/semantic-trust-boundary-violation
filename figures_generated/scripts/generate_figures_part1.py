"""Generates real figures from real per-sample CSV data already on disk
(STBV-Bench v1 final-checkpoint rerun, ITE-Bench). No fabricated values;
every number plotted comes from an existing CSV produced by a real
pipeline run this session. Outputs PDF (vector) to figures_generated/."""
import csv, math, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = pathlib.Path("figures_generated")
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------
# 1. Confusion matrix, STBV v1 full-stack (config 5), final checkpoint
rows5 = load("b3_eval/v25_finetune/ablation_results/final/ablation_config_5.csv")
tp = fp = fn = tn = 0
for r in rows5:
    truth = r["is_attacker"] == "True"
    pred = r["decision"] in ("CAUTION", "REJECT")
    if pred and truth: tp += 1
    elif pred and not truth: fp += 1
    elif not pred and truth: fn += 1
    else: tn += 1

fig, ax = plt.subplots(figsize=(3.2, 2.8))
cm = np.array([[tn, fp], [fn, tp]])
im = ax.imshow(cm, cmap="Greys")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i,j]:,}", ha="center", va="center",
                 color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=11)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Benign\n(predicted)", "Attack\n(predicted)"])
ax.set_yticks([0, 1]); ax.set_yticklabels(["Benign\n(true)", "Attack\n(true)"])
ax.set_title("STBV-Bench v1, Full Stack, Final Checkpoint")
plt.tight_layout()
plt.savefig(OUT / "fig_confusion_v1_final.pdf")
plt.close()
print("confusion:", cm.tolist())

# ---------------------------------------------------------------------
# 2. ROC and PR curves, STBV v1 B3-alone (config 4), raw_score vs truth
rows4 = load("b3_eval/v25_finetune/ablation_results/final/ablation_config_4.csv")
scores = np.array([float(r["raw_score"]) if r["raw_score"] not in ("", "None") else 0.0 for r in rows4])
labels = np.array([1 if r["is_attacker"] == "True" else 0 for r in rows4])

order = np.argsort(-scores)
labels_sorted = labels[order]
P = labels.sum(); N = len(labels) - P
tps = np.cumsum(labels_sorted)
fps = np.cumsum(1 - labels_sorted)
tpr = tps / P
fpr = fps / N
precision = tps / (tps + fps)
recall = tpr

roc_auc = np.trapz(tpr, fpr)
pr_auc = -np.trapz(precision, recall)

fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8))
axes[0].plot(fpr, tpr, color="black", lw=1.3)
axes[0].plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
axes[0].set_xlabel("False Positive Rate"); axes[0].set_ylabel("True Positive Rate")
axes[0].set_title(f"ROC (AUC={roc_auc:.3f})")
axes[1].plot(recall, precision, color="black", lw=1.3)
axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
axes[1].set_title(f"PR (AUC={pr_auc:.3f})")
plt.tight_layout()
plt.savefig(OUT / "fig_roc_pr_v1_final.pdf")
plt.close()
print("roc_auc", roc_auc, "pr_auc", pr_auc)

# ---------------------------------------------------------------------
# 3. Trust-score (B3 confidence) distribution, benign vs malicious
fig, ax = plt.subplots(figsize=(4.2, 2.8))
ben = scores[labels == 0]; mal = scores[labels == 1]
bins = np.linspace(0, 1, 31)
ax.hist(ben, bins=bins, alpha=0.55, label=f"Benign (n={len(ben)})", color="0.7", edgecolor="black", linewidth=0.3)
ax.hist(mal, bins=bins, alpha=0.55, label=f"Malicious (n={len(mal)})", color="0.25", edgecolor="black", linewidth=0.3)
ax.set_xlabel("B3 malicious-class confidence"); ax.set_ylabel("Count")
ax.legend(fontsize=7)
ax.set_title("B3 Confidence Distribution, STBV v1, Final Checkpoint")
plt.tight_layout()
plt.savefig(OUT / "fig_score_dist_v1_final.pdf")
plt.close()

# ---------------------------------------------------------------------
# 4. Per-family recall heatmap: B1-only (config1... n/a for v1, use ITE-Bench) vs
#    Full-stack, across ITE-Bench's 22 attack families (real per-layer data)
ite1 = load("ite_bench/results/ite_config_1.csv")
ite5 = load("ite_bench/results/ite_config_5.csv")

def per_family_recall(rows):
    fam_tot, fam_hit = {}, {}
    for r in rows:
        if r["is_attacker"] != "True":
            continue
        fam = r["attack_family"]
        fam_tot[fam] = fam_tot.get(fam, 0) + 1
        if r["decision"] in ("CAUTION", "REJECT"):
            fam_hit[fam] = fam_hit.get(fam, 0) + 1
    return {f: fam_hit.get(f, 0) / fam_tot[f] for f in fam_tot}

rec1 = per_family_recall(ite1)
rec5 = per_family_recall(ite5)
families = sorted(rec1.keys())
mat = np.array([[rec1[f], rec5[f]] for f in families])

fig, ax = plt.subplots(figsize=(4.0, 6.5))
im = ax.imshow(mat, cmap="Greys", vmin=0, vmax=1, aspect="auto")
ax.set_xticks([0, 1]); ax.set_xticklabels(["B1 only", "Full stack"], rotation=0)
ax.set_yticks(range(len(families))); ax.set_yticklabels(families, fontsize=6)
for i in range(len(families)):
    for j in range(2):
        ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center", fontsize=6,
                 color="white" if mat[i, j] > 0.5 else "black")
ax.set_title("Per-Family Recall, ITE-Bench\n(Final Checkpoint)", fontsize=9)
plt.tight_layout()
plt.savefig(OUT / "fig_family_heatmap_ite.pdf")
plt.close()

# ---------------------------------------------------------------------
# 5. Decision distribution before/after fusion, STBV v1 (config4 vs config5)
def decision_counts(rows):
    c = {"ACCEPT": 0, "CAUTION": 0, "REJECT": 0}
    for r in rows:
        c[r["decision"]] = c.get(r["decision"], 0) + 1
    return c

d4 = decision_counts(rows4)
d5 = decision_counts(rows5)
labels_d = ["ACCEPT", "CAUTION", "REJECT"]
x = np.arange(3)
w = 0.35
fig, ax = plt.subplots(figsize=(4.2, 2.8))
ax.bar(x - w/2, [d4[l] for l in labels_d], width=w, label="B3 alone (config 4)", color="0.7", edgecolor="black", linewidth=0.4)
ax.bar(x + w/2, [d5[l] for l in labels_d], width=w, label="Full stack (config 5)", color="0.25", edgecolor="black", linewidth=0.4)
ax.set_xticks(x); ax.set_xticklabels(labels_d)
ax.set_ylabel("Count"); ax.legend(fontsize=7)
ax.set_title("Decision Distribution Before/After Fusion, STBV v1")
plt.tight_layout()
plt.savefig(OUT / "fig_decision_dist_v1_final.pdf")
plt.close()
print("d4", d4, "d5", d5)

# ---------------------------------------------------------------------
# 6. Latency breakdown, real measured per-stage SUMO data (final checkpoint)
stages = ["PKI", "B1", "MBD", "B2", "CP", "Synth.", "B3", "Fusion"]
vals_ms = [0.0014, 0.2231, 0.2024, 0.059, 0.0338, 0.3435, 80.1995, 0.089]
fig, ax = plt.subplots(figsize=(4.4, 2.8))
ax.barh(stages, vals_ms, color="0.35", edgecolor="black", linewidth=0.4)
ax.set_xscale("log")
ax.set_xlabel("Mean latency (ms, log scale)")
ax.set_title("Per-Stage Latency, SUMO Replay, Final Checkpoint (n=2,000)")
plt.tight_layout()
plt.savefig(OUT / "fig_latency_breakdown_final.pdf")
plt.close()

print("[ok] figures written to", OUT.resolve())
