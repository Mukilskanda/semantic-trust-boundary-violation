#!/usr/bin/env python3
"""
stbv_bench/run_ablation.py
============================
Layer ablation study on STBV-Bench v1, per ABLATION_STUDY.md (Step 1 audit).
Runs the SAME fixed 10,000-sample slice used for the STBV-Bench v1 baseline
(data/stbv_bench/v1/stbv_bench.jsonl, first --limit samples, identical to
run_stbv_bench_eval.py's slicing) through 5 configurations of the real,
frozen ISCEPipeline:

  1. B1 only              enable_mbd=False, enable_cp=False, enable_b3=False
  2. B1+B2                enable_mbd=True,  enable_cp=False, enable_b3=False
  3. B1+B2+CP             enable_mbd=True,  enable_cp=True,  enable_b3=False
  4. B1+B2+CP+B3, no fusion   full computation (enable_b3=True), but the
                              decision is taken directly from B3's own risk
                              band (TrustPolicy.classify_semantic_risk) rather
                              than TrustDecisionEngine.decide()'s fused output.
  5. Full stack           full computation, decide()'s own fused decision
                          (identical code path to the STBV-Bench v1 baseline)

Configs 4 and 5 require identical layer computation (both run B1/B2/CP/B3 in
full) and differ only in which decision function is applied to that same,
honestly-computed evidence -- so, to avoid redundantly re-running B3's model
forward pass a second time for no reason, ONE pipeline.run() call per sample
is made with enable_b3=True, and both the config-4 (B3-only) and config-5
(fused) decisions are derived from that single result. This does not filter
or alter what either layer produced; it is two decision rules read off the
same real, unfiltered evidence.

Every sample gets a FRESH ISCEPipeline instance per config (same fix as
run_stbv_bench_eval.py -- see PUBLICATION_PROGRESS.md's "state-leakage bug"
entry): STBV-Bench samples are independent, unrelated single messages, not a
continuous trajectory, and MBD/CP/B1's cert-rotation tracking are stateful.

Usage:
  python3 stbv_bench/run_ablation.py \
      --bench data/stbv_bench/v1/stbv_bench.jsonl \
      --out results/ablation --limit 10000
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV
from trust_engine.policy import TrustPolicy
from trust_engine.models import SemanticRisk

_POLICY = TrustPolicy()


def b3_only_decision(b1_dict: dict, b3_result: dict) -> str:
    """Config 4's decision rule: B3's own risk band, bypassing DS fusion.

    Reuses TrustPolicy.classify_semantic_risk() (already-existing code,
    not reimplemented here) to map b3_result -> SemanticRisk, then applies
    the same REJECT/CAUTION/ACCEPT band names decide() uses, but with NO
    crypto/structural evidence folded in.

    B1-fatal messages never reach B3 in the real architecture (B3 is
    skipped by construction on that path -- see orchestrator.py's B1-fatal
    short-circuit) regardless of any ablation config; this rule preserves
    that same real behavior (REJECT) rather than inventing a B3 opinion
    that was never computed. For every other message, an UNAVAILABLE risk
    (B3 genuinely found nothing to flag, or was unavailable) has no basis
    for REJECT/CAUTION under a B3-only rule, so it defaults ACCEPT.
    """
    if b1_dict.get("fatal"):
        return "REJECT"
    risk = _POLICY.classify_semantic_risk(b3_result)
    if risk == SemanticRisk.HIGH:
        return "REJECT"
    if risk in (SemanticRisk.MEDIUM, SemanticRisk.LOW):
        return "CAUTION"
    return "ACCEPT"  # NONE or UNAVAILABLE


CONFIGS = {
    1: dict(enable_mbd=False, enable_cp=False, enable_b3=False, label="B1 only"),
    2: dict(enable_mbd=True, enable_cp=False, enable_b3=False, label="B1+B2"),
    3: dict(enable_mbd=True, enable_cp=True, enable_b3=False, label="B1+B2+CP"),
    # 4 and 5 share one pipeline.run() call (see module docstring); config
    # dict below describes what actually executes.
    45: dict(enable_mbd=True, enable_cp=True, enable_b3=True, label="B1+B2+CP+B3"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=10000)
    args = ap.parse_args()

    samples = []
    with open(args.bench, "r", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))
    samples = samples[: args.limit]

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sample_id", "attack_family", "is_attacker", "decision",
        "raw_score", "contributors", "decision_source",
    ]

    writers = {}
    files = {}
    for cfg_id in (1, 2, 3, 4, 5):
        f = open(out_dir / f"ablation_config_{cfg_id}.csv", "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        files[cfg_id] = f
        writers[cfg_id] = w

    t_start = time.perf_counter()
    for i, s in enumerate(samples):
        msg = s["transformed_message"]
        is_attacker = bool(msg.get("is_attacker", s["attack_family"] != "benign_control"))
        family = s["attack_family"]

        # --- Configs 1-3: real per-layer skips (fresh pipeline per config) ---
        for cfg_id in (1, 2, 3):
            cfg = CONFIGS[cfg_id]
            pipeline = ISCEPipeline(
                scsv=SCSV(), enable_mbd=cfg["enable_mbd"],
                enable_cp=cfg["enable_cp"], enable_b3=cfg["enable_b3"],
            )
            res = pipeline.run([msg], context="urban")
            writers[cfg_id].writerow({
                "sample_id": s["sample_id"], "attack_family": family,
                "is_attacker": is_attacker, "decision": res["decision"],
                "raw_score": res["fusion"].get("trust_score"),
                "contributors": ",".join(res["fusion"].get("contributors", [])),
                "decision_source": "fusion",
            })

        # --- Configs 4 & 5: one shared full-stack run, two decision rules ---
        pipeline45 = ISCEPipeline(
            scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True,
        )
        res45 = pipeline45.run([msg], context="urban")
        b1_dict = res45["b1"]
        b3_result = res45["b3"] or {}

        decision4 = b3_only_decision(b1_dict, b3_result)
        writers[4].writerow({
            "sample_id": s["sample_id"], "attack_family": family,
            "is_attacker": is_attacker, "decision": decision4,
            "raw_score": b3_result.get("confidence"),
            "contributors": "B3" if b3_result.get("available") else "none",
            "decision_source": "b3_raw",
        })

        writers[5].writerow({
            "sample_id": s["sample_id"], "attack_family": family,
            "is_attacker": is_attacker, "decision": res45["decision"],
            "raw_score": res45["fusion"].get("trust_score"),
            "contributors": ",".join(res45["fusion"].get("contributors", [])),
            "decision_source": "fusion",
        })

        if (i + 1) % 200 == 0:
            elapsed = time.perf_counter() - t_start
            rate = (i + 1) / elapsed
            eta_s = (len(samples) - (i + 1)) / rate if rate > 0 else float("nan")
            print(f"  {i + 1}/{len(samples)} evaluated ({elapsed:.0f}s elapsed, "
                  f"~{eta_s:.0f}s remaining)", flush=True)

    for f in files.values():
        f.close()

    total_s = time.perf_counter() - t_start
    print(f"\n[done] {len(samples)} samples x 5 configs in {total_s:.1f}s")
    for cfg_id in (1, 2, 3, 4, 5):
        print(f"  -> {out_dir / f'ablation_config_{cfg_id}.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
