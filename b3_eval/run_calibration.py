"""
b3_eval/run_calibration.py
============================
Part 7: confidence calibration for B3. Computes ECE, Brier score, a
reliability diagram, and a confidence histogram on a labeled held-out set,
then fits a single temperature-scaling parameter T (Guo et al., "On
Calibration of Modern Neural Networks", ICML 2017) as a POST-HOC fix that
leaves the classifier's weights and decisions unchanged -- it only rescales
logits before softmax, so argmax (the predicted label) is invariant while
the confidence used by B3RiskPolicy's 0.85/0.60 bands becomes calibrated.

Why this matters here: b3_bridge.B3RiskPolicy maps confidence directly to
risk_level, and the Trust Engine's Dempster-Shafer mass uses confidence as
the committed-mass fraction. Miscalibrated confidence therefore propagates
into the final trust decision. Calibrating confidence is the single
highest-value B3 change that requires NO retraining.

Requires a labeled split at b3_eval/data/calibration_split.jsonl (one JSON
object per line: {"text": ..., "label": 0|1}). If absent, prints the exact
schema and how to produce it from the repo's existing splits, and exits 0.

Run with:  python3 b3_eval/run_calibration.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from b3_eval._harness import load_predictor, env_manifest, write_json, MODEL_DIR

OUT = ROOT / "b3_eval" / "results"
SPLIT = ROOT / "b3_eval" / "data" / "calibration_split.jsonl"


def load_split():
    if not SPLIT.exists():
        return None
    rows = []
    for line in SPLIT.read_text().splitlines():
        line = line.strip()
        if line:
            o = json.loads(line)
            rows.append((o["text"], int(o["label"])))
    return rows


def _softmax2(z0, z1):
    m = max(z0, z1)
    e0, e1 = math.exp(z0 - m), math.exp(z1 - m)
    return e0 / (e0 + e1), e1 / (e0 + e1)


def ece_and_brier(confidences, correct, probs_pos, labels, n_bins=10):
    # ECE over max-prob confidence
    bins = [[] for _ in range(n_bins)]
    for c, ok in zip(confidences, correct):
        idx = min(int(c * n_bins), n_bins - 1)
        bins[idx].append((c, ok))
    ece = 0.0
    reliability = []
    total = len(confidences)
    for b in bins:
        if not b:
            reliability.append(None)
            continue
        avg_conf = sum(c for c, _ in b) / len(b)
        acc = sum(ok for _, ok in b) / len(b)
        ece += (len(b) / total) * abs(avg_conf - acc)
        reliability.append({"avg_conf": avg_conf, "accuracy": acc, "count": len(b)})
    brier = sum((p - y) ** 2 for p, y in zip(probs_pos, labels)) / len(labels)
    return ece, brier, reliability


def fit_temperature(logit_pairs, labels, lo=0.05, hi=10.0, iters=200):
    """Fit a single temperature T > 0 by minimizing mean NLL (Guo et al.,
    "On Calibration of Modern Neural Networks", ICML 2017).

    Uses bounded ternary search rather than fixed-learning-rate gradient
    descent: the NLL gradient's magnitude scales with dataset size, so a
    fixed lr diverges on larger sets (observed: T -> 630 on a 2000-sample
    underconfident set). Ternary search is scale-free, needs no lr, and NLL
    is unimodal in T here. Argmax -- and therefore every predicted label --
    is invariant to T; only confidence is rescaled.
    """
    def mean_nll(Tv):
        s = 0.0
        for (z0, z1), y in zip(logit_pairs, labels):
            p0, p1 = _softmax2(z0 / Tv, z1 / Tv)
            py = p1 if y == 1 else p0
            s -= math.log(max(py, 1e-12))
        return s / len(labels)

    for _ in range(iters):
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if mean_nll(m1) < mean_nll(m2):
            hi = m2
        else:
            lo = m1
        if hi - lo < 1e-4:
            break
    return (lo + hi) / 2.0


def main():
    rows = load_split()
    manifest = env_manifest("b3_calibration")
    if rows is None:
        print("=" * 78)
        print("B3 CALIBRATION -- NO LABELED SPLIT FOUND")
        print("=" * 78)
        print(f"Expected: {SPLIT}")
        print("Schema: one JSON object per line -> {\"text\": <str>, \"label\": 0|1}")
        print("Produce it from the project's existing held-out split, e.g. the")
        print("test1_stbv_unseen_families.json referenced by b3/.../error_analysis.py:")
        print('  python3 -c "import json,pandas as pd; df=pd.read_json(SPLIT); '
              '[print(json.dumps({\'text\':r.text,\'label\':int(r.label)})) for r in df.itertuples()]"'
              ' > b3_eval/data/calibration_split.jsonl')
        write_json({"manifest": manifest, "status": "no_split"}, OUT / "calibration.json")
        return 0

    predictor, reason = load_predictor()
    if predictor is None:
        print(f"Split present ({len(rows)} rows) but model unavailable: {reason}")
        write_json({"manifest": manifest, "status": "model_unavailable", "reason": reason,
                     "n_rows": len(rows)}, OUT / "calibration.json")
        return 0

    # Need raw logits for temperature scaling -> call the underlying model.
    import torch
    texts = [t for t, _ in rows]
    labels = [y for _, y in rows]
    logit_pairs = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            batch = texts[i:i + 32]
            enc = predictor.tokenizer(batch, max_length=predictor.max_length,
                                       padding=True, truncation=True, return_tensors="pt").to(predictor.device)
            out = predictor.model(**enc)
            for row in out.logits.cpu().tolist():
                logit_pairs.append((row[0], row[1]))

    def metrics_at(T):
        confs, correct, probs_pos = [], [], []
        for (z0, z1), y in zip(logit_pairs, labels):
            p0, p1 = _softmax2(z0 / T, z1 / T)
            pred = 1 if p1 >= p0 else 0
            confs.append(max(p0, p1))
            correct.append(int(pred == y))
            probs_pos.append(p1)
        ece, brier, reliability = ece_and_brier(confs, correct, probs_pos, labels)
        return ece, brier, reliability, confs

    ece0, brier0, rel0, confs0 = metrics_at(1.0)
    T = fit_temperature(logit_pairs, labels)
    ece1, brier1, rel1, confs1 = metrics_at(T)

    print("=" * 78)
    print("B3 CALIBRATION (real model)")
    print("=" * 78)
    print(f"N = {len(rows)}")
    print(f"Before (T=1.0): ECE={ece0:.4f}  Brier={brier0:.4f}")
    print(f"Fitted temperature T = {T:.3f}")
    print(f"After  (T={T:.3f}): ECE={ece1:.4f}  Brier={brier1:.4f}")
    print(f"ECE improvement: {ece0 - ece1:+.4f}")

    # confidence histogram (10 bins)
    hist = [0] * 10
    for c in confs0:
        hist[min(int(c * 10), 9)] += 1

    result = {"manifest": manifest, "n": len(rows),
              "before": {"ece": ece0, "brier": brier0, "reliability": rel0},
              "temperature": T,
              "after": {"ece": ece1, "brier": brier1, "reliability": rel1},
              "confidence_histogram_10bin": hist,
              "recommendation": (
                  f"Apply temperature T={T:.3f} in b3_bridge before risk banding "
                  "if ECE improved materially (>0.01). This changes NO labels; it only "
                  "rescales confidence, which B3RiskPolicy and the DS mass depend on."
                  if (ece0 - ece1) > 0.01 else
                  "Model is already well-calibrated (ECE improvement < 0.01); temperature "
                  "scaling not needed. Report the ECE/Brier as evidence of calibration.")}
    write_json(result, OUT / "calibration.json")
    # Try to draw reliability diagram if matplotlib present.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(3.4, 3.4))
        ax.plot([0, 1], [0, 1], "--", color="gray", lw=0.8)
        xs = [r["avg_conf"] for r in rel0 if r]
        ys = [r["accuracy"] for r in rel0 if r]
        ax.plot(xs, ys, "o-", label=f"T=1 (ECE={ece0:.3f})")
        xs1 = [r["avg_conf"] for r in rel1 if r]
        ys1 = [r["accuracy"] for r in rel1 if r]
        ax.plot(xs1, ys1, "s-", label=f"T={T:.2f} (ECE={ece1:.3f})")
        ax.set_xlabel("confidence"); ax.set_ylabel("accuracy"); ax.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(OUT / "reliability_diagram.png", dpi=200)
        print(f"Reliability diagram: {OUT / 'reliability_diagram.png'}")
    except Exception:
        pass
    print(f"Written: {OUT / 'calibration.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
