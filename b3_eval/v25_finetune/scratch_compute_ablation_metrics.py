"""Compute real Acc/Prec/Rec/F1/FPR for each of the 6 v2.5b ablation configs
from the existing per-sample CSVs in ablation_results/v25b_full_hardmine/.
No fabrication: decision->predicted-positive mapping is CAUTION or REJECT
counted as "flagged" (matches pipeline's Accept/Caution/Reject convention;
the paper's own convention treats non-ACCEPT as the positive/attack call
for FPR, and REJECT as positive for the "recall" figures matching Table
tab:v25b's full-stack numbers -- both are reported below for transparency).
"""
import csv, pathlib, json

BASE = pathlib.Path("b3_eval/v25_finetune/ablation_results/v25b_full_hardmine")
CONFIGS = {
    1: "B1 only",
    2: "B1+B2",
    3: "B1+B2+CP",
    4: "B3 only",
    5: "Full STBV (B1+B2+CP+B3)",
    6: "B1+B2+B3 (no CP)",
}

def metrics_for(decisions_labels, positive_decisions):
    tp = fp = tn = fn = 0
    for dec, is_attacker in decisions_labels:
        pred_pos = dec in positive_decisions
        if is_attacker and pred_pos:
            tp += 1
        elif is_attacker and not pred_pos:
            fn += 1
        elif not is_attacker and pred_pos:
            fp += 1
        else:
            tn += 1
    n = tp + fp + tn + fn
    acc = (tp + tn) / n if n else float("nan")
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    return dict(n=n, tp=tp, fp=fp, tn=tn, fn=fn, acc=acc, prec=prec, rec=rec, f1=f1, fpr=fpr)

results = {}
for cfg, name in CONFIGS.items():
    path = BASE / f"config_{cfg}.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    decisions_labels = [(r["decision"], r["is_attacker"] == "True") for r in rows]
    # REJECT-only-as-positive (strict "blocked" reading)
    m_reject = metrics_for(decisions_labels, {"REJECT"})
    # non-ACCEPT-as-positive (CAUTION+REJECT flagged reading, matches paper's FPR=0.315 for config 5)
    m_flagged = metrics_for(decisions_labels, {"REJECT", "CAUTION"})
    results[cfg] = {"name": name, "reject_only": m_reject, "flagged": m_flagged}

print(json.dumps(results, indent=2))
