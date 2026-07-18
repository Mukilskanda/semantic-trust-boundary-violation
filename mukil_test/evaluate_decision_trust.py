#!/usr/bin/env python3
# =====================================================================
# evaluate_decision_trust.py  --  Decision Trust metric suite  (AV-C1/C2)
# ---------------------------------------------------------------------
# Turns "Decision Trust" into measured quantities. Produces:
#   results/decision_trust.json
#   tables/T25_decision_trust.tex
#   figures/F28_udpr_waterfall.pdf   (attacks -> passed comm -> caught -> residual)
#
# Metrics: DAR, DRR, DCR, UDPR, RUAR (defined in blueprint Part II, C.1).
#
# INPUT SCHEMA (results/decision_preds.json):
# {
#   "y_true":        [0/1 ...],                       # 1 = malicious
#   "comm_decision": ["accept"/"caution"/"reject"...],# communication-only stack
#   "full_decision": ["accept"/"caution"/"reject"...],# full architecture
#   "final_conf":    [float ...],                     # optional, decision confidence
#   "family":        [str ...]
# }
# "accept" = message trusted; anything else = blocked/flagged.
#
# RUN:  python evaluate_decision_trust.py                     # demo
#       python evaluate_decision_trust.py --input results/decision_preds.json
#       python evaluate_decision_trust.py --caution-blocks    # count caution as blocked
# =====================================================================
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_common import (set_style, demo_watermark, bootstrap_ci,
                         load_json_or_demo, save_json, save_latex_table, savefig,
                         ACC, NEUTRAL, THREAT, BENIGN, INK)
import matplotlib.pyplot as plt


def make_demo(seed=0):
    rng = np.random.default_rng(seed)
    n = 260
    y_true = (rng.random(n) < 0.60).astype(int)
    comm, full, conf, fam = [], [], [], []
    for t in y_true:
        # communication stack: authenticated attacks are accepted (the whole point)
        comm.append("accept" if t == 1 else ("accept" if rng.random() < 0.97 else "reject"))
        if t == 1:
            # full stack rejects most malicious (semantic gate), misses a few (dilution)
            full.append("reject" if rng.random() < 0.75 else "accept")
        else:
            full.append("accept" if rng.random() < 0.98 else "caution")
        conf.append(float(np.clip(rng.normal(0.82, 0.12), 0, 1)))
        fam.append("malicious" if t else "benign")
    return {"y_true": y_true.tolist(), "comm_decision": comm,
            "full_decision": full, "final_conf": conf, "family": fam}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/decision_preds.json")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--caution-blocks", action="store_true",
                    help="treat 'caution' as blocked (default: only 'reject' blocks)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    set_style()

    d, is_demo = load_json_or_demo(args.input, lambda: make_demo(args.seed), "DECISION")
    yt = np.array(d["y_true"])
    block_set = {"reject", "caution"} if args.caution_blocks else {"reject"}
    accepted = lambda dec: np.array([0 if x in block_set else 1 for x in dec])  # 1 = accepted/trusted

    comm_acc = accepted(d["comm_decision"])
    full_acc = accepted(d["full_decision"])
    N = len(yt); mal = (yt == 1); ben = (yt == 0)

    # ---- metric family ----
    DAR = full_acc.mean()                         # decision acceptance rate
    DRR = 1 - DAR                                 # decision rejection rate
    DCR = float((comm_acc != full_acc).mean())    # decisions the full stack corrects
    # UDPR: of malicious accepted by comm, fraction the full stack blocks
    comm_unsafe = mal & (comm_acc == 1)
    prevented = comm_unsafe & (full_acc == 0)
    UDPR = float(prevented.sum() / comm_unsafe.sum()) if comm_unsafe.sum() else float("nan")
    # RUAR: malicious still accepted by full stack (residual risk)
    RUAR = float((mal & (full_acc == 1)).sum() / mal.sum()) if mal.sum() else float("nan")
    # benign false-block rate under full stack
    BFR = float((ben & (full_acc == 0)).sum() / ben.sum()) if ben.sum() else float("nan")

    def ci_udpr():
        rng = np.random.default_rng(args.seed); idx0 = np.arange(N); vals = []
        for _ in range(10000):
            i = rng.integers(0, N, N)
            cu = mal[i] & (comm_acc[i] == 1)
            if cu.sum():
                vals.append((cu & (full_acc[i] == 0)).sum() / cu.sum())
        return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (float("nan"),)*2

    udpr_ci = ci_udpr()
    out = {"demo": is_demo, "n": N, "caution_blocks": args.caution_blocks,
           "DAR": DAR, "DRR": DRR, "DCR": DCR,
           "UDPR": UDPR, "UDPR_ci95": udpr_ci, "RUAR": RUAR, "benign_false_block": BFR,
           "counts": {"malicious": int(mal.sum()), "benign": int(ben.sum()),
                      "comm_unsafe_accepts": int(comm_unsafe.sum()),
                      "prevented": int(prevented.sum()),
                      "residual_unsafe": int((mal & (full_acc == 1)).sum())}}
    save_json(out, os.path.join(args.outdir, "results/decision_trust.json"))

    # ---- T25 ----
    rows = [
        ["Decision Acceptance Rate (DAR)", f"{DAR:.3f}"],
        ["Decision Rejection Rate (DRR)", f"{DRR:.3f}"],
        ["Decision Correction Rate (DCR)", f"{DCR:.3f}"],
        [r"\textbf{Unsafe-Decision Prevention (UDPR)}",
         f"\\textbf{{{UDPR:.3f}}} [{udpr_ci[0]:.3f}, {udpr_ci[1]:.3f}]"],
        ["Residual Unsafe-Acceptance (RUAR)", f"{RUAR:.3f}"],
        ["Benign false-block rate", f"{BFR:.3f}"],
    ]
    save_latex_table(["Decision-trust metric", "Value (95\\% CI)"], rows,
                     "Decision-trust metrics. UDPR is the fraction of authenticated "
                     "malicious messages that communication trust would accept but the "
                     "full architecture blocks; RUAR is the residual that still slips "
                     "through.", "tab:decisiontrust",
                     os.path.join(args.outdir, "tables/T25_decision_trust.tex"), align="lc")

    # ---- F28: prevention waterfall ----
    n_mal = int(mal.sum())
    passed_comm = int(comm_unsafe.sum())
    caught = int(prevented.sum())
    residual = passed_comm - caught
    stages = ["malicious\nmessages", "accepted by\ncomm. trust", "caught by\nsemantic stack", "residual\nunsafe"]
    vals = [n_mal, passed_comm, caught, residual]
    colors = [NEUTRAL, THREAT, ACC, THREAT]
    fig, ax = plt.subplots(figsize=(4.0, 2.9))
    ax.bar(range(4), vals, color=colors, edgecolor=INK, linewidth=0.5)
    ax.set_xticks(range(4)); ax.set_xticklabels(stages, fontsize=7)
    ax.set_ylabel("messages")
    ax.set_title(f"Unsafe-decision prevention (UDPR = {UDPR:.2f})",
                 loc="left", fontsize=8.5, fontweight="bold")
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.01, str(v), ha="center", fontsize=7.5)
    if is_demo:
        demo_watermark(fig)
    savefig(fig, os.path.join(args.outdir, "figures/F28_udpr_waterfall.pdf"))

    print(f"\n  DAR={DAR:.3f} DRR={DRR:.3f} DCR={DCR:.3f}")
    print(f"  UDPR={UDPR:.3f} {udpr_ci}   RUAR={RUAR:.3f}   benign_false_block={BFR:.3f}")


if __name__ == "__main__":
    main()
