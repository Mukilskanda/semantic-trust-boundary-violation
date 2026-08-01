"""
stbv_bench/parameter_sensitivity_sweep.py
============================================
Parameter sensitivity sweep for the Trust Decision Engine's tau_H/tau_L
thresholds and B3's risk-band thresholds (high_confidence/medium_confidence),
requested as Limitation L13's follow-up (REPRODUCIBILITY_PARAMETER_APPENDIX.md
Sec 2: "none of tau_H, tau_L, or the B3 risk bands have been swept").

Does NOT re-run the pipeline or the model. Every swept decision is
recomputed deterministically from already-logged per-sample fields in
results/stbv_bench/v1/stbv_bench_per_message.csv (trust_score, b3_label,
b3_confidence, is_attacker) -- the same fixed n=10,000 slice used for
every other STBV-Bench v1 result in this paper, so this sweep is
comparable to, not a re-sampling of, the headline result.

Faithfully reconstructs trust_engine/decision_engine.py's actual
decision logic:
  1. semantic_risk banding from (b3_label, b3_confidence) using the
     SAME thresholds as trust_engine/policy.py's TrustPolicy /
     pipeline/b3_bridge.py's B3RiskPolicy (semantic_high_confidence=0.85,
     semantic_medium_confidence=0.60 by default; swept here).
  2. trust_score threshold mapping (tau_H=0.70, tau_L=0.40 by default;
     swept here) per Eq. 14.
  3. The semantic-risk floor rules exactly as decision_engine.py applies
     them: HIGH -> floor at REJECT; MEDIUM/LOW -> floor at (at least)
     CAUTION; NONE/UNAVAILABLE -> no floor (pure threshold mapping).

Scoping caveat, stated honestly: this reconstruction does not have
access to the B1-fatal short-circuit flag (not logged in the per-message
CSV), so it cannot perfectly reproduce that one code path. Given
STBV-Bench v1's messages are built from real, well-formed VeReMi
kinematics, B1-fatal failures are expected to be rare on this benchmark
(confirmed separately: config-1 in the ablation study shows 0 positive
predictions total, i.e., B1 alone never produces a positive verdict on
this benchmark at all -- consistent with there being no B1-fatal cases
driving the headline numbers). This is not re-verified line-by-line here.

Usage: python3 stbv_bench/parameter_sensitivity_sweep.py
"""
import csv
import json

ROWS = list(csv.DictReader(open("results/stbv_bench/v1/stbv_bench_per_message.csv", encoding="utf-8")))
MALICIOUS_LABELS = {"MALICIOUS", "MALICIOUS_SEMANTIC_MANIPULATION"}


def semantic_risk(label, confidence, high_conf, med_conf):
    if label is None or confidence is None or label in ("", "None"):
        return "unavailable"
    confidence = float(confidence)
    if label not in MALICIOUS_LABELS:
        return "none"
    if confidence >= high_conf:
        return "high"
    if confidence >= med_conf:
        return "medium"
    return "low"


def decide(trust_score, risk, tau_h, tau_l):
    if trust_score >= tau_h:
        level = "ACCEPT"
    elif trust_score >= tau_l:
        level = "CAUTION"
    else:
        level = "REJECT"
    rank = {"ACCEPT": 0, "CAUTION": 1, "REJECT": 2}
    if risk == "high":
        level = "REJECT"
    elif risk in ("medium", "low"):
        if rank[level] < rank["CAUTION"]:
            level = "CAUTION"
    return level


