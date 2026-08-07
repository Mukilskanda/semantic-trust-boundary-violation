#!/usr/bin/env python3
"""
b3_eval/v25_finetune/analyze_v2_mixed_recalibrated.py
=========================================================
Three-way comparison (a=original+old thresholds, b=finetuned+old thresholds
[reused from prior task], c=finetuned+recalibrated thresholds) for
STBV-Bench v2 (aggregate Decision-Trust metric, positive=CAUTION|REJECT,
ground truth=is_attacker_sender, identical convention to
stbv_bench/analyze_v2_results.py / UPDATED_TABLES.md section 3) and the
mixed-threat case study (semantic-attacker recall, message-level and
sender-level, identical convention to UPDATED_TABLES.md section 2).

NOTE: trust_score in the v2 per-message CSV is the FUSED trust score
(B1+B2+CP+B3), not B3's raw confidence -- ROC/PR-AUC here are therefore
computed on the fused trust_score exactly as before (same field used
throughout the prior task's v2 analysis), so they measure the full
stack's ranking quality, not B3 in isolation. This matches the existing
methodology (UPDATED_TABLES.md section 3 uses the same field) --
disclosed, not changed.
"""
from __future__ import annotations
import csv
import json
import math
import pathlib
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RESULTS = HERE / "results"
SEED = 42


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ece_brier(probs_pos, labels, n_bins=15):
    n = len(labels)
    if n == 0:
        return {"ece": float("nan"), "brier": float("nan")}
    conf = [max(p, 1 - p) for p in probs_pos]
    pred = [1 if p >= 0.5 else 0 for p in probs_pos]
    correct = [1 if pred[i] == labels[i] else 0 for i in range(n)]
    bins = [[] for _ in range(n_bins)]
    for c, ok in zip(conf, correct):
        idx = min(int(c * n_bins), n_bins - 1)
        bins[idx].append(ok)
    ece = 0.0
    for i, b in enumerate(bins):
        if not b:
            continue
        acc = sum(b) / len(b)
        confs_in_bin = [conf[j] for j in range(n) if min(int(conf[j] * n_bins), n_bins - 1) == i]
        avg_conf = sum(confs_in_bin) / len(confs_in_bin)
        ece += (len(b) / n) * abs(acc - avg_conf)
    brier = sum((probs_pos[i] - labels[i]) ** 2 for i in range(n)) / n
    return {"ece": ece, "brier": brier}


