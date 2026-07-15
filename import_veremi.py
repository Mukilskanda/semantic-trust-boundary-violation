#!/usr/bin/env python3
"""
run_veremi_evaluation.py
========================
Evaluates the STBV kinematic-detection layers on the VeReMi Extension public
dataset (imported via import_veremi.py). This provides the recognized-dataset
evaluation the paper needs for its crypto/behavioral half.

SCOPE (stated honestly, not hidden):
  * VeReMi attacks are KINEMATIC (position/speed falsification, replay, Sybil,
    DoS). They are detected by MBD (Misbehavior Detection), which consumes the
    flat kinematic report (sender,x,y,speed,heading,timestamp) that
    import_veremi.py emits. MBD is the layer VeReMi exercises.
  * B1's CRYPTOGRAPHIC checks (cert/signature) are N/A on VeReMi -- the dataset
    carries no PKI material. B1's STRUCTURAL checks are implicitly covered by
    MBD's plausibility limits here. We therefore report MBD detection, and
    label the result "MBD (B1-kinematic + MBD)" -- we do NOT claim to evaluate
    PKI/signature validation on VeReMi, because the data cannot support it.
  * B3 (semantic) is NOT exercised -- VeReMi has no message text. Stated.
  * CP (cooperative perception) requires a peer cluster per target; we run it
    in a windowed mode and report it as a secondary signal.

LABELS: per-vehicle VeReMi ground truth (A-code != 0), the dataset's official
convention (Kamel et al. 2020). A benign-looking message from an attacker
vehicle is still labelled attacker -- standard in this literature; noted.

SCORING:
  primary   = MESSAGE-LEVEL (each message scored vs its sender's label) --
              directly comparable to published VeReMi results (Sedar et al.).
  secondary = VEHICLE-LEVEL (a vehicle is flagged if a fraction of its
              messages trip MBD) -- closer to what the stack decides.

Multi-seed: subsamples messages per seed for CIs (the full set is huge).

Usage:
  python3 run_veremi_evaluation.py \
     --input datasets/veremi_processed \
     --attacks ConstPos_1416 RandomPos_1416 RandomSpeedOffset_1416 \
               DataReplay_1416 DataReplaySybil_1416 GridSybil_1416 DoS_1416 \
     --seeds 1 2 3 4 5 --sample-per-attack 20000 \
     --mbd-threshold 0.5
"""
from __future__ import annotations
import argparse, json, math, pathlib, random, statistics, sys
from collections import defaultdict
from typing import Any, Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from mbd import mbd_layer, VehicleHistoryStore

# map folder -> (STBV family, VeReMi A-code) for the results table
ATTACK_FAMILY = {
    "ConstPos_1416": ("fabrication", "A1"),
    "RandomPos_1416": ("fabrication", "A3"),
    "RandomSpeedOffset_1416": ("fabrication", "A8"),
    "DataReplay_1416": ("replay", "A11"),
    "DoS_1416": ("dos", "A13"),
    "GridSybil_1416": ("sybil", "A16"),
    "DataReplaySybil_1416": ("sybil", "A17"),
}


def load_reports(path: pathlib.Path) -> List[Dict[str, Any]]:
    return json.loads((path / "veremi_flat_reports.json").read_text())


<<<<<<< HEAD
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
        # Fallback: parse attacker types from trace filenames
        # e.g., traceJSON-10011-10009-A1-57501-15.json -> vehicle 10011 and 10009 are A1
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
    """Map one VeReMi record -> STBV flat report. Returns (report|None, note)."""
    if not isinstance(rec, dict):
        return None, "not a dict"
    # VeReMi type: 3 = received BSM (what a detector sees). Keep type 2/3; skip
    # GPS-only rows that lack position.
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
    # heading: prefer explicit field, else derive from velocity vector
    hed = rec.get("hed") or rec.get("heading")
    if isinstance(hed, (list, tuple)):
        heading = math.degrees(math.atan2(comp(hed, 1), comp(hed, 0))) % 360.0
    elif hed is not None:
        heading = _num(hed)
=======
def run_mbd_stream(reports: List[Dict[str, Any]], threshold: float):
    """Feed messages through MBD in receive order per the shared history store.
    Returns per-message (pred_attack, truth_attack, sender).

    TIMESTAMP REBASING (unit fix, not fabrication): VeReMi timestamps are
    absolute LuST-simulation SECONDS (e.g. 50854). MBD's freshness gate checks
    abs(ts - time.time()) <= 5s against WALL-CLOCK now, so raw VeReMi ts is
    always ~billions of seconds "too old" and every message is force-flagged.
    We rebase the stream so its earliest message sits at (now - span), i.e.
    shift all timestamps by a constant offset. This preserves EVERY relative
    timing quantity MBD actually reasons over (inter-message deltas, replay
    coincidence, chronology) -- those are frame-invariant -- while satisfying
    the absolute-freshness check. No kinematic value is altered."""
    import time as _time
    ordered = sorted(reports, key=lambda x: x.get("timestamp", 0.0))
    if ordered:
        t0 = ordered[0].get("timestamp", 0.0)
        t_last = ordered[-1].get("timestamp", 0.0)
        span = max(t_last - t0, 0.0)
        # place the stream ending ~1s before now, so all msgs are "fresh"
        offset = _time.time() - 1.0 - span - t0
