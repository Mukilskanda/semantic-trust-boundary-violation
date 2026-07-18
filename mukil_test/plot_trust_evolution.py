#!/usr/bin/env python3
# =====================================================================
# plot_trust_evolution.py  --  trust evolution across layers  (AV-F1/F2)
# ---------------------------------------------------------------------
# The thesis made visible: an authenticated semantic attack keeps high
# belief through every communication layer and collapses at B3.
# Produces:
#   figures/F33_trust_evolution.pdf   belief vs layer, one line per class
#   figures/F34_ignorance_evolution.pdf
#   tables/T28_trust_inflation.tex    area between comm-trust and decision-trust curves
#
# INPUT SCHEMA (results/trust_traces.json):
# {
#   "layers": ["PKI","B1","MBD","B2","CP","B3","Trust Engine","Fusion","Decision"],
#   "classes": {
#      "benign":         {"belief":[...], "ignorance":[...]},
#      "semantic_attack":{"belief":[...], "ignorance":[...]},
#      "colluding":      {"belief":[...], "ignorance":[...]},
#      "adaptive":       {"belief":[...], "ignorance":[...]}
#   }
# }
# belief/ignorance are per-layer values in [0,1], length == len(layers).
#
# RUN:  python plot_trust_evolution.py            # demo
#       python plot_trust_evolution.py --input results/trust_traces.json
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, load_json_or_demo,
                         save_json, save_latex_table, savefig,
                         ACC, NEUTRAL, THREAT, BENIGN, AMBER, INK)
import matplotlib.pyplot as plt

# numpy 2.x renamed trapz -> trapezoid; support both
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

LAYERS = ["PKI", "B1", "MBD", "B2", "CP", "B3", "Trust\nEngine", "Fusion", "Decision"]
STYLE = {  # color, linestyle, marker per class
    "benign":          (BENIGN, "-",  "o"),
    "semantic_attack": (THREAT, "-",  "s"),
    "colluding":       (AMBER,  "--", "^"),
    "adaptive":        (ACC,    "-.", "D"),
}
B3_IDX = 5  # index of B3 in LAYERS


def make_demo(seed=0):
    rng = np.random.default_rng(seed)
    L = len(LAYERS)

    def trace(collapse_at, collapse_to, base=0.9, noise=0.02, partial=1.0):
        b = np.full(L, base) + rng.normal(0, noise, L)
        if collapse_at is not None:
            for i in range(collapse_at, L):
                b[i] = collapse_to + (b[collapse_at - 1] - collapse_to) * (1 - partial)
        return np.clip(b, 0, 1)

    classes = {
        "benign":          {"belief": trace(None, None, base=0.92).tolist()},
        "semantic_attack": {"belief": trace(B3_IDX, 0.15).tolist()},
        "colluding":       {"belief": trace(B3_IDX, 0.25, partial=0.85).tolist()},
        "adaptive":        {"belief": trace(B3_IDX, 0.45, partial=0.6).tolist()},  # partly evades
    }
    # ignorance rises around CP/B3 where the architecture reasons under uncertainty
    ig_profile = np.array([0, 0, 0, 0, 0.10, 0.25, 0.15, 0.10, 0.05])
    for c in classes:
        ig = np.clip(0.04 + ig_profile * (0.0 if c == "benign" else 1.0), 0, 0.6)
        classes[c]["ignorance"] = ig.tolist()
    return {"layers": LAYERS, "classes": classes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/trust_traces.json")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    set_style()

    d, is_demo = load_json_or_demo(args.input, lambda: make_demo(args.seed), "TRUST-EVOL")
    layers = d["layers"]; classes = d["classes"]
    x = np.arange(len(layers))

    # ---- F33 belief evolution ----
    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    for name, series in classes.items():
        col, ls, mk = STYLE.get(name, (INK, "-", "o"))
        ax.plot(x, series["belief"], ls, color=col, marker=mk, markersize=3.4,
                linewidth=1.3, label=name.replace("_", " "))
    ax.axvline(B3_IDX - 0.5, color=INK, ls=":", lw=0.8, alpha=0.6)
    ax.text(B3_IDX - 0.5, 1.02, "inter-layer boundary", fontsize=6.2, ha="center", color=INK)
    ax.set_xticks(x); ax.set_xticklabels(layers, fontsize=6.5)
    ax.set_ylim(0, 1.08); ax.set_ylabel("belief (trust)")
    ax.set_title("Trust evolution across the pipeline", loc="left", fontsize=8.5, fontweight="bold")
    ax.legend(fontsize=6.3, frameon=False, loc="lower left", ncol=2)
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F33_trust_evolution.pdf"))

    # ---- F34 ignorance evolution ----
    fig2, ax2 = plt.subplots(figsize=(4.6, 2.5))
    for name, series in classes.items():
        col, ls, mk = STYLE.get(name, (INK, "-", "o"))
        ax2.plot(x, series["ignorance"], ls, color=col, marker=mk, markersize=3.2,
                 linewidth=1.2, label=name.replace("_", " "))
    ax2.set_xticks(x); ax2.set_xticklabels(layers, fontsize=6.5)
    ax2.set_ylabel(r"ignorance mass $\Theta$")
    ax2.set_title("Uncertainty across the pipeline", loc="left", fontsize=8.5, fontweight="bold")
    ax2.legend(fontsize=6.3, frameon=False, ncol=2)
    if is_demo:
        demo_watermark(fig2)
    savefig(fig2, os.path.join(args.outdir, "figures/F34_ignorance_evolution.pdf"))

    # ---- T28 trust-inflation = area between benign and attack belief up to B3 ----
    benign_b = np.array(classes["benign"]["belief"])
    rows = []
    for name in classes:
        if name == "benign":
            continue
        b = np.array(classes[name]["belief"])
        # "trust inflation" = area where an attack retains benign-like belief before B3
        inflation = float(_trapz(np.clip(b[:B3_IDX + 1], 0, 1), x[:B3_IDX + 1]))
        collapse = float(benign_b[-1] - b[-1])  # final belief gap vs benign
        rows.append([name.replace("_", " "), f"{inflation:.3f}", f"{collapse:.3f}"])
    save_latex_table(["Attack class", "pre-B3 trust area", "final belief drop"], rows,
                     "Trust inflation: authenticated attacks retain benign-like belief "
                     "through the communication layers (pre-B3 area) and collapse only at "
                     "the semantic gate (final belief drop).", "tab:inflation",
                     os.path.join(args.outdir, "tables/T28_trust_inflation.tex"))
    save_json({"demo": is_demo, "layers": layers,
               "trust_inflation_rows": rows}, os.path.join(args.outdir, "results/trust_evolution.json"))

    print("\n  F33/F34 written; T28 trust-inflation rows:")
    for r in rows:
        print("   ", r)


if __name__ == "__main__":
    main()
