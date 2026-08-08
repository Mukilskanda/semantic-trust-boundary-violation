"""
b3_eval/v25_finetune/audit_hardmine_leakage.py
=================================================
Hostile leakage audit for the new hand-authored hard-example batch
(data/hardmine_v1_raw.jsonl, 110 rows targeting the real FN clusters
mined from b3_eval/v25_finetune/ablation_results/v25b_full/
direct_classifier_pmalicious.csv: sensor_discreditation, goal_manipulation,
traffic_efficiency_lure, narrative_poisoning, role_confusion,
false_clearance, plus benign counter-examples for the FP cluster).

Checks the new batch against every existing corpus (v2.5 train/val/test,
v2.5b held-out eval, v2.5c training augmentation) for:
  1. Exact duplicate text
  2. Semantic near-duplicate (Sentence-BERT cosine similarity) vs v2.5b
     specifically, since v2.5b must remain a clean held-out set -- any new
     training example too similar to a v2.5b sample would contaminate the
     benchmark this paper reports as primary.
"""
from __future__ import annotations
import hashlib, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
NEW_BATCH = HERE / "data" / "hardmine_v1_raw.jsonl"
OUT = HERE / "results" / "hardmine_leakage_audit.json"


def load_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def main():
    new_rows = load_jsonl(NEW_BATCH)
    print(f"[hardmine-audit] {len(new_rows)} new rows")

    corpora = {
        "v25b_eval": ROOT / "data" / "stbv_bench" / "v25b" / "stbv_bench_v25b.jsonl",
        "v25c_train_aug": ROOT / "data" / "stbv_bench" / "v25c" / "stbv_bench_v25c.jsonl",
    }
    v25_dir = HERE / "data"
    for name in ("train_split_full", "val_split_full", "test_split_full", "mixed_train_split", "mixed_val_split"):
        p = v25_dir / f"{name}.jsonl"
        if p.exists():
            corpora[name] = p

    corpus_texts = {}
    for name, path in corpora.items():
        rows = load_jsonl(path)
        corpus_texts[name] = {r["text"] for r in rows}
        print(f"  loaded {name}: {len(rows)} rows")

    new_hashes = {sha(r["text"]): r for r in new_rows}
    report = {"n_new_rows": len(new_rows), "exact_duplicates": {}, "near_duplicates_vs_v25b": []}

    total_exact = 0
    for name, texts in corpus_texts.items():
        dups = [r for r in new_rows if r["text"] in texts]
        report["exact_duplicates"][name] = len(dups)
        total_exact += len(dups)
        print(f"  exact-duplicate check vs {name}: {len(dups)} collisions")

    from sentence_transformers import SentenceTransformer
    import numpy as np

    model = SentenceTransformer("all-MiniLM-L6-v2")
    new_texts = [r["text"] for r in new_rows]
    v25b_rows = load_jsonl(corpora["v25b_eval"])
    v25b_texts = [r["text"] for r in v25b_rows]

    new_emb = model.encode(new_texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    v25b_emb = model.encode(v25b_texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    sim = new_emb @ v25b_emb.T

    thr = 0.90
    idx = np.argwhere(sim > thr)
    pairs = []
    for i, j in idx:
        pairs.append({
            "similarity": float(sim[i, j]),
            "new_text": new_rows[i]["text"],
            "v25b_text": v25b_rows[j]["text"],
            "v25b_sample_id": v25b_rows[j].get("sample_id"),
        })
    pairs.sort(key=lambda p: -p["similarity"])
    report["near_duplicates_vs_v25b"] = pairs
    report["near_duplicate_threshold"] = thr
    report["n_near_duplicates_vs_v25b"] = len(pairs)

    print(f"\nExact duplicates across all corpora: {total_exact}")
    print(f"Near-duplicates (cosine > {thr}) vs v2.5b (the held-out benchmark): {len(pairs)}")
    for p in pairs[:10]:
        print(f"  sim={p['similarity']:.3f}")
        print(f"    NEW : {p['new_text'][:100]}")
        print(f"    V25B: {p['v25b_text'][:100]}")

    report["verdict"] = "CLEAN" if total_exact == 0 and len(pairs) == 0 else "LEAKAGE DETECTED -- do not train on this batch as-is"
    print(f"\nVERDICT: {report['verdict']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"[ok] {OUT}")


if __name__ == "__main__":
    main()
