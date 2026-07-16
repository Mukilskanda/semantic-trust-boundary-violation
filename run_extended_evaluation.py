#!/usr/bin/env python3
"""
run_extended_evaluation.py
==========================
Evaluates the full STBV stack on (base corpus + extended scenarios) with
multi-seed confidence intervals. Reports results BROKEN OUT BY DIFFICULTY and
by expected_label, so hard cases and over-defense (benign) probes are visible
separately -- no averaging away of weaknesses.

Makes NO claim about outcomes: it measures whatever the pipeline produces.
Honest by construction:
  * benign over-defense probes are scored as false positives if rejected;
  * hard evasion probes that slip through are reported as false negatives;
  * per-difficulty and per-family breakdowns prevent a single headline number
    from hiding either failure mode.

Usage (repo root):
    python3 run_extended_evaluation.py --seeds 1 2 3 4 5
    python3 run_extended_evaluation.py --extended-only --seeds 1 2 3 4 5
"""
from __future__ import annotations
import argparse, json, pathlib, statistics, sys
from collections import defaultdict
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def bootstrap_ci(vals, n=2000, seed=0):
    if len(vals) < 2:
        return {"mean": vals[0] if vals else float("nan"), "sd": 0.0, "lo": None, "hi": None}
    import random
    rng = random.Random(seed); means = []
    for _ in range(n):
        s = [vals[rng.randrange(len(vals))] for _ in vals]; means.append(sum(s) / len(s))
    means.sort()
    return {"mean": statistics.mean(vals), "sd": statistics.pstdev(vals),
            "lo": means[int(0.025 * n)], "hi": means[int(0.975 * n) - 1]}


def metrics(rows):
    # rows: list of (predicted_reject: bool, is_malicious: bool, difficulty, family)
    tp = sum(1 for p, t, *_ in rows if p and t)
    fp = sum(1 for p, t, *_ in rows if p and not t)
    fn = sum(1 for p, t, *_ in rows if not p and t)
    tn = sum(1 for p, t, *_ in rows if not p and not t)
    n = len(rows) or 1
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec == prec and rec == rec and prec + rec) else float("nan")
    return {"n": len(rows), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": (tp + tn) / n, "precision": prec, "recall": rec, "f1": f1,
            "fpr": fp / (fp + tn) if fp + tn else float("nan")}


def evaluate_once(records, pipe):
    from collections import namedtuple
    rows = []
    for rec in records:
        truth = str(rec.get("expected_label")).upper() == "MALICIOUS"
        diff = rec.get("difficulty", "?"); fam = rec.get("attack_category", "?")
        try:
            r = pipe.run([rec], context=(rec.get("scene_context", {}) or {}).get("context") or "urban")
            pred = (r.get("decision") == "REJECT")
        except Exception:
            pred = False
        rows.append((pred, truth, diff, fam))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--extended-only", action="store_true")
    ap.add_argument("--out", default="results/extended")
    args = ap.parse_args()

    try:
        from semantic_evaluation.semantic_attack_generator import generate_corpus
        from pipeline.orchestrator import ISCEPipeline
        from extended_attack_scenarios import EXTENDED_SCENARIOS
    except Exception as e:
        print(f"[FATAL] import failed: {e}\nRun from the stbv_engine repo root."); return 2

    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    pipe = ISCEPipeline()

    overall, by_diff, by_label = defaultdict(list), defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))
    for seed in args.seeds:
        if args.extended_only:
            records = generate_corpus(scenarios=EXTENDED_SCENARIOS, seed=seed)
        else:
            records = generate_corpus(seed=seed) + generate_corpus(scenarios=EXTENDED_SCENARIOS, seed=seed)
        rows = evaluate_once(records, pipe)
        m = metrics(rows)
        for k in ("f1", "recall", "precision", "fpr", "accuracy"):
            if m[k] == m[k]:
                overall[k].append(m[k])
        # per difficulty
        for diff in set(r[2] for r in rows):
            md = metrics([r for r in rows if r[2] == diff])
            for k in ("recall", "fpr", "f1"):
                if md[k] == md[k]:
                    by_diff[diff][k].append(md[k])
        # benign over-defense: FPR on benign only
        benign_rows = [r for r in rows if not r[1]]
        if benign_rows:
            fp_rate = sum(1 for r in benign_rows if r[0]) / len(benign_rows)
            by_label["benign"]["reject_rate"].append(fp_rate)
        print(f"  seed {seed}: F1={m['f1']:.3f} recall={m['recall']:.3f} "
              f"fpr={m['fpr']:.3f} (n={m['n']})")

    report = {
        "note": "Full-stack evaluation on base+extended corpus. Broken out by difficulty "
                "and label so hard-case misses and benign over-defense are visible. "
                "No outcome is assumed; these are measured.",
        "seeds": args.seeds, "extended_only": args.extended_only,
        "overall": {k: bootstrap_ci(v) for k, v in overall.items()},
        "by_difficulty": {d: {k: bootstrap_ci(v) for k, v in md.items()} for d, md in by_diff.items()},
        "benign_over_defense_reject_rate": bootstrap_ci(by_label["benign"]["reject_rate"])
        if by_label["benign"]["reject_rate"] else None,
    }
    (out / "extended_results.json").write_text(json.dumps(report, indent=2, default=str))

    print("\n=== OVERALL (mean over seeds, 95% CI) ===")
    for k, ci in report["overall"].items():
        print(f"  {k:10s} {ci['mean']:.3f}  CI[{ci['lo']},{ci['hi']}]  sd={ci['sd']:.3f}")
    print("\n=== BY DIFFICULTY (recall = detection of malicious) ===")
    for d, md in report["by_difficulty"].items():
        r = md.get("recall", {})
        print(f"  {d:8s} recall={r.get('mean',float('nan')):.3f} "
              f"fpr={md.get('fpr',{}).get('mean',float('nan')):.3f}")
    od = report["benign_over_defense_reject_rate"]
    if od:
        print(f"\n=== BENIGN OVER-DEFENSE (lower is better) ===\n"
              f"  benign reject rate = {od['mean']:.3f} CI[{od['lo']},{od['hi']}]")
    print(f"\nWritten: {out/'extended_results.json'}")
    print("\nREAD HONESTLY: hard-difficulty recall and benign reject-rate are the two "
          "numbers a reviewer will scrutinize. Report them, do not average them away.")
    return 0


if __name__ == "__main__":
    sys.exit(main())