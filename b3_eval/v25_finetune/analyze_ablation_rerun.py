"""
b3_eval/v25_finetune/analyze_ablation_rerun.py
==================================================
Consumes b3_eval/v25_finetune/ablation_results/{original,finetuned}/
ablation_config_{1,2,3,4,5}.csv (written by rerun_paper_ablation.py) and
reproduces exactly the manuscript's Table tab:main_ablation / Table
tab:full_ablation metrics (Acc/Prec/Rec/F1/FPR per config), for both
checkpoints, plus:

  - Old vs new comparison table
  - McNemar's test + Cohen's h, config 5 (full stack) old vs new
  - McNemar's test + Cohen's h, config 4 (B3 alone) old vs new
  - Per-attack-family recall, both checkpoints, config 5
  - Confirmation that configs 1-3 are byte-identical to the original
    numbers already in the paper (since enable_b3=False makes them
    checkpoint-independent by construction)

Scoring convention matches the paper exactly: positive = Caution or
Reject (never Accept).

Run with: python3 b3_eval/v25_finetune/analyze_ablation_rerun.py
"""
from __future__ import annotations

import csv
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RESULTS_DIR = HERE / "ablation_results"
OUT = HERE / "results" / "ablation_rerun_comparison.json"

CONFIG_LABELS = {1: "B1 only", 2: "B1+B2", 3: "B1+B2+CP",
                  4: "B1+B2+CP+B3, no fusion", 5: "B1+B2+CP+B3 (full stack)"}


def load_config(checkpoint, cfg_id):
    path = RESULTS_DIR / checkpoint / f"ablation_config_{cfg_id}.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def positive(decision):
    return decision in ("CAUTION", "REJECT")


def prf(rows):
    tp = sum(1 for r in rows if r["is_attacker"] == "True" and positive(r["decision"]))
    fp = sum(1 for r in rows if r["is_attacker"] == "False" and positive(r["decision"]))
    fn = sum(1 for r in rows if r["is_attacker"] == "True" and not positive(r["decision"]))
    tn = sum(1 for r in rows if r["is_attacker"] == "False" and not positive(r["decision"]))
    n = len(rows)
    acc = (tp + tn) / n
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec is not None and (prec + rec) > 0) else None
    fpr = fp / (fp + tn) if (fp + tn) else None
    return {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "fpr": fpr}


def per_family_recall(rows):
    from collections import defaultdict
    fam = defaultdict(lambda: {"tp": 0, "fn": 0})
    for r in rows:
        if r["is_attacker"] != "True":
            continue
        f = r["attack_family"]
        if positive(r["decision"]):
            fam[f]["tp"] += 1
        else:
            fam[f]["fn"] += 1
    out = {}
    for f, d in fam.items():
        n = d["tp"] + d["fn"]
        out[f] = {"n": n, "recall": d["tp"] / n if n else None}
    return out


def mcnemar(rows_a, rows_b, labels_key="is_attacker"):
    # Paired on identical sample_id ordering (both configs iterate the same
    # samples list in the same order in rerun_paper_ablation.py).
    correct_a = [int(positive(a["decision"]) == (a["is_attacker"] == "True")) for a in rows_a]
    correct_b = [int(positive(b["decision"]) == (b["is_attacker"] == "True")) for b in rows_b]
    b01 = sum(1 for ca, cb in zip(correct_a, correct_b) if ca == 1 and cb == 0)
    b10 = sum(1 for ca, cb in zip(correct_a, correct_b) if ca == 0 and cb == 1)
    n_disc = b01 + b10
    if n_disc == 0:
        return {"b01": b01, "b10": b10, "n_discordant": 0, "p_value": 1.0}
    if n_disc < 25:
        from scipy.stats import binomtest
        p = binomtest(min(b01, b10), n_disc, 0.5, alternative="two-sided").pvalue
        return {"b01": b01, "b10": b10, "n_discordant": n_disc, "p_value": float(p), "method": "exact_binomial"}
    stat = (abs(b01 - b10) - 1) ** 2 / (b01 + b10)
    from scipy.stats import chi2
    p = 1 - chi2.cdf(stat, df=1)
    return {"b01": b01, "b10": b10, "n_discordant": n_disc, "statistic": stat,
            "p_value": float(p), "method": "chi2_continuity_corrected"}


def cohens_h(p1, p2):
    return 2 * math.asin(math.sqrt(p2)) - 2 * math.asin(math.sqrt(p1))


def main():
    out = {"per_checkpoint": {}, "old_vs_new": {}}

    all_rows = {}
    for ckpt in ("original", "finetuned"):
        all_rows[ckpt] = {cfg: load_config(ckpt, cfg) for cfg in (1, 2, 3, 4, 5)}
        out["per_checkpoint"][ckpt] = {}
        print(f"\n=== {ckpt} ===")
        for cfg in (1, 2, 3, 4, 5):
            m = prf(all_rows[ckpt][cfg])
            out["per_checkpoint"][ckpt][CONFIG_LABELS[cfg]] = m
            print(f"  {CONFIG_LABELS[cfg]:30s} acc={m['accuracy']:.3f} "
                  f"prec={m['precision']:.3f} rec={m['recall']:.3f} "
                  f"f1={m['f1']:.3f} fpr={m['fpr']:.3f}" if m['precision'] is not None else
                  f"  {CONFIG_LABELS[cfg]:30s} acc={m['accuracy']:.3f} rec={m['recall']:.3f} fpr={m['fpr']:.3f}")

        fam5 = per_family_recall(all_rows[ckpt][5])
        out["per_checkpoint"][ckpt]["per_family_recall_config5"] = fam5

    # configs 1-3 checkpoint-independence check
    for cfg in (1, 2, 3):
        o = [r["decision"] for r in all_rows["original"][cfg]]
        f = [r["decision"] for r in all_rows["finetuned"][cfg]]
        n_diff = sum(1 for a, b in zip(o, f) if a != b)
        print(f"\nConfig {cfg} ({CONFIG_LABELS[cfg]}) decisions differ old vs new: {n_diff}/{len(o)} "
              f"(expected 0 -- enable_b3=False, B3 never loaded)")
        out["old_vs_new"][f"config_{cfg}_independence_check"] = {"n_differ": n_diff, "n_total": len(o)}

    # configs 4 and 5: real comparison
    for cfg in (4, 5):
        mc = mcnemar(all_rows["original"][cfg], all_rows["finetuned"][cfg])
        rec_o = out["per_checkpoint"]["original"][CONFIG_LABELS[cfg]]["recall"]
        rec_f = out["per_checkpoint"]["finetuned"][CONFIG_LABELS[cfg]]["recall"]
        h = cohens_h(rec_o, rec_f) if rec_o is not None and rec_f is not None else None
        out["old_vs_new"][f"config_{cfg}_mcnemar"] = mc
        out["old_vs_new"][f"config_{cfg}_cohens_h_recall"] = h
        print(f"\nConfig {cfg} ({CONFIG_LABELS[cfg]}) old vs new: McNemar {mc}, Cohen's h (recall)={h}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nWritten: {OUT}")


if __name__ == "__main__":
    main()
