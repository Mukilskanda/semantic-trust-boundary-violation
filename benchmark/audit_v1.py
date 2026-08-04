#!/usr/bin/env python3
"""
benchmark/audit_v1.py
======================
Complete diversity / lexical-leakage audit of STBV-Bench v1.
Writes BENCHMARK_AUDIT.md and results/benchmark_audit/audit_v1.json.

Run:  python benchmark/audit_v1.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmark"))

from corpus_metrics import full_corpus_report, self_bleu  # noqa: E402

OUT = ROOT / "results" / "benchmark_audit"
OUT.mkdir(parents=True, exist_ok=True)
FIGS = OUT / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

BENCH = ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"
N = 10_000
MODEL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"


def peer_text(tm):
    sc = tm.get("scene_context", {}) or {}
    parts = list(sc.get("peer_reports", [])) + list(sc.get("rsu_messages", []))
    return " ".join(parts).strip()


def load_v1():
    texts, labels, fams = [], [], []
    with open(BENCH, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= N:
                break
            r = json.loads(line)
            tm = r["transformed_message"]
            texts.append(peer_text(tm))
            labels.append(1 if tm.get("is_attacker") else 0)
            fams.append(r["attack_family"])
    return texts, np.array(labels), fams


def lexical_probe(texts, labels):
    """How well do trivial lexical models separate the classes?

    This is the operational definition of a lexical shortcut: if a
    bag-of-words model with no semantic capacity separates the classes
    near-perfectly, the separation is lexical, not semantic.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import f1_score, accuracy_score, roc_auc_score

    X = np.array(texts, dtype=object)
    models = {
        "TF-IDF + LogisticRegression": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("c", LogisticRegression(max_iter=2000, class_weight="balanced",
                                     random_state=42))]),
        "TF-IDF + LinearSVC": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("c", LinearSVC(class_weight="balanced", random_state=42))]),
        "Count + MultinomialNB": Pipeline([
            ("v", CountVectorizer(ngram_range=(1, 2), min_df=2)),
            ("c", MultinomialNB())]),
        "TF-IDF + RandomForest": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 1), min_df=2, max_features=20000)),
            ("c", RandomForestClassifier(n_estimators=200, n_jobs=-1,
                                         class_weight="balanced", random_state=42))]),
        "TF-IDF + DecisionTree": Pipeline([
            ("v", TfidfVectorizer(ngram_range=(1, 1), min_df=2, max_features=20000)),
            ("c", DecisionTreeClassifier(class_weight="balanced", random_state=42))]),
    }
    skf = StratifiedKFold(5, shuffle=True, random_state=42)
    out = {}
    for name, pipe in models.items():
        pred = cross_val_predict(pipe, X, labels, cv=skf, n_jobs=1)
        try:
            proba = cross_val_predict(pipe, X, labels, cv=skf, method="predict_proba",
                                      n_jobs=1)[:, 1]
            auc = roc_auc_score(labels, proba)
        except Exception:
            auc = float("nan")
        out[name] = {"accuracy": accuracy_score(labels, pred),
                     "f1": f1_score(labels, pred), "roc_auc": auc}
        print(f"    {name:32s} F1={out[name]['f1']:.4f}  acc={out[name]['accuracy']:.4f}")
    return out


def make_figures(texts, labels, rep):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from collections import Counter
    plt.rcParams.update({"font.size": 8, "axes.grid": True, "grid.alpha": 0.3})

    ben = [t for t, l in zip(texts, labels) if l == 0]
    mal = [t for t, l in zip(texts, labels) if l == 1]

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.4))
    # unique-string counts
    axes[0].bar(["benign", "malicious"], [len(set(ben)), len(set(mal))],
                color=["#4C72B0", "#C44E52"], alpha=0.85)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("unique message strings (log)")
    for i, v in enumerate([len(set(ben)), len(set(mal))]):
        axes[0].text(i, v * 1.15, str(v), ha="center", fontsize=8, fontweight="bold")
    axes[0].set_title("Unique strings per class", fontsize=8)
    # repeat-count distribution for benign
    cb = Counter(ben)
    axes[1].bar(range(len(cb)), sorted(cb.values(), reverse=True), color="#4C72B0")
    axes[1].set_xlabel("benign template rank"); axes[1].set_ylabel("occurrences")
    axes[1].set_title(f"Benign class = {len(cb)} templates", fontsize=8)
    # length distributions
    lb = [len(t.split()) for t in ben]; lm = [len(t.split()) for t in mal]
    axes[2].hist([lb, lm], bins=25, label=["benign", "malicious"],
                 color=["#4C72B0", "#C44E52"], alpha=0.85)
    axes[2].set_xlabel("tokens"); axes[2].legend(fontsize=6)
    axes[2].set_title("Message length", fontsize=8)
    fig.suptitle("STBV-Bench v1 — benign class collapses to a handful of templates",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / "audit_v1_diversity.pdf")
    fig.savefig(FIGS / "audit_v1_diversity.png", dpi=150)
    plt.close(fig)
    print(f"[figs] -> {FIGS}")


def main():
    print("[audit] loading STBV-Bench v1...")
    texts, labels, fams = load_v1()
    print(f"        n={len(texts)}  benign={int((labels==0).sum())}  "
          f"malicious={int((labels==1).sum())}")

    print("[audit] computing diversity metrics (self-BLEU, edit distance, ...)")
    rep = full_corpus_report(texts, labels, families=fams,
                             model_dir=str(MODEL_DIR), transformer=True)

    print("[audit] lexical-shortcut probe (5 bag-of-words models, 5-fold CV)")
    rep["lexical_probe"] = lexical_probe(texts, labels)

    (OUT / "audit_v1.json").write_text(json.dumps(rep, indent=2, default=float),
                                       encoding="utf-8")
    make_figures(texts, labels, rep)
    print(f"[ok] {OUT/'audit_v1.json'}")
    return rep


if __name__ == "__main__":
    main()
