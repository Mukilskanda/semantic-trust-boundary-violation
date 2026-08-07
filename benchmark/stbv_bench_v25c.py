#!/usr/bin/env python3
"""
benchmark/stbv_bench_v25c.py
=============================
STBV-Bench v2.5c generator + quality control + cross-corpus leakage audit
against BOTH v2.5 (train) and v2.5b (held-out eval).

v2.5c is TRAINING-ONLY augmentation data: same taxonomy as v2.5/v2.5b,
entirely new core templates (benchmark/v25c_compositional.py). Used to
continue fine-tuning the mixed-corpus checkpoint. Must stay disjoint from
v2.5b so v2.5b remains uncontaminated as an evaluation set. Run:

    python benchmark/stbv_bench_v25c.py
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

from v25c_compositional import (BENIGN_CORE, MALICIOUS_CORE, realise, slots,  # noqa: E402
                                pick_core)
from corpus_metrics import tokens, ngrams, levenshtein, _bleu               # noqa: E402

OUT_DIR = ROOT / "data" / "stbv_bench" / "v25c"
OUT_DIR.mkdir(parents=True, exist_ok=True)
V25_PATH = ROOT / "data" / "stbv_bench" / "v25" / "stbv_bench_v25.jsonl"
V25B_PATH = ROOT / "data" / "stbv_bench" / "v25b" / "stbv_bench_v25b.jsonl"
SEED = 20260807217  # distinct from v2.5 (20260802) and v2.5b (20260807)


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


def quality_control(rows, bleu_max=0.60, edit_min=0.25, ngram_max=0.70,
                    jaccard_gate=0.45, window=60):
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


def cross_corpus_audit(accepted, other_path, other_name):
    if not other_path.exists():
        return {"error": f"{other_name} corpus not found at {other_path}"}
    other_rows = [json.loads(l) for l in other_path.open(encoding="utf-8")]
    other_texts = set(r["text"].lower() for r in other_rows)
    other_tids = set(r["template_id"] for r in other_rows)
    other_4grams = set()
    for r in other_rows:
        other_4grams |= set(ngrams(tokens(r["text"]), 4))

    exact_overlap = [r for r in accepted if r["text"].lower() in other_texts]
    tid_overlap = [r for r in accepted if r["template_id"] in other_tids]

    max_4gram_containment = 0.0
    for r in accepted:
        n4 = set(ngrams(tokens(r["text"]), 4))
        if not n4:
            continue
        ov = len(n4 & other_4grams) / len(n4)
        max_4gram_containment = max(max_4gram_containment, ov)

    return {
        f"{other_name}_n_total": len(other_rows),
        "exact_text_overlap_count": len(exact_overlap),
        "template_id_overlap_count": len(tid_overlap),
        "max_4gram_containment": round(max_4gram_containment, 4),
        "verdict": "TEMPLATE_DISJOINT" if (len(exact_overlap) == 0 and len(tid_overlap) == 0)
                   else "LEAKAGE_DETECTED",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benign", type=int, default=3000)
    ap.add_argument("--malicious", type=int, default=3700)
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

    print("[audit] cross-corpus disjointness vs v2.5 (train)")
    audit25 = cross_corpus_audit(acc, V25_PATH, "v25")
    print(f"      {audit25}")
    print("[audit] cross-corpus disjointness vs v2.5b (held-out eval)")
    audit25b = cross_corpus_audit(acc, V25B_PATH, "v25b")
    print(f"      {audit25b}")

    nb = sum(1 for r in acc if r["label"] == 0)
    nm = sum(1 for r in acc if r["label"] == 1)

    out = OUT_DIR / "stbv_bench_v25c.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for i, r in enumerate(acc):
            rec = {"sample_id": f"v25c-{i:06d}", **r}
            rec.pop("core_template", None)
            f.write(json.dumps(rec) + "\n")
    with open(OUT_DIR / "rejected.jsonl", "w", encoding="utf-8") as f:
        for r in rej:
            r = dict(r)
            r.pop("core_template", None)
            f.write(json.dumps(r) + "\n")

    manifest = {
        "benchmark": "STBV-Bench v2.5c (training-only augmentation, template-disjoint)",
        "seed": args.seed,
        "n_total": len(acc), "n_benign": nb, "n_malicious": nm,
        "prevalence_malicious": nm / max(1, len(acc)),
        "attack_families": dict(Counter(r["attack_family"] for r in acc
                                        if r["label"] == 1)),
        "benign_intents": dict(Counter(r["intent"] for r in acc if r["label"] == 0)),
        "n_rejected": len(rej), "reject_reasons": dict(rc),
        "cross_corpus_disjointness_audit": {"vs_v25_train": audit25, "vs_v25b_eval": audit25b},
        "usage_policy": "TRAINING AUGMENTATION ONLY. Must never be merged into "
                        "or evaluated as v2.5b; kept disjoint from v2.5b by "
                        "construction and verified programmatically above.",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                           encoding="utf-8")
    print(f"\n[ok] {out}")


if __name__ == "__main__":
    main()
