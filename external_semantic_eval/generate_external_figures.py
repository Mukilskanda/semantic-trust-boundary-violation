#!/usr/bin/env python3
"""Generates ROC, PR, calibration, and per-family recall figures for the
external semantic evaluation corpus, from external_eval_results.json.
Read-only against B3; plotting only."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
d = json.loads((HERE / "external_eval_results.json").read_text())
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=150)
    plt.close(fig)


# ROC
roc_pts = d["roc"]["points_sample"]
fig, ax = plt.subplots(figsize=(3.6, 3.2))
ax.plot([p[0] for p in roc_pts], [p[1] for p in roc_pts], marker="o", ms=2,
        label=f"AUC={d['roc']['auc']:.3f}")
ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
ax.set_title("ROC — External Semantic Evaluation Corpus")
ax.legend(fontsize=8)
save(fig, "ext_fig_roc")

# PR
pr_pts = d["pr"]["points_sample"]
fig, ax = plt.subplots(figsize=(3.6, 3.2))
ax.plot([p[0] for p in pr_pts], [p[1] for p in pr_pts], marker="o", ms=2,
        label=f"AUC={d['pr']['auc']:.3f}")
ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
ax.set_title("Precision-Recall — External Semantic Evaluation Corpus")
ax.legend(fontsize=8)
save(fig, "ext_fig_pr")

# Calibration reliability (raw vs existing-T applied)
raw = d["calibration"]["raw_T1"]; withT = d["calibration"]["with_existing_T_2p145_posthoc"]
fig, ax = plt.subplots(figsize=(3.6, 3.2))
ax.bar(["Raw (T=1)\nECE={:.3f}".format(raw["ece"]),
        "Existing T=2.145\napplied post-hoc\nECE={:.3f}".format(withT["ece"])],
       [raw["ece"], withT["ece"]], color=["#1f77b4", "#d62728"])
ax.set_ylabel("Expected Calibration Error")
ax.set_title("Calibration Transfer — External Corpus")
save(fig, "ext_fig_calibration")

# Per-family recall
fam_recall = d["per_family_recall"]
fams = sorted(fam_recall.keys(), key=lambda f: fam_recall[f]["recall"])
fig, ax = plt.subplots(figsize=(4.2, 3.4))
ax.barh(fams, [fam_recall[f]["recall"] for f in fams], color="#2ca02c")
for i, f in enumerate(fams):
    ax.text(fam_recall[f]["recall"] + 0.01, i,
            f"n={fam_recall[f]['n_malicious']}", va="center", fontsize=7)
ax.set_xlabel("Recall"); ax.set_xlim(0, 1.15)
ax.set_title("Per-Family Recall — External Corpus (frozen B3)")
save(fig, "ext_fig_per_family_recall")

print(f"Wrote 4 figures to {OUT}")
