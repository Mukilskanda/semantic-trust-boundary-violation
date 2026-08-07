"""
b3_eval/v25_finetune/eval_common.py
=====================================
Shared model-loading and scoring plumbing for comparing the ORIGINAL B3
checkpoint (semantic_gate_v3) against the LoRA fine-tuned checkpoint
(semantic_gate_v3_v25_lora) on identical text/label pairs.

Both models are loaded as plain transformers PyTorch modules (no ONNX /
int8-quantization path -- that path in inference.py only ever activates on
CPU; both models are evaluated here primarily on CUDA, matching the
deployment-relevant path). Predictions and confidences are therefore
directly comparable between the two checkpoints.
"""
from __future__ import annotations

import json
import pathlib
import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ORIGINAL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"
LORA_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_v25_lora"
MAX_LENGTH = 256


class LoadedModel:
    def __init__(self, name, model, tokenizer, device, temperature=1.0):
        self.name = name
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.temperature = temperature

    @torch.no_grad()
    def predict(self, texts, batch_size=32):
        """Returns list of dicts: {label_id, label, confidence (calibrated), logits}."""
        self.model.eval()
        out = []
        id2label = self.model.config.id2label
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            enc = self.tokenizer(chunk, max_length=MAX_LENGTH, padding=True,
                                  truncation=True, return_tensors="pt").to(self.device)
            logits = self.model(**enc).logits.float()
            scaled = logits / self.temperature
            probs = torch.softmax(scaled, dim=-1)
            conf, pred = probs.max(dim=-1)
            for j in range(len(chunk)):
                pid = int(pred[j].item())
                out.append({
                    "label_id": pid,
                    "label": id2label[pid],
                    "confidence": float(conf[j].item()),
                    "prob_malicious": float(probs[j, 1].item()),
                    "logits": logits[j].cpu().tolist(),
                })
        return out


def load_original(device="cuda", temperature=1.0):
    tok = AutoTokenizer.from_pretrained(str(ORIGINAL_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(ORIGINAL_DIR), local_files_only=True)
    model.to(device)
    return LoadedModel("original_B3_semantic_gate_v3", model, tok, device, temperature)


def load_finetuned(device="cuda", temperature=1.0):
    from peft import PeftModel
    assert LORA_DIR.exists(), f"LoRA checkpoint missing: {LORA_DIR} -- run train_lora.py first"
    tok = AutoTokenizer.from_pretrained(str(LORA_DIR), local_files_only=True)
    base = AutoModelForSequenceClassification.from_pretrained(str(ORIGINAL_DIR), local_files_only=True)
    peft_model = PeftModel.from_pretrained(base, str(LORA_DIR))
    merged = peft_model.merge_and_unload()  # standalone dense model, base weights untouched on disk
    merged.to(device)
    return LoadedModel("finetuned_B3_v25_lora", merged, tok, device, temperature)


def load_jsonl(path, text_key="text", label_key="label"):
    rows = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        rows.append(o)
    return rows


def prf1(preds, labels):
    tp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 1)
    fp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 0)
    fn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 1)
    tn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / len(labels) if labels else 0.0
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(labels)}


def roc_pr_auc(scores, labels):
    """Simple dependency-free ROC-AUC / PR-AUC via rank statistics + sorted sweep."""
    pairs = sorted(zip(scores, labels), key=lambda x: -x[0])
    P = sum(labels)
    N = len(labels) - P
    if P == 0 or N == 0:
        return {"roc_auc": float("nan"), "pr_auc": float("nan")}
    tp = fp = 0
    tpr_prev = fpr_prev = 0.0
    roc_auc = 0.0
    prec_recall_points = []
    for s, y in pairs:
        if y == 1:
            tp += 1
        else:
            fp += 1
        tpr = tp / P
        fpr = fp / N
        roc_auc += (fpr - fpr_prev) * (tpr + tpr_prev) / 2.0
        fpr_prev, tpr_prev = fpr, tpr
        prec = tp / (tp + fp)
        prec_recall_points.append((tpr, prec))
    # PR-AUC via trapezoid over recall-sorted points
    prec_recall_points.sort(key=lambda x: x[0])
    pr_auc = 0.0
    r_prev, p_prev = 0.0, 1.0
    for r, p in prec_recall_points:
        pr_auc += (r - r_prev) * (p + p_prev) / 2.0
        r_prev, p_prev = r, p
    return {"roc_auc": roc_auc, "pr_auc": pr_auc}


def score_dataset(loaded_model, rows, text_key="text", label_key="label", batch_size=32):
    texts = [r[text_key] for r in rows]
    labels = [int(r[label_key]) for r in rows]
    t0 = time.perf_counter()
    preds = loaded_model.predict(texts, batch_size=batch_size)
    elapsed = time.perf_counter() - t0
    pred_ids = [p["label_id"] for p in preds]
    confs = [p["confidence"] for p in preds]
    prob_mal = [p["prob_malicious"] for p in preds]
    metrics = prf1(pred_ids, labels)
    metrics.update(roc_pr_auc(prob_mal, labels))
    metrics["mean_confidence"] = sum(confs) / len(confs) if confs else 0.0
    metrics["eval_seconds"] = elapsed
    metrics["throughput_msg_per_sec"] = len(rows) / elapsed if elapsed > 0 else float("inf")
    return metrics, preds, labels
