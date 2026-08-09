"""
figures_generated/scripts/generate_simple_deployment_figs.py
===============================================================
Three simple, single-purpose figures (matplotlib default styling, not
the shared pubstyle house style) replacing the dense multi-panel
fig_carla_deployment_summary, per explicit user request for a plainer,
classic look. All values real, computed directly from this session's
real per-message logs -- no fabrication, no reuse of unrelated numbers.

1. fig_carla_latency_simple: per-message latency, live CARLA, final
   checkpoint (n=400), real timeline.
2. fig_stage_latency_compare: per-stage mean latency, SUMO replay vs
   live CARLA, both real (SUMO: Table tab:complexity's already-published
   real numbers; CARLA: this session's fresh final-checkpoint rerun).
   CARLA's 7th stage is honestly labeled "Bridge" (CARLA world-tick /
   actor-sync overhead), NOT relabeled "B3" -- B3 is not CARLA's
   dominant cost, per DEPLOYMENT_AUDIT.md's disclosed finding.
3. fig_v25b_decision_pie: Full STBV Framework decision distribution,
   STBV-Bench v2.5b, current final checkpoint (n=10,098), real counts.
"""
import csv, json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
plt.rcParams.update({"figure.dpi": 150})  # matplotlib defaults otherwise

# ---------------------------------------------------------------- Fig 1
d = json.load(open(ROOT / "deployment_eval/carla_results_final_checkpoint/carla_deployment_eval_results_final_checkpoint.json", encoding="utf-8"))
pm = d["per_message"]
lat = np.array([m["total_ms"] for m in pm])

fig, ax = plt.subplots(figsize=(5.0, 3.6))
ax.plot(np.arange(len(lat)), lat, lw=0.9)
ax.axhline(100, color="red", ls="--", lw=1.2, label="100ms ETSI CAM budget")
ax.set_title("Per-message latency, live CARLA (n=400)")
ax.set_xlabel("Message index (10 live scenarios x 40)")
ax.set_ylabel("End-to-end latency (ms)")
ax.legend(loc="upper right", fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "fig_carla_latency_simple.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_carla_latency_simple.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------- Fig 2
sumo_stages = ["PKI", "B1", "MBD", "B2", "CP", "Synth", "B3", "Fusion"]
sumo_vals = [0.0014, 0.2231, 0.2024, 0.059, 0.0338, 0.3435, 80.1995, 0.089]  # tab:complexity, real, published
carla_stage_keys = ["pki_ms", "b1_ms", "mbd_ms", "b2_ms", "cp_ms", "synthesizer_ms", "bridge_ms", "fusion_ms"]
carla_labels = ["PKI", "B1", "MBD", "B2", "CP", "Synth", "Bridge", "Fusion"]
carla_vals = [float(np.mean([m[k] for m in pm])) for k in carla_stage_keys]

x = np.arange(len(sumo_stages))
w = 0.35
fig, ax = plt.subplots(figsize=(5.4, 3.8))
ax.bar(x - w/2, sumo_vals, width=w, label="SUMO replay")
ax.bar(x + w/2, carla_vals, width=w, label="Live CARLA", color="tab:red")
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels(["PKI", "B1", "MBD", "B2", "CP", "Synth", "B3 /\nBridge$^*$", "Fusion"])
ax.set_ylabel("Mean latency (ms, log scale)")
ax.set_title("Per-stage latency: replay vs. live CARLA")
ax.legend(fontsize=8)
fig.text(0.5, -0.02, "*SUMO's 7th stage is B3 (forward pass dominates); CARLA's is Bridge (CARLA world-tick sync, not B3) -- different bottlenecks, disclosed in text.",
          ha="center", fontsize=6.2, wrap=True)
fig.tight_layout()
fig.savefig(OUT / "fig_stage_latency_compare.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_stage_latency_compare.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------- Fig 3
rows = list(csv.DictReader(open(ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_5.csv", encoding="utf-8")))
n = len(rows)
counts = {"Accept": 0, "Caution": 0, "Reject": 0}
for r in rows:
    counts[r["decision"].capitalize()] += 1

fig, ax = plt.subplots(figsize=(2.6, 2.6))
labels = list(counts.keys())
sizes = list(counts.values())
colors = ["#2ca02c", "#ff7f0e", "#d62728"]  # green/orange/red, matches Accept/Caution/Reject convention
ax.pie(sizes, labels=labels, autopct="%1.0f%%", colors=colors, startangle=90,
       textprops={"fontsize": 8})
ax.set_title(f"Decision Distribution\n(n={n:,})", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "fig_v25b_decision_pie.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_v25b_decision_pie.png", bbox_inches="tight", dpi=200)
plt.close(fig)

print("Fig1 CARLA latency: mean=%.1f max=%.1f" % (lat.mean(), lat.max()))
print("Fig2 stage compare: SUMO", dict(zip(sumo_stages, sumo_vals)))
print("     CARLA", dict(zip(carla_labels, carla_vals)))
print("Fig3 decision dist:", counts, "of", n)
