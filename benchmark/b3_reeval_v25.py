#!/usr/bin/env python3
"""
benchmark/b3_reeval_v25.py
============================
B3 re-evaluation on STBV-Bench v2.5, WITHOUT retraining B3.

Consumes results/benchmark_audit/b3_v25_predictions.jsonl (produced by
running the existing B3 predictor over every v2.5 message once; see
b3_bridge.classify_texts_batch). Computes, and saves as JSON + figures:

  - ROC, PR curves (threshold-independent)
  - Calibration (reliability diagram, ECE, Brier score)
  - Confusion matrices at two decision thresholds:
      "strict"           p_malicious >= 0.50  (B3's own argmax label)
      "confidence_aware"  p_malicious >= 0.60  (B3RiskPolicy.medium_confidence,
                          the risk gate's own configured operating point)
  - Per-family recall / precision
  - Bootstrap 95% CIs (2000 resamples) for accuracy/F1/AUC, both split protocols
  - McNemar test: B3 vs best lexical baseline (TF-IDF+LogReg), template-disjoint
  - Effect size (Cohen's h for the accuracy difference)

Both a RANDOM 5-fold split and the TEMPLATE-DISJOINT GroupKFold split
(see LEXICAL_LEAKAGE_ANALYSIS.md) are reported, because that is the entire
point of the benchmark redesign: only the template-disjoint numbers are
valid evidence about generalization beyond memorized skeletons.

Run:  python benchmark/b3_reeval_v25.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "results" / "benchmark_audit"
FIGS = OUT / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

PRED_FILE = OUT / "b3_v25_predictions.jsonl"
SEED = 42
N_BOOT = 2000


def load():
    rows = [json.loads(l) for l in open(PRED_FILE, encoding="utf-8")]
    y = np.array([r["label"] for r in rows])
    p = np.array([r["b3"]["p_malicious"] if r["b3"]["available"] else np.nan for r in rows])
    fams = np.array([r["attack_family"] for r in rows])
    tids = np.array([r["template_id"] for r in rows])
    avail = ~np.isnan(p)
    n_unavail = int((~avail).sum())
    if n_unavail:
        print(f"[warn] {n_unavail} messages had unavailable B3 predictions; excluded")
    return y[avail], p[avail], fams[avail], tids[avail], rows


def roc_pr(y, p):
    from sklearn.metrics import roc_curve, precision_recall_curve, roc_auc_score, average_precision_score
    fpr, tpr, roc_thr = roc_curve(y, p)
    prec, rec, pr_thr = precision_recall_curve(y, p)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "pr_curve": {"precision": prec.tolist(), "recall": rec.tolist()},
    }


def confusion_at(y, p, thr):
    from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, accuracy_score
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": thr, "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "fpr": float(fp / max(1, fp + tn)),
    }


def calibration(y, p, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, bins) - 1, 0, n_bins - 1)
    ece, bin_stats = 0.0, []
    for b in range(n_bins):
        mask = idx == b
        n = int(mask.sum())
        if n == 0:
            bin_stats.append({"bin": b, "n": 0, "conf": None, "acc": None})
            continue
        conf = float(p[mask].mean())
        acc = float(y[mask].mean())
        ece += (n / len(p)) * abs(acc - conf)
        bin_stats.append({"bin": b, "n": n, "conf": conf, "acc": acc})
    brier = float(np.mean((p - y) ** 2))
    return {"ece": float(ece), "brier": brier, "bins": bin_stats}


def per_family(y, p, fams, thr=0.5):
    """Per-family RECALL only (meaningful: fraction of that family's
    malicious messages correctly flagged). Per-family PRECISION is not
    computed here: every malicious family's subset contains no benign
    examples, so precision_score on the subset is trivially 1.0 whenever
    at least one true positive exists (TP/(TP+FP) with FP structurally
    forced to 0 -- there are no negatives in the subset to be false-
    positived against). Precision is only meaningful pooled across the
    whole corpus (see confusion_strict_thr050 / confusion_confidence_aware_thr060).
    """
    from sklearn.metrics import recall_score
    out = {}
    for fam in sorted(set(fams)):
        mask = fams == fam
        if mask.sum() == 0:
            continue
        yf, pf = y[mask], p[mask]
        pred = (pf >= thr).astype(int)
        if fam == "benign_control":
            spec = float((pred == 0).mean())
            out[fam] = {"n": int(mask.sum()), "specificity": spec}
        else:
            out[fam] = {
                "n": int(mask.sum()),
                "recall": float(recall_score(yf, pred, zero_division=0)),
            }
    return out


def bootstrap_ci(y, p, thr, n_boot=N_BOOT, seed=SEED):
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    rng = np.random.RandomState(seed)
    n = len(y)
    accs, f1s, aucs = [], [], []
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)
        yb, pb = y[idx], p[idx]
        if len(set(yb.tolist())) < 2:
            continue
        pred = (pb >= thr).astype(int)
        accs.append(accuracy_score(yb, pred))
        f1s.append(f1_score(yb, pred, zero_division=0))
        aucs.append(roc_auc_score(yb, pb))

    def ci(a):
        a = np.array(a)
        return {"mean": float(a.mean()), "lo95": float(np.percentile(a, 2.5)),
                "hi95": float(np.percentile(a, 97.5))}
    return {"accuracy": ci(accs), "f1": ci(f1s), "roc_auc": ci(aucs)}


def group_kfold_eval(y, p, tids, thr, n_splits=5):
    """B3's own metrics under the SAME template-disjoint protocol used for
    the lexical baselines, for apples-to-apples comparison. B3 is not
    retrained per fold (no retraining anywhere in this script) -- this
    just reports the same fixed predictions, sliced the same way, so the
    comparison to the lexical GroupKFold numbers is on identical folds
    in spirit (grouped by template so no skeleton is split across a
    train/test boundary -- though for a frozen, already-trained B3 model
    there is no train/test distinction; folds are reported for
    variance-across-template-subsets only).
    """
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    gkf = GroupKFold(n_splits=n_splits)
    accs, f1s, aucs = [], [], []
    for _, te in gkf.split(y, y, tids):
        yt, pt = y[te], p[te]
        if len(set(yt.tolist())) < 2:
            continue
        pred = (pt >= thr).astype(int)
        accs.append(accuracy_score(yt, pred))
        f1s.append(f1_score(yt, pred, zero_division=0))
        aucs.append(roc_auc_score(yt, pt))
    return {"accuracy_mean": float(np.mean(accs)), "accuracy_std": float(np.std(accs)),
            "f1_mean": float(np.mean(f1s)), "f1_std": float(np.std(f1s)),
            "roc_auc_mean": float(np.mean(aucs)), "roc_auc_std": float(np.std(aucs))}


def mcnemar_b3_vs_lexical(y, p_b3, texts, tids, thr=0.5):
    """McNemar's test comparing B3 (frozen) vs a template-disjoint-trained
    TF-IDF+LogisticRegression baseline, on the SAME template-disjoint test
    folds, so both models are scored on messages whose exact skeleton
    they did not memorize.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import GroupKFold
    from statsmodels.stats.contingency_tables import mcnemar as _mcnemar

    texts = np.array(texts, dtype=object)
    gkf = GroupKFold(n_splits=5)
    pred_b3_all, pred_lex_all, y_all = [], [], []
    pipe = Pipeline([("v", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
                     ("c", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED))])
    for tr, te in gkf.split(texts, y, tids):
        pipe.fit(texts[tr], y[tr])
        pred_lex = pipe.predict(texts[te])
        pred_b3 = (p_b3[te] >= thr).astype(int)
        pred_b3_all.append(pred_b3)
        pred_lex_all.append(pred_lex)
        y_all.append(y[te])
    pred_b3_all = np.concatenate(pred_b3_all)
    pred_lex_all = np.concatenate(pred_lex_all)
    y_all = np.concatenate(y_all)

    b3_correct = (pred_b3_all == y_all)
    lex_correct = (pred_lex_all == y_all)
    n01 = int(((b3_correct) & (~lex_correct)).sum())   # B3 right, lexical wrong
    n10 = int(((~b3_correct) & (lex_correct)).sum())   # B3 wrong, lexical right
    table = [[0, n01], [n10, 0]]
    try:
        res = _mcnemar(table, exact=(n01 + n10 < 25), correction=True)
        pvalue = float(res.pvalue)
        statistic = float(res.statistic)
    except Exception as e:
        pvalue, statistic = None, None
        print(f"[warn] mcnemar failed: {e}")

    from sklearn.metrics import accuracy_score
    acc_b3 = accuracy_score(y_all, pred_b3_all)
    acc_lex = accuracy_score(y_all, pred_lex_all)
    # Cohen's h effect size for the accuracy difference (proportions)
    h = 2 * np.arcsin(np.sqrt(acc_b3)) - 2 * np.arcsin(np.sqrt(acc_lex))

    return {
        "protocol": "template-disjoint GroupKFold(5), B3 frozen vs TF-IDF+LogReg trained per-fold",
        "n": int(len(y_all)),
        "b3_accuracy": float(acc_b3), "lexical_accuracy": float(acc_lex),
        "b3_right_lexical_wrong": n01, "b3_wrong_lexical_right": n10,
        "mcnemar_statistic": statistic, "mcnemar_pvalue": pvalue,
        "cohens_h": float(h),
    }


