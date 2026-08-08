"""
HISTORICAL, SUPERSEDED (kept for audit trail, not the current pipeline).
Configs-4/5-only rerun of the STBV-Bench v1 ablation (n=10,000) against the
PRIOR continued checkpoint (semantic_gate_v3_mixed_lora_continued_merged),
closing the freeze-audit gap flagged in FINAL_FREEZE_AUDIT.md/
READY_FOR_SUBMISSION.md: Table I's B3-alone/full-stack rows had not been
independently re-run against that checkpoint. Configs 1-3
(enable_b3=False) are checkpoint-invariant by construction and are not
rerun here. This checkpoint is now superseded by
semantic_gate_v3_mixed_lora_hardmine_merged; STBV-Bench v1 is this paper's
supplementary (not primary) benchmark and was not rerun against the new
checkpoint (see FINAL_SUBMISSION_REPORT.md, disclosed open item) -- so
Table I in the manuscript still reflects the checkpoint this script
produces, explicitly captioned as such.
"""
from __future__ import annotations
import csv, json, pathlib, sys, tempfile, time
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_continued_merged"
BENCH = str(ROOT / "data" / "stbv_bench" / "v1" / "stbv_bench.jsonl")
OUT = ROOT / "b3_eval" / "v25_finetune" / "ablation_results" / "final"
OUT.mkdir(parents=True, exist_ok=True)
LIMIT = 10000


def make_override_config(model_path):
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["b3_semantic_gate"]["model_path"] = model_path
    data["b3_semantic_gate"]["temperature_scaling"] = 2.82
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    return tmp


def main():
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

    samples = []
    with open(BENCH, "r", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))
    samples = samples[:LIMIT]

    fieldnames = ["sample_id", "attack_family", "is_attacker", "decision",
                  "raw_score", "contributors", "decision_source"]
    f4 = open(OUT / "ablation_config_4.csv", "w", newline="", encoding="utf-8")
    f5 = open(OUT / "ablation_config_5.csv", "w", newline="", encoding="utf-8")
    w4 = csv.DictWriter(f4, fieldnames=fieldnames); w4.writeheader()
    w5 = csv.DictWriter(f5, fieldnames=fieldnames); w5.writeheader()

    t_start = time.perf_counter()
    for i, s in enumerate(samples):
        msg = s["transformed_message"]
        is_attacker = bool(msg.get("is_attacker", s["attack_family"] != "benign_control"))
        family = s["attack_family"]

        pipeline45 = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
        res45 = pipeline45.run([msg], context="urban")
        b1_dict = res45["b1"]
        b3_result = res45["b3"] or {}
        decision4 = b3_only_decision(b1_dict, b3_result)
        w4.writerow({
            "sample_id": s["sample_id"], "attack_family": family, "is_attacker": is_attacker,
            "decision": decision4, "raw_score": b3_result.get("confidence"),
            "contributors": "B3" if b3_result.get("available") else "none", "decision_source": "b3_raw"})
        w5.writerow({
            "sample_id": s["sample_id"], "attack_family": family, "is_attacker": is_attacker,
            "decision": res45["decision"], "raw_score": res45["fusion"].get("trust_score"),
            "contributors": ",".join(res45["fusion"].get("contributors", [])), "decision_source": "fusion"})
        f4.flush(); f5.flush()

        if (i + 1) % 1000 == 0:
            elapsed = time.perf_counter() - t_start
            rate = (i + 1) / elapsed
            eta_s = (len(samples) - (i + 1)) / rate if rate > 0 else float("nan")
            print(f"  {i + 1}/{len(samples)} ({elapsed:.0f}s elapsed, ~{eta_s:.0f}s remaining)", flush=True)

    f4.close(); f5.close()
    total_s = time.perf_counter() - t_start
    print(f"[done] {len(samples)} samples in {total_s:.1f}s")
    (OUT / "run_manifest_configs45.json").write_text(json.dumps({
        "checkpoint": "final_continued", "model_path": MODEL_PATH, "bench": BENCH,
        "n_samples": len(samples), "total_seconds": total_s}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
