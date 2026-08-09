"""
Defense-in-Depth Staircase (replaces the checkmark/triangle/dash "Layer-wise
Threat Coverage Matrix" per LAYER_FIGURE_REDESIGN.md: a binary-symbol matrix
was judged to communicate almost no information, since every "checkmark"
cell looked identical regardless of the real magnitude behind it).

Every value plotted is copied directly from Table II (tab:ite_ablation,
ITE-Bench recall progression, n=9,900) and Table V (tab:carla, this
session's real, freshly-rerun final-checkpoint live-CARLA results) --
no new metric is computed here.
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
plt.rcParams["font.family"] = "DejaVu Sans"
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"

# Real recall progression, ITE-Bench, Table II (tab:ite_ablation).
stages = ["B1", "B1+B2", "B1+B2\n+CP", "Full\nSTBV"]
recall = [0.381, 0.667, 0.667, 1.000]
gains = [recall[0]] + [recall[i] - recall[i-1] for i in range(1, len(recall))]
closes = ["closes\ncommunication", "closes\nbehavioral",
          "CP: gap\n(disclosed)", "closes\nsemantic"]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.0, 4.2), gridspec_kw={"width_ratios": [2.1, 1]})

x = np.arange(len(stages))
colors = [ps.ARCH_C, ps.ARCH_C, "#BBBBBB", ps.SUCCESS_C]
bars = ax1.bar(x, recall, color=colors, width=0.55, edgecolor="0.2", linewidth=0.6)
ax1.plot(x, recall, "o-", color="0.2", lw=1.2, ms=4, zorder=5)
for i, (xi, r, g) in enumerate(zip(x, recall, gains)):
    ax1.text(xi, r + 0.035, f"{r:.3f}", ha="center", fontsize=9.5, fontweight="bold")
    if i > 0:
        sign = "+" if g >= 0.0005 else ""
        ax1.text(xi + 0.32, (recall[i-1] + r) / 2, f"{sign}{g:.3f}", ha="left", va="center", fontsize=7.5, color="0.3")
for i, (xi, c) in enumerate(zip(x, closes)):
    ax1.annotate(c, xy=(xi, 0), xytext=(xi, -0.30), ha="center", va="top", fontsize=7.3, color="0.3", annotation_clip=False)

ax1.set_xticks(x); ax1.set_xticklabels(stages, fontsize=9.5)
ax1.set_ylim(0, 1.12)
ax1.set_xlim(-0.6, len(stages) - 0.2)
ax1.set_ylabel("Overall recall, ITE-Bench ($n{=}9{,}900$)\n(communication+behavioral+semantic mix)", fontsize=8.8)
ax1.set_title("Defense-in-depth: each layer's real,\nmeasured contribution to overall recall", fontsize=9.5)
fig.subplots_adjust(bottom=0.28)
for spine in ("top", "right"):
    ax1.spines[spine].set_visible(False)

# Deployment-robustness panel, kept separate (different benchmark, not
# merged into the ITE-Bench recall axis -- avoids the benchmark-conflation
# mistake this session's table redesign specifically corrected).
carla_labels = ["authority_\noverride", "false_hazard_\nclearance", "sybil_\nattack*", "semantic_\nmanipulation*", "goal_\nmanipulation"]
carla_status = ["Reject\n40/40", "Reject\n40/40", "Reject\n40/40", "Reject\n40/40", "Reject/Caution\n40/40"]
carla_colors = [ps.SUCCESS_C, ps.SUCCESS_C, ps.CAUTION_ROLE_C, ps.CAUTION_ROLE_C, ps.CAUTION_ROLE_C]
ypos = np.arange(len(carla_labels))
ax2.barh(ypos, [1]*5, color=carla_colors, height=0.6, edgecolor="0.2", linewidth=0.5)
ax2.set_yticks(ypos); ax2.set_yticklabels(carla_labels, fontsize=7.8)
ax2.set_xticks([])
for yi, s in zip(ypos, carla_status):
    ax2.text(0.5, yi, s, ha="center", va="center", fontsize=7.3, color="white", fontweight="bold")
ax2.set_xlim(0, 1)
ax2.invert_yaxis()
ax2.set_title("Trust Decision Engine, live CARLA\n(Table V, final checkpoint):\nall 5 real attack scenarios flagged", fontsize=8.6)
for spine in ax2.spines.values():
    spine.set_visible(False)
ax2.annotate("*B3-invisible; caught by MBD backstop", xy=(0.5, len(carla_labels) - 0.5),
             xytext=(0.5, len(carla_labels) + 0.15), ha="center", fontsize=6.3, color="0.35", annotation_clip=False)

fig.tight_layout()
fig.subplots_adjust(bottom=0.28, top=0.82)
ps.save(fig, OUT / "fig_layer_responsibility")
plt.close()
print("[defense_in_depth_staircase] rebuilt from Table II + Table V real values, no new metric")
