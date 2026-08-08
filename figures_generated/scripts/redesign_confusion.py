import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"

rows = list(csv.DictReader(open(V25B_HM / "config_5.csv", encoding="utf-8")))
tp = fp = fn = tn = 0
for r in rows:
    y = r["is_attacker"] == "True"
    p = r["decision"] != "ACCEPT"
    if p and y: tp += 1
    elif p and not y: fp += 1
    elif not p and y: fn += 1
    else: tn += 1

mat = np.array([[tn, fp], [fn, tp]], dtype=float)
row_totals = mat.sum(axis=1, keepdims=True)
pct = mat / row_totals * 100

fig, ax = plt.subplots(figsize=(3.4, 3.1))
im = ax.imshow(pct, cmap=ps.SEQ_BLUE, vmin=0, vmax=100)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Accept", "Caution/Reject"])
ax.set_yticks([0, 1]); ax.set_yticklabels(["Benign", "Malicious"])
ax.tick_params(length=0)
for i in range(2):
    for j in range(2):
        color = "white" if pct[i, j] > 55 else "black"
        ax.text(j, i, f"{pct[i, j]:.1f}%\n({int(mat[i, j]):,})", ha="center", va="center",
                 fontsize=11, color=color, linespacing=1.6)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.set_title("Full STBV Framework\nSTBV-Bench v2.5b, current final checkpoint ($n{=}10{,}098$)", fontsize=9)
cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Row-normalized (%)", fontsize=8)
cbar.ax.tick_params(labelsize=7)
plt.tight_layout()
ps.save(fig, OUT / "fig_v25b_confusion_single")
plt.close()
print(f"[ok] tp={tp} fp={fp} fn={fn} tn={tn}")
