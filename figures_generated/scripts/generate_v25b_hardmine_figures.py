"""
figures_generated/scripts/generate_v25b_hardmine_figures.py
===============================================================
Real figures for STBV-Bench v2.5b against the CURRENT final checkpoint
(semantic_gate_v3_mixed_lora_hardmine_merged), generated from the actual
per-sample data already produced this pass:
  - direct-classifier P(malicious): eval_hardmine_v25b's underlying scores
    (recomputed here directly for the confusion matrix / ROC / PR, since
    eval_hardmine_v25b.py reported aggregate metrics but did not dump
    per-sample scores to a CSV)
  - full-pipeline decision + raw ensembled score:
    b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_5.csv
Fills the gap noted in FINAL_FIGURES_REPORT.md: v2.5b previously had table
numbers only, no dedicated confusion-matrix/ROC/PR figure like STBV v1 has.
"""
import csv, pathlib, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "figures_generated"
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

# ---- Full-pipeline confusion matrix + decision distribution ----
rows = list(csv.DictReader(open(ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_5.csv", encoding="utf-8")))
tp = sum(1 for r in rows if r["decision"] != "ACCEPT" and r["is_attacker"] == "True")
fn = sum(1 for r in rows if r["decision"] == "ACCEPT" and r["is_attacker"] == "True")
fp = sum(1 for r in rows if r["decision"] != "ACCEPT" and r["is_attacker"] == "False")
tn = sum(1 for r in rows if r["decision"] == "ACCEPT" and r["is_attacker"] == "False")

fig, ax = plt.subplots(figsize=(3.2, 3.0))
mat = np.array([[tn, fp], [fn, tp]])
im = ax.imshow(mat, cmap="Greys", vmin=0)
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{mat[i, j]:,}", ha="center", va="center",
                 color="white" if mat[i, j] > mat.max() / 2 else "black", fontsize=10)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Accept", "Caution/Reject"])
ax.set_yticks([0, 1]); ax.set_yticklabels(["Benign", "Malicious"])
ax.set_xlabel("Predicted"); ax.set_ylabel("Ground truth")
ax.set_title("Full Pipeline, STBV-Bench v2.5b\n(current final checkpoint)")
plt.tight_layout()
plt.savefig(OUT / "fig_confusion_v25b_hardmine.pdf")
plt.close()
print(f"[confusion] tp={tp} fp={fp} fn={fn} tn={tn}")

# ---- Direct-classifier ROC/PR (re-score fresh, matching eval_hardmine_v25b.py's model) ----
from b3_eval.v25_finetune.eval_common import load_jsonl, LoadedModel  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402
import torch  # noqa: E402

MODEL_DIR = ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_hardmine_merged"
V25B = ROOT / "data/stbv_bench/v25b/stbv_bench_v25b.jsonl"

device = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR), local_files_only=True).to(device)
lm = LoadedModel(str(MODEL_DIR.name), model, tok, device, temperature=1.0)

bench_rows = load_jsonl(V25B)
texts = [r["text"] for r in bench_rows]
labels = np.array([int(r["label"]) for r in bench_rows])
preds = lm.predict(texts, batch_size=64)
scores = np.array([p["prob_malicious"] for p in preds])

order = np.argsort(-scores)
labels_sorted = labels[order]
P = labels.sum(); N = len(labels) - P
tps = np.cumsum(labels_sorted); fps = np.cumsum(1 - labels_sorted)
tpr = np.concatenate([[0], tps / P]); fpr = np.concatenate([[0], fps / N])
precision = np.concatenate([[1.0], tps / (tps + fps)]); recall = tpr
roc_auc = np.trapezoid(tpr, fpr)
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
plt.savefig(OUT / "fig_roc_pr_v25b_hardmine.pdf")
plt.close()
print(f"[roc/pr] roc_auc={roc_auc:.4f} pr_auc={pr_auc:.4f}")

# sanity check against eval_hardmine_v25b.py's already-reported ROC AUC (0.9892)
assert abs(roc_auc - 0.9892) < 0.002, f"ROC AUC mismatch: {roc_auc} vs expected ~0.9892"
print("[ok] ROC AUC matches previously reported value -- not stale")
