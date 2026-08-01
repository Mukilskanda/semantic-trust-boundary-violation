#!/usr/bin/env python3
"""Figures for the backbone comparison: F1 vs latency vs memory tradeoff,
per-metric grouped bars, and per-family recall heatmap."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
analysis = json.loads((HERE / "results" / "backbone_comparison_analysis.json").read_text())
rows = analysis["comparison_rows"]
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=150)
    plt.close(fig)


names = [r["backbone"] for r in rows]

# 1. Grouped bars: accuracy/precision/recall/F1
fig, ax = plt.subplots(figsize=(5.2, 3.4))
x = range(len(names))
width = 0.2
for i, (key, label) in enumerate([("accuracy_mean", "Accuracy"), ("precision_mean", "Precision"),
                                    ("recall_mean", "Recall"), ("f1_mean", "F1")]):
    ax.bar([xi + i * width for xi in x], [r[key] for r in rows], width=width, label=label)
ax.set_xticks([xi + 1.5 * width for xi in x])
ax.set_xticklabels(names, fontsize=8)
ax.set_ylabel("Score")
ax.set_ylim(0, 1.05)
ax.legend(fontsize=7, ncol=4, loc="lower center")
ax.set_title("Classification Metrics by Backbone")
save(fig, "backbone_fig_metrics")

# 2. F1 vs latency (bubble size = memory)
fig, ax = plt.subplots(figsize=(4.4, 3.6))
for r in rows:
    size = (r["peak_vram_mb"] or 500) / 10
    ax.scatter(r["latency_p95_ms"], r["f1_mean"], s=size, alpha=0.6)
    ax.annotate(r["backbone"], (r["latency_p95_ms"], r["f1_mean"]), fontsize=7,
                xytext=(4, 4), textcoords="offset points")
ax.set_xlabel("p95 latency (ms), single message")
ax.set_ylabel("F1")
ax.set_title("F1 vs. Latency (bubble size = peak VRAM)")
save(fig, "backbone_fig_f1_vs_latency")

# 3. Parameters vs train time
fig, ax = plt.subplots(figsize=(4.2, 3.4))
ax.bar(names, [r["parameters_millions"] for r in rows], color="#1f77b4", alpha=0.7, label="Params (M)")
ax2 = ax.twinx()
ax2.plot(names, [r["train_seconds"] for r in rows], color="#d62728", marker="o", label="Train time (s)")
ax.set_ylabel("Parameters (millions)")
ax2.set_ylabel("Train time (s)")
ax.set_title("Model Size vs. Training Cost")
plt.setp(ax.get_xticklabels(), fontsize=7.5)
save(fig, "backbone_fig_size_vs_traintime")

# 4. Per-family recall heatmap-ish (grouped bars, worst families highlighted)
per_fam = analysis["per_family_recall"]
fam_names = sorted({fam for m in per_fam.values() for fam in m})
fig, ax = plt.subplots(figsize=(7.5, 4.2))
width = 0.15
xs = range(len(fam_names))
model_list = [n for n in names if n in per_fam]
for i, m in enumerate(model_list):
    vals = [per_fam[m].get(f, {}).get("recall") or 0 for f in fam_names]
    ax.bar([xi + i * width for xi in xs], vals, width=width, label=m)
ax.set_xticks([xi + (len(model_list) - 1) * width / 2 for xi in xs])
ax.set_xticklabels(fam_names, rotation=60, ha="right", fontsize=6)
ax.set_ylabel("Recall")
ax.legend(fontsize=7)
ax.set_title("Per-Family Recall by Backbone")
save(fig, "backbone_fig_per_family_recall")

print(f"Wrote 4 figures to {OUT}")
