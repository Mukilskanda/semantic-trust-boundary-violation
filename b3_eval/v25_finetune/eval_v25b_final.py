"""
b3_eval/v25_finetune/eval_v25b_final.py
==========================================
Evaluates the FINAL checkpoint (semantic_gate_v3_mixed_lora_continued_merged,
produced by train_lora_continue.py resuming semantic_gate_v3_mixed_lora on
mixed-corpus + STBV-Bench v2.5c) against STBV-Bench v2.5b
(data/stbv_bench/v25b/stbv_bench_v25b.jsonl, n=10,098) -- a held-out,
template-disjoint benchmark over the SAME semantic taxonomy as v2.5,
verified disjoint from v2.5, v2.5c, and (by construction, since it was
never referenced during training/data-building) the training corpus.

Also scores the PRE-continuation mixed checkpoint on the same benchmark
for a direct before/after comparison, and the original base checkpoint
as a lower reference point.

v2.5b is evaluation-only; it is never included in any training split
(see data/stbv_bench/v25b/manifest.json usage_policy).
"""
from __future__ import annotations
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from b3_eval.v25_finetune.eval_common import (  # noqa: E402
    load_jsonl, score_dataset, LoadedModel)
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402
import torch  # noqa: E402

MODELS = {
    "original_base": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3",
    "mixed_corpus_pre_continuation": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged",
    "final_continued_checkpoint": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_continued_merged",
}

V25B_PATH = ROOT / "data" / "stbv_bench" / "v25b" / "stbv_bench_v25b.jsonl"
OUT_PATH = HERE / "results" / "v25b_final_checkpoint_eval.json"


def load_dense(path, device="cuda"):
    tok = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(path), local_files_only=True)
    model.to(device)
    return LoadedModel(str(path.name), model, tok, device, temperature=1.0)


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = load_jsonl(V25B_PATH)
    print(f"[v2.5b] n={len(rows)} loaded from {V25B_PATH}")

    results = {}
    for key, path in MODELS.items():
        if not path.exists():
            print(f"[skip] {key}: {path} not found")
            continue
        print(f"\n=== {key} ({path.name}) ===")
        m = load_dense(path, device)
        metrics, preds, labels = score_dataset(m, rows)
        print(json.dumps({k: v for k, v in metrics.items() if k not in ("tp", "fp", "fn", "tn")}, indent=2))
        results[key] = {"metrics": metrics, "model_dir": str(path)}
        del m.model
        torch.cuda.empty_cache()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "benchmark": "STBV-Bench v2.5b (held-out, template-disjoint eval-only benchmark)",
        "benchmark_path": str(V25B_PATH), "n": len(rows),
        "results": results,
    }, indent=2, default=str))
    print(f"\n[ok] {OUT_PATH}")


if __name__ == "__main__":
    main()
