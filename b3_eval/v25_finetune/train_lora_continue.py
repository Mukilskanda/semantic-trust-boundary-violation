"""
b3_eval/v25_finetune/train_lora_continue.py
=============================================
TRUE continuation of the existing mixed-corpus LoRA adapter
(semantic_gate_v3_mixed_lora, best val F1 = 0.8992, epoch 6 -- see
training_log_mixed.jsonl / MIXED_CORPUS_REPORT.md).

Unlike train_lora_mixed.py / train_lora.py (which always reinitialize a
fresh LoRA adapter from the frozen base semantic_gate_v3), this script
loads the EXISTING adapter's weights via
PeftModel.from_pretrained(base, ADAPTER_CKPT, is_trainable=True) and
continues optimizing them -- a real weight continuation, not a retrain
from scratch.

Data: continued_train_split.jsonl / continued_val_split.jsonl
(b3_eval/v25_finetune/build_continued_corpus.py) = the original mixed
corpus (v2.5 train split + v1 stratified sample) PLUS STBV-Bench v2.5c
(template-disjoint training-only augmentation, verified disjoint from the
held-out v2.5b evaluation benchmark).

Lower LR than the original run (this is fine-tuning an already-converged
adapter, not training from a fresh LoRA init) and a smaller epoch budget.
Saved to a NEW directory (semantic_gate_v3_mixed_lora_continued) --
the original semantic_gate_v3_mixed_lora/ is never overwritten, so the
prior checkpoint remains available for comparison.
"""
from __future__ import annotations

import json
import pathlib
import random
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                           get_linear_schedule_with_warmup)
from peft import PeftModel

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BASE_CKPT = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"
ADAPTER_CKPT = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora"
OUT_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_continued"
DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
LOG_PATH = pathlib.Path(__file__).resolve().parent / "training_log_mixed_continued.jsonl"

SEED = 42
MAX_LENGTH = 256
LR = 3e-6  # lower than the original 1e-5: continuing an already-converged adapter
BATCH_SIZE = 16
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.10
GRAD_CLIP = 1.0
MAX_EPOCHS = 6
PATIENCE = 2


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class JsonlDataset(Dataset):
    def __init__(self, path, tok, max_length):
        self.rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.tok = tok
        self.max_length = max_length

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        enc = self.tok(r["text"], max_length=self.max_length, padding="max_length",
                        truncation=True, return_tensors="pt")
        item = {k: v.squeeze(0) for k, v in enc.items()}
        item["labels"] = torch.tensor(int(r["label"]), dtype=torch.long)
        return item


def prf1(preds, labels):
    tp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 1)
    fp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 0)
    fn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 1)
    tn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / len(labels)
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


@torch.no_grad()
def evaluate(model, dl, device):
    model.eval()
    preds, labels = [], []
    total_loss, n = 0.0, 0
    for batch in dl:
        batch = {k: v.to(device) for k, v in batch.items()}
        out = model(**batch)
        total_loss += out.loss.item() * batch["labels"].size(0)
        n += batch["labels"].size(0)
        preds.extend(out.logits.argmax(dim=-1).cpu().tolist())
        labels.extend(batch["labels"].cpu().tolist())
    m = prf1(preds, labels)
    m["loss"] = total_loss / n
    return m


