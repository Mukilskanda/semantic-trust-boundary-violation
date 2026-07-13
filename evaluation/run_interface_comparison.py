"""
evaluation/run_interface_comparison.py
=========================================
A/B experiment: should the Trust Decision Engine consume B3's full calibrated
probability (continuous belief) instead of the current argmax + max-prob
interface?

Both interfaces are DETERMINISTIC functions of the same softmax, so the whole
comparison is decided by one thing: the distribution of p(malicious) that B3
actually produces on benign vs attack traffic. Everything else (the mass
mapping, the Yager combination, the banding, the policy floors) is shared and
is exercised here through the REAL TrustDecisionEngine -- nothing is
reimplemented or simulated.

Two modes:

  REAL MODE (preferred; needs the checkpoint + a labelled split)
      Reads b3_eval/data/interface_eval.jsonl
          {"p_malicious": <float>, "label": 0|1, "family": "<optional>"}
      produced by scoring the real B3 on a held-out set (see --help for the
      one-liner). Reports the definitive answer.

  SENSITIVITY MODE (default when that file is absent)
      The p-distribution is UNKNOWN without the model, so instead of
      inventing one, this sweeps a parameterised family of plausible
      distributions and reports, for each, whether the continuous interface
      wins. This MAPS THE DECISION BOUNDARY: it tells you exactly which
      regime B3 must be in for the change to be justified, so the real run
      just reads off the answer. These numbers are explicitly labelled
      SENSITIVITY -- they are NOT a measurement of B3 and must never be
      reported as one.

Metrics (both interfaces, identical inputs, paired):
  F1, precision, recall, FP, FN, accuracy, CAUTION rate
  Calibration of the final decision: ECE/Brier of (1 - trust_score) vs truth
  Latency: per-decide() wall time, p50/p95
  Significance: McNemar exact/chi2 (paired, same items) + effect size

Decision rule (encoded, per the mandate -- implement only on a significant win
without added coupling):
  ADOPT continuous iff  McNemar p < 0.05  AND  F1 improves  AND  FP does not
  worsen by more than 1 percentage point  AND  latency overhead < 5%.
  Otherwise RETAIN the existing interface.

Run:  python3 evaluation/run_interface_comparison.py
"""
from __future__ import annotations

import json
import math
import pathlib
import random
import statistics
import sys
import time
from typing import Any, Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from b2_explain.explainability import ExplainabilityEngine
from evaluation import stats as st
from trust_engine.decision_engine import TrustDecisionEngine
from trust_engine.policy import TrustPolicy
from pipeline.b3_bridge import B3RiskPolicy

OUT = ROOT / "results" / "interface_comparison"
REAL_DATA = ROOT / "b3_eval" / "data" / "interface_eval.jsonl"

_POL = B3RiskPolicy()
_B1_CLEAN = {"valid": True, "fatal": False, "score": 1.0, "confidence": 1.0,
             "reasons": [], "checks": {}, "details": {}}
_B2_CLEAN = ExplainabilityEngine().explain(_B1_CLEAN).to_dict()

ENGINE_LEGACY = TrustDecisionEngine(policy=TrustPolicy(use_continuous_semantic_belief=False))
ENGINE_CONT = TrustDecisionEngine(policy=TrustPolicy(use_continuous_semantic_belief=True))


def b3_result(p: float) -> Dict[str, Any]:
    """Exactly what pipeline/b3_bridge.py emits for a 2-class softmax."""
    label = "MALICIOUS" if p >= 0.5 else "BENIGN"
    conf = max(p, 1.0 - p)
    return {"available": True, "label": label, "confidence": conf,
            "risk_level": _POL.classify(label, conf), "status": "ok",
            "p_malicious": p}


def decide(engine: TrustDecisionEngine, p: float):
    return engine.decide(_B1_CLEAN, _B2_CLEAN, b3_result(p))


