import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"

# Verified this file matches the manuscript's reported SUMO stats exactly
# (mean 81.2, p50 79.2, p95 98.9, p99 126.6) before being used here.
d = json.load(open(ROOT / "deployment_eval/results/deployment_eval_results.json", encoding="utf-8"))
pm = d["per_message"]
idx = np.array([r["i"] for r in pm])
lat = np.array([r["total_ms"] for r in pm])
mean_lat = lat.mean()
assert abs(mean_lat - 81.2) < 0.5, f"mean mismatch: {mean_lat}"

window = 25
rolling = np.convolve(lat, np.ones(window) / window, mode="valid")
rolling_idx = idx[window - 1:]

fig, ax = plt.subplots(figsize=(6.6, 2.8))
ax.scatter(idx, lat, s=4, color=ps.BLUE, alpha=0.18, linewidths=0, label="Per-message latency")
ax.plot(rolling_idx, rolling, color=ps.BLUE, lw=2.0, label=f"Rolling mean (w={window})")
ax.axhline(100, color=ps.RED, ls="--", lw=1.3, label="ETSI 100~ms budget")
ax.set_xlabel("Message index (SUMO replay)")
ax.set_ylabel("Latency (ms)")
ax.set_ylim(0, max(lat.max() * 1.05, 130))
ax.legend(loc="upper right", ncol=1, fontsize=7)
ax.set_title(f"Per-Message Latency, SUMO Replay, Current Final Checkpoint\n(n={len(lat)}, mean={mean_lat:.1f}ms)", fontsize=9)
plt.tight_layout()
ps.save(fig, OUT / "fig_v25b_latency_timeline")
plt.close()
print(f"[latency] n={len(lat)} mean={mean_lat:.2f} over_budget_pct={100*(lat>100).mean():.1f}")
