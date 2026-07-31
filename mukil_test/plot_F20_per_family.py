"""
Plot F20_per_family: per-family accuracy from lolo_preds.json (full config).
Run from repo root:
    python mukil_test/plot_F20_per_family.py
"""

import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Load data
JSON_PATH = os.path.join("results", "lolo_preds.json")

with open(JSON_PATH, "r") as f:
    data = json.load(f)

full = data["configs"]["full"]
y_true   = full["y_true"]
y_pred   = full["y_pred"]
families = full["family"]

assert len(y_true) == len(y_pred) == len(families), (
    f"Length mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}, family={len(families)}"
)

# Per-family accuracy
correct_by_family = defaultdict(int)
total_by_family   = defaultdict(int)

for yt, yp, fam in zip(y_true, y_pred, families):
    total_by_family[fam]   += 1
    correct_by_family[fam] += int(yt == yp)

# Sort ascending by accuracy (barh draws bottom-to-top, so lowest at bottom)
family_names = sorted(total_by_family.keys(),
                      key=lambda f: correct_by_family[f] / total_by_family[f])

# Console output
print(f"\n{'Family':<22} {'Samples':>8} {'Accuracy':>10}")
print("-" * 44)
for fam in reversed(family_names):
    n   = total_by_family[fam]
    acc = correct_by_family[fam] / n
    print(f"{fam:<22} {n:>8} {acc:>10.4f}")
print()

# Build chart data
accuracies = [correct_by_family[f] / total_by_family[f] for f in family_names]
colors     = ["steelblue" if f == "benign" else "crimson" for f in family_names]

# Plot
fig_height = max(5, len(family_names) * 0.55 + 1.5)
fig, ax = plt.subplots(figsize=(9, fig_height), facecolor="white")
ax.set_facecolor("white")

bars = ax.barh(family_names, accuracies, color=colors, edgecolor="none", height=0.55)

for bar, acc in zip(bars, accuracies):
    ax.text(
        acc + 0.012,
        bar.get_y() + bar.get_height() / 2,
        f"{acc:.2f}",
        va="center", ha="left",
        fontsize=9, color="#222222"
    )

ax.set_xlim(0.0, 1.15)
ax.set_xlabel("Accuracy", fontsize=11)
ax.set_title("Per-Family Accuracy (full stack)", fontsize=13, fontweight="bold", pad=12)

ax.xaxis.grid(True, color="#dddddd", linewidth=0.7, zorder=0)
ax.yaxis.grid(False)
ax.set_axisbelow(True)

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color("#cccccc")
ax.spines["bottom"].set_color("#cccccc")

ax.tick_params(axis="x", labelsize=9)
ax.tick_params(axis="y", labelsize=9)

benign_patch   = mpatches.Patch(color="steelblue", label="Benign")
malicious_patch = mpatches.Patch(color="crimson",   label="Malicious")
ax.legend(handles=[benign_patch, malicious_patch],
          loc="lower right", fontsize=9, framealpha=0.9)

plt.tight_layout()

out_dir = os.path.join("mukil_test", "figures")
os.makedirs(out_dir, exist_ok=True)

pdf_path = os.path.join(out_dir, "F20_per_family.pdf")
png_path = os.path.join(out_dir, "F20_per_family.png")

fig.savefig(pdf_path, dpi=150, bbox_inches="tight", facecolor="white")
fig.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")

print(f"Saved PDF -> {pdf_path}")
print(f"Saved PNG -> {png_path}")
