"""
benchmark/corpus_metrics.py
============================
Corpus-diversity and lexical-leakage metrics, shared by the v1 audit, the
v2.5 quality-control filters, and the v2.5 audit, so every number in every
report is produced by one implementation.

Dependencies deliberately limited to numpy/scipy/sklearn: BLEU and
Levenshtein are implemented here rather than pulled from NLTK/python-
Levenshtein (neither installed) so the metrics are inspectable and the
pipeline has no unstated dependency.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

_WORD = re.compile(r"[A-Za-z0-9']+")


def tokens(text: str):
    return _WORD.findall(text.lower())


def ngrams(toks, n):
    return [tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)]


# ---------------------------------------------------------------- diversity
def type_token_ratio(texts):
    """Corpus-level TTR over word tokens."""
    toks = [t for x in texts for t in tokens(x)]
    return len(set(toks)) / max(1, len(toks))


def mtld(texts, threshold=0.72):
    """Measure of Textual Lexical Diversity -- length-robust unlike raw TTR.

    TTR falls mechanically as corpus size grows, so comparing TTR between
    corpora of different sizes is invalid. MTLD is the standard correction:
    mean length of consecutive token runs that sustain TTR >= threshold.
    """
    toks = [t for x in texts for t in tokens(x)]
    if len(toks) < 50:
        return float("nan")

    def _pass(seq):
        factors, types, count = 0, set(), 0
        for t in seq:
            types.add(t)
            count += 1
            if len(types) / count <= threshold:
                factors += 1
                types, count = set(), 0
        if count:
            factors += (1 - len(types) / count) / (1 - threshold)
        return len(seq) / factors if factors else float("nan")

    return float(np.mean([_pass(toks), _pass(toks[::-1])]))


def vocabulary_stats(texts):
    toks = [t for x in texts for t in tokens(x)]
    vocab = Counter(toks)
    return {
        "n_tokens": len(toks),
        "vocab_size": len(vocab),
        "hapax_legomena": sum(1 for v in vocab.values() if v == 1),
        "hapax_fraction": sum(1 for v in vocab.values() if v == 1) / max(1, len(vocab)),
    }


def length_stats(texts):
    lens = np.array([len(tokens(t)) for t in texts], dtype=float)
    chars = np.array([len(t) for t in texts], dtype=float)
    return {
        "mean_tokens": float(lens.mean()), "std_tokens": float(lens.std()),
        "min_tokens": int(lens.min()), "max_tokens": int(lens.max()),
        "mean_chars": float(chars.mean()),
    }


def duplicate_stats(texts):
    c = Counter(texts)
    n_dup_items = sum(v for v in c.values() if v > 1)
    return {
        "n_total": len(texts),
        "n_unique": len(c),
        "unique_ratio": len(c) / max(1, len(texts)),
        "duplicate_rate": n_dup_items / max(1, len(texts)),
        "max_repeat_count": max(c.values()) if c else 0,
    }


# -------------------------------------------------------------------- BLEU
def _bleu(candidate_toks, reference_toks_list, max_n=4):
    """Sentence BLEU with add-epsilon smoothing (Chen & Cherry smoothing 1)."""
    if not candidate_toks:
        return 0.0
    precisions = []
    for n in range(1, max_n + 1):
        cand = Counter(ngrams(candidate_toks, n))
        if not cand:
            precisions.append(0.0)
            continue
        maxref = Counter()
        for ref in reference_toks_list:
            rc = Counter(ngrams(ref, n))
            for g, cnt in rc.items():
                if cnt > maxref[g]:
                    maxref[g] = cnt
        clipped = sum(min(c, maxref[g]) for g, c in cand.items())
        total = sum(cand.values())
        precisions.append((clipped + 1e-9) / (total + 1e-9))
    logp = sum(math.log(p) for p in precisions) / max_n
    clen = len(candidate_toks)
    rlen = min((len(r) for r in reference_toks_list),
               key=lambda x: (abs(x - clen), x))
    bp = 1.0 if clen > rlen else math.exp(1 - rlen / max(1, clen))
    return bp * math.exp(logp)


def self_bleu(texts, sample=300, refs=30, seed=42):
    """Mean BLEU of each sampled text against `refs` other texts.

    HIGH self-BLEU => the corpus repeats itself => low diversity.
    O(sample*refs) rather than O(n^2) so it stays tractable on 10k corpora.
    """
    rng = np.random.default_rng(seed)
    toks = [tokens(t) for t in texts]
    n = len(toks)
    if n < 3:
        return float("nan")
    idx = rng.choice(n, size=min(sample, n), replace=False)
    scores = []
    for i in idx:
        pool = rng.choice(n, size=min(refs + 1, n), replace=False)
        pool = [j for j in pool if j != i][:refs]
        if not pool:
            continue
        scores.append(_bleu(toks[i], [toks[j] for j in pool]))
    return float(np.mean(scores)) if scores else float("nan")


# ----------------------------------------------------------- edit distance
def levenshtein(a, b, cap=None):
    """Iterative Levenshtein with two rows; `cap` allows early exit."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
        if cap is not None and min(prev) > cap:
            return cap + 1
    return prev[-1]


