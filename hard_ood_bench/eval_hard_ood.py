"""
hard_ood_bench/eval_hard_ood.py
=================================
Evaluates the frozen, final production checkpoint
(semantic_gate_v3_mixed_lora_merged) directly (B3 only, no retraining) on
hard_ood_corpus.jsonl. Uses pipeline.b3_bridge.classify_text, the same
production inference class used throughout this paper's other evaluations.
"""
import json, time, pathlib, sys
import yaml, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged"


def make_override_config():
    real_config = ROOT / "isce_config.yaml"
    with open(real_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["b3_semantic_gate"]["model_path"] = MODEL_PATH
    tmp = pathlib.Path(tempfile.mkdtemp()) / "isce_config_override.yaml"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    return tmp


def main():
    override_path = make_override_config()
    import pipeline.b3_bridge as b3_bridge
    b3_bridge._DEFAULT_CONFIG_PATH = override_path
    b3_bridge.preload_classifier()

    rows = [json.loads(l) for l in open(ROOT / "hard_ood_bench" / "hard_ood_corpus.jsonl", encoding="utf-8")]

    results = []
    t0 = time.perf_counter()
    for r in rows:
        t_msg0 = time.perf_counter()
        out = b3_bridge.classify_text(r["text"])
        lat_ms = (time.perf_counter() - t_msg0) * 1000
        results.append({
            **r,
            "pred_label": out.get("label"),
            "confidence": out.get("confidence"),
            "risk_level": out.get("risk_level"),
            "latency_ms": lat_ms,
        })
        if len(results) % 50 == 0:
            print(f"  {len(results)}/{len(rows)}", flush=True)
    total_s = time.perf_counter() - t0

    out_path = ROOT / "hard_ood_bench" / "hard_ood_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "manifest": {
                "checkpoint": "mixed",
                "model_path": MODEL_PATH,
                "n": len(results),
                "total_seconds": total_s,
            },
            "results": results,
        }, f, indent=2)
    print(f"[done] {len(results)} messages in {total_s:.1f}s -> {out_path}")


if __name__ == "__main__":
    sys.exit(main())
