#!/usr/bin/env python3
"""
evaluate_external.py
======================
Evaluates the FROZEN, already-fine-tuned B3 checkpoint (no retraining,
no gradient updates) against external_corpus.json -- the independently
authored/generated external semantic evaluation corpus.

Reports: accuracy, precision, recall, F1, confusion counts, ROC (points +
AUC), PR (points + AUC), calibration (ECE/Brier, raw and with the
already-existing T=2.144598 temperature applied post-hoc, NOT refit here),
and per-family recall.

Does not modify B3. Read-only inference only.

Run:
    python3 external_semantic_eval/evaluate_external.py
"""
from __future__ import annotations
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "b3" / "solution_stb" / "b3_semantic_gate"))

HERE = pathlib.Path(__file__).resolve().parent
EXISTING_T = 2.144598003491752  # from b3_eval/results/calibration.json; NOT refit here


def checkpoint_status():
    model_dir = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"
    binp = model_dir / "pytorch_model.bin"
    if not binp.exists():
        return {"ok": False, "reason": f"no weight file under {model_dir}"}, model_dir
    size = binp.stat().st_size
    if size < 10_000:
        return {"ok": False, "reason": f"{binp.name} is a {size}-byte LFS pointer, not weights"}, model_dir
    import hashlib
    return {"ok": True, "size_bytes": size,
            "sha256_16": hashlib.sha256(binp.read_bytes()).hexdigest()[:16]}, model_dir


