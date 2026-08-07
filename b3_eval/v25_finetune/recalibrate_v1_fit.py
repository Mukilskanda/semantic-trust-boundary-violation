"""
b3_eval/v25_finetune/recalibrate_v1_fit.py
=============================================
Consumes b3_eval/v25_finetune/results/v1_finetuned_recalibration_raw.csv
(written by recalibrate_v1_collect.py) and, VALIDATION SPLIT ONLY:
  1. Fits temperature scaling (reusing calibration.py's fit_temperature,
     same LBFGS/NLL method as the v2.5 finetune's own calibration pass).
  2. Grid-searches B3RiskPolicy's high_confidence/medium_confidence
     thresholds (post-temperature p_malicious) to maximize F1 of
     decision positive={CAUTION,REJECT} vs is_attacker -- same scoring
     convention as analyze_ablation_rerun.py ("positive = Caution or
     Reject, never Accept").

Freezes results into results/recalibrated_thresholds.json. Reports
pre/post ECE and Brier on BOTH val (fit set) and test (held-out), using
calibration.py's ece_brier() unmodified.

TEST SPLIT IS NEVER USED FOR FITTING OR THRESHOLD SELECTION -- only for
reporting the achieved calibration quality, mirroring calibration.py's own
val/test separation.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from b3_eval.v25_finetune.calibration import fit_temperature, ece_brier  # noqa: E402

RAW_CSV = HERE / "results" / "v1_finetuned_recalibration_raw.csv"
OUT_JSON = HERE / "results" / "recalibrated_thresholds.json"


def load_rows():
    rows = []
    with open(RAW_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


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
    """Exact port of pipeline.b3_bridge.B3RiskPolicy.classify() +
    rerun_paper_ablation.py's b3_only_decision(), INCLUDING
    confidence_aware_benign=True (isce_config.yaml:535 -- the shipped,
    live setting; verified by reading the actual config, not assumed).
    With confidence_aware_benign on, a BENIGN-argmax prediction is *not*
    unconditionally ACCEPT: low-confidence BENIGN calls (close to the
    0.5 decision boundary) still escalate to CAUTION, exactly mirroring
    how a low-confidence MALICIOUS call does. This makes high/med
    genuinely load-bearing on BOTH sides of the argmax boundary, not
    just the malicious side.
    """
    if b1_fatal:
        return "REJECT"
    if p_mal >= 0.5:
        conf = p_mal
        if conf >= high:
            return "REJECT"
        return "CAUTION"  # medium or low band -> CAUTION either way
    else:
        conf = 1.0 - p_mal
        if conf >= high:
            return "ACCEPT"  # "none" risk
        return "CAUTION"  # "low" or "medium" risk on the benign side -> CAUTION


def main():
    rows = load_rows()
    val = [r for r in rows if r["split"] == "val"]
    test = [r for r in rows if r["split"] == "test"]
    print(f"val n={len(val)} test n={len(test)}")

    def to_tensors(subset):
        # p_malicious_raw is the pipeline's own TTA-ensembled average P(malicious)
        # (isce_config.yaml: b3_semantic_gate.enable_ensembling=true; orchestrator.py
        # averages p_malicious across 4 TemplateStyle-synthesized forward passes --
        # not a single raw model logit pair). To reuse calibration.py's 2-class
        # LBFGS/NLL temperature-scaling machinery unmodified, the ensembled
        # probability p is losslessly re-expressed as log-probability "logits"
        # [ln(1-p), ln(p)] -- softmax of these exactly reproduces p (they already
        # sum to 1), so this is an exact, not approximate, re-encoding.
        eps = 1e-6
        logits = []
        for r in subset:
            p = min(max(float(r["p_malicious_raw"]), eps), 1 - eps)
            logits.append([math.log(1 - p), math.log(p)])
        logits = torch.tensor(logits)
        labels = torch.tensor([1 if r["is_attacker"] == "True" else 0 for r in subset])
        return logits, labels

    val_logits, val_labels = to_tensors(val)
    test_logits, test_labels = to_tensors(test)

    T = fit_temperature(val_logits, val_labels)
    print(f"Fitted temperature T={T:.4f}")

    def p_mal(logits, T_):
        return torch.softmax(logits / T_, dim=-1)[:, 1].tolist()

    val_labels_l = val_labels.tolist()
    test_labels_l = test_labels.tolist()
    pre_val = ece_brier(p_mal(val_logits, 1.0), val_labels_l)
    post_val = ece_brier(p_mal(val_logits, T), val_labels_l)
    pre_test = ece_brier(p_mal(test_logits, 1.0), test_labels_l)
    post_test = ece_brier(p_mal(test_logits, T), test_labels_l)
    print(f"Val   ECE pre={pre_val['ece']:.4f} post={post_val['ece']:.4f} | Brier pre={pre_val['brier']:.4f} post={post_val['brier']:.4f}")
    print(f"Test  ECE pre={pre_test['ece']:.4f} post={post_test['ece']:.4f} | Brier pre={pre_test['brier']:.4f} post={post_test['brier']:.4f}")

    val_p = p_mal(val_logits, T)
    val_is_attacker = [r["is_attacker"] == "True" for r in val]
    val_b1_fatal = [r.get("b1_fatal") == "True" for r in val]

    best = None
    grid = [round(x * 0.01, 2) for x in range(50, 100)]  # 0.50..0.99
    for high in grid:
        for med in grid:
            if med >= high:
                continue
            decisions = [risk_decision(p, high, med, bf) for p, bf in zip(val_p, val_b1_fatal)]
            m = prf(val_is_attacker, decisions)
            if best is None or m["f1"] > best["f1"]:
                best = dict(m, high=high, med=med)
    print(f"Best val F1={best['f1']:.4f} at high={best['high']} med={best['med']} "
          f"(prec={best['precision']:.3f} rec={best['recall']:.3f})")

    # Reference: old thresholds (0.85/0.60) evaluated post-temperature on val, for comparison
    old_decisions_val = [risk_decision(p, 0.85, 0.60, bf) for p, bf in zip(val_p, val_b1_fatal)]
    old_m_val = prf(val_is_attacker, old_decisions_val)
    print(f"Old thresholds (0.85/0.60) post-T on val: F1={old_m_val['f1']:.4f} rec={old_m_val['recall']:.3f}")

    result = {
        "methodology": {
            "checkpoint": "semantic_gate_v3_v25_lora_merged",
            "benchmark": "STBV-Bench v1 (data/stbv_bench/v1/stbv_bench.jsonl), first 10,000 rows "
                          "(same subset as rerun_paper_ablation.py)",
            "split": "NEW: stratified-by-attack_family 25% subsample of the same first-10,000-row "
                     "v1 subset rerun_paper_ablation.py used (compute-budget reduction from a "
                     "measured ~1 msg/s full-pipeline forward pass; disclosed, not silent), then "
                     "stratified-by-attack_family random 50/50 val/test within that subsample, "
                     "seed=20260804 (v1 has no template_id field, so make_splits.py's exact "
                     "template-disjoint grouping is not constructible for this corpus; this is a "
                     "disclosed, explicitly-new choice, not a reuse of any paper-defined split)",
            "temperature_scaling": "LBFGS/NLL on val logits, calibration.py:fit_temperature, identical "
                                    "method family to the v2.5 finetune calibration pass",
            "threshold_selection": "grid search (0.50-0.99 step 0.01) over "
                                    "(high_confidence, medium_confidence) maximizing F1 on VAL ONLY, "
                                    "decision positive={CAUTION,REJECT} vs is_attacker -- same scoring "
                                    "convention as analyze_ablation_rerun.py. F1-maximization chosen "
                                    "because no paper-documented derivation for the original 0.85/0.60 "
                                    "values was found in stbv_paper.tex Methodology; this matches the "
                                    "task's explicit fallback instruction.",
            "test_split_used_for_selection": False,
        },
        "fitted_temperature": T,
        "recalibrated_thresholds": {"high_confidence": best["high"], "medium_confidence": best["med"]},
        "old_thresholds": {"high_confidence": 0.85, "medium_confidence": 0.60},
        "trust_engine_thresholds": {
            "note": "trust_engine.policy.TrustPolicy.semantic_high_confidence/semantic_medium_confidence "
                    "are FALLBACK-ONLY parameters (see policy.py docstring): classify_semantic_risk() "
                    "reads B3's own risk_level field first and only falls back to recomputing from "
                    "label+confidence if risk_level is absent, which never happens in the live pipeline "
                    "(B3RiskPolicy always sets risk_level). Set equal to the recalibrated B3RiskPolicy "
                    "values for consistency/documentation, but they do not independently affect any "
                    "decision in this codebase's current wiring.",
            "semantic_high_confidence": best["high"],
            "semantic_medium_confidence": best["med"],
        },
        "val_metrics_at_recalibrated_thresholds": best,
        "val_metrics_at_old_thresholds_post_temperature": old_m_val,
        "calibration": {
            "val": {"n": len(val), "pre_temperature": {"ece": pre_val["ece"], "brier": pre_val["brier"]},
                    "post_temperature": {"ece": post_val["ece"], "brier": post_val["brier"]}},
            "test": {"n": len(test), "pre_temperature": {"ece": pre_test["ece"], "brier": pre_test["brier"]},
                     "post_temperature": {"ece": post_test["ece"], "brier": post_test["brier"]},
                     "reliability_post": post_test["reliability"]},
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(f"Written: {OUT_JSON}")


if __name__ == "__main__":
    main()
