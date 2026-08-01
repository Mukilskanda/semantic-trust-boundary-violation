#!/usr/bin/env python3
"""
Supplementary diagnostic, NOT part of the controlled 5-backbone
comparison (which uses an identical lr=2e-5 for all backbones and found
microsoft/deberta-v3-base fails to train under it -- fp16 crashes on a
known GradScaler/disentangled-attention incompatibility, and the fp32
fallback converges to a degenerate always-one-class predictor, F1=0.00).

This script asks a narrower, separate question: is that a fundamental
inability of the DeBERTa-v3 architecture to learn this task, or a known
sensitivity of DeBERTa-v3's disentangled attention to the learning rate
(informally documented in the Hugging Face community as needing a lower
LR than BERT/RoBERTa-style models)? One seed, fp32, lr=1e-5 (half of the
controlled comparison's lr). Reported separately and labeled as
supplementary, never blended into the controlled comparison's numbers.
"""
import json, pathlib, sys, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
HERE = pathlib.Path(__file__).resolve().parent

sys.path.insert(0, str(HERE))
from run_backbone_comparison import load_jsonl, prf1, measure_latency, MAX_LENGTH, BATCH_SIZE, EPOCHS

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
train = load_jsonl(HERE / "data" / "train.jsonl")
test = load_jsonl(HERE / "data" / "test.jsonl")
test_texts = [r["text"] for r in test]
test_labels = [r["label"] for r in test]

ood_path = ROOT / "external_semantic_eval" / "external_corpus.json"
ood_texts, ood_labels = None, None
if ood_path.exists():
    entries = json.loads(ood_path.read_text())["entries"]
    ood_texts = [e["text"] for e in entries]
    ood_labels = [1 if e["label"] == "MALICIOUS" else 0 for e in entries]


class DS(Dataset):
    def __init__(self, rows, tok):
        self.rows, self.tok = rows, tok
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, i):
        r = self.rows[i]
        e = self.tok(r["text"], max_length=MAX_LENGTH, padding="max_length",
                      truncation=True, return_tensors="pt")
        return {k: v.squeeze(0) for k, v in e.items()} | {"labels": torch.tensor(r["label"])}


for lr in [1e-5, 5e-6]:
    print(f"\n=== microsoft/deberta-v3-base, fp32, lr={lr}, seed=0 ===")
    torch.manual_seed(0)
    tok = AutoTokenizer.from_pretrained("microsoft/deberta-v3-base")
    model = AutoModelForSequenceClassification.from_pretrained(
        "microsoft/deberta-v3-base", num_labels=2).to(device)
    dl = DataLoader(DS(train, tok), batch_size=BATCH_SIZE, shuffle=True)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    t0 = time.perf_counter()
    model.train()
    for ep in range(EPOCHS):
        ep_loss = 0.0
        for batch in dl:
            batch = {k: v.to(device) for k, v in batch.items()}
            opt.zero_grad()
            out = model(**batch)
            out.loss.backward()
            opt.step()
            ep_loss += out.loss.item()
        print(f"  epoch {ep} mean loss = {ep_loss/len(dl):.4f}")
    train_s = time.perf_counter() - t0

    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(test_texts), 32):
            enc = tok(test_texts[i:i+32], max_length=MAX_LENGTH, padding=True,
                      truncation=True, return_tensors="pt").to(device)
            preds.extend(model(**enc).logits.argmax(dim=1).cpu().tolist())
    m = prf1(preds, test_labels)
    print(f"  test: F1={m['f1']*100:.2f} acc={m['accuracy']*100:.2f} "
          f"tp={m['tp']} fp={m['fp']} fn={m['fn']} tn={m['tn']} train_s={train_s:.1f}")

    ood_m = None
    if ood_texts:
        ood_preds = []
        with torch.no_grad():
            for i in range(0, len(ood_texts), 32):
                enc = tok(ood_texts[i:i+32], max_length=MAX_LENGTH, padding=True,
                          truncation=True, return_tensors="pt").to(device)
                ood_preds.extend(model(**enc).logits.argmax(dim=1).cpu().tolist())
        ood_m = prf1(ood_preds, ood_labels)
        print(f"  ood:  F1={ood_m['f1']*100:.2f} acc={ood_m['accuracy']*100:.2f}")

    out_path = HERE / "results" / f"deberta_diagnostic_lr{lr}.json"
    out_path.write_text(json.dumps({"lr": lr, "fp16": False, "epochs": EPOCHS,
                                     "test_metrics": m, "ood_metrics": ood_m,
                                     "train_seconds": train_s}, indent=2))
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()

print("\nDone.")
