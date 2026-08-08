"""Corrected capture: B3's actual p_malicious (not confidence-in-argmax-label)
inside the full pipeline, for all v2.5b samples. Single full-stack pass per
sample (not all 5 configs -- only need B3's real synthesized-text score)."""
import json, sys, pathlib, time
sys.path.insert(0, '.')

ROOT = pathlib.Path('.').resolve()
MODEL_PATH = 'b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_continued_merged'

import yaml, tempfile
real_config = ROOT / 'isce_config.yaml'
with open(real_config, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
data['b3_semantic_gate']['model_path'] = MODEL_PATH
data['b3_semantic_gate']['temperature_scaling'] = 2.82
tmp = pathlib.Path(tempfile.mkdtemp()) / 'isce_config_override.yaml'
with open(tmp, 'w', encoding='utf-8') as f:
    yaml.safe_dump(data, f)

import pipeline.b3_bridge as b3_bridge
b3_bridge._DEFAULT_CONFIG_PATH = tmp
from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

samples = [json.loads(l) for l in open('data/stbv_bench/v25b/stbv_bench_v25b.jsonl', encoding='utf-8') if l.strip()]
print(f"[corrected-pmalicious] {len(samples)} samples")

out = open('b3_eval/v25_finetune/ablation_results/v25b_full/pipeline_pmalicious_CORRECTED.csv', 'w', encoding='utf-8')
out.write("sample_id,attack_family,is_attacker,p_malicious,label,decision\n")

t0 = time.perf_counter()
for i, s in enumerate(samples):
    text = s["text"]
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
        "scene_context": {"peer_reports": [text], "rsu_messages": []},
    }
    p = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
    res = p.run([msg], context="urban")
    b3 = res.get("b3") or {}
    out.write(f'{s["sample_id"]},{s["attack_family"]},{bool(s["label"])},{b3.get("p_malicious")},{b3.get("label")},{res.get("decision")}\n')

    if (i + 1) % 500 == 0:
        out.flush()
        elapsed = time.perf_counter() - t0
        rate = (i + 1) / elapsed
        eta = (len(samples) - (i + 1)) / rate if rate > 0 else float("nan")
        print(f"  {i+1}/{len(samples)} ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)", flush=True)

out.close()
print(f"[done] {len(samples)} samples in {time.perf_counter()-t0:.1f}s")
