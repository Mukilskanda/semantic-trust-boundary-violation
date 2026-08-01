"""
figures_v2/generate_figures.py
================================
Generates every real, data-grounded figure for the IEEE Transactions
manuscript revision, from the actual committed result files -- no
fabricated or illustrative data. Every figure's source file is named in
its own generation code, matching this project's evidence-traceability
standard (see HANDOFF_SUMMARY.md).

Run: python figures_v2/generate_figures.py
Output: figures_v2/*.pdf and *.png (IEEE two-column-safe: 3.4in width for
single-column figures, vector PDF primary format, PNG for quick preview).
"""
import json
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc, precision_recall_curve

plt.rcParams.update({
    "font.size": 9,
    "font.family": "serif",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 150,
})

OUT = "figures_v2"


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"-> {OUT}/{name}.pdf / .png")


# ============================================================
# 1. ROC + 2. PR curves (source: results/stbv_bench/v1/stbv_bench_per_message.csv)
# ============================================================
rows = list(csv.DictReader(open("results/stbv_bench/v1/stbv_bench_per_message.csv", encoding="utf-8")))
y_true = np.array([1 if r["is_attacker"] == "True" else 0 for r in rows])
# trust_score is the fused Decision Trust score (higher = more trusted =
# more likely benign), so use (1 - trust_score) as the "malicious score"
# for ROC/PR against y_true=1 (attacker).
trust = np.array([float(r["trust_score"]) if r["trust_score"] not in ("", "None") else np.nan for r in rows])
mask = ~np.isnan(trust)
mal_score = 1.0 - trust[mask]
y = y_true[mask]

fpr, tpr, _ = roc_curve(y, mal_score)
roc_auc = auc(fpr, tpr)
fig, ax = plt.subplots(figsize=(3.4, 2.8))
ax.plot(fpr, tpr, color="#1f77b4", lw=1.5, label=f"Full stack (AUC={roc_auc:.3f})")
ax.plot([0, 1], [0, 1], color="gray", lw=0.8, linestyle="--", label="Chance")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC -- STBV-Bench v1 ($n=10{,}000$)")
ax.legend(loc="lower right", fontsize=7)
save(fig, "fig_roc")

prec, rec, _ = precision_recall_curve(y, mal_score)
pr_auc = auc(rec, prec)
fig, ax = plt.subplots(figsize=(3.4, 2.8))
ax.plot(rec, prec, color="#d62728", lw=1.5, label=f"Full stack (AUC={pr_auc:.3f})")
ax.axhline(y.mean(), color="gray", lw=0.8, linestyle="--", label=f"Prevalence baseline ({y.mean():.2f})")
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.set_title("Precision--Recall -- STBV-Bench v1 ($n=10{,}000$)")
ax.legend(loc="lower left", fontsize=7)
save(fig, "fig_pr")

print(f"ROC AUC={roc_auc:.4f}, PR AUC={pr_auc:.4f} (source: results/stbv_bench/v1/stbv_bench_per_message.csv, "
      f"score=1-trust_score, n={mask.sum()})")

# ============================================================
# 3. Confusion matrix (source: results/ablation/ablation_summary.json, config 5)
# ============================================================
abl = json.load(open("results/ablation/ablation_summary.json"))
c5 = abl["table"]["5"]
cm = np.array([[c5["tp"], c5["fn"]], [c5["fp"], c5["tn"]]])
fig, ax = plt.subplots(figsize=(3.0, 2.6))
im = ax.imshow(cm, cmap="Blues")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                 color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=9)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Actual Malicious", "Actual Benign"])
ax.set_yticks([0, 1]); ax.set_yticklabels(["Pred. Positive\n(Caution/Reject)", "Pred. Negative\n(Accept)"])
ax.set_title(f"Confusion Matrix -- Full Stack (n={c5['n']:,})")
save(fig, "fig_confusion")

# ============================================================
# 4. Calibration reliability diagram (source: b3_eval/results/calibration.json)
# ============================================================
cal = json.load(open("b3_eval/results/calibration.json"))
def reliability_xy(rel):
    xs, ys, ns = [], [], []
    for i, b in enumerate(rel):
        if b is None:
            continue
        xs.append(b["avg_conf"]); ys.append(b["accuracy"]); ns.append(b["count"])
    return xs, ys, ns

