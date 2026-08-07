"""
b3_eval/v25_finetune/build_mixed_corpus.py
============================================
Builds the mixed training corpus (v2.5 + v1) for the mixed-corpus LoRA
retrain. See MIXED_CORPUS_REPORT.md for full rationale/leakage audit.

Source-availability finding (documented, not a shortcut): STBV-Bench v2
(rerun_stbv_v2.py, n_windows=150, ALL windows scored) and the external
semantic corpus (rerun_external_and_cp.py, evaluate_external.py, n=117,
ALL entries scored) are used in their ENTIRETY as evaluation sets in the
prior tasks' methodology -- there is no held-out "unused" portion of
either corpus that could be added to training without contaminating the
benchmark those scripts already report against. Including any row from
either would invalidate the very evaluation this task is supposed to
report. So the mixed corpus is v2.5 (as-is) + a disjoint slice of v1.

v1 leakage avoidance: rerun_paper_ablation.py, recalibrate_v1_collect.py,
and recalibrate_v1_test_rerun.py all draw their samples from
data/stbv_bench/v1/stbv_bench.jsonl[:10000] (first 10,000 rows, the
LIMIT=10000 default everywhere v1 is read). This script therefore only
ever reads rows[10000:] (the remaining 90,000) for training -- disjoint by
construction, no id-level checking needed, but a sample_id intersection
check is run anyway as a hard assertion.

Text synthesis: v1 rows are raw CAM-message dicts, not natural-language
text. Production B3 scores an ensemble of 4 TemplateStyle renderings
(orchestrator.py ~line 505-558); training data (both the original v2.5
corpus and this script) uses a single canonical rendering per row --
TemplateStyle.DEFAULT (the same style A2/B3 have always used as the
"compact key=value" baseline) -- via pipeline.synthesizer.synthesize_message,
called directly (pure-Python, deterministic, no model forward needed).
Label: is_attacker field (falls back to attack_family != "benign_control"),
identical rule to recalibrate_v1_collect.py's b3_only_decision ground truth.

Balance: v2.5 train contributes 8,535 rows. v1 is capped to a comparable
order of magnitude (target ~8,500) via per-family stratified sampling from
rows[10000:], seed 42, so v1's 90,000-row pool doesn't drown out v2.5 in
the mixture (per B3_FINETUNE_PLAN.md-style judgment call, documented here).
"""
from __future__ import annotations

import collections
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.synthesizer import synthesize_message, TemplateStyle  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA  # write alongside existing v2.5 splits, new filenames

V1_BENCH = ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"
V1_EVAL_LIMIT = 10000  # rows [0:V1_EVAL_LIMIT] are reserved for eval scripts; never read for training
V1_TARGET_TOTAL = 8500
SEED = 42