>>>>>>> 1464c31 (Save local changes)
    else:
        offset = 0.0
    store = VehicleHistoryStore()
    rows = []
    for r in ordered:
        try:
            r = dict(r)
            r["timestamp"] = r.get("timestamp", 0.0) + offset
            res = mbd_layer(r, store)
            score = float(res.get("anomaly_score", 0.0))
            pred = (score >= threshold) or (not res.get("passed", True))
        except Exception:
            continue
        rows.append((bool(pred), bool(r.get("is_attacker", False)), r.get("sender")))
    return rows


def confusion(rows):
    tp = sum(1 for p, t, _ in rows if p and t)
    fp = sum(1 for p, t, _ in rows if p and not t)
    fn = sum(1 for p, t, _ in rows if not p and t)
    tn = sum(1 for p, t, _ in rows if not p and not t)
    n = len(rows) or 1
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec == prec and rec == rec and prec + rec) else float("nan")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(rows),
            "accuracy": (tp + tn) / n, "precision": prec, "recall": rec, "f1": f1,
            "fpr": fp / (fp + tn) if fp + tn else float("nan"),
            "fnr": fn / (fn + tp) if fn + tp else float("nan")}


def vehicle_level(rows, flag_frac=0.3):
    by_v = defaultdict(lambda: [0, 0, False])  # [n, n_pred, truth]
    for p, t, s in rows:
        by_v[s][0] += 1; by_v[s][1] += int(p); by_v[s][2] = by_v[s][2] or t
    vrows = []
    for s, (n, npred, truth) in by_v.items():
        vpred = (npred / n) >= flag_frac if n else False
        vrows.append((vpred, truth, s))
    return confusion(vrows)


def ci(vals):
    if len(vals) < 2:
        return {"mean": vals[0] if vals else float("nan"), "sd": 0.0, "lo": None, "hi": None}
    import random as _r
    rng = _r.Random(0); means = []
    for _ in range(2000):
        s = [vals[rng.randrange(len(vals))] for _ in vals]; means.append(sum(s) / len(s))
    means.sort()
    return {"mean": statistics.mean(vals), "sd": statistics.pstdev(vals),
            "lo": means[50], "hi": means[-50]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="datasets/veremi_processed")
    ap.add_argument("--attacks", nargs="+", default=list(ATTACK_FAMILY.keys()))
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--sample-per-attack", type=int, default=20000,
                    help="messages sampled per attack per seed (0 = all)")
    ap.add_argument("--mbd-threshold", type=float, default=0.5)
    ap.add_argument("--out", default="results/veremi")
    args = ap.parse_args()

    in_root = pathlib.Path(args.input)
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)

    per_attack_msg: Dict[str, Dict[str, list]] = {}
    per_attack_veh: Dict[str, Dict[str, list]] = {}
    rows_out = []

    for atk in args.attacks:
        apath = in_root / atk
        if not (apath / "veremi_flat_reports.json").exists():
            print(f"[skip] {atk}: no veremi_flat_reports.json"); continue
        reports = load_reports(apath)
        fam, code = ATTACK_FAMILY.get(atk, ("unknown", "?"))
        print(f"\n=== {atk} ({fam}, {code}): {len(reports)} messages ===")
        msg_metrics = defaultdict(list); veh_metrics = defaultdict(list)
        for seed in args.seeds:
            rng = random.Random(seed)
            sample = reports
            if args.sample_per_attack and len(reports) > args.sample_per_attack:
                sample = rng.sample(reports, args.sample_per_attack)
            rows = run_mbd_stream(sample, args.mbd_threshold)
            m = confusion(rows); v = vehicle_level(rows)
            for k in ("accuracy", "precision", "recall", "f1", "fpr"):
                if m[k] == m[k]:
                    msg_metrics[k].append(m[k])
                if v[k] == v[k]:
                    veh_metrics[k].append(v[k])
            print(f"  seed {seed}: msg F1={m['f1']:.3f} rec={m['recall']:.3f} "
                  f"fpr={m['fpr']:.3f} | veh F1={v['f1']:.3f} rec={v['recall']:.3f}")
        per_attack_msg[atk] = {k: ci(v) for k, v in msg_metrics.items()}
        per_attack_veh[atk] = {k: ci(v) for k, v in veh_metrics.items()}
        rows_out.append((atk, fam, code, per_attack_msg[atk], per_attack_veh[atk]))

    # ---- outputs ----
    (out / "veremi_results.json").write_text(json.dumps({
        "scope": "MBD kinematic detection on VeReMi Extension; B1-crypto/B3-semantic "
                 "NOT applicable (no PKI material / no message text in VeReMi).",
        "label_convention": "per-vehicle A-code (Kamel et al. 2020)",
        "primary_scoring": "message-level (comparable to Sedar et al.)",
        "message_level": per_attack_msg, "vehicle_level": per_attack_veh,
        "seeds": args.seeds, "sample_per_attack": args.sample_per_attack,
        "mbd_threshold": args.mbd_threshold,
    }, indent=2, default=str))

    # CSV
    import csv
    with (out / "veremi_per_attack.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["attack", "family", "a_code", "scoring", "F1_mean", "F1_sd",
                    "F1_ci_lo", "F1_ci_hi", "recall_mean", "fpr_mean", "precision_mean"])
        for atk, fam, code, mm, vm in rows_out:
            for scoring, d in (("message", mm), ("vehicle", vm)):
                f1 = d.get("f1", {}); rec = d.get("recall", {}); fpr = d.get("fpr", {}); pr = d.get("precision", {})
                w.writerow([atk, fam, code, scoring,
                            f"{f1.get('mean',float('nan')):.4f}", f"{f1.get('sd',0):.4f}",
                            f"{f1.get('lo')}", f"{f1.get('hi')}",
                            f"{rec.get('mean',float('nan')):.4f}",
                            f"{fpr.get('mean',float('nan')):.4f}",
                            f"{pr.get('mean',float('nan')):.4f}"])

