#!/usr/bin/env python3
"""
import_veremi.py
=================
Imports raw VeReMi / VeReMi Extension simulation logs (van der Heijden et al.,
SecureComm 2018; Kamel et al., IEEE ICC 2020) into this repo's flat STBV
report schema: {sender, x, y, speed, heading, timestamp, is_attacker,
veremi_attacker_type, source}. This is the schema `bridges/message_adapter.
to_flat_report` already accepts directly (its first branch: `if "x" in
cam_message and "y" in cam_message`), and the schema `mbd/mbd_layer.py`
consumes -- confirmed by inspecting the already-produced
`data/veremi_processed/*/veremi_flat_reports.json` files, which this script
reproduces.

BUG-FIX PROVENANCE: this file previously contained unresolved git merge
conflict markers (`<<<<<<<`/`=======`/`>>>>>>>`) that spliced together this
importer's logic with an unrelated evaluation script's logic
(`run_veremi_evaluation.py`, which already exists separately at the repo
root and is unaffected/unchanged), leaving the file syntactically broken
(missing imports for `glob`, `os`, `Counter`, `Optional`; an undefined
`_iter_json_lines` helper; a truncated `_extract` function; and a `main()`
that referenced both scripts' incompatible argument sets simultaneously).
Rewritten here as a single, self-contained importer. The ground-truth
lookup and per-record extraction logic below preserve the original,
verified-correct approach recovered from the pre-conflict HEAD side of the
merge (confirmed against real files under `data/veremi/*_extracted/` this
session); the previously-truncated tail of `_extract` (heading-from-velocity
fallback + report assembly) and the `main()` driver are new, written to
reproduce exactly the schema already present in this repo's existing
`data/veremi_processed/*/manifest.json` files.

VeReMi log format (confirmed against `data/veremi/ConstPos_1416_extracted/`):
JSON-Lines (one JSON object per line) per-vehicle trace files named
`traceJSON-<receiver>-<sender>-A<attackerType>-<...>.json`, plus one
`traceGroundTruthJSON-*.json` per run. No `attackerType` field is present
directly on individual records in this dataset's extraction -- ground truth
is recovered from the trace filename's `-A<n>-` component (the fallback
path below), matching VeReMi Extension's own documented convention
(Kamel et al. 2020).

Usage:
  python3 import_veremi.py \
      --input data/veremi/ConstPos_1416_extracted/VeReMi_54000_57600_2022-9-11_18_8_38 \
      --output data/veremi_processed/ConstPos_1416 \
      --max 0
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import pathlib
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _iter_json_lines(path: str):
    """Yields one parsed JSON object per non-empty line of `path`. VeReMi
    trace files are JSON-Lines, not a single JSON array or object."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeDecodeError):
        return


