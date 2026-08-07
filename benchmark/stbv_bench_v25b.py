#!/usr/bin/env python3
"""
benchmark/stbv_bench_v25b.py
=============================
STBV-Bench v2.5b generator + quality control + cross-corpus leakage audit
against STBV-Bench v2.5.

v2.5b is EVALUATION-ONLY: same taxonomy as v2.5 (11 benign intents incl.
3 lexical-bridge hard negatives, 13 malicious attack families), entirely
new core sentence templates (benchmark/v25b_compositional.py), never used
for training. Run:

    python benchmark/stbv_bench_v25b.py
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

from v25b_compositional import (BENIGN_CORE, MALICIOUS_CORE, realise, slots,  # noqa: E402
                                pick_core)
from corpus_metrics import tokens, ngrams, levenshtein, _bleu               # noqa: E402

OUT_DIR = ROOT / "data" / "stbv_bench" / "v25b"
OUT_DIR.mkdir(parents=True, exist_ok=True)
V25_PATH = ROOT / "data" / "stbv_bench" / "v25" / "stbv_bench_v25.jsonl"
SEED = 20260807  # distinct from v2.5's seed (20260802)


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
                     "template_id": tid, "core_template": core_template})
        return True

    intents = list(BENIGN_CORE)
    per = max(1, n_benign // len(intents))
    for intent in intents:
        got = tries = 0
        while got < per and tries < per * 400:
            tries += 1
            s = slots(rng)
            core, mood = pick_core(rng, BENIGN_CORE, intent)
            if emit(realise(rng, core, s), 0, "benign_control", intent, mood, core):
                got += 1

    fams = list(MALICIOUS_CORE)
    per = max(1, n_malicious // len(fams))
    for fam in fams:
        got = tries = 0
        while got < per and tries < per * 400:
            tries += 1
            s = slots(rng)
            core, mood = pick_core(rng, MALICIOUS_CORE, fam)
            if emit(realise(rng, core, s), 1, fam, fam, mood, core):
                got += 1
    return rows


# ===========================================================================
def quality_control(rows, bleu_max=0.60, edit_min=0.25, ngram_max=0.70,
                    jaccard_gate=0.45, window=60):
    """Reject near-duplicates WITHIN a family (same policy as v2.5)."""
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
def cross_corpus_audit(accepted, v25_path):
    """Verify v2.5b has zero template-id overlap, zero exact-text overlap,
    and low n-gram leakage against v2.5. This is the disjointness proof."""
    if not v25_path.exists():
        return {"error": f"v2.5 corpus not found at {v25_path}"}

    v25_rows = [json.loads(l) for l in v25_path.open(encoding="utf-8")]
    v25_texts = set(r["text"].lower() for r in v25_rows)
    v25_tids = set(r["template_id"] for r in v25_rows)
    v25_4grams = set()
    for r in v25_rows:
        v25_4grams |= set(ngrams(tokens(r["text"]), 4))

    exact_overlap = [r for r in accepted if r["text"].lower() in v25_texts]
    tid_overlap = [r for r in accepted if r["template_id"] in v25_tids]

    max_4gram_containment = 0.0
    high_containment_samples = []
    for r in accepted:
        n4 = set(ngrams(tokens(r["text"]), 4))
        if not n4:
            continue
        ov = len(n4 & v25_4grams) / len(n4)
        max_4gram_containment = max(max_4gram_containment, ov)
        if ov > 0.70:
            high_containment_samples.append({"text": r["text"], "containment": ov})

    return {
        "v25_n_total": len(v25_rows),
        "v25b_n_total": len(accepted),
        "exact_text_overlap_count": len(exact_overlap),
        "template_id_overlap_count": len(tid_overlap),
        "max_4gram_containment_vs_v25": round(max_4gram_containment, 4),
        "n_samples_with_4gram_containment_over_0.70": len(high_containment_samples),
        "high_containment_examples": high_containment_samples[:5],
        "verdict": "TEMPLATE_DISJOINT" if (len(exact_overlap) == 0 and len(tid_overlap) == 0)
                   else "LEAKAGE_DETECTED",
    }


# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benign", type=int, default=4500)
    ap.add_argument("--malicious", type=int, default=5600)
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

    print("[audit] cross-corpus disjointness check vs STBV-Bench v2.5")
    audit = cross_corpus_audit(acc, V25_PATH)
    print(f"      verdict={audit.get('verdict')} "
          f"exact_overlap={audit.get('exact_text_overlap_count')} "
          f"template_id_overlap={audit.get('template_id_overlap_count')} "
          f"max_4gram_containment={audit.get('max_4gram_containment_vs_v25')}")

    nb = sum(1 for r in acc if r["label"] == 0)
    nm = sum(1 for r in acc if r["label"] == 1)

    out = OUT_DIR / "stbv_bench_v25b.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for i, r in enumerate(acc):
            rec = {"sample_id": f"v25b-{i:06d}", **r}
            rec.pop("core_template", None)
            f.write(json.dumps(rec) + "\n")
    with open(OUT_DIR / "rejected.jsonl", "w", encoding="utf-8") as f:
        for r in rej:
            r = dict(r)
            r.pop("core_template", None)
            f.write(json.dumps(r) + "\n")

    manifest = {
        "benchmark": "STBV-Bench v2.5b (held-out, template-disjoint, eval-only)",
        "seed": args.seed,
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
        "cross_corpus_disjointness_audit": audit,
        "usage_policy": "EVALUATION ONLY. Never include in any training, "
                        "fine-tuning, LoRA, or model-selection split.",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                           encoding="utf-8")
    print(f"\n[ok] {out}")
    print(f"     unique benign={manifest['n_unique_benign']} "
          f"malicious={manifest['n_unique_malicious']} "
          f"prevalence={manifest['prevalence_malicious']:.3f}")


if __name__ == "__main__":
    main()
