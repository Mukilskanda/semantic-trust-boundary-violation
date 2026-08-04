#!/usr/bin/env python3
"""
validation/build_validation_sample.py
======================================
Builds a stratified 300-message human-validation sample for STBV-Bench and
emits blank annotation templates for two independent annotators.

WHY THIS EXISTS. STBV-Bench's ground-truth labels are assigned by the same
generator that produced the text. Nothing in the paper currently verifies
that a message labelled `malicious` reads as malicious to a competent human,
or that a `benign_control` message reads as benign. If the generator emits a
benign-reading sentence under a malicious label, then what the paper counts
as a detector "miss" may in fact be correct detector behaviour on a
mislabelled item. This study measures that.

THIS SCRIPT DOES NOT PRODUCE ANNOTATIONS. It produces the sample and empty
forms. `label` columns in the annotator templates are intentionally blank
and MUST be filled by humans. `agreement_analysis.py` refuses to run on
unfilled or auto-filled templates.

Run:
    python validation/build_validation_sample.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "validation"
OUT.mkdir(parents=True, exist_ok=True)
BENCH_JSONL = ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl"

N_TOTAL = 300
N_SAMPLES = 10_000        # the paper's evaluated slice
SEED = 20260802           # distinct from the modelling seed (42) on purpose


def peer_text(tm):
    sc = tm.get("scene_context", {}) or {}
    parts = list(sc.get("peer_reports", [])) + list(sc.get("rsu_messages", []))
    return " ".join(parts).strip()


def main():
    rng = np.random.default_rng(SEED)

    rows = []
    with open(BENCH_JSONL, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= N_SAMPLES:
                break
            r = json.loads(line)
            tm = r["transformed_message"]
            rows.append({
                "sample_id": r["sample_id"],
                "attack_family": r["attack_family"],
                "ground_truth": "malicious" if tm.get("is_attacker") else "benign",
                "severity": r.get("severity", ""),
                "transformation_rule": r.get("transformation_rule", ""),
                "semantic_objective": r.get("semantic_objective", ""),
                "message": peer_text(tm),
            })

    # ---- stratified allocation across all families, proportional w/ floor ----
    by_fam = {}
    for r in rows:
        by_fam.setdefault(r["attack_family"], []).append(r)
    fams = sorted(by_fam)
    base = max(1, N_TOTAL // len(fams))
    alloc = {fam: min(base, len(by_fam[fam])) for fam in fams}
    # distribute the remainder to the largest families, deterministically
    rem = N_TOTAL - sum(alloc.values())
    for fam in sorted(fams, key=lambda f: -len(by_fam[f])):
        if rem <= 0:
            break
        take = min(rem, len(by_fam[fam]) - alloc[fam])
        alloc[fam] += take
        rem -= take

    sample = []
    for fam in fams:
        idx = rng.choice(len(by_fam[fam]), size=alloc[fam], replace=False)
        sample.extend(by_fam[fam][i] for i in sorted(idx))
    rng.shuffle(sample)          # de-correlate presentation order from family

    # ---- master file (WITH ground truth -- for the analyst, NOT annotators) ----
    master = OUT / "validation_sample.csv"
    with open(master, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "item_id", "sample_id", "message", "ground_truth", "attack_family",
            "reason", "severity"])
        w.writeheader()
        for k, r in enumerate(sample, 1):
            w.writerow({
                "item_id": f"V{k:03d}",
                "sample_id": r["sample_id"],
                "message": r["message"],
                "ground_truth": r["ground_truth"],
                "attack_family": r["attack_family"],
                "reason": r["semantic_objective"] or r["transformation_rule"],
                "severity": r["severity"],
            })

    # ---- blind annotator templates (NO ground truth, NO family) ----
    for ann in ("A", "B"):
        p = OUT / f"annotation_template_annotator_{ann}.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["item_id", "message", "label", "confidence", "notes"])
            for k, r in enumerate(sample, 1):
                w.writerow([f"V{k:03d}", r["message"], "", "", ""])

    counts = {}
    for r in sample:
        counts.setdefault(r["attack_family"], {"n": 0, "mal": 0})
        counts[r["attack_family"]]["n"] += 1
        counts[r["attack_family"]]["mal"] += (r["ground_truth"] == "malicious")

    (OUT / "sampling_manifest.json").write_text(json.dumps({
        "n_sampled": len(sample),
        "n_population": N_SAMPLES,
        "seed": SEED,
        "strategy": "stratified by attack_family, proportional with a floor of "
                    f"{base}/family, remainder to largest families; presentation "
                    "order shuffled to de-correlate family from position",
        "n_families": len(fams),
        "per_family": counts,
        "prevalence_malicious_in_sample":
            sum(1 for r in sample if r["ground_truth"] == "malicious") / len(sample),
        "annotations_present": False,
        "note": "Annotator templates are intentionally BLANK. No labels in this "
                "repository are machine-generated for the human-validation study.",
    }, indent=2), encoding="utf-8")

    print(f"[ok] {master}  (n={len(sample)}, {len(fams)} families)")
    print(f"[ok] annotation_template_annotator_A.csv / _B.csv  (BLANK label column)")
    print(f"[ok] sampling_manifest.json")
    print("\nNEXT: two annotators independently fill `label` with "
          "malicious|benign (and optionally confidence 1-5), then run:")
    print("      python validation/agreement_analysis.py")


if __name__ == "__main__":
    main()