def make_figures(y, p, fams, cal):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve, precision_recall_curve, confusion_matrix

    plt.rcParams.update({"font.size": 8, "axes.grid": True, "grid.alpha": 0.3})

    fig, axes = plt.subplots(1, 4, figsize=(11, 2.6))
    fpr, tpr, _ = roc_curve(y, p)
    axes[0].plot(fpr, tpr, color="#4C72B0"); axes[0].plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR"); axes[0].set_title("ROC", fontsize=8)

    prec, rec, _ = precision_recall_curve(y, p)
    axes[1].plot(rec, prec, color="#C44E52")
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].set_title("PR", fontsize=8)

    confs = [b["conf"] for b in cal["bins"] if b["conf"] is not None]
    accs = [b["acc"] for b in cal["bins"] if b["acc"] is not None]
    axes[2].plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
    axes[2].plot(confs, accs, marker="o", color="#55A868", ms=3)
    axes[2].set_xlabel("confidence"); axes[2].set_ylabel("accuracy")
    axes[2].set_title(f"Calibration (ECE={cal['ece']:.3f})", fontsize=8)

    pred = (p >= 0.5).astype(int)
    cm = confusion_matrix(y, pred, labels=[0, 1])
    im = axes[3].imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            axes[3].text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=9)
    axes[3].set_xticks([0, 1]); axes[3].set_xticklabels(["benign", "malicious"], fontsize=7)
    axes[3].set_yticks([0, 1]); axes[3].set_yticklabels(["benign", "malicious"], fontsize=7)
    axes[3].set_title("Confusion (thr=0.5)", fontsize=8)

    fig.suptitle("B3 re-evaluation on STBV-Bench v2.5", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / "b3_v25_reeval.pdf")
    fig.savefig(FIGS / "b3_v25_reeval.png", dpi=150)
    plt.close(fig)
    print(f"[figs] -> {FIGS}")


