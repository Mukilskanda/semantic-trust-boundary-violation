"""
b3_eval/v25_finetune/eval_hardmine_v25b.py
=============================================
Verifies whether the hardmine-continued checkpoint
(semantic_gate_v3_mixed_lora_hardmine_merged) genuinely improves on the
REAL held-out benchmark (STBV-Bench v2.5b, n=10,098), not just on the
training-adjacent validation split used for early-stopping during
training. The validation split includes samples close to the training
distribution; v2.5b is the actual generalization test.

Also reports per-family recall specifically for the six families the
hard-mining batch targeted (sensor_discreditation, goal_manipulation,
traffic_efficiency_lure, narrative_poisoning, role_confusion,
false_clearance) plus benign_control precision, to check whether the
targeted fix actually closed the mined gap or just moved metrics
elsewhere.
"""
from __future__ import annotations
import json, pathlib, sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from b3_eval.v25_finetune.eval_common import load_jsonl, score_dataset, LoadedModel  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402
import torch  # noqa: E402

MODELS = {
    "final_continued_checkpoint": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_continued_merged",
    "hardmine_checkpoint": ROOT / "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_hardmine_merged",
}
V25B_PATH = ROOT / "data" / "stbv_bench" / "v25b" / "stbv_bench_v25b.jsonl"
OUT_PATH = HERE / "results" / "hardmine_v25b_eval.json"
TARGET_FAMILIES = ["sensor_discreditation", "goal_manipulation", "traffic_efficiency_lure",
                    "narrative_poisoning", "role_confusion", "false_clearance"]


def load_dense(path, device="cuda"):
    tok = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(path), local_files_only=True)
    model.to(device)
    return LoadedModel(str(path.name), model, tok, device, temperature=1.0)


def per_family_recall(rows, pred_ids, labels):
    fam_stats = defaultdict(lambda: [0, 0])
    for r, p, y in zip(rows, pred_ids, labels):
        fam = r.get("attack_family", "unknown")
        if y == 1:
            fam_stats[fam][1] += 1
            if p == 1:
                fam_stats[fam][0] += 1
    return {fam: (correct / total if total else None) for fam, (correct, total) in fam_stats.items()}


def benign_precision(rows, pred_ids, labels):
    fp = sum(1 for r, p, y in zip(rows, pred_ids, labels) if p == 1 and y == 0 and r.get("attack_family") == "benign_control")
    return fp


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = load_jsonl(V25B_PATH)
    print(f"[v2.5b] n={len(rows)}")

    results = {}
    for key, path in MODELS.items():
        if not path.exists():
            print(f"[skip] {key}: missing")
            continue
        print(f"\n=== {key} ===")
        m = load_dense(path, device)
        metrics, preds, labels = score_dataset(m, rows)
        pred_ids = [p["label_id"] for p in preds]
        fam_recall = per_family_recall(rows, pred_ids, labels)
        fp_from_benign = benign_precision(rows, pred_ids, labels)
        target_recall = {f: fam_recall.get(f) for f in TARGET_FAMILIES}
        print(json.dumps({k: v for k, v in metrics.items() if k not in ("tp", "fp", "fn", "tn")}, indent=2))
        print("Target-family recall:", json.dumps(target_recall, indent=2))
        print("False positives from benign_control:", fp_from_benign)
        results[key] = {"metrics": metrics, "target_family_recall": target_recall,
                         "benign_control_false_positives": fp_from_benign, "model_dir": str(path)}
        del m.model
        torch.cuda.empty_cache()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"benchmark": "STBV-Bench v2.5b", "n": len(rows), "results": results}, indent=2, default=str))
    print(f"\n[ok] {OUT_PATH}")


if __name__ == "__main__":
    main()
