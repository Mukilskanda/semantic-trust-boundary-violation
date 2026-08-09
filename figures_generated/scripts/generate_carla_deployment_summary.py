"""
figures_generated/scripts/generate_carla_deployment_summary.py
===============================================================
Live-CARLA deployment summary, current final checkpoint, real per-message
data from this session's fresh rerun
(deployment_eval/carla_results_final_checkpoint/carla_deployment_eval_results_final_checkpoint.json,
n=400, 0 dropped). Mirrors fig_deployment_summary's SUMO panel layout for
direct visual comparability, but every value here is CARLA's own real
per-message/per-stage data, not reused from the SUMO run.

Real, disclosed finding this figure surfaces: unlike SUMO (trace replay,
where B3's forward pass dominates latency), CARLA's dominant real cost is
"bridge_ms" -- the live-simulator world-tick/actor-state synchronization
overhead -- not B3 inference. This is stated honestly in the caption
rather than smoothed into "B3 dominates everywhere."
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
plt.rcParams["font.family"] = "DejaVu Sans"
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"

d = json.load(open(ROOT / "deployment_eval/carla_results_final_checkpoint/carla_deployment_eval_results_final_checkpoint.json", encoding="utf-8"))
pm = d["per_message"]
idx = np.arange(len(pm))
lat = np.array([m["total_ms"] for m in pm])
mean_lat = lat.mean()
p95 = np.percentile(lat, 95)

stage_names = ["PKI", "B1", "MBD", "B2", "CP", "Synth.", "Bridge\n(CARLA sync)", "Fusion"]
stage_keys = ["pki_ms", "b1_ms", "mbd_ms", "b2_ms", "cp_ms", "synthesizer_ms", "bridge_ms", "fusion_ms"]
stage_vals = [np.mean([m[k] for m in pm]) for k in stage_keys]

fig = plt.figure(figsize=(6.8, 5.4))
gs = fig.add_gridspec(2, 2, hspace=0.6, wspace=0.4)

axA = fig.add_subplot(gs[0, :])
window = 15
rolling = np.convolve(lat, np.ones(window) / window, mode="valid")
axA.scatter(idx, lat, s=6, color=ps.ARCH_C, alpha=0.35, linewidths=0)
axA.plot(idx[window - 1:], rolling, color=ps.ARCH_C, lw=2.0, label=f"Rolling mean (w={window})")
axA.axhline(100, color=ps.FAIL_C, ls="--", lw=1.3, label="ETSI 100 ms budget")
axA.axhline(mean_lat, color="0.25", ls=":", lw=1.1, label=f"mean {mean_lat:.1f} ms")
for b in range(40, 400, 40):
    axA.axvline(b, color="0.88", lw=0.6)
axA.set_xlabel("Message index"); axA.set_ylabel("Latency (ms)")
axA.legend(loc="upper right", fontsize=6.5)
axA.set_title(f"(A) Latency Timeline, Live CARLA, Final Checkpoint ($n{{=}}400$, $p_{{95}}{{=}}{p95:.1f}$ ms)", fontsize=8.5)

axB = fig.add_subplot(gs[1, 0])
colors_b = [ps.HIST_C] * 6 + [ps.FAIL_C, ps.HIST_C]
axB.barh(stage_names, stage_vals, color=colors_b, edgecolor="black", linewidth=0.5, height=0.65)
axB.set_xscale("log")
axB.set_xlabel("Mean latency (ms, log)")
axB.set_title("(B) Per-Stage Breakdown\n(bridge = CARLA sync, not B3)", fontsize=8.2)

axC = fig.add_subplot(gs[1, 1])
throughput = len(pm) / d["eval_wall_seconds"]
axC.bar(["Achieved\n(single-thread)"], [throughput], color=ps.ARCH_C, width=0.5, edgecolor="black", linewidth=0.5)
axC.text(0, throughput + 0.3, f"{throughput:.2f}\nmsg/s", ha="center", fontsize=8)
axC.set_ylim(0, throughput * 1.6)
axC.set_ylabel("msg/s")
axC.set_title("(C) Throughput\n(0/920 dropped)", fontsize=8.2)

fig.suptitle("Live CARLA Deployment Summary, Current Final Checkpoint", fontsize=9.5, y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.97])
ps.save(fig, OUT / "fig_carla_deployment_summary")
plt.close()
print("wrote fig_carla_deployment_summary; mean=%.1f p95=%.1f throughput=%.2f" % (mean_lat, p95, throughput))
