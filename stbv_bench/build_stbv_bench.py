#!/usr/bin/env python3
"""
stbv_bench/build_stbv_bench.py
================================
Top-level, reproducible, parameterized, versioned CLI driver for the full
STBV-Bench pipeline:

    Standard Public Dataset (VeReMi Extension flat reports)
        -> Canonical Message Representation   (stbv_bench/canonical.py)
        -> Semantic Transformation Engine      (stbv_bench/transformations.py)
        -> Semantic Validation                 (generator.py's assertions)
        -> STBV Attack Injection                (generator.py's payload write)
        -> Benchmark Validation                 (this script's schema check, §3)
        -> Final STBV-Bench                     (data/stbv_bench/<version>/)

HONESTY CONTRACT (matching this repo's existing evaluation-framework
convention -- see evaluation/, b3_eval/, semantic_evaluation/):
  - Every generated message's kinematics come from a REAL VeReMi Extension
    record; nothing about position/speed/heading is invented.
  - VeReMi's own kinematic attack labels are NEVER relabelled as STBV
    attacks. STBV-Bench's attack_family/is_attacker fields describe ONLY
    whether a semantic transformation was applied; VeReMi's kinematic
    ground truth is preserved separately as `_veremi_provenance`.
  - Everything is seeded: the same --seed always produces the same
    (source-record, attack-family) assignment and the same rendered text.
  - This script does NOT run the messages through the trust pipeline --
    that is a deliberately separate, explicit step (see
    stbv_bench/run_stbv_bench_eval.py) so "building the benchmark" and
    "evaluating a system against it" stay decoupled, the way a real
    benchmark should be.

Usage:
  python3 stbv_bench/build_stbv_bench.py \
      --source data/veremi_processed/ConstPos_1416 \
      --n 3000 --seed 7 --benign-fraction 0.30 \
      --out data/stbv_bench/v1
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

from stbv_bench.generator import generate_sample
from stbv_bench.transformations import ALL_RULES

STBV_BENCH_VERSION = "1.0.0"


def load_veremi_reports(source_dir: pathlib.Path):
    f = source_dir / "veremi_flat_reports.json"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} not found -- run import_veremi.py first, or point --source "
            f"at an existing data/veremi_processed/<name>/ directory."
        )
    return json.loads(f.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, nargs="+",
                     help="One or more data/veremi_processed/<name>/ directories to draw real kinematics from")
    ap.add_argument("--n", type=int, default=2000, help="Total number of STBV-Bench samples to generate")
    ap.add_argument("--seed", type=int, default=7, help="Master RNG seed (fully reproducible)")
    ap.add_argument("--benign-fraction", type=float, default=0.30,
                     help="Fraction of samples assigned the benign_control rule (negative controls)")
    ap.add_argument("--out", required=True, help="Output directory, e.g. data/stbv_bench/v1")
    args = ap.parse_args()

    master_rng = random.Random(args.seed)

    # --- Load real source records from every requested VeReMi directory ---
    pool = []
    for src in args.source:
        src_path = pathlib.Path(src)
        reports = load_veremi_reports(src_path)
        dataset_label = f"VeReMi Extension / {src_path.name}"
        for r in reports:
            pool.append((dataset_label, r))
    if not pool:
        print("[error] no source records loaded", file=sys.stderr)
        return 1
    if args.n > len(pool):
        print(f"[error] requested --n {args.n} exceeds available source pool "
              f"({len(pool)} records across {len(args.source)} source(s)). "
              f"Add more --source directories or reduce --n.", file=sys.stderr)
        return 1

    # --- Deterministic sampling (without replacement) of source records ---
    chosen_idx = master_rng.sample(range(len(pool)), args.n)

    # --- Deterministic attack-family assignment ---
    attack_rules = [r for r in ALL_RULES if r.family != "benign_control"]
    benign_rule = next(r for r in ALL_RULES if r.family == "benign_control")
    n_benign = round(args.n * args.benign_fraction)
    n_attack = args.n - n_benign
    # Evenly distribute attack samples across all non-benign families
    # (round-robin over a shuffled family order, seeded, so no single
    # family systematically lands on any particular subset of records).
    family_cycle = attack_rules[:]
    master_rng.shuffle(family_cycle)
    assignments = [benign_rule] * n_benign
    for i in range(n_attack):
        assignments.append(family_cycle[i % len(family_cycle)])
    master_rng.shuffle(assignments)  # interleave benign/attack, seeded

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples_path = out_dir / "stbv_bench.jsonl"
    family_counts: Counter = Counter()

    with samples_path.open("w", encoding="utf-8") as f:
        for i, (record_idx, rule) in enumerate(zip(chosen_idx, assignments)):
            dataset_label, veremi_report = pool[record_idx]
            per_sample_seed = args.seed * 1_000_003 + i  # deterministic, unique per sample
            station_id = 20000 + i
            sample = generate_sample(
                veremi_report, rule,
                sample_id=f"stbv-{i:06d}",
                source_dataset=dataset_label,
                seed=per_sample_seed,
                station_id=station_id,
            )
            f.write(json.dumps(sample.to_dict()) + "\n")
            family_counts[rule.family] += 1

    # --- Benchmark Validation (Step 6): schema + metadata completeness ---
    required_keys = {
        "sample_id", "source_dataset", "original_message", "transformed_message",
        "attack_family", "transformation_rule", "semantic_objective",
        "expected_trust_layer", "expected_decision", "severity", "seed",
    }
    validated = 0
    with samples_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            missing = required_keys - set(row.keys())
            if missing:
                print(f"[FAIL] benchmark validation: sample missing keys {missing}", file=sys.stderr)
                return 1
            validated += 1

    manifest = {
        "benchmark": "STBV-Bench",
        "version": STBV_BENCH_VERSION,
        "seed": args.seed,
        "n_samples": args.n,
        "n_validated": validated,
        "benign_fraction_requested": args.benign_fraction,
        "source_datasets": args.source,
        "source_pool_size": len(pool),
        "attack_family_counts": dict(family_counts),
        "n_attack_families": len(attack_rules),
        "not_a_relabeling_of_veremi_attacks": (
            "attack_family/is_attacker describe ONLY the semantic transformation "
            "applied here; VeReMi's own kinematic attacker labels are preserved "
            "unchanged under transformed_message._veremi_provenance.veremi_is_attacker "
            "and are never conflated with STBV-Bench's own labels."
        ),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"[done] STBV-Bench v{STBV_BENCH_VERSION}: {validated}/{args.n} samples validated")
    print(f"       attack family distribution: {dict(family_counts)}")
    print(f"       -> {samples_path}")
    print(f"       -> {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
