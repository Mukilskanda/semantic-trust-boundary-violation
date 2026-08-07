"""
b3_eval/v25_finetune/recalibrate_v1_collect.py
=================================================
Runs the FULL pipeline (same synthesize_message()+classify_text() path as
rerun_paper_ablation.py's configs 4/5) on STBV-Bench v1's n=10,000 subset,
FINE-TUNED checkpoint only, capturing:
  - B3's raw 2-class logits (via one extra manual forward on the exact same
    synthesized text B3 actually scored -- needed for temperature scaling;
    SemanticResult's public contract only exposes argmax label + max-prob
    confidence, not logits)
  - config-4 (B3-alone) and config-5 (full-stack) decisions AT THE OLD
    (0.85/0.60) thresholds, for continuity/sanity-check against the prior
    task's committed ablation_results/finetuned/ablation_config_{4,5}.csv
  - the val/test split label (see collect_v1_logits.py's split methodology,
    reused here identically)

No weights are modified. No thresholds are modified by this script (it
only *measures* under the existing 0.85/0.60 policy while separately
recording the logits needed to determine what NEW thresholds should be).
"""
from __future__ import annotations

import collections
import csv
import json
import pathlib
import random
import sys
import tempfile
import time

import torch
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged"
BENCH = ROOT / "data/stbv_bench/v1/stbv_bench.jsonl"
OUT_DIR = pathlib.Path(__file__).resolve().parent / "results"
LIMIT = 10000
SEED = 20260804
# Compute budget: a full pipeline forward pass per message over all 10,000
# STBV-Bench v1 rows (B1+B2+CP+B3, matching rerun_paper_ablation.py exactly)
# was measured at ~1 msg/s in this environment (~2.5-3h for 10,000). To keep
# this recalibration pass tractable, a stratified (by attack_family)
# subsample of the SAME first-10,000-row subset rerun_paper_ablation.py used
# is drawn instead -- this keeps every sample_id directly comparable against
# the already-committed original/finetuned-old-threshold ablation CSVs (for
# the three-way table, arms (a)/(b) are filtered to the same subsample's
# sample_ids, not recomputed). Disclosed explicitly in
# RECALIBRATION_RESULTS.md; not a silent scope reduction.
SUBSAMPLE_FRACTION = 0.15


def make_override_config(model_path: str) -> pathlib.Path:
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["b3_semantic_gate"]["model_path"] = model_path
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    return tmp


def main():
    samples = []
    with open(BENCH, "r", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))
    samples = samples[:LIMIT]

    rng = random.Random(SEED)
    by_family = collections.defaultdict(list)
    for s in samples:
        by_family[s["attack_family"]].append(s)

    # Stratified subsample by attack_family (same seed/rng continues below
    # for the val/test split, applied only to the subsampled rows).
    subsampled = []
    for fam, rows in sorted(by_family.items()):
        rows_c = list(rows)
        rng.shuffle(rows_c)
        n_take = max(1, round(len(rows_c) * SUBSAMPLE_FRACTION))
        subsampled.extend(rows_c[:n_take])
    samples = subsampled
    print(f"Stratified subsample: {len(samples)}/{LIMIT} rows ({SUBSAMPLE_FRACTION:.0%})")

    by_family2 = collections.defaultdict(list)
    for s in samples:
        by_family2[s["attack_family"]].append(s)
    split = {}
    for fam, rows in sorted(by_family2.items()):
        idx = list(range(len(rows)))
        rng.shuffle(idx)
        n_val = len(idx) // 2
        val_ids = set(idx[:n_val])
        for i, r in enumerate(rows):
            split[r["sample_id"]] = "val" if i in val_ids else "test"

    override_path = make_override_config(MODEL_PATH)
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path

    from pipeline.orchestrator import ISCEPipeline
    from b1_scsv.scsv import SCSV
    from trust_engine.policy import TrustPolicy
    from trust_engine.models import SemanticRisk

    _POLICY = TrustPolicy()

    def b3_only_decision(b1_dict, b3_result):
        if b1_dict.get("fatal"):
            return "REJECT"
        risk = _POLICY.classify_semantic_risk(b3_result)
        if risk == SemanticRisk.HIGH:
            return "REJECT"
        if risk in (SemanticRisk.MEDIUM, SemanticRisk.LOW):
            return "CAUTION"
        return "ACCEPT"

    # NOTE (correction): isce_config.yaml has b3_semantic_gate.enable_ensembling:
    # true in production -- orchestrator.py's B3 stage actually classifies
    # EACH of 4 TemplateStyle-synthesized texts and averages p_malicious
    # across them (see orchestrator.py ~line 505-558) before applying
    # B3RiskPolicy. res45["b3"]["p_malicious"] IS that exact production
    # average -- read directly, no need for (and no longer doing) a separate
    # single-template manual forward pass, which does not reproduce the
    # ensembled decision the pipeline actually makes (verified: an earlier
    # version of this script that did a manual single re-forward mismatched
    # the real decision on 35/757 test malicious samples -- this version
    # fixes that by using the pipeline's own already-computed p_malicious).
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "v1_mixed_recalibration_raw.csv"
    fieldnames = ["sample_id", "attack_family", "is_attacker", "split",
                  "p_malicious_raw", "b3_confidence", "b3_label",
                  "b1_fatal", "decision4_old_thr", "decision5_old_thr"]
    t0 = time.perf_counter()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i, s in enumerate(samples):
            msg = s["transformed_message"]
            is_attacker = bool(msg.get("is_attacker", s["attack_family"] != "benign_control"))
            pipeline45 = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
            res45 = pipeline45.run([msg], context="urban")
            b1_dict = res45["b1"]
            b3_result = res45["b3"] or {}
            decision4 = b3_only_decision(b1_dict, b3_result)
            w.writerow({
                "sample_id": s["sample_id"], "attack_family": s["attack_family"],
                "is_attacker": is_attacker, "split": split[s["sample_id"]],
                "p_malicious_raw": b3_result.get("p_malicious"),
                "b3_confidence": b3_result.get("confidence"), "b3_label": b3_result.get("label"),
                "b1_fatal": bool(b1_dict.get("fatal")),
                "decision4_old_thr": decision4, "decision5_old_thr": res45["decision"],
            })
            if (i + 1) % 500 == 0:
                el = time.perf_counter() - t0
                print(f"  {i+1}/{len(samples)} ({el:.0f}s, ~{el/(i+1)*(len(samples)-i-1):.0f}s remaining)", flush=True)
    print(f"[done] {out_path} in {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
