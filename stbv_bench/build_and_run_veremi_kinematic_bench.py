#!/usr/bin/env python3
"""
stbv_bench/build_and_run_veremi_kinematic_bench.py
=====================================================
Companion benchmark to STBV-Bench, requested to verify the "complementary
threat-class coverage" claim: STBV-Bench is semantic-attacks-only by
design (DATASET_INTEGRATION.md), so B1/MBD/CP showing near-zero recall
there says nothing about whether those layers work at all -- only that
STBV-Bench gives them nothing to catch. This evaluates the same real,
frozen ISCEPipeline against REAL VeReMi Extension KINEMATIC attacks
(constant-position falsification, data replay, DoS/flooding), using
VeReMi's OWN is_attacker ground truth -- the exact threat class MBD is
designed for -- with NO semantic transformation applied (no injected
scene-context text; canonical.py's peer_reports/rsu_messages are left
empty, matching real VeReMi content, which never carried text).

METHODOLOGY NOTE (important, and different from STBV-Bench/run_ablation.py
on purpose): kinematic/behavioral attacks like constant-position
falsification and data replay are BY DEFINITION only detectable by
comparing a sender's current report against its own prior reports over
time (MBD's ProjectionOrigin/VehicleHistoryStore are stateful for exactly
this reason). Evaluating each VeReMi report as an independent single
message (the way STBV-Bench correctly evaluates independent, unrelated
messages) would silently reproduce a null result here for the WRONG
reason -- not "MBD is weak" but "MBD was never given the temporal history
it needs," which would be exactly the kind of methodological error this
whole exercise is trying to avoid repeating. Confirmed directly before
writing this docstring: a real ConstPos-attacker vehicle (VeReMi sender
8193) evaluated with a persistent, growing per-vehicle window correctly
triggers MBD's constant-position check ("Vehicle reports movement (avg
speed 53.29 km/h) but displacement is only 0.00m over 5000.00s") ->
CAUTION; the same vehicle's reports evaluated independently would not
have this history available at all.

So: this benchmark selects N real vehicles (senders) per VeReMi scenario,
and replays EACH vehicle's own real, time-ordered message sequence
through ONE fresh, persistent ISCEPipeline per (vehicle, config) --
fresh per vehicle (to avoid cross-vehicle state leakage, per the same
principle as the STBV-Bench fix), but persistent ACROSS that one
vehicle's own sequence (so MBD's temporal checks have real history to
work with, which is the correct and necessary methodology for this
threat class).

Usage:
  python3 stbv_bench/build_and_run_veremi_kinematic_bench.py \
      --source data/veremi_processed/ConstPos_1416 \
               data/veremi_processed/DataReplay_1416_full \
               data/veremi_processed/DoS_1416_full \
      --vehicles-per-class 60 --max-msgs-per-vehicle 40 --seed 13 \
      --out results/veremi_kinematic
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
from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

CONFIGS = {
    1: dict(enable_mbd=False, enable_cp=False, enable_b3=False, label="B1 only"),
    2: dict(enable_mbd=True, enable_cp=False, enable_b3=False, label="B1+B2(MBD)"),
    3: dict(enable_mbd=True, enable_cp=True, enable_b3=False, label="B1+B2+CP"),
    4: dict(enable_mbd=True, enable_cp=True, enable_b3=True, label="B1+B2+CP+B3 (full stack)"),
}


def load_veremi_reports(source_dir: pathlib.Path):
    f = source_dir / "veremi_flat_reports.json"
    if not f.exists():
        raise FileNotFoundError(f"{f} not found -- run import_veremi.py first.")
    return json.loads(f.read_text())


def select_vehicles(pool_by_source, vehicles_per_class: int, seed: int):
    """For each source dataset, pick up to vehicles_per_class attacker
    senders and vehicles_per_class benign senders, seeded and
    deterministic. Returns list of (source_name, sender_id, records[sorted by ts])."""
    rng = random.Random(seed)
    selected = []
    for source_name, records in pool_by_source.items():
        by_sender = defaultdict(list)
        for r in records:
            by_sender[r["sender"]].append(r)
        attacker_senders = sorted(s for s, rs in by_sender.items() if any(r.get("is_attacker") for r in rs))
        benign_senders = sorted(s for s, rs in by_sender.items() if not any(r.get("is_attacker") for r in rs))
        rng.shuffle(attacker_senders)
        rng.shuffle(benign_senders)
        for s in attacker_senders[:vehicles_per_class]:
            recs = sorted(by_sender[s], key=lambda r: r["timestamp"])
            selected.append((source_name, s, recs))
        for s in benign_senders[:vehicles_per_class]:
            recs = sorted(by_sender[s], key=lambda r: r["timestamp"])
            selected.append((source_name, s, recs))
    rng.shuffle(selected)
    return selected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, nargs="+")
    ap.add_argument("--vehicles-per-class", type=int, default=60,
                     help="attacker vehicles AND benign vehicles selected per source dataset")
    ap.add_argument("--max-msgs-per-vehicle", type=int, default=40)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pool_by_source = {}
    for src in args.source:
        src_path = pathlib.Path(src)
        pool_by_source[src_path.name] = load_veremi_reports(src_path)

    vehicles = select_vehicles(pool_by_source, args.vehicles_per_class, args.seed)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "benchmark": "VeReMi-Kinematic-Companion-Bench",
        "seed": args.seed,
        "vehicles_per_class_per_source": args.vehicles_per_class,
        "max_msgs_per_vehicle": args.max_msgs_per_vehicle,
        "source_datasets": args.source,
        "n_vehicles_selected": len(vehicles),
        "n_attacker_vehicles": sum(1 for _, _, recs in vehicles if any(r.get("is_attacker") for r in recs)),
        "n_benign_vehicles": sum(1 for _, _, recs in vehicles if not any(r.get("is_attacker") for r in recs)),
        "methodology": (
            "Each selected vehicle's own real, time-ordered VeReMi message "
            "sequence (capped at max_msgs_per_vehicle) is replayed through "
            "ONE persistent ISCEPipeline per (vehicle, config) -- fresh per "
            "vehicle, persistent within that vehicle's sequence, so MBD's "
            "temporal/history-dependent checks have real data to work "
            "with. Ground truth is VeReMi's own per-report is_attacker "
            "label (NOT any STBV-Bench semantic label); no scene-context "
            "text is injected."
        ),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[build] {len(vehicles)} vehicles selected: "
          f"{manifest['n_attacker_vehicles']} attacker / {manifest['n_benign_vehicles']} benign")

    files, writers = {}, {}
    fieldnames = ["sample_id", "sender", "source_dataset", "msg_index", "is_attacker",
                  "veremi_attacker_type", "decision", "raw_score", "contributors", "mbd_evidence"]
    for cfg_id in CONFIGS:
        f = open(out_dir / f"veremi_kinematic_config_{cfg_id}.csv", "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        files[cfg_id] = f
        writers[cfg_id] = w

    t_start = time.perf_counter()
    n_msgs_total = 0
    for vi, (source_name, sender, records) in enumerate(vehicles):
        records = records[: args.max_msgs_per_vehicle]
        msgs = [veremi_report_to_canonical(r, station_id=int(sender), station_type=5) for r in records]
        is_attacker = bool(records[0].get("is_attacker", False)) if records else False
        attacker_type = records[0].get("veremi_attacker_type", 0) if records else 0

        for cfg_id, cfg in CONFIGS.items():
            pipeline = ISCEPipeline(
                scsv=SCSV(), enable_mbd=cfg["enable_mbd"],
                enable_cp=cfg["enable_cp"], enable_b3=cfg["enable_b3"],
            )
            window = []
            for mi, m in enumerate(msgs):
                window.append(m)
                res = pipeline.run(list(window), context="urban")
                mbd = res.get("mbd") or {}
                writers[cfg_id].writerow({
                    "sample_id": f"vkb-{source_name}-{sender}-{mi:03d}",
                    "sender": sender, "source_dataset": source_name, "msg_index": mi,
                    "is_attacker": is_attacker, "veremi_attacker_type": attacker_type,
                    "decision": res["decision"], "raw_score": res["fusion"].get("trust_score"),
                    "contributors": ",".join(res["fusion"].get("contributors", [])),
                    "mbd_evidence": ";".join(mbd.get("evidence", []) or []),
                })
        n_msgs_total += len(msgs)
        if (vi + 1) % 20 == 0:
            elapsed = time.perf_counter() - t_start
            rate = (vi + 1) / elapsed
            eta = (len(vehicles) - (vi + 1)) / rate
            print(f"  {vi + 1}/{len(vehicles)} vehicles ({n_msgs_total} msgs so far, "
                  f"{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)", flush=True)

    for f in files.values():
        f.close()
    total_s = time.perf_counter() - t_start
    print(f"\n[done] {len(vehicles)} vehicles, {n_msgs_total} total messages x "
          f"{len(CONFIGS)} configs in {total_s:.1f}s")
    for cfg_id in CONFIGS:
        print(f"  -> {out_dir / f'veremi_kinematic_config_{cfg_id}.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
