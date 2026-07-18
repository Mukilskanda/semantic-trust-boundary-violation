#!/usr/bin/env python3
# =====================================================================
# run_lolo.py  --  Leave-One-Layer-Out (LOLO) architecture ablation  (AV0)
# ---------------------------------------------------------------------
# Answers reviewer: "Is every layer necessary?"  Produces:
#   results/lolo.json      per-config metrics + per-family recall
#   tables/T16_lolo.tex    LOLO matrix (LaTeX, booktabs)
#   figures/F19_lolo.pdf   tornado of F1 lost when each layer is removed
#
# INPUT SCHEMA (results/lolo_preds.json):
# {
#   "families": ["forgery","replay","kinematic","inconsistency",
#                "collusion","semantic_role","semantic_inject", ...],
#   "configs": {
#      "full":     {"y_true":[0/1...], "y_pred":[0/1...], "family":[str...]},
#      "no_pki":   {...}, "no_b1":{...}, "no_mbd":{...}, "no_b2":{...},
#      "no_cp":{...}, "no_b3":{...}, "no_fusion":{...}
#   }
# }
#   y_true: 1 = malicious, 0 = benign ;  y_pred: 1 = flagged/blocked
#
# RUN:  python run_lolo.py                      # demo
#       python run_lolo.py --input results/lolo_preds.json
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, binary_metrics, bootstrap_ci,
                         load_json_or_demo, save_json, save_latex_table, savefig,
                         ACC, NEUTRAL, THREAT, INK)
import matplotlib.pyplot as plt

CONFIG_ORDER = ["full", "no_pki", "no_b1", "no_mbd", "no_b2", "no_cp", "no_b3", "no_fusion"]
# which family each layer "owns" (removing the layer should blind that family)
OWNS = {"no_pki": ["forgery"], "no_b1": ["replay"], "no_mbd": ["kinematic"],
        "no_b2": ["inconsistency"], "no_cp": ["collusion"],
        "no_b3": ["semantic_role", "semantic_inject", "semantic_multi"], "no_fusion": []}


def make_demo(seed=0):
    rng = np.random.default_rng(seed)
    families = ["forgery", "replay", "kinematic", "inconsistency", "collusion",
                "semantic_role", "semantic_inject", "semantic_multi", "benign"]
    n_per = {f: 22 for f in families}; n_per["benign"] = 40
    fam = sum(([f] * n_per[f] for f in families), [])
    y_true = np.array([0 if f == "benign" else 1 for f in fam])

    def preds_for(removed):
        yp = []
        for f, t in zip(fam, y_true):
            if t == 0:
                yp.append(0)  # benign: no false positives in demo
            elif removed != "full" and f in OWNS.get(removed, []):
                yp.append(0)  # blinded family -> missed
            else:
                # full stack detects most; semantic families a bit weaker (dilution)
                p = 0.72 if f.startswith("semantic") else 0.97
                if removed == "no_fusion":
                    p -= 0.06  # fusion loss: a few borderline cases flip
                yp.append(int(rng.random() < p))
        return yp

    return {"families": families,
            "configs": {c: {"y_true": y_true.tolist(), "y_pred": preds_for(c),
                            "family": fam} for c in CONFIG_ORDER}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/lolo_preds.json")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    set_style()

    data, is_demo = load_json_or_demo(args.input, lambda: make_demo(args.seed), "LOLO")
    configs = data["configs"]

    # ---- per-config metrics ----
    summary = {}
    for cfg in CONFIG_ORDER:
        if cfg not in configs:
            continue
        yt, yp = configs[cfg]["y_true"], configs[cfg]["y_pred"]
        m = binary_metrics(yt, yp)
        lo, hi = bootstrap_ci(yt, yp, "f1", seed=args.seed)
        m["f1_ci"] = [lo, hi]
        summary[cfg] = m

    full_f1 = summary["full"]["f1"]
    for cfg in summary:
        cfg_f1 = summary[cfg]["f1"]
        summary[cfg]["f1_drop_vs_full"] = (full_f1 - cfg_f1) if cfg_f1 == cfg_f1 else full_f1

    save_json({"demo": is_demo, "per_config": summary}, os.path.join(args.outdir, "results/lolo.json"))

    # ---- T16 LaTeX ----
    rows = []
    for cfg in CONFIG_ORDER:
        if cfg not in summary:
            continue
        m = summary[cfg]
        f1 = "---" if m["f1"] != m["f1"] else f"{m['f1']:.3f}"
        rec = "---" if m["rec"] != m["rec"] else f"{m['rec']:.3f}"
        fpr = f"{m['fpr']:.3f}" if m["fpr"] == m["fpr"] else "---"
        drop = f"{m['f1_drop_vs_full']:+.3f}" if m["f1"] == m["f1"] else "---"
        rows.append([cfg.replace("_", r"\_"), f1, rec, fpr, drop])
    save_latex_table(
        ["Configuration", "F1", "Recall", "FPR", r"$\Delta$F1 vs full"], rows,
        "Leave-one-layer-out (LOLO) ablation. Each row removes one layer; "
        "$\\Delta$F1 is the end-to-end F1 lost relative to the full stack.",
        "tab:lolo", os.path.join(args.outdir, "tables/T16_lolo.tex"))

    # ---- F19 tornado (F1 lost when each layer removed) ----
    removed = [c for c in CONFIG_ORDER if c != "full" and c in summary]
    drops = [summary[c]["f1_drop_vs_full"] for c in removed]
    order = np.argsort(drops)
    removed = [removed[i] for i in order]; drops = [drops[i] for i in order]
    labels = [c.replace("no_", "").upper() for c in removed]

    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    colors = [THREAT if d >= max(drops) * 0.66 else (ACC if d > 0 else NEUTRAL) for d in drops]
    ax.barh(range(len(removed)), drops, color=colors, edgecolor=INK, linewidth=0.5)
    ax.set_yticks(range(len(removed))); ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("F1 lost when layer removed")
    ax.set_title("LOLO: contribution of each layer", loc="left", fontsize=8.5, fontweight="bold")
    for i, d in enumerate(drops):
        ax.text(d + 0.005, i, f"{d:.2f}", va="center", fontsize=6.5, color=INK)
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F19_lolo.pdf"))

    print("\nSummary (F1 | recall | FPR):")
    for cfg in CONFIG_ORDER:
        if cfg in summary:
            m = summary[cfg]
            print(f"  {cfg:10s}  F1={m['f1'] if m['f1']==m['f1'] else float('nan'):.3f}"
                  f"  rec={m['rec']:.3f}  fpr={m['fpr']:.3f}")


if __name__ == "__main__":
    main()