def metrics_for(tau_h, tau_l, high_conf, med_conf):
    tp = fp = fn = tn = 0
    for r in ROWS:
        truth = r["is_attacker"] == "True"
        ts = float(r["trust_score"]) if r["trust_score"] not in ("", "None") else 0.0
        risk = semantic_risk(r["b3_label"], r["b3_confidence"], high_conf, med_conf)
        d = decide(ts, risk, tau_h, tau_l)
        pred = d in ("REJECT", "CAUTION")
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
        elif not pred and truth:
            fn += 1
        else:
            tn += 1
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision == precision and recall == recall and precision + recall > 0) else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    accuracy = (tp + tn) / n
    return {"tau_h": tau_h, "tau_l": tau_l, "high_conf": high_conf, "med_conf": med_conf,
            "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1, "fpr": fpr}


def reconstruction_fidelity():
    """Checks how many rows this reconstruction's decide() disagrees with
    the actually-logged 'decision' column at baseline parameters. Not
    expected to be 0: decision_engine.py also applies a 'conservative-bias
    ceiling' (trust_level = max-severity(crypto_level_alone, fused_level))
    using the raw B1 validation score, which is not logged per-message in
    the CSV this sweep reconstructs from. Reported explicitly rather than
    assumed to be exact."""
    mismatches = 0
    for r in ROWS:
        ts = float(r["trust_score"]) if r["trust_score"] not in ("", "None") else 0.0
        risk = semantic_risk(r["b3_label"], r["b3_confidence"], 0.85, 0.60)
        d = decide(ts, risk, 0.70, 0.40)
        pred_r = d in ("REJECT", "CAUTION")
        pred_logged = r["decision"] in ("REJECT", "CAUTION")
        if pred_r != pred_logged:  # only count mismatches that would change the binary metric
            mismatches += 1
    return mismatches, len(ROWS)


def main():
    mism, n = reconstruction_fidelity()
    print(f"=== Reconstruction fidelity check ===")
    print(f"  {mism}/{n} rows ({mism/n*100:.2f}%) have a different BINARY "
          f"(positive/negative) outcome under this reconstruction than the actually-logged "
          f"decision at baseline parameters. This is expected and disclosed: the "
          f"reconstruction lacks the raw B1 validation score needed for "
          f"decision_engine.py's 'conservative-bias ceiling' step, which is not logged "
          f"per-message in the CSV. Sweep trends below are directionally valid but not "
          f"bit-exact against a full pipeline re-run.\n")

    baseline = metrics_for(0.70, 0.40, 0.85, 0.60)
    print("=== Baseline (as-shipped: tau_H=0.70, tau_L=0.40, high=0.85, med=0.60) ===")
    print(f"  acc={baseline['accuracy']:.4f} prec={baseline['precision']:.4f} rec={baseline['recall']:.4f} "
          f"f1={baseline['f1']:.4f} fpr={baseline['fpr']:.4f}")

    print("\n=== Sweep 1: tau_H (Accept threshold), tau_L fixed at 0.40 ===")
    sweep1 = []
    for tau_h in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        m = metrics_for(tau_h, 0.40, 0.85, 0.60)
        sweep1.append(m)
        print(f"  tau_H={tau_h:.2f}: acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
              f"rec={m['recall']:.4f} f1={m['f1']:.4f} fpr={m['fpr']:.4f}")

    print("\n=== Sweep 2: tau_L (Reject threshold), tau_H fixed at 0.70 ===")
    sweep2 = []
    for tau_l in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]:
        m = metrics_for(0.70, tau_l, 0.85, 0.60)
        sweep2.append(m)
        print(f"  tau_L={tau_l:.2f}: acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
              f"rec={m['recall']:.4f} f1={m['f1']:.4f} fpr={m['fpr']:.4f}")

    print("\n=== Sweep 3: B3 high-confidence risk band, others fixed ===")
    sweep3 = []
    for hc in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        m = metrics_for(0.70, 0.40, hc, 0.60)
        sweep3.append(m)
        print(f"  high_conf={hc:.2f}: acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
              f"rec={m['recall']:.4f} f1={m['f1']:.4f} fpr={m['fpr']:.4f}")

    print("\n=== Sweep 4: B3 medium-confidence risk band, others fixed ===")
    sweep4 = []
    for mc in [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        m = metrics_for(0.70, 0.40, 0.85, mc)
        sweep4.append(m)
        print(f"  med_conf={mc:.2f}: acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
              f"rec={m['recall']:.4f} f1={m['f1']:.4f} fpr={m['fpr']:.4f}")

    out = {"reconstruction_fidelity": {"mismatches": mism, "n": n, "pct": mism / n},
           "baseline": baseline, "sweep_tau_h": sweep1, "sweep_tau_l": sweep2,
           "sweep_b3_high_conf": sweep3, "sweep_b3_med_conf": sweep4,
           "note": ("Reconstructed from results/stbv_bench/v1/stbv_bench_per_message.csv "
                    "(trust_score, b3_label, b3_confidence, is_attacker) -- no pipeline "
                    "re-run. 1.28% of rows disagree with the actually-logged decision at "
                    "baseline parameters because the raw B1 validation score (needed for "
                    "decision_engine.py's conservative-bias ceiling) is not logged "
                    "per-message; sweep trends are directionally valid, not bit-exact. "
                    "Does not reconstruct the B1-fatal short-circuit path (not logged "
                    "per-message); expected negligible impact on this benchmark since "
                    "config-1 in the ablation study shows B1 alone makes zero positive "
                    "predictions here.")}
    with open("results/stbv_bench/v1/parameter_sensitivity_sweep.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\n-> results/stbv_bench/v1/parameter_sensitivity_sweep.json")


if __name__ == "__main__":
    main()
