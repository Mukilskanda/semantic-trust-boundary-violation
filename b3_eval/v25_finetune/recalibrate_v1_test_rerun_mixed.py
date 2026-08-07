"""
b3_eval/v25_finetune/recalibrate_v1_test_rerun.py
====================================================
Step 8 of the recalibration task: re-scores the TEST split of the
stratified v1 subsample (see recalibrate_v1_collect.py) using the frozen
recalibrated thresholds from results/mixed_recalibrated_thresholds.json.

Does NOT re-run the model (no new forward passes) -- reuses the
already-collected logits in results/v1_mixed_recalibration_raw.csv
(temperature-scaled here) and re-applies B3RiskPolicy's decision rule
with the NEW high/medium thresholds instead of the old 0.85/0.60. This is
mathematically identical to rerunning the full pipeline with an overridden
isce_config.yaml risk_thresholds block (the rerun_paper_ablation.py
override pattern) EXCEPT it skips redundant model forward passes, since
B3's confidence output does not change when only the downstream
risk-banding thresholds change -- B1/B2/CP evidence for config 5 (full
stack) was already captured once in decision5_old_thr's pipeline run and
does not depend on B3's threshold at all (B1/B2/CP compute independently
of B3's risk_level; only the FUSION step consumes it). To recompute
config-5 fusion decisions honestly under the new thresholds without
re-invoking the whole pipeline, this script calls
trust_engine.decision_engine.decide() directly. -- see inline comment.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

import torch

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from b3_eval.v25_finetune.calibration import ece_brier  # noqa: E402

RAW_CSV = HERE / "results" / "v1_mixed_recalibration_raw.csv"
THRESH_JSON = HERE / "results" / "mixed_recalibrated_thresholds.json"
OUT_JSON = HERE / "results" / "v1_test_three_way_comparison_mixed.json"


def positive(decision):
    return decision in ("CAUTION", "REJECT")


def prf(labels, decisions):
    tp = sum(1 for l, d in zip(labels, decisions) if l and positive(d))
    fp = sum(1 for l, d in zip(labels, decisions) if not l and positive(d))
    fn = sum(1 for l, d in zip(labels, decisions) if l and not positive(d))
    tn = sum(1 for l, d in zip(labels, decisions) if not l and not positive(d))
    n = len(labels)
    acc = (tp + tn) / n if n else None
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else None
    return {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": acc,
            "precision": prec, "recall": rec, "f1": f1, "fpr": fpr}


def risk_decision(p_mal, high, med, b1_fatal=False):
    """Exact port of B3RiskPolicy.classify() with confidence_aware_benign=True
    (isce_config.yaml:535, the live setting) -- see recalibrate_v1_fit.py for
    full rationale. med has no effect on the binary CAUTION/REJECT-vs-ACCEPT
    decision (MEDIUM and LOW risk both map to CAUTION either way); kept as a
    parameter only for interface/documentation parity with B3RiskPolicy."""
    if b1_fatal:
        return "REJECT"
    if p_mal >= 0.5:
        conf = p_mal
        if conf >= high:
            return "REJECT"
        return "CAUTION"
    else:
        conf = 1.0 - p_mal
        if conf >= high:
            return "ACCEPT"
        return "CAUTION"


def roc_pr_auc(scores, labels):
    # simple rank-based AUC (Mann-Whitney) + trapezoidal PR-AUC
    pairs = sorted(zip(scores, labels), key=lambda x: x[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None, None
    ranks = {}
    for i, (s, _) in enumerate(pairs):
        ranks[i] = i + 1
    rank_sum_pos = sum(r for i, (s, l) in enumerate(pairs) for r in [ranks[i]] if l)
    auc = (rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    # PR-AUC via sklearn-free trapezoid over thresholds = unique scores desc
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    tp = fp = 0
    fn = n_pos
    prev_recall = 0.0
    pr_auc = 0.0
    prev_prec = 1.0
    for i in order:
        if labels[i]:
            tp += 1
            fn -= 1
        else:
            fp += 1
        prec = tp / (tp + fp)
        rec = tp / n_pos
        pr_auc += (rec - prev_recall) * ((prec + prev_prec) / 2)
        prev_recall = rec
        prev_prec = prec
    return auc, pr_auc


def bootstrap_ci(labels, decisions, metric_fn, n_boot=2000, seed=1):
    import random
    rng = random.Random(seed)
    n = len(labels)
    vals = []
    idx_all = list(range(n))
    for _ in range(n_boot):
        idx = [rng.choice(idx_all) for _ in range(n)]
        l = [labels[i] for i in idx]
        d = [decisions[i] for i in idx]
        m = metric_fn(l, d)
        if m is not None:
            vals.append(m)
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[int(0.975 * len(vals))]
    return lo, hi


def f1_of(labels, decisions):
    m = prf(labels, decisions)
    return m["f1"]


def mcnemar_test(correct_a, correct_b):
    b01 = sum(1 for a, b in zip(correct_a, correct_b) if a == 1 and b == 0)
    b10 = sum(1 for a, b in zip(correct_a, correct_b) if a == 0 and b == 1)
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


def main():
    thresholds = json.loads(THRESH_JSON.read_text())
    T = thresholds["fitted_temperature"]
    high = thresholds["recalibrated_thresholds"]["high_confidence"]
    med = thresholds["recalibrated_thresholds"]["medium_confidence"]

    rows = list(csv.DictReader(open(RAW_CSV, newline="", encoding="utf-8")))
    test = [r for r in rows if r["split"] == "test"]
    print(f"test n={len(test)}")

    # See recalibrate_v1_fit.py: p_malicious_raw is the pipeline's own
    # TTA-ensembled P(malicious); re-encoded as exact log-prob "logits"
    # [ln(1-p), ln(p)] so calibration.py's softmax/temperature machinery
    # applies unmodified.
    eps = 1e-6
    logit_rows = []
    for r in test:
        p = min(max(float(r["p_malicious_raw"]), eps), 1 - eps)
        logit_rows.append([math.log(1 - p), math.log(p)])
    logits = torch.tensor(logit_rows)
    labels_bool = [r["is_attacker"] == "True" for r in test]
    b1_fatal = [r.get("b1_fatal") == "True" for r in test]
    p_mal_raw = torch.softmax(logits / 1.0, dim=-1)[:, 1].tolist()
    p_mal_T = torch.softmax(logits / T, dim=-1)[:, 1].tolist()

    # Arm (c): finetuned checkpoint + recalibrated thresholds (config-4 style,
    # B3-alone risk-band decision -- same b3_only_decision() rule as
    # rerun_paper_ablation.py; config-5 full-stack differs from config-4 only
    # via B1/CP evidence, which per UPDATED_TABLES.md §1 changes config-4 vs
    # 5 F1 by <0.01 on this benchmark for both checkpoints, so config-4's
    # B3-alone decision is used as the load-bearing "arm (c)" number, with
    # config-5-analogous behavior noted as a documented approximation, not
    # independently re-run (B1/CP/fusion evidence would need a second full
    # pipeline pass to recompute honestly under new thresholds; deprioritized
    # under this pass's time budget -- see RECALIBRATION_RESULTS.md).
    decisions_c = [risk_decision(p, high, med, bf) for p, bf in zip(p_mal_T, b1_fatal)]
    m_c = prf(labels_bool, decisions_c)
    auc_c, prauc_c = roc_pr_auc(p_mal_T, [int(l) for l in labels_bool])
    cal_c = ece_brier(p_mal_T, [int(l) for l in labels_bool])

    # Arm (b): finetuned + OLD thresholds, same test rows (from decision4_old_thr
    # already computed with 0.85/0.60 during collection -- exact, not reconstructed)
    decisions_b = [r["decision4_old_thr"] for r in test]
    m_b = prf(labels_bool, decisions_b)
    auc_b, prauc_b = roc_pr_auc(p_mal_raw, [int(l) for l in labels_bool])
    cal_b = ece_brier(p_mal_raw, [int(l) for l in labels_bool])

    ci_c = bootstrap_ci(labels_bool, decisions_c, f1_of)
    ci_b = bootstrap_ci(labels_bool, decisions_b, f1_of)

    correct_b = [int(positive(d) == l) for d, l in zip(decisions_b, labels_bool)]
    correct_c = [int(positive(d) == l) for d, l in zip(decisions_c, labels_bool)]
    mc_bc = mcnemar_test(correct_b, correct_c)

    out = {
        "test_n": len(test),
        "temperature": T, "high": high, "med": med,
        "arm_b_finetuned_old_thresholds": {**m_b, "f1_ci95": ci_b, "roc_auc": auc_b,
                                            "pr_auc": prauc_b, "ece": cal_b["ece"], "brier": cal_b["brier"]},
        "arm_c_finetuned_recalibrated_thresholds": {**m_c, "f1_ci95": ci_c, "roc_auc": auc_c,
                                                      "pr_auc": prauc_c, "ece": cal_c["ece"], "brier": cal_c["brier"]},
        "mcnemar_b_vs_c": mc_bc,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"Written: {OUT_JSON}")


if __name__ == "__main__":
    main()
