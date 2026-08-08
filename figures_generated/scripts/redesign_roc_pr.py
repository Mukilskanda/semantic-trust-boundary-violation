import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "figures_generated"

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

fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0))
axes[0].plot(fpr, tpr, color=ps.BLUE, lw=2.4, solid_capstyle="round")
axes[0].plot([0, 1], [0, 1], "--", color=ps.GREY, lw=1.0)
axes[0].set_xlabel("False Positive Rate"); axes[0].set_ylabel("True Positive Rate")
axes[0].set_xlim(-0.02, 1.02); axes[0].set_ylim(-0.02, 1.02)
axes[0].text(0.97, 0.06, f"AUC = {roc_auc:.4f}", ha="right", va="bottom", fontsize=9,
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=ps.GREY, lw=0.8))
axes[0].set_title("ROC", fontsize=10)

axes[1].plot(recall, precision, color=ps.BLUE, lw=2.4, solid_capstyle="round")
axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
axes[1].set_xlim(-0.02, 1.02); axes[1].set_ylim(min(precision.min(), 0.55) - 0.02, 1.02)
axes[1].text(0.97, 0.06, f"AP = {pr_auc:.4f}", ha="right", va="bottom", fontsize=9,
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=ps.GREY, lw=0.8))
axes[1].set_title("Precision--Recall", fontsize=10)

plt.tight_layout()
ps.save(fig, OUT / "fig_v25b_roc")
plt.close()
print(f"[ok] roc_auc={roc_auc:.4f} pr_auc={pr_auc:.4f}")
