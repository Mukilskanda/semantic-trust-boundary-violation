#!/usr/bin/env python3
"""
stbv_bench/build_stbv_bench_v2.py
====================================
Prototype implementation of STBV-Bench v2 (see STBV_BENCH_V2_DESIGN.md):
multi-vehicle, multi-message evaluation windows built from real VeReMi
data, instead of v1's independent single messages. Implements injection
strategies 1-2 from the design doc (single-attacker-in-window,
multi-source collaborative/contradictory); strategies 3-4 (narrative
evolution, progressive poisoning) are specified but not yet implemented,
per the design doc's stated reasoning (limited value building the full
attack surface before the CP wiring bug is fixed and CP can score any of
it -- see VERIFICATION_ADDENDUM.md Sec 4).

Window construction: groups each source VeReMi scenario's flat reports by
1-second timestamp bucket, finds spatial clusters (senders within
--radius meters of each other) within each bucket, and keeps windows
whose cluster has >= --min-cluster distinct senders persisting across
>= --min-buckets consecutive time buckets (real multi-vehicle co-presence
AND real temporal continuity).

Each window is replayed through ONE fresh, persistent ISCEPipeline
instance for its entire duration (never reused across windows), matching
the fresh-per-independent-unit methodology already established for
run_stbv_bench_eval.py and build_and_run_veremi_kinematic_bench.py.

Usage:
  python3 stbv_bench/build_stbv_bench_v2.py \
      --source data/veremi_processed/ConstPos_1416 \
      --n-windows 150 --seed 21 --out results/stbv_bench_v2
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import random
import sys
import time
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stbv_bench.canonical import veremi_report_to_canonical
from stbv_bench.transformations import ALL_RULES
from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

MULTI_SOURCE_FAMILIES = {"collaborative_semantic_agreement", "cross_source_contradiction"}
SINGLE_ATTACKER_RULES = [r for r in ALL_RULES if r.family not in MULTI_SOURCE_FAMILIES
                          and r.family != "benign_control"]
MULTI_SOURCE_RULES = {r.family: r for r in ALL_RULES if r.family in MULTI_SOURCE_FAMILIES}
BENIGN_RULE = next(r for r in ALL_RULES if r.family == "benign_control")


def find_spatial_clusters(records, radius: float, min_cluster: int, min_buckets: int):
    """Groups records by 1s timestamp bucket, finds within-bucket spatial
    clusters (simple greedy: for each record, all others within `radius`
    meters), then keeps (sender-set) clusters whose membership persists
    (>= min_cluster common senders) across >= min_buckets consecutive
    buckets. Returns list of (bucket_start, sender_ids, records_in_window)."""
    by_bucket = defaultdict(list)
    for r in records:
        by_bucket[round(r["timestamp"])].append(r)

    bucket_clusters = {}  # bucket -> best cluster (set of sender ids)
    for tb, recs in by_bucket.items():
        best = set()
        for r in recs:
            nearby = {r2["sender"] for r2 in recs
                      if math.hypot(r["x"] - r2["x"], r["y"] - r2["y"]) < radius}
            if len(nearby) > len(best):
                best = nearby
        if len(best) >= min_cluster:
            bucket_clusters[tb] = best

    sorted_tbs = sorted(bucket_clusters)
    windows = []
    i = 0
    while i < len(sorted_tbs):
        run_tbs = [sorted_tbs[i]]
        common = set(bucket_clusters[sorted_tbs[i]])
        j = i + 1
        while j < len(sorted_tbs) and sorted_tbs[j] == sorted_tbs[j - 1] + 1:
            inter = common & bucket_clusters[sorted_tbs[j]]
            if len(inter) < min_cluster:
                break
            common = inter
            run_tbs.append(sorted_tbs[j])
            j += 1
        if len(run_tbs) >= min_buckets:
            window_recs = [r for r in records
                            if round(r["timestamp"]) in run_tbs and r["sender"] in common]
            windows.append((run_tbs[0], sorted(common), window_recs))
            i = j if j > i + 1 else i + 1
        else:
            i += 1
    return windows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, nargs="+")
    ap.add_argument("--n-windows", type=int, default=150)
    ap.add_argument("--radius", type=float, default=100.0)
    ap.add_argument("--min-cluster", type=int, default=3)
    ap.add_argument("--min-buckets", type=int, default=2)
    ap.add_argument("--benign-fraction", type=float, default=0.30)
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)

    all_windows = []
    for src in args.source:
        src_path = pathlib.Path(src)
        f = src_path / "veremi_flat_reports.json"
        records = json.loads(f.read_text())
        clusters = find_spatial_clusters(records, args.radius, args.min_cluster, args.min_buckets)
        for tb, senders, recs in clusters:
            all_windows.append((src_path.name, tb, senders, recs))
    print(f"[cluster] found {len(all_windows)} eligible multi-vehicle windows "
          f"across {len(args.source)} source(s) (radius={args.radius}m, "
          f"min_cluster={args.min_cluster}, min_buckets={args.min_buckets})")

    if args.n_windows > len(all_windows):
        print(f"[warn] requested {args.n_windows} windows but only {len(all_windows)} "
              f"eligible -- using all of them")
        args.n_windows = len(all_windows)
    chosen = rng.sample(all_windows, args.n_windows)

    n_benign = round(args.n_windows * args.benign_fraction)
    n_attack = args.n_windows - n_benign
    single_cycle = SINGLE_ATTACKER_RULES[:]
    rng.shuffle(single_cycle)
    multi_families = list(MULTI_SOURCE_RULES)
    assignments = ["benign_control"] * n_benign
    for i in range(n_attack):
        # 70% single-attacker-in-window, 30% multi-source (2 families available)
        if rng.random() < 0.7:
            assignments.append(single_cycle[i % len(single_cycle)].family)
        else:
            assignments.append(multi_families[i % len(multi_families)])
    rng.shuffle(assignments)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    windows_meta = []
    for wi, ((source_name, tb, senders, recs), family) in enumerate(zip(chosen, assignments)):
        window_seed = args.seed * 1_000_003 + wi
        wrng = random.Random(window_seed)
        by_sender = defaultdict(list)
        for r in recs:
            by_sender[r["sender"]].append(r)
        for s in by_sender:
            by_sender[s].sort(key=lambda r: r["timestamp"])

        strategy = "none"
        attacker_senders = []
        payload_by_sender = {}

        if family != "benign_control":
            if family in MULTI_SOURCE_RULES:
                strategy = "multi_source_collaborative_or_contradictory"
                rule = MULTI_SOURCE_RULES[family]
                k = min(len(senders), wrng.randint(2, 3))
                attacker_senders = wrng.sample(senders, k)
                if family == "collaborative_semantic_agreement":
                    shared_text = rule.render(wrng)
                    for s in attacker_senders:
                        payload_by_sender[s] = shared_text
                else:  # cross_source_contradiction: each attacker gets its OWN variant
                    for s in attacker_senders:
                        payload_by_sender[s] = rule.render(wrng)
                rule_used = rule
            else:
                strategy = "single_attacker_in_window"
                rule = next(r for r in single_cycle if r.family == family)
                attacker_senders = [wrng.choice(senders)]
                payload_by_sender[attacker_senders[0]] = rule.render(wrng)
                rule_used = rule
        else:
            rule_used = BENIGN_RULE

        messages = []
        for s in senders:
            for r in by_sender[s]:
                msg = veremi_report_to_canonical(r, station_id=int(s), station_type=5)
                if s in payload_by_sender:
                    text = payload_by_sender[s]
                    if rule_used.inject_as in ("peer", "both"):
                        msg["scene_context"]["peer_reports"].append(text)
                    if rule_used.inject_as in ("rsu", "both"):
                        msg["scene_context"]["rsu_messages"].append(text)
                msg["_window_sender"] = s
                msg["_window_is_attacker_sender"] = s in attacker_senders
                messages.append(msg)
        messages.sort(key=lambda m: m["cam"]["generation_delta_time"])

        windows_meta.append({
            "window_id": f"stbv2-{wi:05d}",
            "source_dataset": source_name,
            "cluster_senders": senders,
            "attacker_senders": attacker_senders,
            "attack_family": family,
            "injection_strategy": strategy,
            "transformation_rule": rule_used.transformation_rule,
            "semantic_objective": rule_used.semantic_objective,
            "expected_trust_layer": rule_used.expected_trust_layer,
            "expected_decision": rule_used.expected_decision,
            "severity": rule_used.severity,
            "seed": window_seed,
            "n_messages": len(messages),
            "messages": messages,
        })

    windows_path = out_dir / "stbv_bench_v2_windows.jsonl"
    with windows_path.open("w", encoding="utf-8") as f:
        for w in windows_meta:
            f.write(json.dumps(w) + "\n")
    manifest = {
        "benchmark": "STBV-Bench-v2", "version": "2.0.0-prototype",
        "seed": args.seed, "n_windows": len(windows_meta),
        "n_eligible_windows_found": len(all_windows),
        "attack_family_counts": {f: assignments.count(f) for f in set(assignments)},
        "radius_m": args.radius, "min_cluster": args.min_cluster, "min_buckets": args.min_buckets,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[build] {len(windows_meta)} windows written -> {windows_path}")
    print(f"        family counts: {manifest['attack_family_counts']}")

    # --- Evaluate: replay each window through a fresh, persistent pipeline ---
    rows = []
    t_start = time.perf_counter()
    for wi, w in enumerate(windows_meta):
        pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
        window_msgs = []
        for m in w["messages"]:
            window_msgs.append({k: v for k, v in m.items() if not k.startswith("_window")})
            res = pipeline.run(list(window_msgs), context="urban")
            target_is_attacker = m.get("_window_is_attacker_sender", False)
            rows.append({
                "window_id": w["window_id"], "attack_family": w["attack_family"],
                "injection_strategy": w["injection_strategy"],
                "sender": m.get("_window_sender"), "is_attacker_sender": target_is_attacker,
                "decision": res["decision"], "trust_score": res["fusion"].get("trust_score"),
                "contributors": ",".join(res["fusion"].get("contributors", [])),
                "cp_num_reports": (res.get("cp") or {}).get("num_reports"),
                "cp_confidence": (res.get("cp") or {}).get("cp_confidence"),
            })
        if (wi + 1) % 25 == 0:
            elapsed = time.perf_counter() - t_start
            print(f"  {wi + 1}/{len(windows_meta)} windows evaluated ({elapsed:.0f}s elapsed)", flush=True)

    with (out_dir / "stbv_bench_v2_per_message.csv").open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(rows)

    total_s = time.perf_counter() - t_start
    print(f"\n[done] {len(windows_meta)} windows, {len(rows)} messages evaluated in {total_s:.1f}s")
    print(f"-> {out_dir / 'stbv_bench_v2_per_message.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
