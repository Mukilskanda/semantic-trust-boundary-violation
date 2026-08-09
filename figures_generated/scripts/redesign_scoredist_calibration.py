import pathlib, sys, math
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


def gaussian_kde_1d(x, grid, bw=None):
    """Standard Gaussian KDE, Silverman's rule bandwidth -- no fabrication,
    a textbook density estimator applied to the exact same real scores."""
    n = len(x)
    if bw is None:
        std = np.std(x) if np.std(x) > 1e-6 else 0.05
        bw = 1.06 * std * n ** (-1 / 5)
        bw = max(bw, 0.01)
    diffs = (grid[:, None] - x[None, :]) / bw
    dens = np.exp(-0.5 * diffs ** 2).sum(axis=1) / (n * bw * math.sqrt(2 * math.pi))
    return dens


# ---- Score distribution: histogram + KDE overlay ----
ben = scores[labels == 0]; mal = scores[labels == 1]
grid = np.linspace(0, 1, 400)
fig, ax = plt.subplots(figsize=(4.6, 3.0))
bins = np.linspace(0, 1, 31)
ax.hist(ben, bins=bins, density=True, alpha=0.35, color=ps.BENIGN_C, label=f"Benign (n={len(ben)})")
ax.hist(mal, bins=bins, density=True, alpha=0.35, color=ps.MALICIOUS_C, label=f"Malicious (n={len(mal)})")
ax.plot(grid, gaussian_kde_1d(ben, grid), color=ps.BENIGN_C, lw=2.2)
ax.plot(grid, gaussian_kde_1d(mal, grid), color=ps.MALICIOUS_C, lw=2.2)
ax.set_xlabel("B3 P(malicious)"); ax.set_ylabel("Density")
ax.set_xlim(0, 1)
ax.legend(loc="upper center")
ax.set_title("B3 Score Distribution, STBV-Bench v2.5b\nCurrent Final Checkpoint", fontsize=10)
plt.tight_layout()
ps.save(fig, OUT / "fig_v25b_score_dist")
plt.close()
print(f"[score_dist] n_ben={len(ben)} n_mal={len(mal)}")

# ---- Calibration: reliability diagram + confidence histogram underneath + ECE box ----
T = 3.18
def apply_T(p, T):
    p = min(max(p, 1e-9), 1 - 1e-9)
    logit = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-(logit / T)))

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

fig, axes = plt.subplots(2, 1, figsize=(3.6, 4.2), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
axes[0].plot([0, 1], [0, 1], "--", color=ps.GREY, lw=1.0, label="Perfect calibration")
axes[0].plot(bin_conf, bin_acc, "o-", color=ps.BLUE, lw=2.2, markersize=6)
axes[0].set_ylabel("Empirical accuracy")
axes[0].set_xlim(0, 1); axes[0].set_ylim(0, 1)
axes[0].legend(loc="upper left")
axes[0].text(0.97, 0.06, f"ECE = {ece:.4f}", ha="right", va="bottom", fontsize=9, transform=axes[0].transAxes,
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=ps.GREY, lw=0.8))
axes[0].set_title(f"Calibration, STBV-Bench v2.5b (T={T})", fontsize=10)

axes[1].hist(conf, bins=bin_edges, color=ps.BLUE, alpha=0.6)
axes[1].set_xlabel("Mean predicted confidence"); axes[1].set_ylabel("Count")
plt.tight_layout()
ps.save(fig, OUT / "fig_v25b_calibration")
plt.close()
print(f"[calibration] T={T} ECE={ece:.4f}")
