#!/usr/bin/env python3
"""
stbv_bench/build_mixed_threat_bench.py
=========================================
Task 3: a mixed-threat benchmark combining semantic, kinematic, and
(pending the CP fix) cooperative-perception threats IN THE SAME shared
multi-vehicle scene, to measure how layers interact and complement each
other -- not just how each behaves on a threat-class-pure benchmark.

Built directly on top of STBV-Bench v2's window construction
(stbv_bench/build_stbv_bench_v2.py's find_spatial_clusters, reused not
duplicated): for each real multi-vehicle spatial-temporal cluster, this
script checks whether the cluster ALREADY contains a real VeReMi
kinematic attacker (constant-position falsification / data replay / DoS,
per whichever --source scenario is used, ground truth is VeReMi's own
is_attacker -- untouched, unmodified, exactly per DATASET_INTEGRATION.md's
honesty contract) among its real members. If so, that vehicle is left
exactly as-is (a genuine kinematic threat, no synthetic content).
Independently, a DIFFERENT real-benign cluster member is (with
probability --semantic-injection-rate) assigned a semantic transformation
payload from stbv_bench/transformations.py, exactly as v1/v2 already do.

This produces four possible per-window threat compositions, all
observable in the output:
  - clean:              no kinematic attacker, no semantic injection
  - kinematic-only:      real VeReMi attacker present, no semantic injection
  - semantic-only:       no real kinematic attacker, semantic injection applied
  - mixed:               BOTH a real kinematic attacker AND a semantic
                          injection, on two DIFFERENT vehicles in the same
                          shared scene -- the case Task 3 specifically asks
                          for ("how do all layers interact").

Each window is evaluated once with the full stack (B1+B2+CP+B3+TrustEngine),
and per-message `fusion.contributors` is recorded so that, for the mixed
windows specifically, it is possible to see directly whether B3 catches
the semantic vehicle, MBD catches the kinematic vehicle, and whether
either one's detection affects the other's (cross-vehicle interaction,
via CP once its fix lands, or via any other coupling the real pipeline
exhibits).

Usage:
  python3 stbv_bench/build_mixed_threat_bench.py \
      --source data/veremi_processed/ConstPos_1416 \
      --n-windows 120 --seed 31 --out results/mixed_threat
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import sys
import time
from collections import defaultdict, Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stbv_bench.canonical import veremi_report_to_canonical
from stbv_bench.transformations import ALL_RULES
from stbv_bench.build_stbv_bench_v2 import find_spatial_clusters, SINGLE_ATTACKER_RULES
from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, nargs="+")
    ap.add_argument("--n-windows", type=int, default=120)
    ap.add_argument("--radius", type=float, default=100.0)
    ap.add_argument("--min-cluster", type=int, default=3)
    ap.add_argument("--min-buckets", type=int, default=2)
    ap.add_argument("--semantic-injection-rate", type=float, default=0.6,
                     help="probability a window additionally gets a semantic injection "
                          "on a real-benign member, independent of whether it already "
                          "has a real kinematic attacker")
    ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)

    all_windows = []
    for src in args.source:
        src_path = pathlib.Path(src)
        records = json.loads((src_path / "veremi_flat_reports.json").read_text())
        clusters = find_spatial_clusters(records, args.radius, args.min_cluster, args.min_buckets)
        for tb, senders, recs in clusters:
            all_windows.append((src_path.name, tb, senders, recs))
    print(f"[cluster] {len(all_windows)} eligible windows found")

    if args.n_windows > len(all_windows):
        args.n_windows = len(all_windows)
    chosen = rng.sample(all_windows, args.n_windows)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    windows_meta = []
    for wi, (source_name, tb, senders, recs) in enumerate(chosen):
        window_seed = args.seed * 1_000_003 + wi
        wrng = random.Random(window_seed)
        by_sender = defaultdict(list)
        for r in recs:
            by_sender[r["sender"]].append(r)
        for s in by_sender:
            by_sender[s].sort(key=lambda r: r["timestamp"])

        kinematic_attacker_senders = [
            s for s in senders if any(r.get("is_attacker") for r in by_sender[s])
        ]
        benign_senders = [s for s in senders if s not in kinematic_attacker_senders]

        semantic_attacker_sender = None
        rule_used = None
        if benign_senders and wrng.random() < args.semantic_injection_rate:
            semantic_attacker_sender = wrng.choice(benign_senders)
            rule_used = wrng.choice(SINGLE_ATTACKER_RULES)

        if kinematic_attacker_senders and semantic_attacker_sender is not None:
            composition = "mixed"
        elif kinematic_attacker_senders:
            composition = "kinematic_only"
        elif semantic_attacker_sender is not None:
            composition = "semantic_only"
        else:
            composition = "clean"

        payload_text = rule_used.render(wrng) if rule_used is not None else None

        messages = []
        for s in senders:
            for r in by_sender[s]:
                msg = veremi_report_to_canonical(r, station_id=int(s), station_type=5)
                if s == semantic_attacker_sender and payload_text is not None:
                    if rule_used.inject_as in ("peer", "both"):
                        msg["scene_context"]["peer_reports"].append(payload_text)
                    if rule_used.inject_as in ("rsu", "both"):
                        msg["scene_context"]["rsu_messages"].append(payload_text)
                msg["_window_sender"] = s
                msg["_is_kinematic_attacker"] = s in kinematic_attacker_senders
                msg["_is_semantic_attacker"] = s == semantic_attacker_sender
                messages.append(msg)
        messages.sort(key=lambda m: m["cam"]["generation_delta_time"])

        windows_meta.append({
            "window_id": f"mix-{wi:05d}", "source_dataset": source_name,
            "composition": composition,
            "kinematic_attacker_senders": kinematic_attacker_senders,
            "semantic_attacker_sender": semantic_attacker_sender,
            "semantic_attack_family": rule_used.family if rule_used else None,
            "seed": window_seed, "messages": messages,
        })

    comp_counts = Counter(w["composition"] for w in windows_meta)
    manifest = {
        "benchmark": "Mixed-Threat-Bench", "seed": args.seed,
        "n_windows": len(windows_meta), "composition_counts": dict(comp_counts),
        "note": (
            "kinematic ground truth is VeReMi's own unmodified is_attacker "
            "label; semantic ground truth is this script's own injection "
            "(_is_semantic_attacker). The two are independent and can "
            "co-occur on DIFFERENT vehicles in the SAME window (composition="
            "'mixed')."
        ),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[build] {len(windows_meta)} windows: {dict(comp_counts)}")

    rows = []
    t_start = time.perf_counter()
    for wi, w in enumerate(windows_meta):
        pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
        window_msgs = []
        for m in w["messages"]:
            clean_msg = {k: v for k, v in m.items() if not k.startswith("_")}
            window_msgs.append(clean_msg)
            res = pipeline.run(list(window_msgs), context="urban")
            rows.append({
                "window_id": w["window_id"], "composition": w["composition"],
                "semantic_attack_family": w["semantic_attack_family"],
                "sender": m.get("_window_sender"),
                "is_kinematic_attacker": m.get("_is_kinematic_attacker"),
                "is_semantic_attacker": m.get("_is_semantic_attacker"),
                "decision": res["decision"],
                "contributors": ",".join(res["fusion"].get("contributors", [])),
                "b3_label": (res.get("b3") or {}).get("label"),
                "mbd_evidence": ";".join((res.get("mbd") or {}).get("evidence", []) or []),
            })
        if (wi + 1) % 20 == 0:
            elapsed = time.perf_counter() - t_start
            print(f"  {wi + 1}/{len(windows_meta)} windows ({elapsed:.0f}s elapsed)", flush=True)

    with (out_dir / "mixed_threat_per_message.csv").open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(rows)

    total_s = time.perf_counter() - t_start
    print(f"\n[done] {len(windows_meta)} windows, {len(rows)} messages in {total_s:.1f}s")
    print(f"-> {out_dir / 'mixed_threat_per_message.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