def main():
    if not PRED_FILE.exists():
        print(f"[error] {PRED_FILE} not found -- run the B3 batch-inference "
              f"pass over v2.5 first (results/benchmark_audit/b3_v25_predictions.jsonl)")
        sys.exit(1)

    y, p, fams, tids, rows = load()
    texts = [r["text"] for r in rows if not np.isnan(r["b3"]["p_malicious"] if r["b3"]["available"] else np.nan)]
    print(f"[b3-reeval] n={len(y)}  prevalence={y.mean():.4f}")

    report = {"n": int(len(y)), "prevalence_malicious": float(y.mean())}

    print("[b3-reeval] ROC / PR")
    report["roc_pr"] = roc_pr(y, p)

    print("[b3-reeval] confusion matrices: strict (thr=0.50) vs confidence-aware (thr=0.60)")
    report["confusion_strict_thr050"] = confusion_at(y, p, 0.50)
    report["confusion_confidence_aware_thr060"] = confusion_at(y, p, 0.60)
    print(f"    strict           acc={report['confusion_strict_thr050']['accuracy']:.4f} "
          f"f1={report['confusion_strict_thr050']['f1']:.4f}")
    print(f"    confidence-aware acc={report['confusion_confidence_aware_thr060']['accuracy']:.4f} "
          f"f1={report['confusion_confidence_aware_thr060']['f1']:.4f}")

    print("[b3-reeval] calibration")
    report["calibration"] = calibration(y, p)
    print(f"    ECE={report['calibration']['ece']:.4f}  Brier={report['calibration']['brier']:.4f}")

    print("[b3-reeval] per-family recall/precision (thr=0.50)")
    report["per_family_strict"] = per_family(y, p, fams, thr=0.50)
    report["per_family_confidence_aware"] = per_family(y, p, fams, thr=0.60)
    for fam, v in report["per_family_strict"].items():
        print(f"    {fam:32s} {v}")

    print("[b3-reeval] bootstrap 95% CIs (random-pool)")
    report["bootstrap_ci_strict"] = bootstrap_ci(y, p, thr=0.50)
    report["bootstrap_ci_confidence_aware"] = bootstrap_ci(y, p, thr=0.60)

    print("[b3-reeval] template-disjoint GroupKFold metrics")
    report["template_disjoint_strict"] = group_kfold_eval(y, p, tids, thr=0.50)
    report["template_disjoint_confidence_aware"] = group_kfold_eval(y, p, tids, thr=0.60)
    print(f"    strict           {report['template_disjoint_strict']}")
    print(f"    confidence-aware {report['template_disjoint_confidence_aware']}")

    print("[b3-reeval] McNemar B3 (frozen) vs TF-IDF+LogReg (template-disjoint)")
    try:
        report["mcnemar_vs_lexical"] = mcnemar_b3_vs_lexical(y, p, texts, tids, thr=0.50)
        print(f"    {report['mcnemar_vs_lexical']}")
    except ImportError:
        print("    [skip] statsmodels not installed")
        report["mcnemar_vs_lexical"] = None

    make_figures(y, p, fams, report["calibration"])

    (OUT / "b3_reeval_v25.json").write_text(json.dumps(report, indent=2, default=float),
                                            encoding="utf-8")
    print(f"[ok] {OUT / 'b3_reeval_v25.json'}")
    return report


if __name__ == "__main__":
    main()
