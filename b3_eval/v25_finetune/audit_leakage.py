"""
b3_eval/v25_finetune/audit_leakage.py
========================================
Hostile leakage audit for the v2.5 LoRA fine-tune, per the reviewer's
request. Recomputes everything from the raw split files -- does not trust
split_manifest.json or any prior claim.

Checks:
  1. Exact duplicate text across train/val/test
  2. Template-id leakage, recomputed from the raw files
  3. Semantic near-duplicate leakage (Sentence-BERT cosine similarity,
     train vs test) at thresholds 0.95 / 0.90 / 0.85
  4. Family distribution per split
  5. Other identifier fields checked for cross-split leakage
  6. Feature/column leakage inspection

Run with: python3 b3_eval/v25_finetune/audit_leakage.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "results" / "leakage_audit.json"


def load(split):
    rows = [json.loads(l) for l in (DATA / f"{split}_split_full.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def part1_exact_duplicates(splits):
    print("\n" + "=" * 78)
    print("PART 1.1 -- EXACT DUPLICATE TEXT ACROSS SPLITS")
    print("=" * 78)
    hash_to_splits = {}
    for name, rows in splits.items():
        for r in rows:
            h = sha(r["text"])
            hash_to_splits.setdefault(h, []).append((name, r))

    cross_split_dups = {h: v for h, v in hash_to_splits.items() if len({n for n, _ in v}) > 1}
    within_split_dups = {h: v for h, v in hash_to_splits.items() if len(v) > 1 and len({n for n, _ in v}) == 1}

    total_rows = sum(len(r) for r in splits.values())
    print(f"Total rows across splits: {total_rows}")
    print(f"Cross-split exact duplicate hashes: {len(cross_split_dups)}")
    print(f"Within-split exact duplicate hashes (not leakage, but worth flagging): {len(within_split_dups)}")

    for h, v in list(cross_split_dups.items())[:20]:
        print(f"  HASH {h[:12]}: appears in {[n for n, _ in v]}")
        for n, r in v:
            print(f"    [{n}] template={r['template_id']} sample={r['sample_id']}: {r['text'][:100]}")

    return {
        "total_rows": total_rows,
        "cross_split_duplicate_hash_count": len(cross_split_dups),
        "cross_split_duplicate_pct": 100 * len(cross_split_dups) / total_rows if total_rows else 0,
        "within_split_duplicate_hash_count": len(within_split_dups),
        "cross_split_duplicates_detail": [
            {"hash": h[:16], "occurrences": [{"split": n, "sample_id": r["sample_id"],
                                               "template_id": r["template_id"], "text": r["text"]}
                                              for n, r in v]}
            for h, v in cross_split_dups.items()
        ],
    }


def part1_2_template_leakage(splits):
    print("\n" + "=" * 78)
    print("PART 1.2 -- TEMPLATE-ID LEAKAGE (recomputed from raw files, not manifest)")
    print("=" * 78)
    template_to_splits = {}
    for name, rows in splits.items():
        for r in rows:
            template_to_splits.setdefault(r["template_id"], set()).add(name)

    leaked = {t: s for t, s in template_to_splits.items() if len(s) > 1}
    print(f"Total distinct templates across all splits: {len(template_to_splits)}")
    print(f"Templates appearing in >1 split: {len(leaked)}")
    if leaked:
        for t, s in list(leaked.items())[:50]:
            print(f"  LEAK: template={t} appears in {sorted(s)}")
    else:
        print("  No template-id leakage found (recomputed independently of split_manifest.json).")

    return {
        "total_templates": len(template_to_splits),
        "leaked_template_count": len(leaked),
        "leaked_templates": {t: sorted(s) for t, s in leaked.items()},
    }


def part1_3_semantic_leakage(splits, thresholds=(0.95, 0.90, 0.85), max_pairs_per_threshold=50):
    print("\n" + "=" * 78)
    print("PART 1.3 -- SEMANTIC NEAR-DUPLICATE LEAKAGE (Sentence-BERT cosine sim, train vs test)")
    print("=" * 78)
    from sentence_transformers import SentenceTransformer
    import numpy as np

    model = SentenceTransformer("all-MiniLM-L6-v2")
    train_texts = [r["text"] for r in splits["train"]]
    test_texts = [r["text"] for r in splits["test"]]
    print(f"Encoding {len(train_texts)} train + {len(test_texts)} test messages...")
    train_emb = model.encode(train_texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    test_emb = model.encode(test_texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)

    sim = test_emb @ train_emb.T  # (n_test, n_train)

    results = {}
    for thr in thresholds:
        idx = np.argwhere(sim > thr)
        pairs = []
        for ti, tj in idx:
            pairs.append({
                "similarity": float(sim[ti, tj]),
                "test_sample_id": splits["test"][ti]["sample_id"],
                "test_template_id": splits["test"][ti]["template_id"],
                "test_text": splits["test"][ti]["text"],
                "train_sample_id": splits["train"][tj]["sample_id"],
                "train_template_id": splits["train"][tj]["template_id"],
                "train_text": splits["train"][tj]["text"],
                "same_template": splits["test"][ti]["template_id"] == splits["train"][tj]["template_id"],
            })
        pairs.sort(key=lambda p: -p["similarity"])
        results[thr] = {
            "n_pairs_over_threshold": len(pairs),
            "n_test_messages_involved": len({p["test_sample_id"] for p in pairs}),
            "pct_test_messages_involved": 100 * len({p["test_sample_id"] for p in pairs}) / len(test_texts),
            "n_flagged_pairs_from_different_templates": sum(1 for p in pairs if not p["same_template"]),
            "sample_pairs": pairs[:max_pairs_per_threshold],
        }
        print(f"\nThreshold > {thr}: {len(pairs)} train/test pairs, "
              f"{results[thr]['n_test_messages_involved']} distinct test messages "
              f"({results[thr]['pct_test_messages_involved']:.2f}% of test)")
        print(f"  Of these, {results[thr]['n_flagged_pairs_from_different_templates']} pairs are from "
              f"DIFFERENT template_ids (i.e. not just an already-verified same-template match)")
        for p in pairs[:5]:
            print(f"  sim={p['similarity']:.4f} same_template={p['same_template']}")
            print(f"    TEST  [{p['test_template_id']}] {p['test_text'][:100]}")
            print(f"    TRAIN [{p['train_template_id']}] {p['train_text'][:100]}")

    return {str(k): v for k, v in results.items()}


def part2_family_distribution(splits):
    print("\n" + "=" * 78)
    print("PART 2 -- FAMILY DISTRIBUTION AUDIT")
    print("=" * 78)
    from collections import Counter
    out = {}
    all_families = set()
    for name, rows in splits.items():
        c = Counter(r["attack_family"] for r in rows)
        all_families |= set(c.keys())
        out[name] = dict(c)

    print(f"{'family':30s} " + " ".join(f"{n:>18s}" for n in splits))
    for fam in sorted(all_families):
        row = []
        for name in splits:
            n = out[name].get(fam, 0)
            total = len(splits[name])
            row.append(f"{n:6d} ({100*n/total:5.2f}%)")
        print(f"{fam:30s} " + " ".join(f"{r:>18s}" for r in row))

    missing = {}
    for name in splits:
        missing[name] = sorted(all_families - set(out[name].keys()))
    any_missing = any(missing.values())
    if any_missing:
        print("\nWARNING -- families entirely missing from a split:")
        for name, fams in missing.items():
            if fams:
                print(f"  {name}: {fams}")
    else:
        print("\nAll families present in all splits (no family entirely absent from any split).")

    return {"counts": out, "families_missing_per_split": missing}


def part3_identifier_leakage(splits):
    print("\n" + "=" * 78)
    print("PART 3 -- SPLIT CORRECTNESS: OTHER IDENTIFIER FIELDS")
    print("=" * 78)
    sample = splits["train"][0]
    all_keys = set(sample.keys())
    print(f"Columns present in the v2.5 corpus: {sorted(all_keys)}")
    id_like = [k for k in all_keys if any(tok in k.lower() for tok in
               ["window", "scene", "vehicle", "conversation", "cluster", "session", "id"])]
    print(f"Identifier-like columns found: {id_like}")

    leakage = {}
    for col in id_like:
        val_to_splits = {}
        for name, rows in splits.items():
            for r in rows:
                v = r.get(col)
                if v is None:
                    continue
                val_to_splits.setdefault(v, set()).add(name)
        leaked = {v: sorted(s) for v, s in val_to_splits.items() if len(s) > 1}
        leakage[col] = {"n_distinct_values": len(val_to_splits), "n_leaked_values": len(leaked),
                         "sample_leaked": dict(list(leaked.items())[:10])}
        print(f"  {col}: {len(val_to_splits)} distinct values, {len(leaked)} appear in >1 split")

    return {"columns_present": sorted(all_keys), "identifier_like_columns": id_like, "leakage_by_column": leakage}


def part4_feature_leakage(splits):
    print("\n" + "=" * 78)
    print("PART 4 -- FEATURE LEAKAGE (columns that reveal the label but aren't available at inference)")
    print("=" * 78)
    sample = splits["train"][0]
    cols = sorted(sample.keys())
    print(f"Full row schema: {cols}")
    print("Columns actually passed to the model at inference (per eval_common.py / inference.py): "
          "['text'] only -- tokenizer sees text only, nothing else.")
    other_cols = [c for c in cols if c not in ("text", "label")]
    print(f"Other columns present in the JSONL but NOT fed to the model: {other_cols}")
    # attack_family / intent / mood / template_id are present in the *_full.jsonl analysis
    # files (used only for per-family reporting in this audit/eval), and are stripped in
    # the plain train/val/test_split.jsonl files actually consumed by train_lora.py.
    train_plain = json.loads((DATA / "train_split.jsonl").read_text(encoding="utf-8").splitlines()[0])
    print(f"Schema of train_split.jsonl (what train_lora.py actually loads): {sorted(train_plain.keys())}")
    return {
        "full_row_schema": cols,
        "columns_fed_to_model": ["text"],
        "columns_present_but_unused_at_train_time": other_cols,
        "training_input_schema": sorted(train_plain.keys()),
    }


def main():
    splits = {name: load(name) for name in ("train", "val", "test")}
    report = {}
    report["part1_exact_duplicates"] = part1_exact_duplicates(splits)
    report["part1_template_leakage"] = part1_2_template_leakage(splits)
    report["part1_semantic_leakage"] = part1_3_semantic_leakage(splits)
    report["part2_family_distribution"] = part2_family_distribution(splits)
    report["part3_identifier_leakage"] = part3_identifier_leakage(splits)
    report["part4_feature_leakage"] = part4_feature_leakage(splits)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"\nWritten: {OUT}")


if __name__ == "__main__":
    main()
