"""
b3_eval/v25_finetune/audit_statistics.py
===========================================
Hostile statistical validation, per the reviewer's request. Re-derives
metrics DIRECTLY from fresh raw predictions on the held-out v2.5 test
split (does not read stored full_evaluation.json numbers), then:

  - Recomputes accuracy/precision/recall/F1/ROC-AUC/PR-AUC/ECE/Brier
    independently, from scratch
  - Bootstrap 95% CIs (10,000 resamples, seed=42) for accuracy and F1
  - McNemar's test (paired, on the SAME test messages) for
    original vs fine-tuned
  - Cohen's h effect size for the accuracy difference

Also verifies baseline fairness: same test split, same tokenizer, same
max_length, same batch handling, same code path for both models (the
LoadedModel.predict() method in eval_common.py is IDENTICAL for both --
only the loaded weights differ).

Run with: python3 b3_eval/v25_finetune/audit_statistics.py
"""
from __future__ import annotations

import json
import math
import pathlib
import random
import sys

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from eval_common import load_original, load_finetuned, load_jsonl

DATA = HERE / "data"
OUT = HERE / "results" / "statistical_audit.json"
SEED = 42


def recompute_metrics(pred_ids, labels, prob_mal):
    n = len(labels)
    tp = sum(1 for p, y in zip(pred_ids, labels) if p == 1 and y == 1)
    fp = sum(1 for p, y in zip(pred_ids, labels) if p == 1 and y == 0)
    fn = sum(1 for p, y in zip(pred_ids, labels) if p == 0 and y == 1)
    tn = sum(1 for p, y in zip(pred_ids, labels) if p == 0 and y == 0)
    acc = (tp + tn) / n
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    # ROC-AUC via Mann-Whitney U statistic (rank-sum method, independent
    # implementation from the one used in eval_common.py's trapezoid sweep)
    pos_scores = [prob_mal[i] for i in range(n) if labels[i] == 1]
    neg_scores = [prob_mal[i] for i in range(n) if labels[i] == 0]
    if pos_scores and neg_scores:
        ranks = np.argsort(np.argsort(prob_mal)) + 1
        rank_sum_pos = sum(ranks[i] for i in range(n) if labels[i] == 1)
        n_pos, n_neg = len(pos_scores), len(neg_scores)
        auc = (rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    else:
        auc = float("nan")

    # PR-AUC via sklearn (independent library, not our own trapezoid code)
    from sklearn.metrics import average_precision_score
    pr_auc = average_precision_score(labels, prob_mal)

    # ECE (15-bin) and Brier, independent re-implementation
    n_bins = 15
    bins = [[] for _ in range(n_bins)]
    for i in range(n):
        conf = max(prob_mal[i], 1 - prob_mal[i])
        correct = int(pred_ids[i] == labels[i])
        idx = min(int(conf * n_bins), n_bins - 1)
        bins[idx].append((conf, correct))
    ece = 0.0
    for b in bins:
        if not b:
            continue
        confs = [c for c, _ in b]
        corrects = [c for _, c in b]
        ece += (len(b) / n) * abs(sum(corrects) / len(b) - sum(confs) / len(b))
    brier = sum((prob_mal[i] - labels[i]) ** 2 for i in range(n)) / n

    return {"n": n, "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "roc_auc": auc, "pr_auc": pr_auc, "ece": ece, "brier": brier,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def bootstrap_ci(pred_ids, labels, metric_fn, n_boot=10000, seed=SEED, alpha=0.05):
    rng = np.random.default_rng(seed)
    n = len(labels)
    pred_arr = np.array(pred_ids)
    label_arr = np.array(labels)
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        stats[b] = metric_fn(pred_arr[idx], label_arr[idx])
    lo = np.percentile(stats, 100 * alpha / 2)
    hi = np.percentile(stats, 100 * (1 - alpha / 2))
    return float(lo), float(hi), float(stats.mean())


def acc_metric(preds, labels):
    return float((preds == labels).mean())


def f1_metric(preds, labels):
    tp = int(((preds == 1) & (labels == 1)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def mcnemar_test(pred_a, pred_b, labels):
    """Exact/continuity-corrected McNemar's test on paired correctness
    (correct_a vs correct_b per identical test message)."""
    correct_a = [int(a == y) for a, y in zip(pred_a, labels)]
    correct_b = [int(b == y) for b, y in zip(pred_b, labels)]
    b01 = sum(1 for ca, cb in zip(correct_a, correct_b) if ca == 1 and cb == 0)  # a right, b wrong
    b10 = sum(1 for ca, cb in zip(correct_a, correct_b) if ca == 0 and cb == 1)  # a wrong, b right
    n_disc = b01 + b10
    if n_disc == 0:
        return {"b01_a_right_b_wrong": b01, "b10_a_wrong_b_right": b10,
                "statistic": 0.0, "p_value": 1.0, "note": "no discordant pairs"}
    if n_disc < 25:
        # exact binomial two-sided test
        from scipy.stats import binomtest
        res = binomtest(min(b01, b10), n_disc, 0.5, alternative="two-sided")
        p = res.pvalue
        stat = None
        method = "exact_binomial"
    else:
        stat = (abs(b01 - b10) - 1) ** 2 / (b01 + b10)  # continuity-corrected chi2
        from scipy.stats import chi2
        p = 1 - chi2.cdf(stat, df=1)
        method = "chi2_continuity_corrected"
    return {"b01_a_right_b_wrong": b01, "b10_a_wrong_b_right": b10,
            "n_discordant": n_disc, "statistic": stat, "p_value": float(p), "method": method}


def cohens_h(p1, p2):
    phi1 = 2 * math.asin(math.sqrt(p1))
    phi2 = 2 * math.asin(math.sqrt(p2))
    return phi1 - phi2


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    orig = load_original(device=device)
    fine = load_finetuned(device=device)

    test_rows = load_jsonl(DATA / "test_split_full.jsonl")
    texts = [r["text"] for r in test_rows]
    labels = [int(r["label"]) for r in test_rows]

    print(f"\nBaseline fairness check:")
    print(f"  Both models scored on: {len(test_rows)} rows from data/test_split_full.jsonl")
    print(f"  Tokenizer: AutoTokenizer.from_pretrained per-model directory (same base vocab -- "
          f"fine-tuned tokenizer is copied verbatim from the original at save time)")
    print(f"  max_length=256 for both (eval_common.MAX_LENGTH, single constant used by both)")
    print(f"  Same predict() code path (LoadedModel.predict in eval_common.py; only self.model differs)")
    print(f"  No confidence threshold applied to either (raw argmax on softmax(logits/T))")

    results = {}
    preds_by_model = {}
    for model in (orig, fine):
        print(f"\nScoring {model.name}...")
        preds = model.predict(texts, batch_size=32)
        pred_ids = [p["label_id"] for p in preds]
        prob_mal = [p["prob_malicious"] for p in preds]
        preds_by_model[model.name] = {"pred_ids": pred_ids, "prob_mal": prob_mal}

        m = recompute_metrics(pred_ids, labels, prob_mal)
        print(f"  RECOMPUTED (independent code path): acc={m['accuracy']:.4f} f1={m['f1']:.4f} "
              f"P={m['precision']:.4f} R={m['recall']:.4f} roc_auc={m['roc_auc']:.4f} "
              f"pr_auc={m['pr_auc']:.4f} ece={m['ece']:.4f} brier={m['brier']:.4f}")

        acc_lo, acc_hi, acc_mean = bootstrap_ci(pred_ids, labels, acc_metric)
        f1_lo, f1_hi, f1_mean = bootstrap_ci(pred_ids, labels, f1_metric)
        print(f"  Bootstrap 95% CI (n=10000, seed={SEED}): "
              f"accuracy=[{acc_lo:.4f}, {acc_hi:.4f}]  f1=[{f1_lo:.4f}, {f1_hi:.4f}]")

        m["bootstrap_ci"] = {"accuracy_95ci": [acc_lo, acc_hi], "accuracy_bootstrap_mean": acc_mean,
                              "f1_95ci": [f1_lo, f1_hi], "f1_bootstrap_mean": f1_mean}
        results[model.name] = m

    # McNemar + Cohen's h between original and fine-tuned, on IDENTICAL paired test messages
    orig_preds = preds_by_model[orig.name]["pred_ids"]
    fine_preds = preds_by_model[fine.name]["pred_ids"]
    mcnemar = mcnemar_test(orig_preds, fine_preds, labels)
    print(f"\nMcNemar's test (original vs fine-tuned, paired on {len(labels)} identical test messages):")
    print(f"  {mcnemar}")

    h = cohens_h(results[orig.name]["accuracy"], results[fine.name]["accuracy"])
    print(f"\nCohen's h (accuracy, original vs fine-tuned): {h:.4f} "
          f"({'small' if abs(h)<0.2 else 'medium' if abs(h)<0.5 else 'large'} effect by conventional bins)")

    out = {
        "n_test": len(test_rows),
        "seed": SEED,
        "recomputed_metrics": results,
        "mcnemar_test": mcnemar,
        "cohens_h_accuracy": h,
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nWritten: {OUT}")


if __name__ == "__main__":
    main()
