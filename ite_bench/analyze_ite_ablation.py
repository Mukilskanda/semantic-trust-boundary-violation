"""
ite_bench/analyze_ite_ablation.py
====================================
Computes accuracy/precision/recall/F1/FPR/confusion matrix/bootstrap CI
for each of the 5 ITE-Bench ablation configs, overall and broken out by
layer (B1/B2/B3) and by attack family, plus McNemar tests where the
comparison is valid (paired decisions on the identical sample set).
"""
from __future__ import annotations
import csv, json, math, pathlib, random, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "ite_bench" / "results"


def load(cfg):
    rows = []
    with open(RES / f"ite_config_{cfg}.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["is_attacker"] = r["is_attacker"] == "True"
            rows.append(r)
    return rows


def confusion(rows, positive_decisions=("CAUTION", "REJECT")):
    tp = fp = fn = tn = 0
    for r in rows:
        pred_pos = r["decision"] in positive_decisions
        truth = r["is_attacker"]
        if pred_pos and truth: tp += 1
        elif pred_pos and not truth: fp += 1
        elif not pred_pos and truth: fn += 1
        else: tn += 1
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec == prec and rec == rec and prec + rec) else float("nan")
    acc = (tp + tn) / n if n else float("nan")
    fpr = fp / (fp + tn) if fp + tn else float("nan")
    return {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "fpr": fpr}


def bootstrap_ci(rows, n_resamples=2000, seed=42):
    rng = random.Random(seed)
    n = len(rows)
    f1s = []
    for _ in range(n_resamples):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        m = confusion(sample)
        if m["f1"] == m["f1"]:
            f1s.append(m["f1"])
    f1s.sort()
    if not f1s:
        return None
    lo = f1s[int(0.025 * len(f1s))]
    hi = f1s[int(0.975 * len(f1s))]
    return {"f1_ci_lo": lo, "f1_ci_hi": hi}


def mcnemar(rows_a, rows_b, positive_decisions=("CAUTION", "REJECT")):
    by_id_a = {r["sample_id"]: r["decision"] in positive_decisions for r in rows_a}
    by_id_b = {r["sample_id"]: r["decision"] in positive_decisions for r in rows_b}
    b01 = b10 = 0
    for sid, pa in by_id_a.items():
        pb = by_id_b.get(sid)
        if pb is None:
            continue
        if pa and not pb: b10 += 1
        elif pb and not pa: b01 += 1
    if b01 + b10 == 0:
        return {"b01": b01, "b10": b10, "chi2": 0.0, "p": 1.0}
    chi2 = (abs(b01 - b10) - 1) ** 2 / (b01 + b10)
    p = math.erfc(math.sqrt(chi2 / 2.0))
    return {"b01": b01, "b10": b10, "chi2": chi2, "p": p}


def main():
    configs = {1: "B1 only", 2: "B1+B2", 3: "B1+B2+CP", 4: "B3 only (no fusion)", 5: "Full stack"}
    data = {cfg: load(cfg) for cfg in configs}

    report = {"overall": {}, "by_layer": {}, "by_family": {}, "mcnemar": {}}

    print("=== Overall ===")
    for cfg, name in configs.items():
        m = confusion(data[cfg])
        ci = bootstrap_ci(data[cfg])
        m["f1_ci"] = ci
        report["overall"][cfg] = {"name": name, "metrics": m}
        print(f"[{cfg}] {name:22s} acc={m['accuracy']:.3f} prec={m['precision']:.3f} "
              f"rec={m['recall']:.3f} f1={m['f1']:.3f} fpr={m['fpr']:.3f} "
              f"CI=[{ci['f1_ci_lo']:.3f},{ci['f1_ci_hi']:.3f}]" if ci else "")

    print("\n=== By layer (per-layer subset, full-stack config 5) ===")
    for layer in ("B1", "B2", "B3"):
        layer_rows_by_cfg = {}
        for cfg in (1, 2, 3, 5):
            rows = [r for r in data[cfg] if r["layer"] == layer]
            m = confusion(rows)
            layer_rows_by_cfg[cfg] = m
        report["by_layer"][layer] = layer_rows_by_cfg
        print(f"-- {layer} --")
        for cfg, name in configs.items():
            if cfg == 4:
                continue
            m = layer_rows_by_cfg[cfg]
            print(f"   [{cfg}] {name:22s} acc={m['accuracy']:.3f} rec={m['recall']:.3f} f1={m['f1']:.3f} fpr={m['fpr']:.3f}")

    print("\n=== Per-family recall, full stack (config 5) vs B1 only (config 1) ===")
    families = sorted(set(r["attack_family"] for r in data[5] if r["is_attacker"]))
    for fam in families:
        rows1 = [r for r in data[1] if r["attack_family"] == fam]
        rows5 = [r for r in data[5] if r["attack_family"] == fam]
        rec1 = sum(1 for r in rows1 if r["decision"] in ("CAUTION", "REJECT")) / len(rows1) if rows1 else float("nan")
        rec5 = sum(1 for r in rows5 if r["decision"] in ("CAUTION", "REJECT")) / len(rows5) if rows5 else float("nan")
        report["by_family"][fam] = {"n": len(rows5), "recall_config1": rec1, "recall_config5": rec5}
        print(f"  {fam:38s} n={len(rows5):4d} rec(B1-only)={rec1:.3f} rec(full-stack)={rec5:.3f}")

    print("\n=== McNemar: config 5 (full stack) vs config 4 (B3 alone) ===")
    mc = mcnemar(data[4], data[5])
    report["mcnemar"]["config5_vs_config4"] = mc
    print(f"  b01={mc['b01']} b10={mc['b10']} chi2={mc['chi2']:.2f} p={mc['p']:.2e}")

    print("\n=== McNemar: config 3 (B1+B2+CP) vs config 1 (B1 only) ===")
    mc2 = mcnemar(data[1], data[3])
    report["mcnemar"]["config3_vs_config1"] = mc2
    print(f"  b01={mc2['b01']} b10={mc2['b10']} chi2={mc2['chi2']:.2f} p={mc2['p']:.2e}")

    (RES / "analysis_report.json").write_text(json.dumps(report, indent=2, default=str))
    print(f"\n[ok] {RES / 'analysis_report.json'}")


if __name__ == "__main__":
    main()
