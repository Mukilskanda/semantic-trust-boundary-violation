"""
b3_eval/v25_finetune/recalibrate_v1_arm_a.py
================================================
Extracts arm (a) -- ORIGINAL checkpoint + ORIGINAL thresholds -- filtered
to the exact same TEST sample_ids used in the recalibration three-way
comparison, from the already-committed
b3_eval/v25_finetune/ablation_results/original/ablation_config_{4,5}.csv
(prior task's real rerun; NOT recomputed here, per the task's explicit
instruction to reuse existing numbers for the old-checkpoint arm).
"""
from __future__ import annotations
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RAW_CSV = HERE / "results" / "v1_finetuned_recalibration_raw.csv"
ORIG_DIR = HERE / "ablation_results" / "original"
OUT_JSON = HERE / "results" / "v1_test_arm_a_original.json"


def positive(decision):
    return decision in ("CAUTION", "REJECT")


def prf(rows):
    tp = sum(1 for r in rows if r["is_attacker"] == "True" and positive(r["decision"]))
    fp = sum(1 for r in rows if r["is_attacker"] == "False" and positive(r["decision"]))
    fn = sum(1 for r in rows if r["is_attacker"] == "True" and not positive(r["decision"]))
    tn = sum(1 for r in rows if r["is_attacker"] == "False" and not positive(r["decision"]))
    n = len(rows)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else None
    return {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": (tp + tn) / n,
            "precision": prec, "recall": rec, "f1": f1, "fpr": fpr}


def bootstrap_ci_f1(rows, n_boot=2000, seed=1):
    import random
    rng = random.Random(seed)
    vals = []
    n = len(rows)
    for _ in range(n_boot):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        vals.append(prf(sample)["f1"])
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]


def main():
    test_ids = {r["sample_id"] for r in csv.DictReader(open(RAW_CSV, newline="", encoding="utf-8"))
                if r["split"] == "test"}
    print(f"test_ids n={len(test_ids)}")

    out = {}
    for cfg in (4, 5):
        rows = list(csv.DictReader(open(ORIG_DIR / f"ablation_config_{cfg}.csv", newline="", encoding="utf-8")))
        filtered = [r for r in rows if r["sample_id"] in test_ids]
        m = prf(filtered)
        ci = bootstrap_ci_f1(filtered)
        out[f"config_{cfg}"] = {**m, "f1_ci95": ci}
        print(f"config {cfg}: n={m['n']} f1={m['f1']:.4f} rec={m['recall']:.4f} prec={m['precision']:.4f}")

    OUT_JSON.write_text(json.dumps(out, indent=2))
    print(f"Written: {OUT_JSON}")


if __name__ == "__main__":
    main()
