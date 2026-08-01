#!/usr/bin/env python3
"""
stbv_bench/analyze_ablation.py
================================
Steps 3-5 of the layer ablation study (see ABLATION_STUDY.md): consumes
results/ablation/ablation_config_{1..5}.csv (produced by run_ablation.py)
and computes:

  Step 3: accuracy/precision/recall/F1/FPR/FNR/MCC per config, with a
          2000-resample 95% bootstrap CI on F1 (same method as the
          STBV-Bench v1 baseline's accuracy CI).
  Step 4: decision-divergence analysis -- config 5 vs config 3 (what B3+
          fusion adds over no-semantic-layer), config 5 vs config 4
          (fusion's own marginal contribution over raw B3), with McNemar's
          test, Cohen's h, and a per-attack-family flip breakdown.
  Step 5: explicit anomaly check -- flags any adjacent-config pair whose F1
          differs by <0.01, and uses the Step 4 flip counts to decide
          whether that looks like a real weak-layer result or a dead code
          path (near-zero F1 delta AND near-zero flips => likely inert).

Positive class convention (matches run_stbv_bench_eval.py /
evaluation/metrics_and_outputs.py): decision in {REJECT, CAUTION} counts
as positive ("system raised a concern"); ACCEPT is negative.

Usage:
  python3 stbv_bench/analyze_ablation.py --dir results/ablation
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import random
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONFIG_LABELS = {
    1: "B1 only",
    2: "B1+B2",
    3: "B1+B2+CP",
    4: "B1+B2+CP+B3 (no fusion)",
    5: "Full stack (B1+B2+CP+B3+TrustEngine)",
}


def positive(decision: str) -> bool:
    return decision in ("REJECT", "CAUTION")


def load(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def confusion(rows):
    tp = fp = fn = tn = 0
    for r in rows:
        truth = r["is_attacker"] in ("True", "true", "1")
        pred = positive(r["decision"])
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
        elif not pred and truth:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def metrics_from_confusion(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if (precision == precision and recall == recall and (precision + recall) > 0) else float("nan"))
    accuracy = (tp + tn) / n if n else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    fnr = fn / (fn + tp) if (fn + tp) else float("nan")
    mcc_denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / mcc_denom) if mcc_denom > 0 else float("nan")
    return {
        "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": accuracy, "precision": precision, "recall": recall,
        "f1": f1, "fpr": fpr, "fnr": fnr, "mcc": mcc,
    }


def bootstrap_f1_ci(rows, n_resamples=2000, seed=42):
    rng = random.Random(seed)
    n = len(rows)
    f1s = []
    for _ in range(n_resamples):
        tp = fp = fn = tn = 0
        for _ in range(n):
            r = rows[rng.randrange(n)]
            truth = r["is_attacker"] in ("True", "true", "1")
            pred = positive(r["decision"])
            if pred and truth:
                tp += 1
            elif pred and not truth:
                fp += 1
            elif not pred and truth:
                fn += 1
            else:
                tn += 1
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f1s.append(f1)
    f1s.sort()
    lo = f1s[int(0.025 * n_resamples)]
    hi = f1s[min(int(0.975 * n_resamples), n_resamples - 1)]
    return lo, hi


def mcnemar(rows_a, rows_b):
    """McNemar's test on paired binary predictions (positive=REJECT/CAUTION)
    between two configs over the SAME sample_ids. Returns
    (n01, n10, chi2_corrected, p_value, cohens_h)."""
    by_id_a = {r["sample_id"]: positive(r["decision"]) for r in rows_a}
    by_id_b = {r["sample_id"]: positive(r["decision"]) for r in rows_b}
    ids = sorted(set(by_id_a) & set(by_id_b))
    n01 = n10 = n00 = n11 = 0
    for sid in ids:
        a, b = by_id_a[sid], by_id_b[sid]
        if a and not b:
            n10 += 1
        elif not a and b:
            n01 += 1
        elif a and b:
            n11 += 1
        else:
            n00 += 1
    n_disc = n01 + n10
    if n_disc == 0:
        chi2 = 0.0
        p = 1.0
    else:
        chi2 = (abs(n01 - n10) - 1) ** 2 / n_disc  # continuity-corrected
        p = math.erfc(math.sqrt(chi2 / 2.0))  # chi2(1) survival via erfc
    p_a = sum(by_id_a.values()) / len(ids)
    p_b = sum(by_id_b.values()) / len(ids)
    phi_a = 2 * math.asin(math.sqrt(min(max(p_a, 0.0), 1.0)))
    phi_b = 2 * math.asin(math.sqrt(min(max(p_b, 0.0), 1.0)))
    cohens_h = phi_b - phi_a
    return {
        "n_ids": len(ids), "n01": n01, "n10": n10, "n_flipped": n_disc,
        "pct_flipped": n_disc / len(ids) if ids else float("nan"),
        "chi2": chi2, "p_value": p, "cohens_h": cohens_h,
        "positive_rate_a": p_a, "positive_rate_b": p_b,
    }


def flip_breakdown_by_family(rows_a, rows_b):
    by_id_a = {r["sample_id"]: (positive(r["decision"]), r["attack_family"]) for r in rows_a}
    by_id_b = {r["sample_id"]: positive(r["decision"]) for r in rows_b}
    fam_flips = defaultdict(lambda: {"n": 0, "flipped": 0})
    for sid, (a, fam) in by_id_a.items():
        if sid not in by_id_b:
            continue
        b = by_id_b[sid]
        fam_flips[fam]["n"] += 1
        if a != b:
            fam_flips[fam]["flipped"] += 1
    return {
        fam: {**d, "pct_flipped": d["flipped"] / d["n"] if d["n"] else float("nan")}
        for fam, d in fam_flips.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    d = pathlib.Path(args.dir)

    configs = {i: load(d / f"ablation_config_{i}.csv") for i in (1, 2, 3, 4, 5)}

    # --- Step 3 ---
    table = {}
    for i, rows in configs.items():
        tp, fp, fn, tn = confusion(rows)
        m = metrics_from_confusion(tp, fp, fn, tn)
        lo, hi = bootstrap_f1_ci(rows)
        m["f1_ci95"] = [lo, hi]
        m["label"] = CONFIG_LABELS[i]
        table[i] = m
        print(f"Config {i} ({CONFIG_LABELS[i]}): n={m['n']} "
              f"acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
              f"recall={m['recall']:.4f} f1={m['f1']:.4f} "
              f"[{lo:.4f},{hi:.4f}] fpr={m['fpr']:.4f} fnr={m['fnr']:.4f} "
              f"mcc={m['mcc']:.4f}")

    # --- Step 4: divergence analysis ---
    print("\n--- Divergence analysis ---")
    div_5v3 = mcnemar(configs[5], configs[3])
    div_5v4 = mcnemar(configs[5], configs[4])
    print(f"Config 5 vs Config 3 (what B3+fusion adds over no-semantic-layer): "
          f"{div_5v3['n_flipped']}/{div_5v3['n_ids']} flipped "
          f"({div_5v3['pct_flipped']*100:.1f}%), p={div_5v3['p_value']:.3e}, "
          f"Cohen's h={div_5v3['cohens_h']:.3f}")
    print(f"Config 5 vs Config 4 (fusion's own marginal contribution over raw B3): "
          f"{div_5v4['n_flipped']}/{div_5v4['n_ids']} flipped "
          f"({div_5v4['pct_flipped']*100:.1f}%), p={div_5v4['p_value']:.3e}, "
          f"Cohen's h={div_5v4['cohens_h']:.3f}")

    fam_5v3 = flip_breakdown_by_family(configs[5], configs[3])
    fam_5v4 = flip_breakdown_by_family(configs[5], configs[4])

    # --- Step 5: anomaly check on adjacent configs ---
    print("\n--- Adjacent-config anomaly check (|deltaF1| < 0.01) ---")
    anomalies = []
    adjacent_pairs = [(1, 2), (2, 3), (3, 4), (4, 5)]
    div_cache = {}
    for a, b in adjacent_pairs:
        delta = table[b]["f1"] - table[a]["f1"]
        div = mcnemar(configs[b], configs[a])
        div_cache[(a, b)] = div
        flag = abs(delta) < 0.01
        note = ""
        if flag:
            likely_inert = div["n_flipped"] / div["n_ids"] < 0.01
            note = ("LIKELY INERT (near-zero F1 delta AND near-zero flips)"
                     if likely_inert else
                     "REAL WEAK CONTRIBUTION (near-zero F1 delta but flips are non-trivial -- "
                     "layer changes individual decisions without moving aggregate F1, e.g. "
                     "roughly equal TP gains and FP losses)")
            anomalies.append({
                "pair": f"{a}->{b}", "delta_f1": delta,
                "pct_flipped": div["pct_flipped"], "assessment": note,
            })
            print(f"  Config {a} -> {b}: deltaF1={delta:+.4f}, "
                  f"flipped={div['pct_flipped']*100:.2f}% -> {note}")
    if not anomalies:
        print("  none flagged (all adjacent-config F1 deltas >= 0.01)")

    result = {
        "table": table,
        "divergence": {
            "config5_vs_config3": div_5v3,
            "config5_vs_config4": div_5v4,
            "config5_vs_config3_by_family": fam_5v3,
            "config5_vs_config4_by_family": fam_5v4,
        },
        "adjacent_config_deltas": {
            f"{a}->{b}": {"delta_f1": table[b]["f1"] - table[a]["f1"],
                          **{k: v for k, v in div_cache[(a, b)].items()}}
            for a, b in adjacent_pairs
        },
        "anomalies_flagged": anomalies,
    }
    out_path = d / "ablation_summary.json"
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n-> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
