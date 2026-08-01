#!/usr/bin/env python3
"""
build_backbone_dataset.py
============================
Builds ONE identical dataset (text, label, attack_family) for the
backbone comparison, sourced from this paper's own canonical STBV-Bench
v1 corpus (data/stbv_bench/v1/stbv_bench.jsonl, the same generator behind
every STBV-Bench headline number in this paper) -- not the deprecated,
leakage-flagged 120-scenario corpus, and not a from-scratch generator.

Text is produced by calling pipeline.synthesizer.synthesize_message()
directly on each sample's already-generated transformed_message -- the
SAME function that renders the text B3 classifies in the real pipeline
(pipeline/orchestrator.py's call site). b2_result is passed as {} because
synthesize_message's own docstring states it is accepted for API
stability but never read inside the function (verified: zero references
to b2_result in its body) -- this is a cheap, honest way to get identical
text without paying for a full B1/MBD/CP/B3 pipeline run per sample,
since only the text is needed for this comparison, not a trust decision.

Stratified, seeded, class-family-balanced sampling (40 per family x 21
families) avoids the natural corpus's 30%-benign/3.5%-per-family
imbalance, for the same reason export_semantic_split.py already balances
its own split (a trivial always-predict-majority classifier would
otherwise score deceptively high F1, per that script's own documented
rationale) -- reusing an already-established methodology in this repo,
not inventing a new one.
"""
import json, pathlib, random, sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.synthesizer import synthesize_message

HERE = pathlib.Path(__file__).resolve().parent
BENCH = ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"
SEED = 20260805
N_PER_FAMILY = 40
TEST_FRAC = 0.2


def main():
    by_family = defaultdict(list)
    with BENCH.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            by_family[r["attack_family"]].append(r)

    rng = random.Random(SEED)
    train_rows, test_rows = [], []
    family_counts = {}
    n_malicious_families = sum(1 for fam in by_family if fam != "benign_control")
    # benign_control gets N_PER_FAMILY * n_malicious_families samples, so the
    # overall corpus is class-balanced (50/50 malicious/benign) even though
    # each individual malicious family is still evenly represented at
    # N_PER_FAMILY -- avoids the trivial-always-malicious-predictor problem
    # export_semantic_split.py already documented on the natural (~95%
    # malicious) family-only-balanced alternative.
    for fam, rows in sorted(by_family.items()):
        rows = rows[:]
        rng.shuffle(rows)
        n_pick = N_PER_FAMILY * n_malicious_families if fam == "benign_control" else N_PER_FAMILY
        picked = rows[:n_pick]
        family_counts[fam] = len(picked)
        n_test = max(1, int(round(len(picked) * TEST_FRAC)))
        test_slice, train_slice = picked[:n_test], picked[n_test:]

        for r in train_slice + test_slice:
            msg = r["transformed_message"]
            synth = synthesize_message([msg], {}, context=None)
            text = synth["text"]
            label = 1 if msg["expected_label"] == "MALICIOUS" else 0
            row = {"text": text, "label": label, "attack_family": fam,
                   "sample_id": r["sample_id"]}
            (test_rows if r in test_slice else train_rows).append(row)

    rng.shuffle(train_rows)
    rng.shuffle(test_rows)

    out_dir = HERE / "data"
    out_dir.mkdir(exist_ok=True)
    with (out_dir / "train.jsonl").open("w", encoding="utf-8") as f:
        for r in train_rows:
            f.write(json.dumps(r) + "\n")
    with (out_dir / "test.jsonl").open("w", encoding="utf-8") as f:
        for r in test_rows:
            f.write(json.dumps(r) + "\n")

    manifest = {
        "source": str(BENCH),
        "seed": SEED,
        "n_per_family": N_PER_FAMILY,
        "test_frac": TEST_FRAC,
        "n_families": len(family_counts),
        "family_counts_sampled": family_counts,
        "n_train": len(train_rows),
        "n_test": len(test_rows),
        "n_train_malicious": sum(r["label"] for r in train_rows),
        "n_test_malicious": sum(r["label"] for r in test_rows),
        "note": "Text produced by pipeline.synthesizer.synthesize_message() "
                "directly on stbv_bench.jsonl's transformed_message field "
                "(b2_result={} -- never read by that function). Same text "
                "B3 classifies in the real pipeline.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
