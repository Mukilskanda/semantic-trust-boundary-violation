import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"

d = json.load(open(ROOT / "deployment_eval/results/deployment_eval_results.json", encoding="utf-8"))
pm = d["per_message"]
idx = np.array([r["i"] for r in pm])
lat = np.array([r["total_ms"] for r in pm])
mean_lat = lat.mean()
assert abs(mean_lat - 81.2) < 0.5

# Single, compact latency-timeline panel only -- per-stage breakdown (B) and
# throughput (C) panels removed per explicit request; B's real content is
# already in Table tab:complexity, C's in the SUMO Results paragraph text.
fig, ax = plt.subplots(figsize=(4.4, 2.7))
window = 25
rolling = np.convolve(lat, np.ones(window) / window, mode="valid")
ax.scatter(idx, lat, s=2.5, color=ps.ARCH_C, alpha=0.15, linewidths=0)
ax.plot(idx[window - 1:], rolling, color=ps.ARCH_C, lw=1.6, label=f"Rolling mean (w={window})")
ax.axhline(100, color=ps.FAIL_C, ls="--", lw=1.1, label="ETSI 100 ms budget")
ax.set_xlabel("Message index"); ax.set_ylabel("Latency (ms)")
ax.legend(loc="upper right", fontsize=6.5)
ax.set_title("Latency Timeline, SUMO Replay, Prior Checkpoint ($n{=}2{,}000$)", fontsize=8)

fig.tight_layout()
ps.save(fig, OUT / "fig_deployment_summary")
plt.close()
print(f"[deployment_summary] mean_lat={mean_lat:.2f} (single-panel, reduced size)")
