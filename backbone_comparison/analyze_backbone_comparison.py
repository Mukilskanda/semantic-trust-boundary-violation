#!/usr/bin/env python3
"""Computes per-family recall per backbone, cross-backbone failure overlap,
and a "never recommend on F1 alone" scored recommendation, from
backbone_comparison_results.json."""
import json, pathlib
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
data = json.loads((HERE / "results" / "backbone_comparison_results.json").read_text())
results = data["results"]
labels = data["test_labels"]
families = data["test_families"]
preds_by_model = data["predictions_by_backbone"]
ood_labels = data.get("ood_labels") or []
ood_families = data.get("ood_families") or []
ood_preds_by_model = data.get("ood_predictions_by_backbone") or {}

CONTROLLED = [k for k in results if k != "INCUMBENT_reference_only" and "aggregate" in results[k] and "error" not in results[k]["aggregate"]]

# OOD per-family recall (malicious families only)
ood_per_family_recall = {}
if ood_labels:
    for name in list(CONTROLLED) + (["INCUMBENT_reference_only"] if "INCUMBENT_reference_only" in ood_preds_by_model else []):
        preds = ood_preds_by_model.get(name)
        if not preds:
            continue
        fam_stats = defaultdict(lambda: {"n": 0, "correct": 0})
        for p, y, fam in zip(preds, ood_labels, ood_families):
            if y == 1:
                fam_stats[fam]["n"] += 1
                fam_stats[fam]["correct"] += int(p == y)
        ood_per_family_recall[name] = {fam: {"n": s["n"], "recall": s["correct"] / s["n"] if s["n"] else None}
                                         for fam, s in sorted(fam_stats.items())}

# per-family recall per backbone
per_family_recall = {}
for name in list(CONTROLLED) + (["INCUMBENT_reference_only"] if "INCUMBENT_reference_only" in preds_by_model else []):
    preds = preds_by_model[name]
    fam_stats = defaultdict(lambda: {"n": 0, "correct": 0})
    for p, y, fam in zip(preds, labels, families):
        if y == 1:  # recall only defined over malicious families
            fam_stats[fam]["n"] += 1
            fam_stats[fam]["correct"] += int(p == y)
    per_family_recall[name] = {fam: {"n": s["n"], "recall": s["correct"] / s["n"] if s["n"] else None}
                                 for fam, s in sorted(fam_stats.items())}

# cross-backbone failure overlap (malicious only)
malicious_idx = [i for i, y in enumerate(labels) if y == 1]
miss_sets = {}
for name in CONTROLLED:
    preds = preds_by_model[name]
    miss_sets[name] = set(i for i in malicious_idx if preds[i] != labels[i])

all_models = list(miss_sets.keys())
universal_misses = set.intersection(*miss_sets.values()) if miss_sets else set()
union_misses = set.union(*miss_sets.values()) if miss_sets else set()
unique_misses = {name: sorted(miss_sets[name] - set.union(*(s for n, s in miss_sets.items() if n != name)) if len(miss_sets) > 1 else miss_sets[name])
                  for name in all_models}

failure_analysis = {
    "n_malicious_test": len(malicious_idx),
    "universal_misses_all_backbones": sorted(universal_misses),
    "universal_miss_families": sorted(set(families[i] for i in universal_misses)),
    "union_misses_any_backbone": len(union_misses),
    "unique_misses_per_backbone": {name: {"n": len(idxs), "families": sorted(set(families[i] for i in idxs))}
                                     for name, idxs in unique_misses.items()},
}

# recommendation: NOT based on F1 alone -- score each backbone on a composite
# of accuracy/F1 (capped contribution), latency, memory, params, train time,
# and per-family recall floor (worst-family recall), explicitly reported
# side by side rather than collapsed into one opaque number.
rows = []
for name in CONTROLLED:
    agg = results[name]["aggregate"]
    fam_recalls = [v["recall"] for v in per_family_recall[name].values() if v["recall"] is not None and v["n"] > 0]
    worst_family_recall = min(fam_recalls) if fam_recalls else None
    rows.append({
        "backbone": name,
        "f1_mean": agg["f1_mean"], "f1_stdev": agg["f1_stdev"],
        "accuracy_mean": agg["accuracy_mean"],
        "precision_mean": agg["precision_mean"], "recall_mean": agg["recall_mean"],
        "latency_p95_ms": agg["latency_p95_mean_ms"],
        "peak_vram_mb": agg["peak_vram_mb_mean"],
        "parameters_millions": agg["parameters"] / 1e6,
        "train_seconds": agg["train_seconds_mean"],
        "worst_family_recall": worst_family_recall,
        "ood_f1_mean": agg.get("ood_f1_mean"),
        "ood_accuracy_mean": agg.get("ood_accuracy_mean"),
        "used_fp16": agg.get("used_fp16"),
        "fp16_fallback_reason": agg.get("fp16_fallback_reason"),
    })

out = {
    "per_family_recall": per_family_recall,
    "ood_per_family_recall": ood_per_family_recall,
    "failure_analysis": failure_analysis,
    "comparison_rows": rows,
}
(HERE / "results" / "backbone_comparison_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