def metrics(probs, labels, pred_positive):
    n = len(labels)
    tp = sum(1 for i in range(n) if pred_positive[i] and labels[i])
    fp = sum(1 for i in range(n) if pred_positive[i] and not labels[i])
    fn = sum(1 for i in range(n) if not pred_positive[i] and labels[i])
    tn = sum(1 for i in range(n) if not pred_positive[i] and not labels[i])
    acc = (tp + tn) / n if n else float("nan")
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    pos = [probs[i] for i in range(n) if labels[i]]
    neg = [probs[i] for i in range(n) if not labels[i]]
    if pos and neg:
        order = np.argsort(np.argsort(probs)) + 1
        rank_sum_pos = sum(order[i] for i in range(n) if labels[i])
        auc = (rank_sum_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
        from sklearn.metrics import average_precision_score
        pr_auc = average_precision_score(labels, probs)
    else:
        auc, pr_auc = float("nan"), float("nan")
    cb = ece_brier(probs, labels)
    return {"n": n, "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "roc_auc": float(auc), "pr_auc": float(pr_auc), "ece": cb["ece"], "brier": cb["brier"],
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def bootstrap_ci(probs, labels, pred_positive, n_boot=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(labels)
    probs_a, labels_a, pred_a = np.array(probs), np.array(labels), np.array(pred_positive)
    accs, f1s = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        y_b, p_b = labels_a[idx], pred_a[idx]
        tp = int(((p_b == 1) & (y_b == 1)).sum()); fp = int(((p_b == 1) & (y_b == 0)).sum())
        fn = int(((p_b == 0) & (y_b == 1)).sum()); tn = int(((p_b == 0) & (y_b == 0)).sum())
        acc = (tp + tn) / n
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        accs.append(acc); f1s.append(f1)
    accs.sort(); f1s.sort()
    lo, hi = int(0.025 * n_boot), min(int(0.975 * n_boot), n_boot - 1)
    return {"accuracy_ci95": [accs[lo], accs[hi]], "f1_ci95": [f1s[lo], f1s[hi]]}


def mcnemar(correct_a, correct_b):
    n = len(correct_a)
    b01 = sum(1 for i in range(n) if correct_a[i] == 1 and correct_b[i] == 0)
    b10 = sum(1 for i in range(n) if correct_a[i] == 0 and correct_b[i] == 1)
    if b01 + b10 == 0:
        return {"b01": b01, "b10": b10, "statistic": 0.0, "p_value": 1.0}
    stat = (abs(b01 - b10) - 1) ** 2 / (b01 + b10)
    p = math.erfc(math.sqrt(stat / 2))
    return {"b01": b01, "b10": b10, "statistic": stat, "p_value": p}


def analyze_v2():
    a = read_csv(ROOT / "results" / "stbv_bench_v2" / "stbv_bench_v2_per_message.csv")
    b = read_csv(ROOT / "results" / "stbv_bench_v2_finetuned" / "stbv_bench_v2_per_message.csv")
    c = read_csv(ROOT / "results" / "stbv_bench_v2_finetuned_recalibrated" / "stbv_bench_v2_per_message.csv")

    def prep(rows):
        labels = [1 if r["is_attacker_sender"] == "True" else 0 for r in rows]
        pred = [1 if r["decision"] in ("CAUTION", "REJECT") else 0 for r in rows]
        probs = [float(r["trust_score"]) for r in rows]
        # trust_score is a TRUST score (higher = more trusted), so the
        # "maliciousness" ranking score for AUC purposes is 1-trust_score.
        probs_mal = [1 - p for p in probs]
        return labels, pred, probs_mal

    ya, pa, sa = prep(a)
    yb, pb, sb = prep(b)
    yc, pc, sc = prep(c)

    m_a = metrics(sa, ya, pa)
    m_b = metrics(sb, yb, pb)
    m_c = metrics(sc, yc, pc)
    ci_c = bootstrap_ci(sc, yc, pc)

    correct_a = [1 if pa[i] == ya[i] else 0 for i in range(len(ya))]
    correct_b = [1 if pb[i] == yb[i] else 0 for i in range(len(yb))]
    correct_c = [1 if pc[i] == yc[i] else 0 for i in range(len(yc))]
    n_common_ab = min(len(correct_a), len(correct_b))
    n_common_bc = min(len(correct_b), len(correct_c))

    out = {
        "arm_a_original_old_thresholds": m_a,
        "arm_b_finetuned_old_thresholds": m_b,
        "arm_c_finetuned_recalibrated": m_c,
        "arm_c_bootstrap_ci": ci_c,
        "mcnemar_a_vs_b": mcnemar(correct_a[:n_common_ab], correct_b[:n_common_ab]),
        "mcnemar_b_vs_c": mcnemar(correct_b[:n_common_bc], correct_c[:n_common_bc]),
        "note": "positive=CAUTION|REJECT, ground truth=is_attacker_sender, over ALL rows "
                 "(matches UPDATED_TABLES.md section 3 / stbv_bench/analyze_v2_results.py convention); "
                 "AUCs computed on 1-trust_score (fused stack score, not B3 alone).",
    }
    (RESULTS / "v2_recalibration_analysis.json").write_text(json.dumps(out, indent=2))
    print("=== STBV-Bench v2 ===")
    print(json.dumps(out, indent=2))
    return out


def analyze_mixed_threat():
    a = read_csv(ROOT / "results" / "mixed_threat" / "mixed_threat_per_message.csv")
    b = read_csv(ROOT / "results" / "mixed_threat_finetuned" / "mixed_threat_per_message.csv")
    c = read_csv(ROOT / "results" / "mixed_threat_finetuned_recalibrated" / "mixed_threat_per_message.csv")

    def semantic_recall_msg(rows):
        sem = [r for r in rows if r["is_semantic_attacker"] == "True"]
        if not sem:
            return float("nan"), 0, 0
        flagged = sum(1 for r in sem if r["decision"] in ("CAUTION", "REJECT"))
        return flagged / len(sem), flagged, len(sem)

    def semantic_recall_sender(rows):
        by_sender = {}
        for r in rows:
            by_sender.setdefault((r["window_id"], r["sender"]), []).append(r)
        attacker_senders = {k: v for k, v in by_sender.items()
                             if any(r["is_semantic_attacker"] == "True" for r in v)}
        if not attacker_senders:
            return float("nan"), 0, 0
        detected = sum(1 for k, v in attacker_senders.items()
                        if any(r["decision"] in ("CAUTION", "REJECT") for r in v))
        return detected / len(attacker_senders), detected, len(attacker_senders)

    def kinematic_recall_msg(rows):
        kin = [r for r in rows if r["is_kinematic_attacker"] == "True"]
        if not kin:
            return float("nan"), 0, 0
        flagged = sum(1 for r in kin if r["decision"] in ("CAUTION", "REJECT"))
        return flagged / len(kin), flagged, len(kin)

    out = {}
    for name, rows in [("arm_a_original_old_thresholds", a),
                        ("arm_b_finetuned_old_thresholds", b),
                        ("arm_c_finetuned_recalibrated", c)]:
        rec_msg, f_msg, n_msg = semantic_recall_msg(rows)
        rec_send, f_send, n_send = semantic_recall_sender(rows)
        rec_kin, f_kin, n_kin = kinematic_recall_msg(rows)
        out[name] = {
            "n_rows": len(rows),
            "semantic_recall_message": rec_msg, "semantic_flagged_message": f_msg, "semantic_n_message": n_msg,
            "semantic_recall_sender": rec_send, "semantic_flagged_sender": f_send, "semantic_n_sender": n_send,
            "kinematic_recall_message": rec_kin, "kinematic_flagged_message": f_kin, "kinematic_n_message": n_kin,
        }

    # McNemar on message-level semantic-attacker detection (paired samples,
    # only over rows common to both compared arms by (window_id, sender)
    # since window construction is byte-identical/deterministic per seed).
    def sem_pred_map(rows):
        return {(r["window_id"], r["sender"]): (r["decision"] in ("CAUTION", "REJECT"),
                                                   r["is_semantic_attacker"] == "True")
                for r in rows if r["is_semantic_attacker"] == "True"}

    pa_map, pb_map, pc_map = sem_pred_map(a), sem_pred_map(b), sem_pred_map(c)
    keys_ab = sorted(set(pa_map) & set(pb_map))
    keys_bc = sorted(set(pb_map) & set(pc_map))
    correct_a_ab = [1 if pa_map[k][0] else 0 for k in keys_ab]
    correct_b_ab = [1 if pb_map[k][0] else 0 for k in keys_ab]
    correct_b_bc = [1 if pb_map[k][0] else 0 for k in keys_bc]
    correct_c_bc = [1 if pc_map[k][0] else 0 for k in keys_bc]
    out["mcnemar_a_vs_b_semantic_detection"] = mcnemar(correct_a_ab, correct_b_ab)
    out["mcnemar_b_vs_c_semantic_detection"] = mcnemar(correct_b_bc, correct_c_bc)
    out["note"] = ("semantic-attacker recall = fraction of is_semantic_attacker=True rows/senders "
                    "flagged CAUTION|REJECT (matches UPDATED_TABLES.md section 2 convention).")

    (RESULTS / "mixed_threat_recalibration_analysis.json").write_text(json.dumps(out, indent=2))
    print("=== Mixed-threat case study ===")
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    analyze_v2()
    analyze_mixed_threat()
