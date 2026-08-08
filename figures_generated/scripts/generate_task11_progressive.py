"""
figures_generated/scripts/generate_task11_progressive.py
============================================================
Progressive-layer performance curve and layer-contribution bar chart for
the v2.5b full-pipeline ablation, current final checkpoint. Built from
the real per-config CSVs already on disk (configs 1-5;
config 6 added once run_v25b_config6_hardmine.py completes -- this
script degrades gracefully and proceeds with 5 configs if config_6.csv
is not yet present, re-run after it lands to include it).
"""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})


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
    acc = (tp + tn) / len(rows) if rows else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return dict(acc=acc, prec=prec, rec=rec, f1=f1, fpr=fpr)


configs = [1, 2, 3, 4, 5]
labels = ["Traditional\n(B1)", "+B2\n(B1+B2)", "+CP\n(B1+B2+CP)", "B3 only", "Full STBV\n(B1+B2+B3+CP)"]
if (V25B_HM / "config_6.csv").exists():
    configs.append(6)
    labels.append("B1+B2+B3\n(no CP)")

data = {c: metrics(list(csv.DictReader(open(V25B_HM / f"config_{c}.csv", encoding="utf-8")))) for c in configs}

# ---- Progressive performance curve ----
fig, ax = plt.subplots(figsize=(5.2, 3.0))
x = range(len(configs))
for metric, marker in [("acc", "o"), ("prec", "s"), ("rec", "^"), ("f1", "D")]:
    ax.plot(x, [data[c][metric] for c in configs], marker=marker, lw=1.3, markersize=5,
             label={"acc": "Accuracy", "prec": "Precision", "rec": "Recall", "f1": "F1"}[metric])
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=7)
ax.set_ylabel("Score"); ax.set_ylim(-0.02, 1.02)
ax.legend(fontsize=7, loc="center right")
ax.set_title("Progressive Layer Addition, STBV-Bench v2.5b\n(current final checkpoint)")
plt.tight_layout()
plt.savefig(OUT / "fig_progressive_performance_v25b.pdf")
plt.close()
print("[progressive]", {c: {k: round(v, 3) for k, v in data[c].items()} for c in configs})

# ---- Layer contribution bar chart (marginal F1 delta per added layer) ----
fig, ax = plt.subplots(figsize=(4.4, 2.8))
deltas, delta_labels = [], []
prev_f1 = 0.0
seq = [1, 2, 3]  # traditional -> +B2 -> +CP, all structurally 0 on v2.5b (semantic-only benchmark)
for i, c in enumerate(seq):
    deltas.append(data[c]["f1"] - prev_f1)
    delta_labels.append(labels[configs.index(c)].replace("\n", " "))
    prev_f1 = data[c]["f1"]
# B3's marginal contribution is measured relative to the traditional stack at 0, since B3-alone (config 4) is not a cumulative addition to configs1-3 in the pipeline sense -- shown as its own bar, then fusion's marginal contribution (full stack vs B3-alone).
deltas.append(data[4]["f1"] - 0.0); delta_labels.append("+B3 (semantic layer)")
deltas.append(data[5]["f1"] - data[4]["f1"]); delta_labels.append("+Fusion (Trust Decision Engine)")

colors = ["0.75" if d == 0 else "0.3" for d in deltas]
ax.barh(range(len(deltas)), deltas, color=colors, edgecolor="black", linewidth=0.4)
ax.set_yticks(range(len(deltas))); ax.set_yticklabels(delta_labels, fontsize=7)
ax.set_xlabel("Marginal F1 contribution")
ax.set_title("Layer Contribution to F1, STBV-Bench v2.5b\n(current final checkpoint; zero bars are the\ndisclosed structural blind spot, not measurement noise)")
ax.axvline(0, color="black", lw=0.6)
plt.tight_layout()
plt.savefig(OUT / "fig_layer_contribution_v25b.pdf")
plt.close()
print("[layer contribution]", list(zip(delta_labels, [round(d, 4) for d in deltas])))