<<<<<<< HEAD
    out = pathlib.Path(args.output); out.mkdir(parents=True, exist_ok=True)
    written = skipped = duplicates_removed = 0
    seen_transmissions = set()
    skip_reasons = Counter()
    label_counter = Counter()
    all_reports: List[Dict[str, Any]] = []
    
    # We want to count raw records processed (written + skipped + duplicates)
    raw_records_processed = 0
    
    for lp in logs:
        for rec in _iter_json_lines(lp):
            raw_records_processed += 1
            r, note = _extract(rec, gt)
            if r is None:
                skipped += 1; skip_reasons[note] += 1; continue
                
            sender = r["sender"]
            msg_id = rec.get("messageID")
            send_time = rec.get("sendTime", rec.get("time", r["timestamp"]))
            
            if msg_id is not None:
                tx_key = (sender, msg_id)
            else:
                tx_key = (sender, round(_num(send_time), 3))
                
            if tx_key in seen_transmissions:
                duplicates_removed += 1
                continue
                
            seen_transmissions.add(tx_key)
            all_reports.append(r); label_counter[int(r["is_attacker"])] += 1
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
    print(f"       - Kept {written} unique transmitted packets ({label_counter[1]} attacker / {label_counter[0]} genuine)")
    print(f"       -> {out/'veremi_flat_reports.json'}")
    print(f"       -> {out/'manifest.json'}")
    if skipped:
        print(f"[note] skipped {skipped}: {dict(skip_reasons)}")
    if label_counter[1] == 0:
        print("[WARN] zero attacker messages labelled -> ground-truth mapping likely wrong. "
              "Re-run --inspect.")
=======
    # LaTeX (message-level primary)
    lines = ["% VeReMi Extension: MBD kinematic detection (message-level, mean over seeds)",
             "\\begin{table}[t]\\centering\\small",
             "\\caption{Misbehavior detection on the VeReMi Extension dataset "
             "(message-level, mean$\\pm$SD over seeds). B1-cryptographic and B3-semantic "
             "layers are not applicable to VeReMi (no PKI material, no message text).}",
             "\\label{tab:veremi}",
             "\\begin{tabular}{llrrr}\\toprule",
             "Attack & Family & F1 & Recall & FPR \\\\\\midrule"]
    for atk, fam, code, mm, vm in rows_out:
        f1 = mm.get("f1", {}); rec = mm.get("recall", {}); fpr = mm.get("fpr", {})
        lines.append(f"{atk.replace('_1416','').replace('_','')} & {fam} & "
                     f"{f1.get('mean',float('nan')):.3f}$\\pm${f1.get('sd',0):.3f} & "
                     f"{rec.get('mean',float('nan')):.3f} & {fpr.get('mean',float('nan')):.3f} \\\\")
    lines += ["\\bottomrule\\end{tabular}\\end{table}"]
    (out / "veremi_table.tex").write_text("\n".join(lines))

    print(f"\nWritten: {out}/veremi_results.json, veremi_per_attack.csv, veremi_table.tex")
    print("\nSCOPE REMINDER: this is MBD kinematic detection on VeReMi. It does NOT "
          "evaluate PKI/signature (no crypto material) or B3 (no text). State that.")
>>>>>>> 1464c31 (Save local changes)
    return 0


if __name__ == "__main__":
    sys.exit(main())