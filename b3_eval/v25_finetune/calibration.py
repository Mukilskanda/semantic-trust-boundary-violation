"""
b3_eval/v25_finetune/calibration.py
======================================
Temperature scaling (Guo et al., ICML 2017) fit on the VALIDATION split
only (never test), for both the original and fine-tuned B3 checkpoints.
Post-hoc: rescales logits before softmax, does not change argmax/labels.

Reports ECE (15-bin, equal-width), Brier score, and a reliability curve,
before and after calibration, on both val (fit set) and test (held-out).
"""
from __future__ import annotations

import json
import math

import torch


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor, max_iter=200, lr=0.01):
    """logits: (N, 2) float tensor, labels: (N,) long tensor. Returns scalar T."""
    T = torch.nn.Parameter(torch.ones(1) * 1.5)
    opt = torch.optim.LBFGS([T], lr=lr, max_iter=max_iter)
    nll = torch.nn.CrossEntropyLoss()

    def closure():
        opt.zero_grad()
        loss = nll(logits / T.clamp(min=1e-3), labels)
        loss.backward()
        return loss

    opt.step(closure)
    return float(T.detach().clamp(min=1e-3).item())


def ece_brier(probs_pos, labels, n_bins=15):
    """probs_pos: P(malicious) per sample. labels: 0/1. Returns ECE (over
    max-class confidence) and Brier score (over the positive-class prob)."""
    n = len(labels)
    conf = [max(p, 1 - p) for p in probs_pos]
    pred = [1 if p >= 0.5 else 0 for p in probs_pos]
    correct = [1 if pred[i] == labels[i] else 0 for i in range(n)]

    bins = [[] for _ in range(n_bins)]
    for c, ok in zip(conf, correct):
        idx = min(int(c * n_bins), n_bins - 1)
        bins[idx].append(ok)
    ece = 0.0
    reliability = []
    for i, b in enumerate(bins):
        if not b:
            reliability.append({"bin_lo": i / n_bins, "bin_hi": (i + 1) / n_bins,
                                 "count": 0, "accuracy": None, "avg_confidence": None})
            continue
        acc = sum(b) / len(b)
        lo, hi = i / n_bins, (i + 1) / n_bins
        confs_in_bin = [conf[j] for j in range(n) if min(int(conf[j] * n_bins), n_bins - 1) == i]
        avg_conf = sum(confs_in_bin) / len(confs_in_bin)
        ece += (len(b) / n) * abs(acc - avg_conf)
        reliability.append({"bin_lo": lo, "bin_hi": hi, "count": len(b),
                             "accuracy": acc, "avg_confidence": avg_conf})

    brier = sum((probs_pos[i] - labels[i]) ** 2 for i in range(n)) / n
    return {"ece": ece, "brier": brier, "reliability": reliability}


def calibration_report(model_name, val_logits, val_labels, test_logits, test_labels):
    T = fit_temperature(val_logits, val_labels)

    def probs_pos(logits, T_):
        p = torch.softmax(logits / T_, dim=-1)[:, 1]
        return p.tolist()

    val_labels_l = val_labels.tolist()
    test_labels_l = test_labels.tolist()

    pre_val = ece_brier(probs_pos(val_logits, 1.0), val_labels_l)
    post_val = ece_brier(probs_pos(val_logits, T), val_labels_l)
    pre_test = ece_brier(probs_pos(test_logits, 1.0), test_labels_l)
    post_test = ece_brier(probs_pos(test_logits, T), test_labels_l)

    # argmax invariance check
    pre_pred_test = [1 if p >= 0.5 else 0 for p in probs_pos(test_logits, 1.0)]
    post_pred_test = [1 if p >= 0.5 else 0 for p in probs_pos(test_logits, T)]
    flips = sum(1 for a, b in zip(pre_pred_test, post_pred_test) if a != b)

    return {
        "model": model_name,
        "fitted_temperature": T,
        "val_set_fit_on": {"n": len(val_labels_l), "pre": {"ece": pre_val["ece"], "brier": pre_val["brier"]},
                            "post": {"ece": post_val["ece"], "brier": post_val["brier"]}},
        "test_set_held_out": {"n": len(test_labels_l), "pre": {"ece": pre_test["ece"], "brier": pre_test["brier"]},
                               "post": {"ece": post_test["ece"], "brier": post_test["brier"]},
                               "reliability_post": post_test["reliability"]},
        "argmax_label_flips_on_test": flips,
    }