def load_v25_split(name):
    return [json.loads(l) for l in (DATA / f"{name}_split_full.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def load_v1_pool():
    rows = []
    with open(V1_BENCH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < V1_EVAL_LIMIT:
                continue
            rows.append(json.loads(line))
    return rows


def v1_to_training_row(r):
    msg = r["transformed_message"]
    is_attacker = bool(msg.get("is_attacker", r["attack_family"] != "benign_control"))
    synth = synthesize_message([msg], {}, context="urban", template=TemplateStyle.DEFAULT)
    return {
        "text": synth["text"],
        "label": int(is_attacker),
        "source": "v1",
        "attack_family": r["attack_family"],
        "sample_id": r["sample_id"],
    }


def main():
    rng = random.Random(SEED)

    # ---- v2.5: reused as-is ----
    v25_train = load_v25_split("train")
    v25_val = load_v25_split("val")
    v25_train_ids = {r["sample_id"] for r in v25_train}
    v25_val_ids = {r["sample_id"] for r in v25_val}

    # ---- v1: eval-disjoint pool, stratified subsample ----
    v1_pool = load_v1_pool()
    v1_eval_ids = set()
    with open(V1_BENCH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= V1_EVAL_LIMIT:
                break
            v1_eval_ids.add(json.loads(line)["sample_id"])
    pool_ids = {r["sample_id"] for r in v1_pool}
    assert not (pool_ids & v1_eval_ids), "v1 train pool overlaps eval-reserved rows"

    by_family = collections.defaultdict(list)
    for r in v1_pool:
        by_family[r["attack_family"]].append(r)
    n_families = len(by_family)
    per_family_target = max(1, round(V1_TARGET_TOTAL / n_families))

    v1_selected_raw = []
    for fam, rows in sorted(by_family.items()):
        rows_c = list(rows)
        rng.shuffle(rows_c)
        v1_selected_raw.extend(rows_c[:per_family_target])
    rng.shuffle(v1_selected_raw)

    print(f"Synthesizing text for {len(v1_selected_raw)} selected v1 rows...")
    v1_rows = [v1_to_training_row(r) for r in v1_selected_raw]

    # split v1 selection 85/15 train/val (row-level; v1 has no template_id
    # analog -- each row is an independent VeReMi-derived scene/timestamp,
    # so row-level splitting does not create the kind of skeleton-level
    # leakage template_id grouping was designed to prevent in v2.5)
    rng.shuffle(v1_rows)
    n_val = round(len(v1_rows) * 0.15)
    v1_val, v1_train = v1_rows[:n_val], v1_rows[n_val:]

    # ---- assemble mixed splits ----
    def to_plain(rows, source_label):
        out = []
        for r in rows:
            out.append({"text": r["text"], "label": int(r["label"])})
        return out

    v25_train_plain = [{"text": r["text"], "label": int(r["label"])} for r in v25_train]
    v25_val_plain = [{"text": r["text"], "label": int(r["label"])} for r in v25_val]

    mixed_train = v25_train_plain + to_plain(v1_train, "v1")
    mixed_val = v25_val_plain + to_plain(v1_val, "v1")
    rng.shuffle(mixed_train)
    rng.shuffle(mixed_val)

    # exact-text dedup within/across splits
    def texts(rows):
        return {r["text"] for r in rows}
    dup_train_val = texts(mixed_train) & texts(mixed_val)

    with open(OUT / "mixed_train_split.jsonl", "w", encoding="utf-8") as f:
        for r in mixed_train:
            f.write(json.dumps(r) + "\n")
    with open(OUT / "mixed_val_split.jsonl", "w", encoding="utf-8") as f:
        for r in mixed_val:
            f.write(json.dumps(r) + "\n")
    # full-fidelity v1 rows (with ids/family) for the leakage audit + report
    with open(OUT / "mixed_v1_train_full.jsonl", "w", encoding="utf-8") as f:
        for r in v1_train:
            f.write(json.dumps(r) + "\n")
    with open(OUT / "mixed_v1_val_full.jsonl", "w", encoding="utf-8") as f:
        for r in v1_val:
            f.write(json.dumps(r) + "\n")

    manifest = {
        "seed": SEED,
        "v25_train_rows": len(v25_train_plain),
        "v25_val_rows": len(v25_val_plain),
        "v1_pool_available_rows": len(v1_pool),
        "v1_selected_raw_rows": len(v1_selected_raw),
        "v1_train_rows": len(v1_train),
        "v1_val_rows": len(v1_val),
        "v1_per_family_target": per_family_target,
        "v1_families": n_families,
        "mixed_train_total": len(mixed_train),
        "mixed_val_total": len(mixed_val),
        "v1_eval_reserved_rows_excluded": len(v1_eval_ids),
        "v1_pool_eval_overlap_check": "PASS - zero overlap (assert in script)",
        "exact_text_dup_train_val": len(dup_train_val),
        "v2_and_external_excluded_reason": (
            "STBV-Bench v2 (150/150 windows) and the external semantic corpus "
            "(117/117 entries) are used in their ENTIRETY by the prior evaluation "
            "scripts (rerun_stbv_v2.py, rerun_external_and_cp.py) -- no unused "
            "portion exists to add to training without contaminating those "
            "benchmarks. Both are therefore excluded from the mixed training "
            "corpus and remain pure evaluation-only sources."
        ),
    }
    (OUT / "mixed_corpus_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