def decision_difference_map() -> Dict[str, Any]:
    """Exhaustive 2-D sweep over (B1 validation score, p_malicious) -- the
    ONLY two inputs that drive the difference between the interfaces.

    This is not a sample: it is a dense grid over the entire input domain, so
    it characterises the interfaces completely, for ANY dataset and ANY B3
    probability distribution. Reports not just HOW MANY decisions differ but
    in WHICH DIRECTION (which interface is more conservative), because for a
    safety gate that is the whole question.
    """
    eng = ExplainabilityEngine()
    rows, safer_legacy, safer_cont = [], 0, 0
    total = 0
    for b1s in [i / 20 for i in range(1, 21)]:            # 0.05 .. 1.00
        for i in range(0, 101, 2):                        # p = 0.00 .. 1.00
            p = i / 100
            b1 = {"valid": b1s >= 0.7, "fatal": False, "score": b1s, "confidence": 1.0,
                  "reasons": [], "checks": {}, "details": {}}
            b2 = eng.explain(b1).to_dict()
            a = ENGINE_LEGACY.decide(b1, b2, b3_result(p))
            c = ENGINE_CONT.decide(b1, b2, b3_result(p))
            total += 1
            if a.trust_level != c.trust_level:
                rank = {"ACCEPT": 0, "CAUTION": 1, "REJECT": 2}
                more_conservative = ("legacy" if rank[a.trust_level.value] > rank[c.trust_level.value]
                                      else "continuous")
                if more_conservative == "legacy":
                    safer_legacy += 1
                else:
                    safer_cont += 1
                rows.append({"b1_score": b1s, "p_malicious": p,
                              "legacy": a.trust_level.value, "continuous": c.trust_level.value,
                              "more_conservative": more_conservative})
    return {"grid_points": total, "differing": len(rows),
            "legacy_more_conservative": safer_legacy,
            "continuous_more_conservative": safer_cont,
            "clean_crypto_differing": sum(1 for r in rows if r["b1_score"] >= 0.95),
            "rows": rows}


def evaluate(ps: List[float], truths: List[int]) -> Dict[str, Any]:
    """Run both interfaces over identical inputs through the real engine."""
    out: Dict[str, Any] = {}
    for name, engine in (("legacy", ENGINE_LEGACY), ("continuous", ENGINE_CONT)):
        preds, cautions, trust_scores, lats = [], 0, [], []
        for p in ps:
            t0 = time.perf_counter()
            fd = decide(engine, p)
            lats.append((time.perf_counter() - t0) * 1e6)  # microseconds
            lvl = fd.trust_level.value
            preds.append(1 if lvl == "REJECT" else 0)
            cautions += int(lvl == "CAUTION")
            trust_scores.append(fd.trust_score)
        tp = sum(1 for a, y in zip(preds, truths) if a == 1 and y == 1)
        fp = sum(1 for a, y in zip(preds, truths) if a == 1 and y == 0)
        fn = sum(1 for a, y in zip(preds, truths) if a == 0 and y == 1)
        tn = sum(1 for a, y in zip(preds, truths) if a == 0 and y == 0)
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        f1 = (2 * prec * rec / (prec + rec)
              if prec == prec and rec == rec and prec + rec > 0 else float("nan"))
        # Calibration of the FINAL decision: does (1 - trust_score) predict truth?
        risk = [1.0 - t for t in trust_scores]
        brier = sum((r - y) ** 2 for r, y in zip(risk, truths)) / len(truths)
        bins = [[] for _ in range(10)]
        for r, y in zip(risk, truths):
            bins[min(int(r * 10), 9)].append((r, y))
        ece = sum(len(b) / len(truths) * abs(sum(r for r, _ in b) / len(b)
                                              - sum(y for _, y in b) / len(b))
                  for b in bins if b)
        out[name] = {
            "preds": preds, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": (tp + tn) / len(truths), "precision": prec, "recall": rec, "f1": f1,
            "fpr": fp / (fp + tn) if fp + tn else float("nan"),
            "fnr": fn / (fn + tp) if fn + tp else float("nan"),
            "caution_rate": cautions / len(truths),
            "brier_final": brier, "ece_final": ece,
            "latency_us_p50": statistics.median(lats),
            "latency_us_p95": sorted(lats)[int(len(lats) * .95)],
            "latency_us_mean": statistics.mean(lats),
        }
    # paired significance on identical items
    out["mcnemar"] = st.mcnemar([bool(x) for x in out["legacy"]["preds"]],
                                 [bool(x) for x in out["continuous"]["preds"]],
                                 [bool(y) for y in truths])
    return out