def log(entry):
    entry["timestamp_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry))


def main():
    assert BASE_CKPT.exists(), f"base checkpoint missing: {BASE_CKPT}"
    assert ADAPTER_CKPT.exists(), f"adapter to continue from missing: {ADAPTER_CKPT}"
    assert (DATA_DIR / "continued_train_split.jsonl").exists(), (
        "run build_continued_corpus.py first")
    LOG_PATH.write_text("")
    set_seed(SEED)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log({"event": "start", "device": str(device),
         "base_checkpoint": str(BASE_CKPT), "resumed_from_adapter": str(ADAPTER_CKPT),
         "output_dir": str(OUT_DIR),
         "config": {"lr": LR, "batch_size": BATCH_SIZE, "weight_decay": WEIGHT_DECAY,
                    "warmup_ratio": WARMUP_RATIO, "grad_clip": GRAD_CLIP,
                    "max_epochs": MAX_EPOCHS, "patience": PATIENCE, "seed": SEED,
                    "max_length": MAX_LENGTH}})

    tok = AutoTokenizer.from_pretrained(str(BASE_CKPT), local_files_only=True)
    base_model = AutoModelForSequenceClassification.from_pretrained(str(BASE_CKPT), local_files_only=True)

    # TRUE continuation: load existing adapter weights, not a fresh LoRA init.
    model = PeftModel.from_pretrained(base_model, str(ADAPTER_CKPT), is_trainable=True).to(device)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log({"event": "peft_model_resumed", "trainable_params": trainable, "total_params": total,
         "trainable_pct": round(100 * trainable / total, 4)})

    train_ds = JsonlDataset(DATA_DIR / "continued_train_split.jsonl", tok, MAX_LENGTH)
    val_ds = JsonlDataset(DATA_DIR / "continued_val_split.jsonl", tok, MAX_LENGTH)
    g = torch.Generator().manual_seed(SEED)
    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, generator=g)
    val_dl = DataLoader(val_ds, batch_size=32, shuffle=False)

    # Baseline: score the resumed adapter on the new combined val set before
    # any further training, so improvement (or regression) is measurable.
    baseline = evaluate(model, val_dl, device)
    log({"event": "baseline_before_continuation", "val": baseline})

    steps_per_epoch = len(train_dl)
    total_steps = steps_per_epoch * MAX_EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)

    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=LR, weight_decay=WEIGHT_DECAY,
    )
    sched = get_linear_schedule_with_warmup(opt, num_warmup_steps=warmup_steps,
                                             num_training_steps=total_steps)

    best_f1 = baseline["f1"]
    best_epoch = 0
    epochs_without_improve = 0
    t_start = time.perf_counter()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT_DIR))
    tok.save_pretrained(str(OUT_DIR))
    (OUT_DIR / "best_epoch_metrics.json").write_text(json.dumps(
        {"epoch": 0, "val_metrics": baseline, "note": "resumed adapter, pre-continuation baseline"}, indent=2))

    epoch = 0
    while epoch < MAX_EPOCHS:
        epoch += 1
        model.train()
        t0 = time.perf_counter()
        running_loss, nsteps = 0.0, 0
        for batch in train_dl:
            batch = {k: v.to(device) for k, v in batch.items()}
            opt.zero_grad()
            out = model(**batch)
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], GRAD_CLIP)
            opt.step()
            sched.step()
            running_loss += out.loss.item()
            nsteps += 1
        train_time = time.perf_counter() - t0

        val_metrics = evaluate(model, val_dl, device)
        log({"event": "epoch_end", "epoch": epoch, "train_loss": running_loss / nsteps,
             "train_seconds": train_time, "val": val_metrics,
             "lr_last": sched.get_last_lr()[0]})

        improved = val_metrics["f1"] > best_f1
        if improved:
            best_f1 = val_metrics["f1"]
            best_epoch = epoch
            epochs_without_improve = 0
            model.save_pretrained(str(OUT_DIR))
            tok.save_pretrained(str(OUT_DIR))
            (OUT_DIR / "best_epoch_metrics.json").write_text(json.dumps(
                {"epoch": epoch, "val_metrics": val_metrics}, indent=2))
            log({"event": "checkpoint_saved", "epoch": epoch, "val_f1": val_metrics["f1"]})
        else:
            epochs_without_improve += 1
            log({"event": "no_improvement", "epoch": epoch,
                 "epochs_without_improve": epochs_without_improve})

        if epochs_without_improve >= PATIENCE:
            log({"event": "early_stop", "epoch": epoch, "best_epoch": best_epoch, "best_val_f1": best_f1})
            break

    total_time = time.perf_counter() - t_start
    log({"event": "training_complete", "baseline_f1": baseline["f1"],
         "best_epoch": best_epoch, "best_val_f1": best_f1,
         "total_epochs_run": epoch, "total_seconds": total_time,
         "output_dir": str(OUT_DIR)})


if __name__ == "__main__":
    main()