def normalized_edit_distance_stats(texts, sample=250, seed=42):
    """Mean/percentile normalized edit distance between random pairs.

    LOW values => texts differ only trivially (e.g. one swapped word).
    """
    rng = np.random.default_rng(seed)
    n = len(texts)
    if n < 2:
        return {}
    vals = []
    for _ in range(sample):
        i, j = rng.choice(n, size=2, replace=False)
        a, b = texts[i], texts[j]
        d = levenshtein(a, b)
        vals.append(d / max(1, max(len(a), len(b))))
    v = np.array(vals)
    return {
        "mean_normalized_edit_distance": float(v.mean()),
        "p05": float(np.percentile(v, 5)),
        "median": float(np.percentile(v, 50)),
        "frac_pairs_below_0.20": float((v < 0.20).mean()),
    }


# -------------------------------------------------------- n-gram / overlap
def ngram_overlap_between(a_texts, b_texts, n=4):
    """Jaccard + containment of n-gram sets between two classes.

    High cross-class overlap is GOOD here: it means the two classes share
    surface vocabulary and cannot be separated lexically.
    """
    A = set(g for t in a_texts for g in ngrams(tokens(t), n))
    B = set(g for t in b_texts for g in ngrams(tokens(t), n))
    if not A or not B:
        return {}
    inter = len(A & B)
    return {
        f"n{n}_unique_A": len(A), f"n{n}_unique_B": len(B),
        f"n{n}_jaccard": inter / len(A | B),
        f"n{n}_containment_A_in_B": inter / len(A),
        f"n{n}_containment_B_in_A": inter / len(B),
    }


def distinct_n(texts, n=2):
    g = [x for t in texts for x in ngrams(tokens(t), n)]
    return len(set(g)) / max(1, len(g))


