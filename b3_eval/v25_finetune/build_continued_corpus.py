"""
b3_eval/v25_finetune/build_continued_corpus.py
================================================
Builds the training/validation splits for continued fine-tuning of the
mixed-corpus checkpoint: the existing mixed corpus (v2.5 train split + v1
stratified sample, per MIXED_CORPUS_REPORT.md) PLUS STBV-Bench v2.5c
(data/stbv_bench/v25c/, template-disjoint training-only augmentation,
verified disjoint from v2.5b in stbv_bench_v25c.py's manifest).

v2.5c is split 85/15 train/val, stratified per family/intent, seed 42
(matching the seed used to build the original mixed corpus).
"""
from __future__ import annotations

import json
import pathlib
import random
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
V25C_PATH = ROOT / "data" / "stbv_bench" / "v25c" / "stbv_bench_v25c.jsonl"

SEED = 42
VAL_FRAC = 0.15


def main():
    rng = random.Random(SEED)
    rows = [json.loads(l) for l in V25C_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]

    by_key = defaultdict(list)
    for r in rows:
        key = r["attack_family"] if r["label"] == 1 else f"benign::{r['intent']}"
        by_key[key].append(r)

    train_rows, val_rows = [], []
    for key, group in by_key.items():
        rng.shuffle(group)
        n_val = max(1, int(len(group) * VAL_FRAC))
        val_rows.extend(group[:n_val])
        train_rows.extend(group[n_val:])

    rng.shuffle(train_rows)
    rng.shuffle(val_rows)

    existing_train = [json.loads(l) for l in (DATA_DIR / "mixed_train_split.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    existing_val = [json.loads(l) for l in (DATA_DIR / "mixed_val_split.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    combined_train = existing_train + [{"text": r["text"], "label": r["label"]} for r in train_rows]
    combined_val = existing_val + [{"text": r["text"], "label": r["label"]} for r in val_rows]
    rng.shuffle(combined_train)
    rng.shuffle(combined_val)

    out_train = DATA_DIR / "continued_train_split.jsonl"
    out_val = DATA_DIR / "continued_val_split.jsonl"
    with open(out_train, "w", encoding="utf-8") as f:
        for r in combined_train:
            f.write(json.dumps(r) + "\n")
    with open(out_val, "w", encoding="utf-8") as f:
        for r in combined_val:
            f.write(json.dumps(r) + "\n")

    manifest = {
        "existing_mixed_train": len(existing_train), "existing_mixed_val": len(existing_val),
        "v25c_added_train": len(train_rows), "v25c_added_val": len(val_rows),
        "combined_train": len(combined_train), "combined_val": len(combined_val),
        "v25c_source": str(V25C_PATH), "seed": SEED, "val_frac_v25c": VAL_FRAC,
        "note": "v2.5c is disjoint from v2.5b (held-out eval) by construction; "
                "see data/stbv_bench/v25c/manifest.json cross_corpus_disjointness_audit.",
    }
    (DATA_DIR / "continued_corpus_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
