import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"

# Exact same real, measured per-stage values as the original figure
# (generate_figures_part1.py) -- restyled only, not recomputed.
stages = ["PKI", "B1", "MBD", "B2", "CP", "Synth.", "B3", "Fusion"]
vals_ms = [0.0014, 0.2231, 0.2024, 0.059, 0.0338, 0.3435, 80.1995, 0.089]

fig, ax = plt.subplots(figsize=(4.6, 2.9))
colors = [ps.LIGHT_GREY] * 6 + [ps.RED, ps.LIGHT_GREY]
bars = ax.barh(stages, vals_ms, color=colors, edgecolor="black", linewidth=0.5, height=0.65)
for b, v in zip(bars, vals_ms):
    ax.text(v * 1.15, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=7.5)
ax.set_xscale("log")
ax.set_xlabel("Mean latency (ms, log scale)")
ax.set_title("Per-Stage Latency, SUMO Replay\nCurrent Final Checkpoint ($n{=}2{,}000$)", fontsize=9)
ax.grid(axis="x", alpha=0.25)
plt.tight_layout()
ps.save(fig, OUT / "fig_latency_breakdown_final")
plt.close()
print("[ok] restyled per-stage latency, same real values")
