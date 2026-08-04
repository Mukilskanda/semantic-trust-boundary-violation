#!/usr/bin/env python3
"""
benchmark/stbv_bench_v25.py
============================
STBV-Bench v2.5 generator + quality control.  Single command:

    python benchmark/stbv_bench_v25.py

WHY v1 FAILED (measured -- see BENCHMARK_AUDIT.md, not assumed):
  * benign class = 10 unique strings across 2,993 samples (TTR 0.0009,
    self-BLEU 0.977, vocabulary 23 words)
  * mean length 8.4 tokens benign vs 22.1 malicious -- LENGTH ALONE nearly
    separates the classes
  * cross-class 4-gram Jaccard 0.0035 -- the classes shared almost no
    surface material
  * consequence: five different bag-of-words models (LogReg, LinearSVC,
    MultinomialNB, RandomForest, DecisionTree) each reached F1 = 1.0000

v2.5 fixes the corpus, not the metric. Design and rationale live in
benchmark/v25_compositional.py; the short version is that every
label-independent constituent (opening, warrant, closing, lexicon, length
profile, register) is SHARED between classes, so only the semantic act
differs, and benign hard negatives deliberately reuse each attack family's
characteristic vocabulary legitimately.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmark"))

from v25_compositional import (BENIGN_CORE, MALICIOUS_CORE, realise, slots,  # noqa: E402
                               pick_core)
from corpus_metrics import tokens, ngrams, levenshtein, _bleu               # noqa: E402

OUT_DIR = ROOT / "data" / "stbv_bench" / "v25"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 20260802


# ===========================================================================
def generate(n_benign, n_malicious, seed=SEED):
    rng = random.Random(seed)
    rows, seen = [], set()

    def emit(text, label, family, intent, mood, core_template):
        k = text.lower()
        if k in seen:
            return False
        seen.add(k)
        tid = f"{intent}:{mood}:{abs(hash(core_template)) % 100000}"
        rows.append({"text": text, "label": label,
                     "attack_family": family, "intent": intent, "mood": mood,
                     "template_id": tid})
        return True

    # ---- benign: even allocation across intents (incl. hard negatives) ----
    intents = list(BENIGN_CORE)
    per = max(1, n_benign // len(intents))
    for intent in intents:
        got = tries = 0
        while got < per and tries < per * 300:
            tries += 1
            s = slots(rng)
            core, mood = pick_core(rng, BENIGN_CORE, intent)
            if emit(realise(rng, core, s), 0, "benign_control", intent, mood, core):
                got += 1

    # ---- malicious: even allocation across families ----
    fams = list(MALICIOUS_CORE)
    per = max(1, n_malicious // len(fams))
    for fam in fams:
        got = tries = 0
        while got < per and tries < per * 300:
            tries += 1
            s = slots(rng)
            core, mood = pick_core(rng, MALICIOUS_CORE, fam)
            if emit(realise(rng, core, s), 1, fam, fam, mood, core):
                got += 1
    return rows


# ===========================================================================
def quality_control(rows, bleu_max=0.60, edit_min=0.25, ngram_max=0.70,
                    jaccard_gate=0.45, window=60):
    """Reject near-duplicates WITHIN a family. Every rejection is logged.

    Near-duplication only matters within a family: two different families
    sharing surface form is the design goal, not a defect, so cross-family
    similarity is deliberately not penalised.

    A token-set Jaccard gate runs before the expensive Levenshtein/BLEU
    checks; pairs below the gate are already lexically distant and cannot
    trip any of the thresholds.
    """
    accepted, rejected = [], []
    pools, exact = {}, {}
    for r in rows:
        fam = r["attack_family"] if r["label"] == 1 else f"benign::{r['intent']}"
        pool = pools.setdefault(fam, [])
        ex = exact.setdefault(fam, set())
        t = r["text"]
        tk = tokens(t)
        tset, n4 = set(tk), set(ngrams(tk, 4))
        reason = None

        if t.lower() in ex:
            reason = "exact_duplicate"
        if reason is None and pool:
            close = []
            for ptext, ptset, pn4 in pool[-window:]:
                jac = len(tset & ptset) / max(1, len(tset | ptset))
                if jac < jaccard_gate:
                    continue
                close.append((ptext, ptset, pn4))
                if n4 and pn4:
                    ov = len(n4 & pn4) / len(n4)
                    if ov > ngram_max:
                        reason = f"ngram4_overlap={ov:.2f}"
                        break
                nd = levenshtein(t, ptext) / max(1, max(len(t), len(ptext)))
                if nd < edit_min:
                    reason = f"edit_distance={nd:.2f}"
                    break
            if reason is None and close:
                b = _bleu(tk, [tokens(p[0]) for p in close[-20:]])
                if b > bleu_max:
                    reason = f"self_bleu={b:.2f}"

        if reason:
            rejected.append({**r, "reject_reason": reason})
        else:
            pool.append((t, tset, n4))
            ex.add(t.lower())
            accepted.append(r)
    return accepted, rejected


# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benign", type=int, default=6000)
    ap.add_argument("--malicious", type=int, default=7800)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    print(f"[gen] target benign={args.benign} malicious={args.malicious}")
    rows = generate(args.benign, args.malicious, args.seed)
    print(f"      raw unique: {len(rows)} "
          f"(benign {sum(1 for r in rows if r['label']==0)}, "
          f"malicious {sum(1 for r in rows if r['label']==1)})")

    print("[qc ] dedup / n-gram containment / edit distance / self-BLEU")
    acc, rej = quality_control(rows)
    rc = Counter(r["reject_reason"].split("=")[0] for r in rej)
    print(f"      accepted={len(acc)} rejected={len(rej)} "
          f"({100*len(rej)/max(1,len(rows)):.1f}%)")
    for k, v in rc.most_common():
        print(f"        {k:20s} {v}")

    nb = sum(1 for r in acc if r["label"] == 0)
    nm = sum(1 for r in acc if r["label"] == 1)

    out = OUT_DIR / "stbv_bench_v25.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for i, r in enumerate(acc):
            f.write(json.dumps({"sample_id": f"v25-{i:06d}", **r}) + "\n")
    with open(OUT_DIR / "rejected.jsonl", "w", encoding="utf-8") as f:
        for r in rej:
            f.write(json.dumps(r) + "\n")

    manifest = {
        "benchmark": "STBV-Bench v2.5", "seed": args.seed,
        "n_total": len(acc), "n_benign": nb, "n_malicious": nm,
        "prevalence_malicious": nm / max(1, len(acc)),
        "n_unique_benign": len(set(r["text"] for r in acc if r["label"] == 0)),
        "n_unique_malicious": len(set(r["text"] for r in acc if r["label"] == 1)),
        "attack_families": dict(Counter(r["attack_family"] for r in acc
                                        if r["label"] == 1)),
        "benign_intents": dict(Counter(r["intent"] for r in acc if r["label"] == 0)),
        "n_rejected": len(rej), "reject_reasons": dict(rc),
        "qc_thresholds": {"self_bleu_max": 0.60, "min_normalized_edit_distance": 0.25,
                          "max_4gram_containment": 0.70,
                          "jaccard_prefilter_gate": 0.45},
        "design_principle": "all label-independent constituents (opening, warrant, "
                            "closing, lexicon, length, register) shared across classes; "
                            "benign hard negatives reuse each attack family's "
                            "characteristic vocabulary legitimately",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                           encoding="utf-8")
    print(f"\n[ok] {out}")
    print(f"     unique benign={manifest['n_unique_benign']} "
          f"malicious={manifest['n_unique_malicious']} "
          f"prevalence={manifest['prevalence_malicious']:.3f}")


if __name__ == "__main__":
    main()
