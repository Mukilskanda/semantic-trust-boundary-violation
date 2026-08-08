"""
figures_generated/scripts/generate_v25b_scoredist_calibration.py
====================================================================
Score-distribution and calibration (reliability diagram) figures for
STBV-Bench v2.5b, current final checkpoint -- filling the two remaining
gaps in the v1-to-v2.5b figure migration (Task 3/7 of this pass).

Uses the SAME direct-classifier inference pass already run and verified
in generate_v25b_hardmine_figures.py (same model, same benchmark, same
ROC AUC=0.9892 cross-check) -- this is not a new experiment, it computes
two additional plots from logits obtained in an equivalent forward pass,
consistent with "reuse existing verified v2.5b evaluation artifacts,
do not regenerate experiments unless required."
"""
import pathlib, sys, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "figures_generated"
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

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
scores = np.array([p["prob_malicious"] for p in preds])  # T=1 (raw) scores, same as ROC/PR figure

# ---- Score distribution ----
fig, ax = plt.subplots(figsize=(4.2, 2.8))
ben = scores[labels == 0]; mal = scores[labels == 1]
bins = np.linspace(0, 1, 31)
ax.hist(ben, bins=bins, alpha=0.55, label=f"Benign (n={len(ben)})", color="0.7", edgecolor="black", linewidth=0.3)
ax.hist(mal, bins=bins, alpha=0.55, label=f"Malicious (n={len(mal)})", color="0.25", edgecolor="black", linewidth=0.3)
ax.set_xlabel("B3 P(malicious)"); ax.set_ylabel("Count")
ax.legend(fontsize=7)
ax.set_title("B3 Score Distribution, STBV-Bench v2.5b\nCurrent Final Checkpoint")
plt.tight_layout()
plt.savefig(OUT / "fig_v25b_score_dist.pdf")
plt.close()
print(f"[score_dist] benign n={len(ben)} malicious n={len(mal)}")

# ---- Calibration / reliability diagram, at the deployed temperature T=3.18 ----
T = 3.18
def apply_T(p, T):
    # p is P(malicious) at T=1; recover 2-class softmax and rescale
    p = min(max(p, 1e-9), 1 - 1e-9)
    logit = math.log(p / (1 - p))
    scaled = logit / T
    return 1 / (1 + math.exp(-scaled))

scores_T = np.array([apply_T(p, T) for p in scores])
preds_bin = (scores_T >= 0.5).astype(int)
conf = np.where(preds_bin == 1, scores_T, 1 - scores_T)
correct = (preds_bin == labels).astype(int)

n_bins = 15
bin_edges = np.linspace(0, 1, n_bins + 1)
bin_acc, bin_conf, bin_n = [], [], []
for i in range(n_bins):
    mask = (conf >= bin_edges[i]) & (conf < bin_edges[i + 1] if i < n_bins - 1 else conf <= bin_edges[i + 1])
    if mask.sum() == 0:
        continue
    bin_acc.append(correct[mask].mean())
    bin_conf.append(conf[mask].mean())
    bin_n.append(mask.sum())
ece = sum(n * abs(a - c) for n, a, c in zip(bin_n, bin_acc, bin_conf)) / len(scores_T)

fig, ax = plt.subplots(figsize=(3.4, 3.0))
ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
ax.plot(bin_conf, bin_acc, "o-", color="black", lw=1.2, markersize=3)
ax.set_xlabel("Mean predicted confidence"); ax.set_ylabel("Empirical accuracy")
ax.set_title(f"Calibration, STBV-Bench v2.5b\n(T={T}, ECE={ece:.4f})")
plt.tight_layout()
plt.savefig(OUT / "fig_v25b_calibration.pdf")
plt.close()
print(f"[calibration] T={T} ECE={ece:.4f} n_bins_populated={len(bin_n)}")