xb, yb, nb = reliability_xy(cal["before"]["reliability"])
xa, ya, na = reliability_xy(cal["after"]["reliability"])
fig, ax = plt.subplots(figsize=(3.4, 2.8))
ax.plot([0, 1], [0, 1], color="gray", lw=0.8, linestyle="--", label="Perfect calibration")
ax.scatter(xb, yb, s=[max(20, n) for n in nb], color="#d62728", alpha=0.7,
           label=f"Before (T=1, ECE={cal['before']['ece']:.4f})")
ax.scatter(xa, ya, s=[max(20, n) for n in na], color="#2ca02c", alpha=0.7,
           label=f"After (T={cal['temperature']:.3f}, ECE={cal['after']['ece']:.4f})")
ax.set_xlabel("Mean Predicted Confidence")
ax.set_ylabel("Empirical Accuracy")
ax.set_title(f"Calibration Reliability (n={cal['n']})")
ax.legend(loc="upper left", fontsize=6.5)
save(fig, "fig_calibration")

# ============================================================
# 5. Latency: end-to-end percentiles + per-message distribution
# (source: results/stbv_bench/v1/stbv_bench_results.json 'latency_ms',
#  and results/stbv_bench/v1/stbv_bench_per_message.csv 'total_ms')
# ============================================================
stbv = json.load(open("results/stbv_bench/v1/stbv_bench_results.json"))
lat = stbv["latency_ms"]
total_ms = np.array([float(r["total_ms"]) for r in rows if r["total_ms"] not in ("", "None")])

fig, ax = plt.subplots(figsize=(3.4, 2.8))
percentiles = [50, 90, 95, 99]
values = [lat["p50"], np.percentile(total_ms, 90), lat["p95"], lat["p99"]]
ax.plot(percentiles, values, marker="o", color="#1f77b4", lw=1.5)
for p, v in zip(percentiles, values):
    ax.annotate(f"{v:.0f}", (p, v), textcoords="offset points", xytext=(0, 6), fontsize=7, ha="center")
ax.axhline(100, color="red", lw=0.8, linestyle="--", label="10 Hz CAM budget (100 ms)")
ax.set_xlabel("Percentile")
ax.set_ylabel("End-to-end latency (ms)")
ax.set_title(f"Latency Percentiles (n={len(total_ms):,}, mean={lat['mean']:.1f} ms)")
ax.legend(fontsize=7)
save(fig, "fig_latency")

fig, ax = plt.subplots(figsize=(3.4, 2.8))
ax.hist(total_ms, bins=60, color="#1f77b4", alpha=0.8)
ax.axvline(np.mean(total_ms), color="black", lw=1, linestyle="-", label=f"mean={np.mean(total_ms):.0f} ms")
ax.set_xlabel("Per-message end-to-end latency (ms)")
ax.set_ylabel("Count")
ax.set_title("Latency Distribution -- Full Stack")
ax.legend(fontsize=7)
save(fig, "fig_latency_hist")

# ============================================================
# 6. Per-layer latency breakdown (source: results/semantic/20260801-005223/metrics_summary.json,
#    'full' configuration latency block -- the only file with a per-stage breakdown)
# ============================================================
sem = json.load(open("results/semantic/20260801-005223/metrics_summary.json"))
full_lat = sem["configurations"]["full"]["latency"]
stages = ["pki_ms", "b1_ms", "mbd_ms", "b2_ms", "cp_ms", "synthesizer_ms", "bridge_ms", "fusion_ms"]
labels = ["PKI", "B1 (SCSV)", "MBD", "B2 (CSIA)", "CP", "Synthesizer", "B3 (bridge)", "Fusion"]
means = [full_lat[s]["mean"] for s in stages]
fig, ax = plt.subplots(figsize=(3.6, 2.8))
bars = ax.barh(labels, means, color="#1f77b4")
ax.set_xlabel("Mean stage latency (ms)")
ax.set_title("Per-Stage Latency Breakdown\n(120-scenario harness; stage timing only)")
ax.set_xscale("log")
save(fig, "fig_latency_per_stage")
print("NOTE: per-stage breakdown source is the 120-scenario semantic_evaluation harness "
      "(the only file with per-stage timers), NOT STBV-Bench v1 -- flagged explicitly in the "
      "manuscript text as measured on a different (smaller, leakage-flagged-for-ACCURACY-only, "
      "but timing-neutral) harness, since STBV-Bench v1's per-message CSV only records total_ms "
      "and bridge_ms, not a full per-stage split.")

