import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"


def metrics(rows):
    tp = fp = fn = tn = 0
    for r in rows:
        y = r["is_attacker"] == "True"
        p = r["decision"] != "ACCEPT"
        if p and y: tp += 1
        elif p and not y: fp += 1
        elif not p and y: fn += 1
        else: tn += 1
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return f1


# ---- Real F1 per realizable configuration -- NOT fabricated intermediates.
# Traditional/+B2/+CP are genuinely 0 (structural, disclosed in the paper text);
# only B3-only, B1+B2+B3(no CP), and Full STBV have non-trivial F1.
labels_order = ["Traditional\n(PKI+B1)", "+B2", "+CP", "B3\nonly", "B1+B2+B3\n(no CP)", "Full\nSTBV"]
cfg_files = {0: 1, 1: 2, 2: 3, 3: 4, 4: 6, 5: 5}
f1_vals = []
for i in range(6):
    rows = list(csv.DictReader(open(V25B_HM / f"config_{cfg_files[i]}.csv", encoding="utf-8")))
    f1_vals.append(metrics(rows))

fig, ax = plt.subplots(figsize=(5.2, 3.0))
x = np.arange(6)
colors = [ps.LIGHT_GREY] * 3 + [ps.BLUE, ps.BLUE, ps.GREEN]
bars = ax.bar(x, f1_vals, color=colors, width=0.6, edgecolor="black", linewidth=0.6)
for xi, v in zip(x, f1_vals):
    ax.text(xi, v + 0.02, f"{v:.3f}" if v > 0 else "0 (structural)", ha="center", fontsize=7.5,
             rotation=0 if v > 0 else 90, va="bottom" if v > 0 else "bottom")
ax.set_xticks(x); ax.set_xticklabels(labels_order, fontsize=7.5)
ax.set_ylabel("F1")
ax.set_ylim(0, 1.05)
ax.set_title("Progressive Layer Contribution, STBV-Bench v2.5b\n(current final checkpoint; grey bars are a genuine\nstructural zero, not missing data -- see Section~VI-C)", fontsize=9)
plt.tight_layout()
ps.save(fig, OUT / "fig_v25b_progressive")
plt.close()
print("[progressive]", dict(zip(labels_order, [round(v, 4) for v in f1_vals])))

# ---- ITE-Bench attack-class x layer coverage heatmap (real Table IV numbers) ----
attack_classes = ["Communication\n(B1-focused)", "Behavioral\n(B2-focused)", "Semantic\n(B3-focused)"]
configs = ["B1 only", "B1+B2(+CP)", "Full stack"]
# Values transcribed exactly from Table IV (tab:ite_ablation) in stbv_paper.tex -- real, published numbers
coverage = np.array([
    [1.000, 1.000, 1.000],
    [0.143, 1.000, 1.000],
    [0.000, 0.000, 1.000],
])

fig, ax = plt.subplots(figsize=(3.6, 2.6))
im = ax.imshow(coverage, cmap=ps.SEQ_BLUE, vmin=0, vmax=1)
ax.set_xticks(range(3)); ax.set_xticklabels(configs, fontsize=7.5)
ax.set_yticks(range(3)); ax.set_yticklabels(attack_classes, fontsize=7.5)
ax.tick_params(length=0)
for i in range(3):
    for j in range(3):
        v = coverage[i, j]
        ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=9,
                 color="white" if v > 0.55 else "black")
for spine in ax.spines.values():
    spine.set_visible(False)
ax.set_title("Recall by Attack Class x Configuration\nITE-Bench, current final checkpoint", fontsize=9)
cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Recall", fontsize=8); cbar.ax.tick_params(labelsize=7)
plt.tight_layout()
ps.save(fig, OUT / "fig_ite_coverage")
plt.close()
print("[coverage] ITE-Bench heatmap built from Table IV's published values")