# ---------------------------------------------------- embedding similarity
def tfidf_similarity_stats(texts, sample=400, seed=42):
    """Mean pairwise cosine similarity under TF-IDF (lexical similarity)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(texts), size=min(sample, len(texts)), replace=False)
    sub = [texts[i] for i in idx]
    X = TfidfVectorizer(ngram_range=(1, 2), min_df=1,
                        sublinear_tf=True).fit_transform(sub)
    S = (X @ X.T).toarray()
    iu = np.triu_indices_from(S, k=1)
    v = S[iu]
    return {
        "tfidf_cosine_mean": float(v.mean()),
        "tfidf_cosine_p95": float(np.percentile(v, 95)),
        "tfidf_cosine_frac_above_0.8": float((v > 0.8).mean()),
    }


def transformer_embedding_stats(texts, sample=300, seed=42, model_dir=None):
    """Mean pairwise cosine similarity under B3's OWN encoder.

    Uses the deployed checkpoint's encoder so 'semantic similarity' is
    measured in the representation space the evaluated model actually uses,
    rather than an unrelated third-party sentence encoder.
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
    except Exception as e:
        return {"error": f"transformers unavailable: {e}"}
    if model_dir is None:
        return {"error": "no model_dir supplied"}
    try:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(texts), size=min(sample, len(texts)), replace=False)
        sub = [texts[i] for i in idx]
        tok = AutoTokenizer.from_pretrained(model_dir)
        mdl = AutoModel.from_pretrained(model_dir)
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        mdl = mdl.to(dev).eval()
        embs = []
        with torch.no_grad():
            for i in range(0, len(sub), 32):
                b = tok(sub[i:i + 32], padding=True, truncation=True,
                        max_length=256, return_tensors="pt").to(dev)
                out = mdl(**b).last_hidden_state
                mask = b["attention_mask"].unsqueeze(-1).float()
                embs.append(((out * mask).sum(1) / mask.sum(1)).cpu().numpy())
        E = np.vstack(embs)
        E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
        S = E @ E.T
        iu = np.triu_indices_from(S, k=1)
        v = S[iu]
        return {
            "embed_cosine_mean": float(v.mean()),
            "embed_cosine_p95": float(np.percentile(v, 95)),
            "embed_cosine_frac_above_0.95": float((v > 0.95).mean()),
            "encoder": str(model_dir), "n_sampled": len(sub),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


# ------------------------------------------------------------- full report
def full_corpus_report(texts, labels, families=None, model_dir=None,
                       transformer=False):
    """Complete diversity + cross-class-separability report."""
    texts = list(texts)
    labels = np.asarray(labels)
    ben = [t for t, l in zip(texts, labels) if l == 0]
    mal = [t for t, l in zip(texts, labels) if l == 1]

    rep = {
        "n_total": len(texts), "n_benign": len(ben), "n_malicious": len(mal),
        "overall": {
            "duplicates": duplicate_stats(texts),
            "vocabulary": vocabulary_stats(texts),
            "length": length_stats(texts),
            "type_token_ratio": type_token_ratio(texts),
            "mtld": mtld(texts),
            "distinct_1": distinct_n(texts, 1), "distinct_2": distinct_n(texts, 2),
            "distinct_3": distinct_n(texts, 3),
        },
        "benign": {
            "duplicates": duplicate_stats(ben),
            "vocabulary": vocabulary_stats(ben),
            "length": length_stats(ben),
            "type_token_ratio": type_token_ratio(ben),
            "mtld": mtld(ben),
            "self_bleu": self_bleu(ben),
            "edit_distance": normalized_edit_distance_stats(ben),
            "tfidf_similarity": tfidf_similarity_stats(ben),
        },
        "malicious": {
            "duplicates": duplicate_stats(mal),
            "vocabulary": vocabulary_stats(mal),
            "length": length_stats(mal),
            "type_token_ratio": type_token_ratio(mal),
            "mtld": mtld(mal),
            "self_bleu": self_bleu(mal),
            "edit_distance": normalized_edit_distance_stats(mal),
            "tfidf_similarity": tfidf_similarity_stats(mal),
        },
        "cross_class_overlap": {
            **ngram_overlap_between(ben, mal, 1),
            **ngram_overlap_between(ben, mal, 2),
            **ngram_overlap_between(ben, mal, 4),
        },
    }
    if families is not None:
        fam = Counter(families)
        rep["families"] = {
            "n_families": len(fam),
            "counts": dict(sorted(fam.items())),
            "min_family_size": min(fam.values()), "max_family_size": max(fam.values()),
        }
        per_fam = {}
        by = {}
        for t, f in zip(texts, families):
            by.setdefault(f, []).append(t)
        for f, ts in sorted(by.items()):
            per_fam[f] = {
                "n": len(ts), "n_unique": len(set(ts)),
                "unique_ratio": len(set(ts)) / len(ts),
                "self_bleu": self_bleu(ts, sample=80, refs=15),
                "ttr": type_token_ratio(ts),
            }
        rep["per_family"] = per_fam
    if transformer and model_dir:
        rep["benign"]["transformer_similarity"] = transformer_embedding_stats(
            ben, model_dir=model_dir)
        rep["malicious"]["transformer_similarity"] = transformer_embedding_stats(
            mal, model_dir=model_dir)
    return rep
