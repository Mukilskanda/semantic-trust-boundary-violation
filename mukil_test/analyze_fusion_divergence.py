#!/usr/bin/env python3
# =====================================================================
# analyze_fusion_divergence.py  --  Trust Engine value beyond B3  (AV-B2)
# ---------------------------------------------------------------------
# Answers reviewer: "Does DS fusion change any decision B3 alone would make,
# and if so, which and why?"  Produces:
#   results/fusion_divergence.json
#   tables/T21_fusion_divergence.tex
#   figures/F23_fusion_divergence.pdf   (cause taxonomy + net effect)
#
# INPUT SCHEMA (results/fusion_preds.json):
# {
#   "y_true":       [0/1 ...],                 # 1 = malicious
#   "b3_only":      ["accept"/"caution"/"reject" ...],   # B3-thresholded alone
#   "fused":        ["accept"/"caution"/"reject" ...],   # after Trust Engine
#   "b3_conf":      [float ...],               # B3 confidence in [0,1]
#   "conflict_K":   [float ...],               # DS conflict mass in [0,1]
#   "family":       [str ...]
# }
# A decision "blocks" a message if it is not "accept" (caution or reject).
#
# RUN:  python analyze_fusion_divergence.py            # demo
#       python analyze_fusion_divergence.py --input results/fusion_preds.json
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, binary_metrics,
                         load_json_or_demo, save_json, save_latex_table, savefig,
                         ACC, NEUTRAL, THREAT, AMBER, INK)
import matplotlib.pyplot as plt

BLOCK = {"caution", "reject"}


def blocks(dec):  # detection = not accepted
    return np.array([1 if d in BLOCK else 0 for d in dec])


def cause_of(b3d, fd, k, conf, k_hi=0.35, conf_lo=0.55):
    """Classify why a decision changed between B3-only and fused."""
    if b3d == fd:
        return "unchanged"
    if k >= k_hi:
        return "inter-source conflict"
    if conf <= conf_lo:
        return "low B3 confidence"
    return "corroboration shift"