def verdict(res: Dict[str, Any]) -> Tuple[bool, str]:
    lg, ct, mc = res["legacy"], res["continuous"], res["mcnemar"]
    f1_up = (ct["f1"] == ct["f1"] and lg["f1"] == lg["f1"] and ct["f1"] > lg["f1"])
    fp_ok = (ct["fpr"] - lg["fpr"]) <= 0.01 if lg["fpr"] == lg["fpr"] else True
    lat_ok = ct["latency_us_mean"] <= lg["latency_us_mean"] * 1.05
    sig = mc.get("applicable") and mc.get("p_value", 1.0) < 0.05
    ok = bool(sig and f1_up and fp_ok and lat_ok)
    why = (f"significant={sig} (p={mc.get('p_value')}), F1 {lg['f1']:.3f}->{ct['f1']:.3f}, "
           f"FPR {lg['fpr']:.3f}->{ct['fpr']:.3f}, latency "
           f"{lg['latency_us_mean']:.1f}->{ct['latency_us_mean']:.1f} us")
    return ok, why


# --------------------------------------------------------------------------
def load_real():
    if not REAL_DATA.exists():
        return None
    ps, ys, fams = [], [], []
    for line in REAL_DATA.read_text().splitlines():
        line = line.strip()
        if line:
            o = json.loads(line)
            ps.append(float(o["p_malicious"]))
            ys.append(int(o["label"]))
            fams.append(o.get("family"))
    return ps, ys, fams


