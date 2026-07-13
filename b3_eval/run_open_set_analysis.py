"""
b3_eval/run_open_set_analysis.py
===================================
Phase 8 decision experiment: does B3 need an explicit UNKNOWN/ABSTAIN
mechanism, or is binary classification + calibrated confidence sufficient?

READ FIRST: UNKNOWN_ABSTAIN_DETERMINATION.md. Two of the three candidate
UNKNOWN designs are already ruled out ANALYTICALLY (no GPU needed, and
regression-locked in tests/test_abstain_semantics.py):
  - UNKNOWN -> vacuous (Theta) mass  = provable no-op under the STBV premise
  - UNKNOWN -> disbelief (not_A) mass = repeats the CP semantics bug that
    CHANGELOG.md just fixed (ignorance is not evidence of guilt; Shafer 1976)
What remains is an EMPIRICAL question that only the real model can answer,
and this script answers it.

THE DECISIVE QUESTION
---------------------
When B3 meets an attack from an UNSEEN family (open-set condition), does it:
  (a) fail LOUDLY -- assign low/ambiguous confidence, so the existing
      Theta-mass path already routes it to CAUTION => binary + calibrated
      confidence is SUFFICIENT, implement nothing; or
  (b) fail SILENTLY -- confidently predict BENIGN => the attack is ACCEPTed
      and no amount of calibration helps, because temperature scaling
      provably cannot fix confidently-wrong predictions on OOD inputs
      (softmax conflates aleatoric and epistemic uncertainty and stays
      overconfident far from the training distribution -- Hendrycks &
      Gimpel 2017; Liang et al. ODIN 2018; and see arXiv:2510.08631 §2.2)
      => an abstain/OOD mechanism IS justified.

WHAT THIS MEASURES
------------------
1. Score distributions on three populations:
     ID-benign, ID-malicious (seen families), OOD-malicious (held-out family)
   using two scores that need NO retraining and NO new head:
     - MSP  (max softmax probability; Hendrycks & Gimpel 2017 baseline)
     - Energy score (-logsumexp of logits; Liu et al. NeurIPS 2020) --
       consistently a stronger OOD signal than MSP at zero extra cost
2. OOD AUROC: can either score separate unseen-family ATTACKS from benign?
3. Selective classification: risk-coverage curve + AURC, and coverage at a
   target risk (Geifman & El-Yaniv 2017; El-Yaniv & Wiener 2010).
4. THE HEADLINE NUMBER -- silent-failure rate:
     among unseen-family ATTACKS that B3 gets WRONG, what fraction did it
     call BENIGN with confidence >= 0.85 (i.e. high-confidence wrong, which
     the fusion layer will ACCEPT and which calibration cannot rescue)?
5. Dead-zone occupancy: fraction of unseen-family attacks landing in
   p_malicious in [0.35, 0.50) -- real suspicion that the current
   argmax->max-prob contract discards entirely (claim C3).

DECISION RULE (encoded below, not left to taste)
------------------------------------------------
  IF silent_failure_rate >= 0.20  -> abstain/OOD mechanism JUSTIFIED.
     Minimal fix, in priority order (do NOT add a discrete UNKNOWN class):
       (i)  expose continuous p_malicious in SemanticResult and let the DS
            mass use it (recovers the dead zone; no retraining, no new head,
            no architecture change), and/or
       (ii) add the energy score as an OOD gate feeding Theta mass, with a
            TrustPolicy floor at CAUTION when it fires.
  ELIF dead_zone_occupancy >= 0.15 -> fix (i) alone is justified.
  ELSE -> binary + calibrated confidence is SUFFICIENT. Implement nothing.
          Report these numbers as the evidence for that claim.

REQUIRES
--------
  b3_eval/data/id_split.jsonl        {"text":..., "label":0|1}  (seen families)
  b3_eval/data/ood_split.jsonl       {"text":..., "label":1, "family":"AF7"}
                                     (attacks from HELD-OUT families only)
The repo's own error_analysis.py already references exactly such a split
(outputs/splits/test1_stbv_unseen_families.json) -- restore it and convert.

Run:  python3 b3_eval/run_open_set_analysis.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from b3_eval._harness import (checkpoint_status, env_manifest, load_predictor,
                                torch_status, write_json)

OUT = ROOT / "b3_eval" / "results"
DATA = ROOT / "b3_eval" / "data"

SILENT_FAILURE_THRESHOLD = 0.20
DEAD_ZONE_THRESHOLD = 0.15
HIGH_CONF = 0.85          # mirrors B3RiskPolicy.high_confidence
DEAD_ZONE = (0.35, 0.50)  # p_malicious band discarded by the argmax contract


def load_jsonl(p):
    if not p.exists():
        return None
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def logits_for(predictor, texts, batch=32):
    import torch
    pairs = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            enc = predictor.tokenizer(texts[i:i + batch], max_length=predictor.max_length,
                                       padding=True, truncation=True,
                                       return_tensors="pt").to(predictor.device)
            for row in predictor.model(**enc).logits.cpu().tolist():
                pairs.append((row[0], row[1]))
    return pairs


def softmax2(z0, z1, T=1.0):
    m = max(z0 / T, z1 / T)
    e0, e1 = math.exp(z0 / T - m), math.exp(z1 / T - m)
    return e0 / (e0 + e1), e1 / (e0 + e1)


def energy(z0, z1, T=1.0):
    """Free energy score (Liu et al., NeurIPS 2020):
           E(x) = -T * logsumexp(logits / T)
    In-distribution inputs produce large logits -> large logsumexp -> LOW
    (very negative) energy. OOD inputs produce small/flat logits -> small
    logsumexp -> HIGHER energy. So HIGHER energy = more OOD, which matches
    the convention auroc() expects for its positive class.
    (Sanity-checked in tests/test_open_set_math.py: a confident sample must
    score strictly LOWER than a flat one.)"""
    m = max(z0 / T, z1 / T)
    lse = m + math.log(math.exp(z0 / T - m) + math.exp(z1 / T - m))
    return -(T * lse)


def auroc(scores_pos, scores_neg):
    """AUROC via rank statistic. pos = should score HIGH."""
    if not scores_pos or not scores_neg:
        return float("nan")
    data = [(s, 1) for s in scores_pos] + [(s, 0) for s in scores_neg]
    data.sort(key=lambda x: x[0])
    ranks, i, n = {}, 0, len(data)
    # average ranks for ties
    while i < n:
        j = i
        while j + 1 < n and data[j + 1][0] == data[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    sum_pos = sum(ranks[k] for k in range(n) if data[k][1] == 1)
    npos, nneg = len(scores_pos), len(scores_neg)
    return (sum_pos - npos * (npos + 1) / 2.0) / (npos * nneg)


def risk_coverage(confidences, correct):
    """Sort by confidence desc; risk = error rate among retained."""
    order = sorted(zip(confidences, correct), key=lambda x: -x[0])
    pts, errs = [], 0
    for i, (_, ok) in enumerate(order, start=1):
        errs += (0 if ok else 1)
        pts.append((i / len(order), errs / i))   # (coverage, risk)
    aurc = sum(r for _, r in pts) / len(pts)
    return pts, aurc


def main():
    manifest = env_manifest("b3_open_set_analysis")
    id_rows = load_jsonl(DATA / "id_split.jsonl")
    ood_rows = load_jsonl(DATA / "ood_split.jsonl")
    ck, tt = checkpoint_status(), torch_status()

    print("=" * 78)
    print("B3 OPEN-SET / SELECTIVE-CLASSIFICATION ANALYSIS")
    print("Decides: is an UNKNOWN/ABSTAIN mechanism justified?")
    print("=" * 78)

    blockers = []
    if id_rows is None:
        blockers.append(f"missing {DATA / 'id_split.jsonl'}")
    if ood_rows is None:
        blockers.append(f"missing {DATA / 'ood_split.jsonl'} (HELD-OUT attack families)")
    if not ck["ok"]:
        blockers.append(ck["reason"])
    if not tt["ok"]:
        blockers.append(tt["reason"])
    if blockers:
        print("\nCANNOT RUN -- blockers:")
        for b in blockers:
            print(f"  - {b}")
        print("\nNOTE: two of the three UNKNOWN designs are ALREADY ruled out analytically")
        print("(no GPU needed) -- see UNKNOWN_ABSTAIN_DETERMINATION.md and run:")
        print("    python3 tests/test_abstain_semantics.py")
        print("This script settles the remaining empirical question only.")
        write_json({"manifest": manifest, "status": "blocked", "blockers": blockers},
                   OUT / "open_set_analysis.json")
        return 0

    predictor, reason = load_predictor()
    if predictor is None:
        print(f"CANNOT RUN: {reason}")
        write_json({"manifest": manifest, "status": "blocked", "blockers": [reason]},
                   OUT / "open_set_analysis.json")
        return 0

    # optional fitted temperature from run_calibration.py
    T = 1.0
    cal = OUT / "calibration.json"
    if cal.exists():
        try:
            T = float(json.loads(cal.read_text()).get("temperature", 1.0))
            print(f"\nUsing fitted temperature T={T:.3f} from run_calibration.py")
        except Exception:
            pass

    id_texts = [r["text"] for r in id_rows]
    id_labels = [int(r["label"]) for r in id_rows]
    ood_texts = [r["text"] for r in ood_rows]

    id_logits = logits_for(predictor, id_texts)
    ood_logits = logits_for(predictor, ood_texts)

    id_p = [softmax2(z0, z1, T)[1] for z0, z1 in id_logits]      # p(malicious)
    ood_p = [softmax2(z0, z1, T)[1] for z0, z1 in ood_logits]
    id_msp = [max(p, 1 - p) for p in id_p]
    ood_msp = [max(p, 1 - p) for p in ood_p]
    id_energy = [energy(z0, z1, T) for z0, z1 in id_logits]
    ood_energy = [energy(z0, z1, T) for z0, z1 in ood_logits]

    id_benign_idx = [i for i, y in enumerate(id_labels) if y == 0]
    id_mal_idx = [i for i, y in enumerate(id_labels) if y == 1]

    # ---- headline: silent-failure rate on unseen families -----------------
    ood_pred = [1 if p >= 0.5 else 0 for p in ood_p]   # truth is 1 (attack) for all
    wrong = [i for i, pr in enumerate(ood_pred) if pr == 0]
    silent = [i for i in wrong if ood_msp[i] >= HIGH_CONF]
    silent_rate = len(silent) / len(ood_rows)
    miss_rate = len(wrong) / len(ood_rows)
    dead_zone = [i for i, p in enumerate(ood_p) if DEAD_ZONE[0] <= p < DEAD_ZONE[1]]
    dead_rate = len(dead_zone) / len(ood_rows)

    # ---- OOD separability: unseen-family attacks vs ID benign -------------
    # (score convention: HIGHER = more suspicious/OOD)
    auroc_msp = auroc([1 - m for m in [ood_msp[i] for i in range(len(ood_p))]],
                      [1 - id_msp[i] for i in id_benign_idx])
    auroc_energy = auroc([ood_energy[i] for i in range(len(ood_p))],
                         [id_energy[i] for i in id_benign_idx])
    auroc_pmal = auroc(ood_p, [id_p[i] for i in id_benign_idx])

    # ---- selective classification on ID ----------------------------------
    id_correct = [1 if (1 if id_p[i] >= 0.5 else 0) == id_labels[i] else 0
                  for i in range(len(id_labels))]
    rc_pts, aurc = risk_coverage(id_msp, id_correct)
    cov_at_risk = {}
    for target in (0.01, 0.05, 0.10):
        feasible = [c for c, r in rc_pts if r <= target]
        cov_at_risk[f"coverage@risk<={target}"] = max(feasible) if feasible else 0.0

    print(f"\nID set: {len(id_rows)} ({len(id_mal_idx)} malicious / {len(id_benign_idx)} benign)")
    print(f"OOD set (unseen attack families): {len(ood_rows)} attacks")
    print("\n--- HEADLINE ---")
    print(f"  miss rate on unseen families              : {miss_rate:.3f}")
    print(f"  SILENT-FAILURE rate (wrong AND conf>={HIGH_CONF}): {silent_rate:.3f}  <-- decides it")
    print(f"  dead-zone occupancy (p_mal in [{DEAD_ZONE[0]},{DEAD_ZONE[1]}))   : {dead_rate:.3f}")
    print("\n--- OOD separability (unseen-family attacks vs ID benign) ---")
    print(f"  AUROC, MSP (1 - max softmax) : {auroc_msp:.3f}")
    print(f"  AUROC, energy score          : {auroc_energy:.3f}")
    print(f"  AUROC, p_malicious           : {auroc_pmal:.3f}")
    print("\n--- Selective classification (ID) ---")
    print(f"  AURC (lower is better): {aurc:.4f}")
    for k, v in cov_at_risk.items():
        print(f"  {k}: {v:.3f}")

    # ---- decision --------------------------------------------------------
    if silent_rate >= SILENT_FAILURE_THRESHOLD:
        decision = (
            f"ABSTAIN/OOD MECHANISM JUSTIFIED. B3 fails SILENTLY on "
            f"{silent_rate:.1%} of unseen-family attacks (high-confidence BENIGN), which the "
            f"fusion layer ACCEPTs and which temperature scaling provably cannot fix "
            f"(calibration does not repair confidently-wrong OOD predictions). "
            f"Do NOT add a discrete UNKNOWN class (ruled out analytically -- see "
            f"tests/test_abstain_semantics.py). Minimal fix: expose continuous p_malicious "
            f"into the DS mass, and add the energy score (AUROC {auroc_energy:.3f}) as an OOD "
            f"gate feeding Theta mass with a TrustPolicy CAUTION floor.")
    elif dead_rate >= DEAD_ZONE_THRESHOLD:
        decision = (
            f"PARTIAL FIX JUSTIFIED. Silent-failure rate is acceptable ({silent_rate:.1%}), but "
            f"{dead_rate:.1%} of unseen-family attacks land in the p_malicious dead zone "
            f"[{DEAD_ZONE[0]},{DEAD_ZONE[1]}) that the argmax->max-prob contract discards. "
            f"Expose continuous p_malicious into the DS mass (no retraining, no new class, "
            f"no architecture change). A discrete UNKNOWN class remains unjustified.")
    else:
        decision = (
            f"NO ABSTAIN MECHANISM NEEDED. Binary classification + calibrated confidence is "
            f"SUFFICIENT: silent-failure rate on unseen families is only {silent_rate:.1%} and "
            f"dead-zone occupancy only {dead_rate:.1%}, i.e. B3 fails LOUDLY (low confidence), "
            f"and the existing Theta-mass path already routes those to CAUTION. Report these "
            f"numbers as the evidence. Implement nothing.")

    print("\n" + "=" * 78)
    print("DECISION: " + decision)

    write_json({"manifest": manifest, "temperature": T,
                 "n_id": len(id_rows), "n_ood": len(ood_rows),
                 "miss_rate_ood": miss_rate, "silent_failure_rate": silent_rate,
                 "dead_zone_occupancy": dead_rate,
                 "auroc": {"msp": auroc_msp, "energy": auroc_energy, "p_malicious": auroc_pmal},
                 "selective": {"aurc": aurc, **cov_at_risk},
                 "thresholds": {"silent_failure": SILENT_FAILURE_THRESHOLD,
                                 "dead_zone": DEAD_ZONE_THRESHOLD, "high_conf": HIGH_CONF},
                 "decision": decision}, OUT / "open_set_analysis.json")

    # plots
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(3.6, 3.2))
        ax.plot([c for c, _ in rc_pts], [r for _, r in rc_pts], lw=1.6)
        ax.set_xlabel("coverage"); ax.set_ylabel("risk (error rate)")
        ax.set_title(f"Risk-Coverage (AURC={aurc:.3f})", fontsize=9)
        fig.tight_layout(); fig.savefig(OUT / "risk_coverage.png", dpi=200); plt.close(fig)

        fig, ax = plt.subplots(figsize=(4.0, 3.2))
        ax.hist([id_p[i] for i in id_benign_idx], bins=20, alpha=.6, label="ID benign", density=True)
        ax.hist([id_p[i] for i in id_mal_idx], bins=20, alpha=.6, label="ID malicious", density=True)
        ax.hist(ood_p, bins=20, alpha=.6, label="OOD (unseen family) attacks", density=True)
        ax.axvspan(DEAD_ZONE[0], DEAD_ZONE[1], color="red", alpha=.12, label="discarded dead zone")
        ax.axvline(0.5, color="k", ls="--", lw=.8)
        ax.set_xlabel("p(malicious)"); ax.set_ylabel("density"); ax.legend(fontsize=6)
        fig.tight_layout(); fig.savefig(OUT / "openset_score_distributions.png", dpi=200); plt.close(fig)
        print(f"Plots: {OUT}/risk_coverage.png, {OUT}/openset_score_distributions.png")
    except Exception as e:
        print(f"(plots skipped: {e})")

    print(f"Written: {OUT / 'open_set_analysis.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
