"""
b3_eval/v25_finetune/eval_v25_test_mixed.py
==============================================
Direct classifier-level evaluation (no full ISCE pipeline; matches how
FULL_EVALUATION_REPORT.md scored v2.5 test originally) of THREE checkpoints
on STBV-Bench v2.5's held-out test split (data/test_split.jsonl, n=1811,
template-disjoint from all training data used anywhere):
  - original (semantic_gate_v3)
  - v2.5-only LoRA finetune (semantic_gate_v3_v25_lora_merged)
  - mixed-corpus LoRA finetune (semantic_gate_v3_mixed_lora_merged)

No calibration/temperature applied here (raw argmax + confidence), for an
apples-to-apples comparison with the checkpoint-swap numbers already
reported in FULL_EVALUATION_REPORT.md / UPDATED_RESULTS.md.
"""
from __future__ import annotations
import json, pathlib, sys, math

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from b3_eval.v25_finetune.eval_common import (  # noqa: E402
    load_jsonl, score_dataset, LoadedModel)
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402
import torch  # noqa: E402

MODELS = {
    "original": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3",
    "v25_only_finetune": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged",
    "mixed_corpus_finetune": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_merged",
}

TEST_PATH = HERE / "data" / "test_split.jsonl"
OUT_PATH = HERE / "results" / "v25_test_three_checkpoint_comparison.json"


def load_dense(path, device="cuda"):
    tok = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(path), local_files_only=True)
    model.to(device)
    return LoadedModel(str(path.name), model, tok, device, temperature=1.0)


def mcnemar(preds_a, preds_b, labels):
    b01 = b10 = 0
    for pa, pb, y in zip(preds_a, preds_b, labels):
        ca, cb = (pa == y), (pb == y)
        if ca and not cb:
            b01 += 1
        elif cb and not ca:
            b10 += 1
    n = b01 + b10
    if n == 0:
        chi2 = 0.0
    else:
        chi2 = (abs(b01 - b10) - 1) ** 2 / n
    # chi2 with 1 dof -> p-value via survival function approx (Wilson-Hilferty not needed, use erf)
    p = math.erfc(math.sqrt(chi2 / 2)) if n > 0 else 1.0
    return {"b01": b01, "b10": b10, "n_discordant": n, "chi2": chi2, "p_value": p}


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = load_jsonl(TEST_PATH)
    labels = [int(r["label"]) for r in rows]

    results = {}
    preds_by_model = {}
    for name, path in MODELS.items():
        assert path.exists(), f"missing checkpoint: {path}"
        print(f"Scoring {name} ({path})...")
        lm = load_dense(path, device)
        metrics, preds, labs = score_dataset(lm, rows)
        results[name] = metrics
        preds_by_model[name] = [p["label_id"] for p in preds]
        del lm
        torch.cuda.empty_cache()
        print(json.dumps({name: metrics}, indent=2))

    comparisons = {
        "original_vs_mixed": mcnemar(preds_by_model["original"], preds_by_model["mixed_corpus_finetune"], labels),
        "v25only_vs_mixed": mcnemar(preds_by_model["v25_only_finetune"], preds_by_model["mixed_corpus_finetune"], labels),
        "original_vs_v25only": mcnemar(preds_by_model["original"], preds_by_model["v25_only_finetune"], labels),
    }

    out = {"n_test": len(rows), "metrics": results, "mcnemar": comparisons}
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"Written: {OUT_PATH}")


if __name__ == "__main__":
    main()