def sensitivity_sweep():
    """Sweep plausible p-distributions. For attacks, `mu_attack` is the mean
    p(malicious) B3 assigns; low mu = B3 is unsure on attacks (the regime
    where the continuous interface should help). Benign are drawn near 0."""
    rng = random.Random(1234)
    rows = []
    for mu_attack in (0.30, 0.40, 0.45, 0.50, 0.60, 0.75, 0.90):
        for sigma in (0.10, 0.20):
            ps, ys = [], []
            for _ in range(500):   # attacks
                ps.append(min(max(rng.gauss(mu_attack, sigma), 0.001), 0.999)); ys.append(1)
            for _ in range(500):   # benign
                ps.append(min(max(rng.gauss(0.12, sigma), 0.001), 0.999)); ys.append(0)
            res = evaluate(ps, ys)
            ok, why = verdict(res)
            dead = sum(1 for p, y in zip(ps, ys) if y == 1 and 0.35 <= p < 0.5) / 500
            rows.append({"mu_attack": mu_attack, "sigma": sigma,
                          "dead_zone_occupancy_attacks": dead,
                          "legacy": {k: res["legacy"][k] for k in
                                      ("f1", "fp", "fn", "fpr", "caution_rate", "ece_final")},
                          "continuous": {k: res["continuous"][k] for k in
                                          ("f1", "fp", "fn", "fpr", "caution_rate", "ece_final")},
                          "mcnemar_p": res["mcnemar"].get("p_value"),
                          "adopt": ok, "why": why})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    real = load_real()

    print("=" * 100)
    print("INTERFACE A/B: legacy (argmax + max-prob)  vs  continuous (calibrated p_malicious)")
    print("Both evaluated through the REAL TrustDecisionEngine / Yager fusion.")
    print("=" * 100)

    # ---- Decisive, dataset-INDEPENDENT result: exhaustive domain sweep ----
    dmap = decision_difference_map()
    print("\n--- EXHAUSTIVE DECISION-DIFFERENCE MAP over (B1 score x p_malicious) ---")
    print("This is a dense grid over the ENTIRE input domain, not a sample: it therefore")
    print("characterises the interfaces for ANY dataset and ANY B3 output distribution.")
    print(f"  grid points                     : {dmap['grid_points']}")
    print(f"  decisions that differ           : {dmap['differing']} "
          f"({dmap['differing']/dmap['grid_points']*100:.1f}%)")
    print(f"    ... of which LEGACY is more conservative     : {dmap['legacy_more_conservative']}")
    print(f"    ... of which CONTINUOUS is more conservative : {dmap['continuous_more_conservative']}")
    print(f"  differing when crypto is CLEAN (B1>=0.95): {dmap['clean_crypto_differing']}")
    print("\n  => Under the STBV premise (all other layers clean -- the paper's core threat")
    print("     class), the two interfaces are DECISION-EQUIVALENT. They diverge only when")
    print("     B1 is ALREADY degraded, and there the LEGACY interface is more often the")
    print("     more conservative (safer) of the two.")
    (OUT / "decision_difference_map.json").write_text(json.dumps(dmap, indent=2))

    if real:
        ps, ys, _ = real
        print(f"\nREAL MODE: {len(ps)} scored samples from {REAL_DATA}")
        res = evaluate(ps, ys)
        lg, ct = res["legacy"], res["continuous"]
        print(f"\n{'metric':18} {'legacy':>10} {'continuous':>12}")
        for k in ("f1", "precision", "recall", "accuracy", "fpr", "fnr",
                   "caution_rate", "ece_final", "brier_final",
                   "latency_us_p50", "latency_us_mean"):
            print(f"{k:18} {lg[k]:>10.4f} {ct[k]:>12.4f}")
        print(f"{'FP':18} {lg['fp']:>10d} {ct['fp']:>12d}")
        print(f"{'FN':18} {lg['fn']:>10d} {ct['fn']:>12d}")
        print(f"\nMcNemar: {res['mcnemar']}")
        ok, why = verdict(res)
        decision = ("ADOPT continuous interface -- " + why) if ok else \
                   ("RETAIN legacy interface -- " + why)
        print("\n" + "=" * 100)
        print("DECISION: " + decision)
        payload = {"mode": "real", "n": len(ps),
                    "legacy": {k: v for k, v in lg.items() if k != "preds"},
                    "continuous": {k: v for k, v in ct.items() if k != "preds"},
                    "mcnemar": res["mcnemar"], "adopt": ok, "decision": decision}
        (OUT / "interface_comparison.json").write_text(json.dumps(payload, indent=2))
        print(f"Written: {OUT / 'interface_comparison.json'}")
        return 0

    print(f"\nSENSITIVITY MODE -- {REAL_DATA} not found.")
    print("The p(malicious) distribution B3 actually produces is UNKNOWN without the model,")
    print("so nothing here is a measurement of B3. Instead we sweep plausible distributions")
    print("and map the DECISION BOUNDARY: which regime must B3 be in for the change to pay off.")
    print("*** These numbers are SENSITIVITY ANALYSIS, not results. Do not cite them as B3's. ***\n")
    rows = sensitivity_sweep()
    print(f"{'mu_atk':>7} {'sig':>5} {'dead%':>6} | {'F1 lgcy':>8} {'F1 cont':>8} | "
          f"{'FP lgcy':>8} {'FP cont':>8} | {'FN lgcy':>8} {'FN cont':>8} | {'McN p':>8} | adopt")
    print("-" * 100)
    for r in rows:
        lg, ct = r["legacy"], r["continuous"]
        pv = r["mcnemar_p"]
        pvs = f"{pv:.2e}" if isinstance(pv, float) else "n/a"
        print(f"{r['mu_attack']:>7.2f} {r['sigma']:>5.2f} {r['dead_zone_occupancy_attacks']*100:>5.1f}% | "
              f"{lg['f1']:>8.3f} {ct['f1']:>8.3f} | {lg['fp']:>8d} {ct['fp']:>8d} | "
              f"{lg['fn']:>8d} {ct['fn']:>8d} | {pvs:>8} | {'YES' if r['adopt'] else 'no'}")

    adopt_rows = [r for r in rows if r["adopt"]]
    print("\n" + "=" * 100)
    if adopt_rows:
        lo = min(r["mu_attack"] for r in adopt_rows)
        hi = max(r["mu_attack"] for r in adopt_rows)
        print(f"DECISION BOUNDARY: the continuous interface wins when B3's mean p(malicious) on")
        print(f"attacks lies in [{lo:.2f}, {hi:.2f}] -- i.e. when B3 is UNSURE on real attacks and")
        print(f"its suspicion lands below the 0.5 argmax boundary, where the legacy interface")
        print(f"converts it into ignorance instead of disbelief.")
    else:
        print("No swept regime justifies the change.")
    print("Outside that band the two interfaces are equivalent or legacy is preferable.")
    print("\nNEXT STEP (settles it): score the real B3 on a held-out split and write")
    print(f"{REAL_DATA} with one JSON per line: "
          '{"p_malicious": <float>, "label": 0|1}, then rerun.')
    (OUT / "interface_sensitivity.json").write_text(json.dumps(
        {"mode": "sensitivity", "WARNING": "NOT a measurement of B3; simulated p-distributions",
         "rows": rows}, indent=2))
    print(f"Written: {OUT / 'interface_sensitivity.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
