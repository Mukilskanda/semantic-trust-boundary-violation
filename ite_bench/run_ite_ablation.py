"""
ite_bench/run_ite_ablation.py
===============================
Runs all 5 ablation configurations (B1 only; B1+B2; B1+B2+CP; B3 only;
full stack) against ITE-Bench (~9,900 samples, balanced across B1/B2/B3
threat classes), using the FINAL production checkpoint for B3.

Protocol (see ABLATION_AUDIT.md for why this differs from STBV-Bench v1's
single-call-per-sample harness): each sample's message window is fed
sequentially, one message at a time, through a SINGLE persistent
ISCEPipeline instance per sample, so B1's replay/certificate-rotation
cache and MBD's per-sender history both genuinely accumulate before the
final (target) message is scored -- required for B1/B2-focused samples
to exercise the checks they are designed to test at all.
"""
from __future__ import annotations
import csv, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BENCH = ROOT / "ite_bench" / "data" / "ite_bench.jsonl"
OUT = ROOT / "ite_bench" / "results"
OUT.mkdir(parents=True, exist_ok=True)


def run_all_configs(messages, scsv_cls, orchestrator_cls, trust_policy_cls, semantic_risk_enum):
    """Runs one sample's message window through all 5 configs, returning a
    dict of decisions. Each config gets its OWN fresh pipeline (and hence
    fresh B1/MBD state) so configs don't contaminate each other; within a
    config, the window is fed sequentially through ONE persistent instance."""
    results = {}

    configs = {
        1: dict(enable_mbd=False, enable_cp=False, enable_b3=False),  # B1 only
        2: dict(enable_mbd=True, enable_cp=False, enable_b3=False),   # B1+B2
        3: dict(enable_mbd=True, enable_cp=True, enable_b3=False),    # B1+B2+CP
        5: dict(enable_mbd=True, enable_cp=True, enable_b3=True),     # full stack
    }
    for cfg_id, kwargs in configs.items():
        pipeline = orchestrator_cls(scsv=scsv_cls(), **kwargs)
        res = None
        for m in messages:
            res = pipeline.run([m], context="urban")
        results[cfg_id] = res

    # Config 4: B3 alone (no fusion) -- same b3-only decision rule used by
    # the STBV-Bench v1 rerun scripts, for consistency across the paper.
    policy = trust_policy_cls()
    pipeline4 = orchestrator_cls(scsv=scsv_cls(), enable_mbd=True, enable_cp=True, enable_b3=True)
    res4 = None
    for m in messages:
        res4 = pipeline4.run([m], context="urban")
    b1_dict = res4["b1"]
    b3_result = res4["b3"] or {}
    if b1_dict.get("fatal"):
        decision4 = "REJECT"
    else:
        risk = policy.classify_semantic_risk(b3_result)
        if risk == semantic_risk_enum.HIGH:
            decision4 = "REJECT"
        elif risk in (semantic_risk_enum.MEDIUM, semantic_risk_enum.LOW):
            decision4 = "CAUTION"
        else:
            decision4 = "ACCEPT"
    results[4] = {"decision": decision4, "b3": b3_result}

    return results


def main():
    from pipeline.orchestrator import ISCEPipeline
    from b1_scsv.scsv import SCSV
    from trust_engine.policy import TrustPolicy
    from trust_engine.models import SemanticRisk

    samples = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines()]
    print(f"[ite-ablation] {len(samples)} samples")

    writers = {}
    files = {}
    fieldnames = ["sample_id", "layer", "attack_family", "is_attacker", "decision"]
    for cfg in (1, 2, 3, 4, 5):
        f = open(OUT / f"ite_config_{cfg}.csv", "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        files[cfg] = f
        writers[cfg] = w

    t_start = time.perf_counter()
    for i, s in enumerate(samples):
        results = run_all_configs(s["messages"], SCSV, ISCEPipeline, TrustPolicy, SemanticRisk)
        for cfg in (1, 2, 3, 4, 5):
            writers[cfg].writerow({
                "sample_id": s["sample_id"], "layer": s["layer"],
                "attack_family": s["attack_family"], "is_attacker": s["is_attacker"],
                "decision": results[cfg]["decision"],
            })
        if (i + 1) % 50 == 0:
            for f in files.values():
                f.flush()
            elapsed = time.perf_counter() - t_start
            rate = (i + 1) / elapsed
            eta = (len(samples) - (i + 1)) / rate if rate > 0 else float("nan")
            print(f"  {i+1}/{len(samples)} ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)", flush=True)

    for f in files.values():
        f.close()
    total_s = time.perf_counter() - t_start
    print(f"[done] {len(samples)} samples, 5 configs each, in {total_s:.1f}s")
    (OUT / "run_manifest.json").write_text(json.dumps({
        "n_samples": len(samples), "total_seconds": total_s,
        "bench": str(BENCH),
    }, indent=2))


if __name__ == "__main__":
    main()
