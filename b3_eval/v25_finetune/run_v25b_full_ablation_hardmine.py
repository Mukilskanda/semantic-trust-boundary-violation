"""
b3_eval/v25_finetune/run_v25b_full_ablation_hardmine.py
==========================================================
Same 5-configuration full-pipeline ablation as run_v25b_full_ablation.py,
but scoring the NEW hardmine-continued checkpoint
(semantic_gate_v3_mixed_lora_hardmine_merged) with its own freshly-fit
temperature (T=3.18, calibrate_hardmine_checkpoint.py) instead of the
prior checkpoint/T=2.82. Verifies whether the checkpoint's real,
held-out-benchmark classifier improvement (F1 0.945->0.957, direct
classifier eval, eval_hardmine_v25b.py) survives being embedded in the
full pipeline's decision policy (ensembling + confidence-aware-benign
floor) -- the same "verify, don't assume" check already applied to the
calibration-temperature investigation.

Writes to a SEPARATE output directory (v25b_full_hardmine) -- the
existing v25b_full/ (current deployed checkpoint) is left untouched
until/unless this pass's results are verified to justify promoting the
new checkpoint to production.
"""
from __future__ import annotations
import csv, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_hardmine_merged"
BENCH = ROOT / "data" / "stbv_bench" / "v25b" / "stbv_bench_v25b.jsonl"
OUT = ROOT / "b3_eval" / "v25_finetune" / "ablation_results" / "v25b_full_hardmine"
OUT.mkdir(parents=True, exist_ok=True)


def make_override_config(model_path):
    import yaml, tempfile
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["b3_semantic_gate"]["model_path"] = model_path
    data["b3_semantic_gate"]["temperature_scaling"] = 3.18  # freshly fit for the hardmine checkpoint; see calibrate_hardmine_checkpoint.py
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

    policy = TrustPolicy()

    def b3_only_decision(b1_dict, b3_result):
        if b1_dict.get("fatal"):
            return "REJECT"
        risk = policy.classify_semantic_risk(b3_result)
        if risk == SemanticRisk.HIGH:
            return "REJECT"
        if risk in (SemanticRisk.MEDIUM, SemanticRisk.LOW):
            return "CAUTION"
        return "ACCEPT"

    samples = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[v25b-ablation] {len(samples)} samples")

    fieldnames = ["sample_id", "attack_family", "is_attacker", "decision", "raw_score"]
    writers, files = {}, {}
    for cfg in (1, 2, 3, 4, 5):
        f = open(OUT / f"config_{cfg}.csv", "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        files[cfg] = f
        writers[cfg] = w

    t_start = time.perf_counter()
    for i, s in enumerate(samples):
        msg = s["messages"][0] if "messages" in s else s.get("transformed_message", s)
        # v2.5b rows: {"sample_id","text","label","attack_family",...} -- build a
        # minimal nested CAM carrying the text in scene_context.peer_reports,
        # matching how STBV-Bench v1's transformed_message embeds attack text.
        if "text" in s:
            msg = {
                "header": {"station_id": 30000 + i, "message_id": 1},
                "cam": {"generation_delta_time": 1000 + i,
                        "cam_parameters": {"basic_container": {"station_type": 5,
                            "reference_position": {"latitude": 485512345, "longitude": 96123456}},
                            "high_frequency_container": {"basic_vehicle_container_high_frequency": {
                                "speed": 1200, "heading": 900, "yaw_rate": 0,
                                "steering_wheel_angle": 0, "lateral_acceleration": 0,
                                "longitudinal_acceleration": 0}}}},
                "certificate_id": f"CERT_5_{30000+i}", "cert_id": f"CERT_5_{30000+i}",
                "local_perception": {"camera": "CLEAR", "radar": "CLEAR", "lidar": "CLEAR"},
                "scene_context": {"peer_reports": [s["text"]], "rsu_messages": []},
            }
        is_attacker = bool(s.get("label", s.get("is_attacker")))
        family = s.get("attack_family", "unknown")

        results = {}
        configs = {1: dict(enable_mbd=False, enable_cp=False, enable_b3=False),
                   2: dict(enable_mbd=True, enable_cp=False, enable_b3=False),
                   3: dict(enable_mbd=True, enable_cp=True, enable_b3=False),
                   5: dict(enable_mbd=True, enable_cp=True, enable_b3=True)}
        for cfg, kwargs in configs.items():
            p = ISCEPipeline(scsv=SCSV(), **kwargs)
            res = p.run([msg], context="urban")
            results[cfg] = res

        p4 = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
        res4 = p4.run([msg], context="urban")
        b1_dict = res4["b1"]; b3_result = res4["b3"] or {}
        decision4 = b3_only_decision(b1_dict, b3_result)

        for cfg in (1, 2, 3, 5):
            raw = None
            if cfg == 5:
                raw = (results[5].get("b3") or {}).get("p_malicious")  # NOT "confidence" -- see PIPELINE_DIFFERENCE_REPORT.md
            writers[cfg].writerow({"sample_id": s.get("sample_id", i), "attack_family": family,
                                    "is_attacker": is_attacker, "decision": results[cfg]["decision"],
                                    "raw_score": raw})
        writers[4].writerow({"sample_id": s.get("sample_id", i), "attack_family": family,
                              "is_attacker": is_attacker, "decision": decision4,
                              "raw_score": b3_result.get("p_malicious")})

        if (i + 1) % 500 == 0:
            for f in files.values():
                f.flush()
            elapsed = time.perf_counter() - t_start
            rate = (i + 1) / elapsed
            eta = (len(samples) - (i + 1)) / rate if rate > 0 else float("nan")
            print(f"  {i+1}/{len(samples)} ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)", flush=True)

    for f in files.values():
        f.close()
    total_s = time.perf_counter() - t_start
    print(f"[done] {len(samples)} samples in {total_s:.1f}s")
    (OUT / "run_manifest.json").write_text(json.dumps({
        "checkpoint": "final_continued", "model_path": MODEL_PATH, "bench": str(BENCH),
        "n_samples": len(samples), "total_seconds": total_s}, indent=2))


if __name__ == "__main__":
    main()