def make_demo(seed=0):
    rng = np.random.default_rng(seed)
    n = 240
    y_true = (rng.random(n) < 0.62).astype(int)
    b3_only, fused, conf, K, fam = [], [], [], [], []
    fams = ["semantic_role", "semantic_inject", "semantic_multi", "collusion", "benign"]
    for t in y_true:
        f = rng.choice(fams if t else ["benign"])
        # malicious messages skew to higher conflict / more spread-out B3 confidence
        c = float(np.clip(rng.normal(0.72 if t else 0.18, 0.22), 0, 1))
        k = float(np.clip(rng.normal(0.30 if t else 0.12, 0.20), 0, 1))
        b3 = "reject" if c > 0.6 else ("caution" if c > 0.4 else "accept")
        fu = b3
        # (i) high inter-source conflict rescues a missed malicious message
        if t == 1 and b3 == "accept" and k >= 0.35:
            fu = "caution"
        # (ii) low B3 confidence on a malicious message -> fusion escalates
        elif t == 1 and b3 == "accept" and c <= 0.55 and rng.random() < 0.6:
            fu = "caution"
        # (iii) corroboration shift: a caution with low conflict is confirmed to reject
        elif b3 == "caution" and k < 0.2 and rng.random() < 0.5:
            fu = "reject"
        # fusion clears an occasional benign false alarm (low conflict)
        if t == 0 and b3 != "accept" and k < 0.1 and rng.random() < 0.5:
            fu = "accept"
        b3_only.append(b3); fused.append(fu); conf.append(c); K.append(k); fam.append(f)
    return {"y_true": y_true.tolist(), "b3_only": b3_only, "fused": fused,
            "b3_conf": conf, "conflict_K": K, "family": fam}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/fusion_preds.json")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    set_style()

    d, is_demo = load_json_or_demo(args.input, lambda: make_demo(args.seed), "FUSION")
    yt = np.array(d["y_true"]); b3 = d["b3_only"]; fu = d["fused"]
    conf = d["b3_conf"]; K = d["conflict_K"]

    causes = [cause_of(b3[i], fu[i], K[i], conf[i]) for i in range(len(yt))]
    changed = sum(1 for c in causes if c != "unchanged")
    tax = {}
    for c in ["inter-source conflict", "low B3 confidence", "corroboration shift"]:
        tax[c] = causes.count(c)

    m_b3 = binary_metrics(yt, blocks(b3))
    m_fu = binary_metrics(yt, blocks(fu))
    # unsafe = malicious that end up accepted
    unsafe_b3 = int(((yt == 1) & (blocks(b3) == 0)).sum())
    unsafe_fu = int(((yt == 1) & (blocks(fu) == 0)).sum())

    out = {"demo": is_demo, "n": len(yt), "decisions_changed": changed,
           "cause_taxonomy": tax,
           "b3_only": {k: m_b3[k] for k in ("f1", "rec", "fpr")},
           "fused":   {k: m_fu[k] for k in ("f1", "rec", "fpr")},
           "delta_f1": m_fu["f1"] - m_b3["f1"],
           "unsafe_acceptances_b3": unsafe_b3, "unsafe_acceptances_fused": unsafe_fu}
    save_json(out, os.path.join(args.outdir, "results/fusion_divergence.json"))

    # ---- T21 ----
    rows = [
        ["Decisions changed by fusion", f"{changed} / {len(yt)}"],
        [r"\ \ inter-source conflict", str(tax['inter-source conflict'])],
        [r"\ \ low B3 confidence", str(tax['low B3 confidence'])],
        [r"\ \ corroboration shift", str(tax['corroboration shift'])],
        ["F1 (B3-only $\\to$ fused)", f"{m_b3['f1']:.3f} $\\to$ {m_fu['f1']:.3f}"],
        ["Unsafe acceptances (B3 $\\to$ fused)", f"{unsafe_b3} $\\to$ {unsafe_fu}"],
    ]
    save_latex_table(["Quantity", "Value"], rows,
                     "Trust Engine value beyond the B3 classifier: decisions changed by "
                     "Dempster--Shafer fusion, by cause, with net effect on F1 and unsafe "
                     "acceptances.", "tab:fusion",
                     os.path.join(args.outdir, "tables/T21_fusion_divergence.tex"),
                     align="lc")

    # ---- F23: cause taxonomy bar + before/after unsafe ----
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 2.7), gridspec_kw={"wspace": 0.35})
    cs = list(tax.keys()); vs = [tax[c] for c in cs]
    a1.bar(range(len(cs)), vs, color=[THREAT, AMBER, ACC], edgecolor=INK, linewidth=0.5)
    a1.set_xticks(range(len(cs)))
    a1.set_xticklabels(["conflict", "low conf.", "corrob."], fontsize=7)
    a1.set_ylabel("decisions changed"); a1.set_title("(a) why fusion changed a decision",
                                                      loc="left", fontsize=8.5, fontweight="bold")
    for i, v in enumerate(vs):
        a1.text(i, v + 0.2, str(v), ha="center", fontsize=7)

    a2.bar([0, 1], [unsafe_b3, unsafe_fu], color=[NEUTRAL, ACC], edgecolor=INK, linewidth=0.5)
    a2.set_xticks([0, 1]); a2.set_xticklabels(["B3 only", "+ fusion"], fontsize=7.5)
    a2.set_ylabel("unsafe acceptances")
    a2.set_title("(b) net safety effect", loc="left", fontsize=8.5, fontweight="bold")
    for i, v in enumerate([unsafe_b3, unsafe_fu]):
        a2.text(i, v + 0.1, str(v), ha="center", fontsize=7.5)
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F23_fusion_divergence.pdf"))

    print(f"\n  decisions changed: {changed}/{len(yt)}  taxonomy={tax}")
    print(f"  F1 {m_b3['f1']:.3f} -> {m_fu['f1']:.3f}   unsafe {unsafe_b3} -> {unsafe_fu}")


if __name__ == "__main__":
    main()