def main():
    corpus_path = HERE / "external_corpus.json"
    if not corpus_path.exists():
        print("[FATAL] external_corpus.json not found -- run build_external_corpus.py first.")
        return 2
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    entries = corpus["entries"]
    if not entries:
        print("[FATAL] corpus has zero entries.")
        return 3

    ck, model_dir = checkpoint_status()
    if not ck["ok"]:
        print(f"[SKIP] checkpoint unavailable: {ck['reason']}")
        print("No numbers fabricated. Re-run once the checkpoint is materialized (git lfs pull).")
        write_json({"manifest": {"checkpoint": ck}, "status": "SKIPPED_NO_CHECKPOINT"},
                    HERE / "external_eval_results.json")
        return 0

    try:
        import torch
        from inference import get_predictor
    except Exception as e:
        print(f"[SKIP] torch/predictor import failed: {e}")
        return 0

    predictor = get_predictor(str(model_dir), max_length=256)

    texts = [e["text"] for e in entries]
    true_labels = [1 if e["label"] == "MALICIOUS" else 0 for e in entries]
    families = [e["family"] for e in entries]
    sources = [e["source"] for e in entries]

    results = predictor.predict(texts, batch_size=32)
    pred_ids = [r.label_id for r in results]
    conf = [float(r.confidence) for r in results]
    # reconstruct P(malicious) as a continuous score for ROC/PR
    p_malicious = [c if pid == 1 else (1.0 - c) for pid, c in zip(pred_ids, conf)]

    n = len(entries)
    tp = sum(1 for t, p in zip(true_labels, pred_ids) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(true_labels, pred_ids) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(true_labels, pred_ids) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(true_labels, pred_ids) if t == 0 and p == 0)
    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) and not math.isnan(precision) and not math.isnan(recall) else float("nan"))

    # ---- ROC / PR (manual, no sklearn dependency assumed) ----
    def roc_pr_points(scores, labels):
        pairs = sorted(zip(scores, labels), key=lambda x: -x[0])
        P = sum(labels); N = len(labels) - P
        tp_c = fp_c = 0
        roc_pts, pr_pts = [(0.0, 0.0)], []
        prev_score = None
        for score, lab in pairs:
            if lab == 1: tp_c += 1
            else: fp_c += 1
            tpr = tp_c / P if P else 0.0
            fpr = fp_c / N if N else 0.0
            prec = tp_c / (tp_c + fp_c)
            roc_pts.append((fpr, tpr))
            pr_pts.append((tpr, prec))
        roc_pts.append((1.0, 1.0))
        return roc_pts, pr_pts

    def auc(points):
        pts = sorted(points)
        area = 0.0
        for i in range(1, len(pts)):
            x0, y0 = pts[i-1]; x1, y1 = pts[i]
            area += (x1 - x0) * (y0 + y1) / 2.0
        return area

    roc_pts, pr_pts = roc_pr_points(p_malicious, true_labels)
    roc_auc = auc(roc_pts)
    pr_auc = auc([(r, p) for r, p in pr_pts])

    # ---- Calibration: ECE + Brier, raw (T=1) and with existing T applied post-hoc ----
    def ece_brier(confidences, correct):
        n_bins = 10
        bins = [[] for _ in range(n_bins)]
        for c, k in zip(confidences, correct):
            idx = min(int(c * n_bins), n_bins - 1)
            bins[idx].append((c, k))
        ece = 0.0
        for b in bins:
            if not b: continue
            avg_conf = sum(c for c, _ in b) / len(b)
            acc = sum(k for _, k in b) / len(b)
            ece += (len(b) / len(confidences)) * abs(avg_conf - acc)
        brier = sum((c - k) ** 2 for c, k in zip(confidences, correct)) / len(confidences)
        return ece, brier

    correct = [1 if (t == p) else 0 for t, p in zip(true_labels, pred_ids)]
    ece_raw, brier_raw = ece_brier(conf, correct)

    # apply existing T post-hoc: need logits, not just confidence. Predictor's
    # confidence is post-softmax at T=1 for this run (config default), so we
    # approximate the T-rescaled confidence via the standard 2-class relation:
    # given p1 = softmax at T=1, recover the effective logit gap and rescale.
    def rescale_confidence(p1, T):
        p1 = min(max(p1, 1e-9), 1 - 1e-9)
        logit_gap = math.log(p1 / (1 - p1))  # z_pred - z_other at T=1
        rescaled_gap = logit_gap / T
        return 1.0 / (1.0 + math.exp(-rescaled_gap))

    conf_T = [rescale_confidence(c, EXISTING_T) for c in conf]
    ece_T, brier_T = ece_brier(conf_T, correct)

    # ---- per-family recall (malicious families only; recall undefined for benign_control) ----
    per_family = {}
    for e, t, p in zip(entries, true_labels, pred_ids):
        fam = e["family"]
        per_family.setdefault(fam, {"n": 0, "tp": 0, "fn": 0, "true_positives_total": 0})
        if t == 1:
            per_family[fam]["true_positives_total"] += 1
            if p == 1: per_family[fam]["tp"] += 1
            else: per_family[fam]["fn"] += 1
        per_family[fam]["n"] += 1
    per_family_recall = {}
    for fam, d in per_family.items():
        if d["true_positives_total"] > 0:
            per_family_recall[fam] = {
                "n_malicious": d["true_positives_total"],
                "recall": d["tp"] / d["true_positives_total"],
            }

    per_source = {}
    for e, t, p in zip(entries, true_labels, pred_ids):
        src = e["source"]
        per_source.setdefault(src, {"n": 0, "correct": 0})
        per_source[src]["n"] += 1
        per_source[src]["correct"] += int(t == p)
    per_source_accuracy = {s: {"n": d["n"], "accuracy": d["correct"] / d["n"]} for s, d in per_source.items()}

    out = {
        "manifest": {
            "experiment": "external_semantic_evaluation",
            "checkpoint": ck,
            "corpus_n": n,
            "corpus_by_source": corpus["by_source"],
            "corpus_by_family": corpus["by_family"],
            "corpus_by_label": corpus["by_label"],
            "note": "Frozen B3 checkpoint, NOT retrained or fine-tuned. Inference only.",
        },
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc": {"auc": roc_auc, "points_sample": roc_pts[::max(1, len(roc_pts)//20)]},
        "pr": {"auc": pr_auc, "points_sample": pr_pts[::max(1, len(pr_pts)//20)]},
        "calibration": {
            "raw_T1": {"ece": ece_raw, "brier": brier_raw},
            "with_existing_T_2p145_posthoc": {"ece": ece_T, "brier": brier_T},
            "note": "T=2.144598 was fit previously on an internal 85-sample split "
                    "(b3_eval/results/calibration.json); NOT refit on this external "
                    "corpus. Applying it here (rather than refitting) tests whether "
                    "the existing calibration transfers, which is the honest question.",
        },
        "per_family_recall": per_family_recall,
        "per_source_accuracy": per_source_accuracy,
        "per_message": [
            {"id": e["id"], "source": e["source"], "family": e["family"],
             "true_label": e["label"], "pred_label": "MALICIOUS" if p == 1 else "BENIGN",
             "confidence": c, "correct": bool(t == p)}
            for e, t, p, c in zip(entries, true_labels, pred_ids, conf)
        ],
    }
    write_json(out, HERE / "external_eval_results.json")
    print(json.dumps({k: v for k, v in out.items() if k != "per_message"}, indent=2))
    return 0


def write_json(obj, path):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
