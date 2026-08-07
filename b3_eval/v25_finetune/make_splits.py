"""
b3_eval/v25_finetune/make_splits.py
====================================
Builds template-disjoint 70/15/15 train/val/test splits of STBV-Bench v2.5
for LoRA fine-tuning of the B3 semantic gate.

Grouping unit: template_id (never row). A template_id's rows all go to the
same split, so no template skeleton leaks across train/val/test. Split is
stratified by attack_family at the template level (each family's templates
are shuffled and cut 70/15/15 independently) so every split gets coverage
of every family, while still respecting the template-disjoint constraint.

Seed: fixed at 42 for reproducibility (matches the checkpoint's original
training seed recorded in training_args.bin, see B3_FINETUNE_PLAN.md).

Output: b3_eval/v25_finetune/data/{train,val,test}_split.jsonl
        schema: {"text": str, "label": 0|1}  (matches b3_eval harness schema)
        plus b3_eval/v25_finetune/data/split_manifest.json with full
        provenance (per-family template counts per split, seed, row counts).
"""
from __future__ import annotations

import collections
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "data" / "stbv_bench" / "v25" / "stbv_bench_v25.jsonl"
OUT_DIR = pathlib.Path(__file__).resolve().parent / "data"
SEED = 42
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}


def main():
    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]

    by_family_templates: dict[str, list[str]] = collections.defaultdict(set)
    rows_by_template: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by_family_templates[r["attack_family"]].add(r["template_id"])
        rows_by_template[r["template_id"]].append(r)

    rng = random.Random(SEED)
    template_split: dict[str, str] = {}
    manifest_families = {}

    for family, tset in sorted(by_family_templates.items()):
        templates = sorted(tset)
        rng.shuffle(templates)
        n = len(templates)
        n_train = round(n * RATIOS["train"])
        n_val = round(n * RATIOS["val"])
        # remainder to test, guarantees every template assigned exactly once
        train_t = templates[:n_train]
        val_t = templates[n_train:n_train + n_val]
        test_t = templates[n_train + n_val:]
        for t in train_t:
            template_split[t] = "train"
        for t in val_t:
            template_split[t] = "val"
        for t in test_t:
            template_split[t] = "test"
        manifest_families[family] = {
            "n_templates": n, "train_templates": len(train_t),
            "val_templates": len(val_t), "test_templates": len(test_t),
        }

    split_rows = {"train": [], "val": [], "test": []}
    for r in rows:
        split_rows[template_split[r["template_id"]]].append(r)

    # sanity: template disjointness
    train_tpl = {r["template_id"] for r in split_rows["train"]}
    val_tpl = {r["template_id"] for r in split_rows["val"]}
    test_tpl = {r["template_id"] for r in split_rows["test"]}
    assert not (train_tpl & val_tpl), "train/val template leakage"
    assert not (train_tpl & test_tpl), "train/test template leakage"
    assert not (val_tpl & test_tpl), "val/test template leakage"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for split, srows in split_rows.items():
        rng.shuffle(srows)
        with open(OUT_DIR / f"{split}_split.jsonl", "w", encoding="utf-8") as f:
            for r in srows:
                f.write(json.dumps({"text": r["text"], "label": int(r["label"])}) + "\n")
        # also keep full-fidelity copy (with family/template) for family-level analysis
        with open(OUT_DIR / f"{split}_split_full.jsonl", "w", encoding="utf-8") as f:
            for r in srows:
                f.write(json.dumps(r) + "\n")

    manifest = {
        "source": str(SRC.relative_to(ROOT)),
        "seed": SEED,
        "ratios": RATIOS,
        "grouping_unit": "template_id",
        "n_rows_total": len(rows),
        "n_templates_total": len(template_split),
        "split_row_counts": {k: len(v) for k, v in split_rows.items()},
        "split_template_counts": {
            "train": len(train_tpl), "val": len(val_tpl), "test": len(test_tpl)
        },
        "template_disjoint_verified": True,
        "per_family": manifest_families,
    }
    (OUT_DIR / "split_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(json.dumps(manifest["split_row_counts"], indent=2))
    print(json.dumps(manifest["split_template_counts"], indent=2))
    print("Template-disjointness verified: OK")
    print(f"Written to {OUT_DIR}")


if __name__ == "__main__":
    main()