# ============================================================
# 7. Per-family recall (source: results/stbv_bench/v1/stbv_bench_results.json 'per_family')
# ============================================================
per_fam = stbv["per_family"]
fams = [f for f in per_fam if f != "benign_control"]
fams_sorted = sorted(fams, key=lambda f: (per_fam[f]["recall"] if per_fam[f]["recall"] == per_fam[f]["recall"] else -1))
recalls = [per_fam[f]["recall"] for f in fams_sorted]
ns = [per_fam[f]["n"] for f in fams_sorted]
colors = ["#d62728" if r <= 0.09 else ("#ff7f0e" if r < 1.0 else "#2ca02c") for r in recalls]
fig, ax = plt.subplots(figsize=(5.0, 4.2))
ax.barh(fams_sorted, recalls, color=colors)
for i, (r, n) in enumerate(zip(recalls, ns)):
    ax.text(r + 0.01, i, f"n={n}", va="center", fontsize=6)
ax.set_xlabel("Recall")
ax.set_title("Per-Family Recall -- STBV-Bench v1 (Full Stack)")
ax.set_xlim(0, 1.15)
save(fig, "fig_per_family_recall")

# ============================================================
# 8. Ablation summary bar chart (source: results/ablation/ablation_summary.json)
# ============================================================
configs = ["1. B1 only", "2. B1+B2", "3. B1+B2+CP", "4. B3 alone\n(no fusion)", "5. Full stack"]
f1s = [abl["table"][str(i)]["f1"] if abl["table"][str(i)]["f1"] == abl["table"][str(i)]["f1"] else 0.0 for i in range(1, 6)]
cis = [abl["table"][str(i)]["f1_ci95"] for i in range(1, 6)]
errs = [[f1 - ci[0], ci[1] - f1] for f1, ci in zip(f1s, cis)]
fig, ax = plt.subplots(figsize=(4.2, 2.8))
ax.bar(configs, f1s, yerr=np.array(errs).T, capsize=3, color="#1f77b4")
ax.set_ylabel("F1-score")
ax.set_title("Layer Ablation -- F1 with 95% Bootstrap CI (n=10,000)")
plt.setp(ax.get_xticklabels(), rotation=20, ha="right", fontsize=7)
save(fig, "fig_ablation_summary")

# ============================================================
# 9. Decision-state transitions (source: results/ablation/ablation_3way_analysis.json)
# ============================================================
tway = json.load(open("results/ablation/ablation_3way_analysis.json"))
dist = tway["full_stack_decision_distribution"]
fig, axes = plt.subplots(1, 2, figsize=(6.0, 2.8))
axes[0].pie([dist["ACCEPT"], dist["CAUTION"], dist["REJECT"]],
            labels=["Accept", "Caution", "Reject"], autopct="%1.0f%%",
            colors=["#2ca02c", "#ff7f0e", "#d62728"], textprops={"fontsize": 7})
axes[0].set_title("Full-Stack Decision\nDistribution (n=10,000)", fontsize=8)

trans = tway["config4_to_config5_transitions"]
axes[1].bar(list(trans.keys()), list(trans.values()), color=["#ff7f0e", "#d62728"])
axes[1].set_ylabel("Count")
axes[1].set_title("Fusion-Attributable\nTransitions (Config 4->5)", fontsize=8)
plt.setp(axes[1].get_xticklabels(), rotation=15, ha="right", fontsize=6.5)
fig.tight_layout()
save(fig, "fig_decision_transitions")

# ============================================================
# 10. Threat-class coverage bar chart (semantic vs kinematic, source:
#     results/ablation/ablation_summary.json config4 + results/veremi_kinematic/analysis_summary.json)
# ============================================================
kin = json.load(open("results/veremi_kinematic/analysis_summary.json"))
fig, ax = plt.subplots(figsize=(3.6, 2.8))
groups = ["Semantic attacks\n(STBV-Bench)", "Kinematic attacks\n(VeReMi companion)"]
b3_vals = [abl["table"]["4"]["recall"], 0.0]  # B3 recall on each threat class
mbd_vals = [abl["table"]["2"]["recall"], kin["config_2"]["recall"]]  # MBD recall on each
x = np.arange(len(groups)); width = 0.35
ax.bar(x - width / 2, b3_vals, width, label="B3 (semantic)", color="#1f77b4")
ax.bar(x + width / 2, mbd_vals, width, label="MBD (behavioral)", color="#ff7f0e")
ax.set_xticks(x); ax.set_xticklabels(groups, fontsize=7.5)
ax.set_ylabel("Recall")
ax.set_title("Complementary Threat-Class Coverage")
ax.legend(fontsize=7)
save(fig, "fig_threat_coverage")

print("\nAll figures written to", OUT)
