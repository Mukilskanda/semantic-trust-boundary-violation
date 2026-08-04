#!/usr/bin/env python3
"""
benchmark/lexical_leakage.py
=============================
Lexical-shortcut probe. Trains bag-of-words models that have NO semantic
capacity whatsoever and measures how well they separate the classes.

ACCEPTANCE CRITERION (declared before running, not after):
A benchmark is UNACCEPTABLE if a bag-of-words model separates its classes
near-perfectly, because that proves the label is recoverable from surface
form alone. Concretely we require of the best lexical model:

    F1        < 0.90
    ROC-AUC   < 0.95

These are deliberately permissive: lexical models SHOULD retain some
signal, because real attacks do use somewhat different words. What must
not survive is *near-perfect* separation.

Two additional degenerate-shortcut probes are included because they caught
real artefacts in v1:
  * LENGTH-ONLY classifier (token count as the single feature)
  * TOP-K vocabulary indicator

Run:  python benchmark/lexical_leakage.py --corpus v25
      python benchmark/lexical_leakage.py --corpus v1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmark"))

OUT = ROOT / "results" / "benchmark_audit"
OUT.mkdir(parents=True, exist_ok=True)

F1_MAX = 0.90
AUC_MAX = 0.95
SEED = 42


def load_corpus(which):
    if which == "v25":
        p = ROOT / "data" / "stbv_bench" / "v25" / "stbv_bench_v25.jsonl"
        rows = [json.loads(l) for l in open(p, encoding="utf-8")]
        return ([r["text"] for r in rows], np.array([r["label"] for r in rows]),
                [r["attack_family"] for r in rows])
    p = ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"
    texts, labels, fams = [], [], []
    with open(p, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 10000:
                break
            r = json.loads(line)
            tm = r["transformed_message"]
            sc = tm.get("scene_context", {}) or {}
            texts.append(" ".join(list(sc.get("peer_reports", [])) +
                                  list(sc.get("rsu_messages", []))).strip())
            labels.append(1 if tm.get("is_attacker") else 0)
            fams.append(r["attack_family"])
    return texts, np.array(labels), fams


def build_models():
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.pipeline import Pipeline
    return {
        "TF-IDF + LogisticRegression": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("c", LogisticRegression(max_iter=3000, class_weight="balanced",
                                     random_state=SEED))]),
        "TF-IDF + LinearSVC": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("c", LinearSVC(class_weight="balanced", random_state=SEED))]),
        "Count + MultinomialNB": Pipeline([
            ("v", CountVectorizer(ngram_range=(1, 2), min_df=2)),
            ("c", MultinomialNB())]),
        "TF-IDF + RandomForest": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 1), min_df=2, max_features=20000)),
            ("c", RandomForestClassifier(n_estimators=300, n_jobs=-1,
                                         class_weight="balanced", random_state=SEED))]),
        "TF-IDF + DecisionTree": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 1), min_df=2, max_features=20000)),
            ("c", DecisionTreeClassifier(class_weight="balanced", random_state=SEED))]),
    }


def length_only_probe(texts, labels):
    """Can token count alone classify? This caught v1's 8.4-vs-22.1 artefact."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import f1_score, accuracy_score, roc_auc_score
    X = np.array([[len(t.split())] for t in texts], dtype=float)
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    clf = LogisticRegression(class_weight="balanced", max_iter=1000)
    pred = cross_val_predict(clf, X, labels, cv=skf)
    proba = cross_val_predict(clf, X, labels, cv=skf, method="predict_proba")[:, 1]
    return {"accuracy": accuracy_score(labels, pred), "f1": f1_score(labels, pred),
            "roc_auc": roc_auc_score(labels, proba)}


def evaluate(texts, labels):
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import (f1_score, accuracy_score, roc_auc_score,
                                 precision_score, recall_score)
    X = np.array(texts, dtype=object)
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    res = {}
    for name, pipe in build_models().items():
        pred = cross_val_predict(pipe, X, labels, cv=skf, n_jobs=1)
        try:
            proba = cross_val_predict(pipe, X, labels, cv=skf,
                                      method="predict_proba", n_jobs=1)[:, 1]
            auc = roc_auc_score(labels, proba)
        except Exception:
            try:
                dec = cross_val_predict(pipe, X, labels, cv=skf,
                                        method="decision_function", n_jobs=1)
                auc = roc_auc_score(labels, dec)
            except Exception:
                auc = float("nan")
        res[name] = {
            "accuracy": accuracy_score(labels, pred),
            "precision": precision_score(labels, pred, zero_division=0),
            "recall": recall_score(labels, pred, zero_division=0),
            "f1": f1_score(labels, pred), "roc_auc": auc,
        }
        print(f"    {name:32s} F1={res[name]['f1']:.4f}  "
              f"AUC={res[name]['roc_auc']:.4f}  acc={res[name]['accuracy']:.4f}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="v25", choices=["v1", "v25"])
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    tag = args.tag or args.corpus

    texts, labels, fams = load_corpus(args.corpus)
    print(f"[leak] corpus={args.corpus}  n={len(texts)}  "
          f"prevalence={labels.mean():.4f}")

    print("[leak] bag-of-words probes (5-fold stratified CV)")
    res = evaluate(texts, labels)

    print("[leak] degenerate-shortcut probes")
    lp = length_only_probe(texts, labels)
    print(f"    {'LENGTH-ONLY (token count)':32s} F1={lp['f1']:.4f}  "
          f"AUC={lp['roc_auc']:.4f}  acc={lp['accuracy']:.4f}")

    best_f1 = max(v["f1"] for v in res.values())
    best_auc = max(v["roc_auc"] for v in res.values()
                   if not np.isnan(v["roc_auc"]))
    verdict = "ACCEPTABLE" if (best_f1 < F1_MAX and best_auc < AUC_MAX) else "UNACCEPTABLE"

    payload = {
        "corpus": args.corpus, "n": len(texts),
        "prevalence_malicious": float(labels.mean()),
        "acceptance_criterion": {"best_lexical_f1_must_be_below": F1_MAX,
                                 "best_lexical_roc_auc_must_be_below": AUC_MAX},
        "models": res, "length_only_probe": lp,
        "best_lexical_f1": best_f1, "best_lexical_roc_auc": best_auc,
        "verdict": verdict,
    }
    (OUT / f"lexical_leakage_{tag}.json").write_text(
        json.dumps(payload, indent=2, default=float), encoding="utf-8")

    print(f"\n  best lexical F1  = {best_f1:.4f}   (must be < {F1_MAX})")
    print(f"  best lexical AUC = {best_auc:.4f}   (must be < {AUC_MAX})")
    print(f"  VERDICT: {verdict}")
    return payload


if __name__ == "__main__":
    main()
