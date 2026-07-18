#!/usr/bin/env python3
# =====================================================================
# plot_timeline.py  --  per-layer real-time timeline vs deadline (F40, T7)
# ---------------------------------------------------------------------
#   results/timeline.json     cumulative timing + headroom vs deadline
#   tables/T7_latency.tex      per-stage mean/p50/p95/p99
#   figures/F40_timeline.pdf   cumulative Gantt with CAM deadline line
#
# INPUT SCHEMA (results/latency.json):
#   {"layers":["PKI","B1","MBD","B2","CP","B3","Trust Engine","Fusion","Decision"],
#    "mean":[ms...], "p50":[ms...], "p95":[ms...], "p99":[ms...],
#    "deadline_ms": 100}
#   (only "p95" is strictly required; others optional.)
#
# RUN:  python plot_timeline.py                        # demo
#       python plot_timeline.py --input results/latency.json
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, load_json_or_demo, save_json,
                         save_latex_table, savefig, ACC, THREAT, NEUTRAL, AMBER, INK)
import matplotlib.pyplot as plt

LAYERS = ["PKI", "B1", "MBD", "B2", "CP", "B3", "Trust Engine", "Fusion", "Decision"]


def make_demo():
    # B3 dominates; everything else small. Deadline = CAM period at 10 Hz.
    p95 = [0.4, 0.6, 1.2, 1.5, 2.0, 33.0, 1.0, 0.8, 0.2]
    mean = [x * 0.7 for x in p95]; p50 = [x * 0.6 for x in p95]; p99 = [x * 1.3 for x in p95]
    return {"layers": LAYERS, "mean": mean, "p50": p50, "p95": p95, "p99": p99,
            "deadline_ms": 100.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/latency.json")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()
    set_style()

    d, is_demo = load_json_or_demo(args.input, make_demo, "TIMELINE")
    layers = d["layers"]; p95 = np.asarray(d["p95"], float)
    deadline = float(d.get("deadline_ms", 100.0))
    cum = np.concatenate([[0], np.cumsum(p95)])
    total = float(cum[-1]); headroom = deadline - total

    save_json({"demo": is_demo, "total_p95_ms": total, "deadline_ms": deadline,
               "headroom_ms": headroom, "meets_deadline": bool(total <= deadline)},
              os.path.join(args.outdir, "results/timeline.json"))

    # ---- T7 latency table ----
    hdr = ["Stage", "mean", "p50", "p95", "p99"]
    rows = []
    for i, L in enumerate(layers):
        row = [L.replace("_", r"\_")]
        for k in ("mean", "p50", "p95", "p99"):
            row.append(f"{d[k][i]:.2f}" if k in d else "---")
        rows.append(row)
    rows.append([r"\textbf{Total}", "",
                 f"{np.sum(d['p50']):.2f}" if "p50" in d else "",
                 f"\\textbf{{{total:.2f}}}",
                 f"{np.sum(d['p99']):.2f}" if "p99" in d else ""])
    save_latex_table(hdr, rows,
                     "Per-stage latency (ms). Total p95 vs.\\ the CAM deadline "
                     f"({deadline:.0f}\\,ms at 10\\,Hz) determines real-time adequacy.",
                     "tab:latency", os.path.join(args.outdir, "tables/T7_latency.tex"),
                     align="lcccc")

    # ---- F40 cumulative Gantt ----
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ncol = len(layers)
    cmap = plt.get_cmap("Blues")
    for i in range(ncol):
        col = THREAT if layers[i].startswith("B3") else cmap(0.35 + 0.5 * i / ncol)
        ax.barh(0, p95[i], left=cum[i], height=0.5, color=col,
                edgecolor="white", linewidth=0.6)
        if p95[i] >= total * 0.04:  # label only non-tiny segments
            ax.text(cum[i] + p95[i] / 2, 0, layers[i], ha="center", va="center",
                    fontsize=6.2, color="white" if layers[i].startswith("B3") else INK,
                    rotation=0)
    ax.axvline(deadline, color=INK, lw=1.2, ls="--")
    ax.text(deadline, 0.42, f"  CAM deadline {deadline:.0f} ms", fontsize=7,
            color=INK, va="center")
    ax.text(total, -0.42, f"total p95 = {total:.1f} ms  (headroom {headroom:.0f} ms)",
            fontsize=7, ha="center", color=(ACC if headroom >= 0 else THREAT))
    ax.set_ylim(-0.7, 0.7); ax.set_yticks([])
    ax.set_xlim(0, max(deadline * 1.05, total * 1.1))
    ax.set_xlabel("cumulative latency (ms)")
    ax.set_title("End-to-end timing across the trust pipeline",
                 loc="left", fontsize=9, fontweight="bold")
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F40_timeline.pdf"))
    print(f"  total p95 = {total:.1f} ms | deadline {deadline:.0f} ms | "
          f"headroom {headroom:.0f} ms | meets={total <= deadline}")


if __name__ == "__main__":
    main()
