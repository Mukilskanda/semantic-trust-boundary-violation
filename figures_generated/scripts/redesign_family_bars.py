import csv, pathlib, sys
from collections import defaultdict
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"

rows = list(csv.DictReader(open(V25B_HM / "config_5.csv", encoding="utf-8")))
fam = defaultdict(lambda: [0, 0])  # correct, total (malicious only)
for r in rows:
    if r["is_attacker"] != "True":
        continue
    f = r["attack_family"]
    fam[f][1] += 1
    if r["decision"] != "ACCEPT":
        fam[f][0] += 1

data = [(f, c / t, t) for f, (c, t) in fam.items()]
data.sort(key=lambda x: x[1])  # ascending recall, worst at top when plotted with barh

names = [d[0] for d in data]
recalls = [d[1] for d in data]
counts = [d[2] for d in data]

cmap = mcolors.LinearSegmentedColormap.from_list("gyor", ["#D55E00", "#E69F00", "#F0E442", "#009E73"])
colors = [cmap(r) for r in recalls]

fig, ax = plt.subplots(figsize=(5.2, 0.32 * len(names) + 1.0))
y = np.arange(len(names))
bars = ax.barh(y, recalls, color=colors, edgecolor="black", linewidth=0.5, height=0.65)
for yi, r, n in zip(y, recalls, counts):
    ax.text(r + 0.015, yi, f"{r:.3f} (n={n})", va="center", fontsize=7)
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=7.5)
ax.set_xlim(0, 1.18)
ax.set_xlabel("Recall")
ax.axvline(0.5, color=ps.GREY, ls=":", lw=0.8)
ax.axvline(0.9, color=ps.GREY, ls=":", lw=0.8)
ax.text(0.25, len(names) - 0.3, "Low", ha="center", fontsize=7, color=ps.GREY)
ax.text(0.70, len(names) - 0.3, "Medium", ha="center", fontsize=7, color=ps.GREY)
ax.text(0.95, len(names) - 0.3, "High", ha="center", fontsize=7, color=ps.GREY)
ax.set_title("Per-Family Recall, Full STBV Framework\nSTBV-Bench v2.5b, Current Final Checkpoint", fontsize=9)
plt.tight_layout()
ps.save(fig, OUT / "fig_v25b_family_bars")
plt.close()
print("[family_bars]", [(n, round(r, 3), c) for n, r, c in data])