def _find_ground_truth(input_dir: str) -> Tuple[Dict[Any, int], str]:
    """Locate a VeReMi ground-truth file and build {sender_or_pseudo:
    attackerType}. Returns (map, description). Empty map if none found."""
    gt_candidates = []
    for pat in ("**/GroundTruthJSONlog*", "**/*ground*truth*", "**/*GroundTruth*",
                "**/traceGroundTruthJSON*"):
        gt_candidates += glob.glob(os.path.join(input_dir, pat), recursive=True)
    gt_candidates = sorted(set(p for p in gt_candidates if os.path.isfile(p)))
    gt: Dict[Any, int] = {}
    used = []
    for path in gt_candidates:
        for rec in _iter_json_lines(path):
            if not isinstance(rec, dict):
                continue
            atk = rec.get("attackerType", rec.get("attacker_type"))
            key = rec.get("sender", rec.get("senderPseudo", rec.get("pseudo")))
            if atk is not None and key is not None:
                # a sender is an attacker if EVER marked non-zero
                gt[key] = max(int(gt.get(key, 0)), int(atk))
        if gt:
            used.append(path)

    if not gt:
        # Fallback: parse attacker types from trace filenames, e.g.
        # traceJSON-10011-10009-A1-57501-15.json -> vehicles 10011 and
        # 10009 are attacker type 1. Confirmed this is the ONLY source of
        # ground truth in this dataset's extraction (no per-record
        # attackerType field is present -- verified against real files).
        log_patterns = ("**/traceJSONlog*", "**/*JSONlog*", "**/veins*", "**/*.json")
        logs = []
        for pat in log_patterns:
            logs += glob.glob(os.path.join(input_dir, pat), recursive=True)
        logs = sorted(set(p for p in logs if os.path.isfile(p) and "round" not in os.path.basename(p).lower()
                          and "ground" not in os.path.basename(p).lower()))
        for lp in logs:
            basename = os.path.basename(lp)
            parts = basename.split("-")
            atk_val = None
            atk_idx = -1
            for idx, part in enumerate(parts):
                if part.startswith("A") and part[1:].isdigit():
                    atk_val = int(part[1:])
                    atk_idx = idx
                    break
            if atk_val is not None and atk_idx > 1:
                for i in range(1, atk_idx):
                    if parts[i].isdigit():
                        gt[int(parts[i])] = atk_val
                        gt[parts[i]] = atk_val
        if gt:
            used = ["parsed from trace filenames"]

    return gt, (f"{len(gt)} senders from {used}" if gt else "none found")


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _extract(rec: Dict[str, Any], gt: Dict[Any, int]) -> Tuple[Optional[Dict[str, Any]], str]:
    """Map one VeReMi record -> STBV flat report. Returns (report|None, note).

    VeReMi type: 3 = received BSM (what a detector sees). Records without a
    position or sender are skipped (mostly type-2 "sent" self-observations,
    which are not what a receiving detector would see).
    """
    if not isinstance(rec, dict):
        return None, "not a dict"
    pos = rec.get("pos") or rec.get("position")
    spd = rec.get("spd") or rec.get("speed")
    sender = rec.get("sender", rec.get("senderPseudo", rec.get("pseudo")))
    t = rec.get("rcvTime", rec.get("sendTime", rec.get("time")))
    if pos is None or sender is None:
        return None, "missing pos/sender"

    def comp(v, i):
        if isinstance(v, (list, tuple)) and len(v) > i:
            return _num(v[i])
        return 0.0

    x, y = comp(pos, 0), comp(pos, 1)
    vx, vy = comp(spd, 0), comp(spd, 1)
    speed = math.hypot(vx, vy)
    # Heading: prefer an explicit field; VeReMi's own records carry none, so
    # in practice this always falls through to deriving heading from the
    # velocity vector, which is the standard VeReMi-literature convention
    # (heading is not independently transmitted in the BSM this dataset
    # simulates -- it is inferred by the receiver, same as here).
    hed = rec.get("hed") or rec.get("heading")
    if isinstance(hed, (list, tuple)):
        heading = math.degrees(math.atan2(comp(hed, 1), comp(hed, 0))) % 360.0
    elif hed is not None:
        heading = _num(hed) % 360.0
    else:
        heading = math.degrees(math.atan2(vy, vx)) % 360.0 if (vx or vy) else 0.0

    if t is None:
        return None, "missing timestamp"

    # A sender with no ground-truth entry at all is of UNKNOWN attacker
    # status, not confirmed genuine -- silently defaulting it to "genuine"
    # would fabricate a label. Skip it instead (confirmed this matches the
    # convention already used to produce this repo's existing
    # data/veremi_processed/ConstPos_1416/manifest.json: that manifest
    # records exactly 1,978 messages skipped for "no ground-truth
    # attackerType for sender", separate from and in addition to "missing
    # pos/sender").
    if sender not in gt and str(sender) not in gt:
        return None, "no ground-truth attackerType for sender"

    atk_type = int(gt.get(sender, gt.get(str(sender), 0)))
    return {
        "sender": sender,
        "x": x,
        "y": y,
        "speed": speed,
        "heading": heading,
        "timestamp": _num(t),
        "is_attacker": atk_type != 0,
        "veremi_attacker_type": atk_type,
        "source": "veremi",
    }, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True,
                     help="Directory containing one VeReMi run's extracted traceJSON*/traceGroundTruthJSON* files")
    ap.add_argument("--output", required=True,
                     help="Output directory; writes veremi_flat_reports.json + manifest.json")
    ap.add_argument("--max", type=int, default=0,
                     help="Stop after writing this many unique messages (0 = no limit)")
    ap.add_argument("--inspect", action="store_true",
                     help="Print the first 3 raw records and the ground-truth lookup summary, then exit (no files written)")
    args = ap.parse_args()

    gt, gt_desc = _find_ground_truth(args.input)

    if args.inspect:
        print(f"[inspect] ground truth: {gt_desc}")
        logs = sorted(set(
            p for p in glob.glob(os.path.join(args.input, "**", "traceJSON-*.json"), recursive=True)
            if os.path.isfile(p)
        ))
        print(f"[inspect] found {len(logs)} traceJSON-* files")
        shown = 0
        for lp in logs:
            for rec in _iter_json_lines(lp):
                if shown >= 3:
                    break
                r, note = _extract(rec, gt)
                print(f"[inspect] raw={rec}\n          -> extracted={r} ({note})")
                shown += 1
            if shown >= 3:
                break
        return 0

    logs = sorted(set(
        p for p in glob.glob(os.path.join(args.input, "**", "traceJSON-*.json"), recursive=True)
        if os.path.isfile(p)
    ))
    if not logs:
        print(f"[error] no traceJSON-*.json files found under {args.input}")
        return 1

    out = pathlib.Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    written = skipped = duplicates_removed = 0
    seen_transmissions = set()
    skip_reasons: Counter = Counter()
    label_counter: Counter = Counter()
    all_reports: List[Dict[str, Any]] = []
    raw_records_processed = 0

    for lp in logs:
        for rec in _iter_json_lines(lp):
            raw_records_processed += 1
            r, note = _extract(rec, gt)
            if r is None:
                skipped += 1
                skip_reasons[note] += 1
                continue

            sender = r["sender"]
            msg_id = rec.get("messageID")
            send_time = rec.get("sendTime", rec.get("time", r["timestamp"]))
            tx_key = (sender, msg_id) if msg_id is not None else (sender, round(_num(send_time), 3))

            if tx_key in seen_transmissions:
                duplicates_removed += 1
                continue

            seen_transmissions.add(tx_key)
            all_reports.append(r)
            label_counter[int(r["is_attacker"])] += 1
            written += 1
            if args.max and written >= args.max:
                break
        if args.max and written >= args.max:
            break

    (out / "veremi_flat_reports.json").write_text(json.dumps(all_reports))
    manifest = {
        "dataset": "VeReMi / VeReMi Extension",
        "cite": ["van der Heijden et al., SecureComm 2018",
                 "Kamel et al., VeReMi Extension, IEEE ICC 2020"],
        "source_url": "https://veremi-dataset.github.io",
        "input_dir": os.path.abspath(args.input),
        "ground_truth_source": gt_desc,
        "raw_records_processed": raw_records_processed,
        "duplicate_observations_removed": duplicates_removed,
        "messages_written": written,
        "messages_skipped": skipped,
        "skip_reasons": dict(skip_reasons),
        "label_distribution": {"genuine(0)": label_counter[0], "attacker(1)": label_counter[1]},
        "label_rule": "is_attacker = (attackerType != 0), from VeReMi ground truth",
        "schema": "STBV flat report: sender,x,y,speed,heading,timestamp,is_attacker",
        "VALIDATE": "Confirm field mapping with --inspect before trusting these labels.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n[done] processed {raw_records_processed} raw records:")
    print(f"       - Removed {duplicates_removed} duplicate receiver observations")
    print(f"       - Kept {written} unique transmitted packets "
          f"({label_counter[1]} attacker / {label_counter[0]} genuine)")
    print(f"       -> {out / 'veremi_flat_reports.json'}")
    print(f"       -> {out / 'manifest.json'}")
    if skipped:
        print(f"[note] skipped {skipped}: {dict(skip_reasons)}")
    if label_counter[1] == 0:
        print("[WARN] zero attacker messages labelled -> ground-truth mapping likely wrong. "
              "Re-run --inspect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
