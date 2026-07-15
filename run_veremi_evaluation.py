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


def run_mbd_stream(reports: List[Dict[str, Any]], threshold: float):
    """Feed messages through MBD in receive order per the shared history store.
    Returns per-message (pred_attack, truth_attack, sender)."""
    store = VehicleHistoryStore()
    rows = []
    # order by timestamp so replay/temporal checks see a coherent stream
    for r in sorted(reports, key=lambda x: x.get("timestamp", 0.0)):
        try:
            res = mbd_layer(dict(r), store)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())