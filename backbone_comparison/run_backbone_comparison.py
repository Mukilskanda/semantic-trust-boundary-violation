#!/usr/bin/env python3
"""
run_backbone_comparison.py
=============================
Fine-tunes five transformer backbones (BERT, RoBERTa, DeBERTa, ModernBERT,
DistilBERT) on the IDENTICAL dataset (backbone_comparison/data/{train,test}.jsonl),
with IDENTICAL preprocessing (same tokenizer call signature: max_length=256,
padding="max_length", truncation=True), IDENTICAL training budget (3 epochs,
batch size 16, AdamW, lr 2e-5, fp16 autocast -- matching the methodology
already established in b3_eval/run_model_benchmark.py), and IDENTICAL
metrics (accuracy/precision/recall/F1, latency, peak VRAM, parameter count,
training time).

Does NOT alter the trust architecture: this is an isolated classifier-only
comparison, exactly like the existing b3_eval/run_model_benchmark.py
methodology it extends, with two differences: (1) the required five named
backbones, not five arbitrary candidates, and (2) peak-VRAM tracking added
(b3_eval/run_model_benchmark.py did not track memory; b3_eval/run_latency.py's
pattern, torch.cuda.reset_peak_memory_stats/max_memory_allocated, is reused
here). The production B3 checkpoint is separately reported, unmodified, as
a non-comparable reference row (different training data, budget, and
architecture depth -- stated explicitly, not blended into the controlled
comparison).

Run:  python3 backbone_comparison/run_backbone_comparison.py
"""
from __future__ import annotations
import json, pathlib, statistics, sys, time
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "b3" / "solution_stb" / "b3_semantic_gate"))

HERE = pathlib.Path(__file__).resolve().parent

BACKBONES = {
    "BERT": "bert-base-uncased",
    "RoBERTa": "roberta-base",
    "DeBERTa": "microsoft/deberta-v3-base",
    "ModernBERT": "answerdotai/ModernBERT-base",
    "DistilBERT": "distilbert-base-uncased",
}

EPOCHS = 3
BATCH_SIZE = 16
LR = 2e-5
MAX_LENGTH = 256
SEEDS = [0, 1]  # two seeds per backbone, for a mean +/- spread rather than a single run


def load_jsonl(p):
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def prf1(preds, labels):
    tp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 1)
    fp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 0)
    fn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 1)
    tn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / len(labels)
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def measure_latency(fn, n=50):
    for _ in range(10):
        fn()
    runs = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        runs.append((time.perf_counter() - t0) * 1000.0)
    s = sorted(runs)
    return {"p50": s[len(s) // 2], "p95": s[int(len(s) * .95)], "mean": statistics.mean(runs)}


def load_ood_corpus():
    """The independently-authored external semantic corpus
    (external_semantic_eval/external_corpus.json) used as an
    out-of-distribution generalization check: the matched STBV-Bench-style
    test set saturates to F1=100 for most backbones once fine-tuned
    (near-identical templated phrasing to the training data), which makes
    it uninformative for distinguishing architectures or producing a real
    failure analysis. The external corpus is written by different
    authorial processes (Claude directly, Claude batch, GPT, Gemini,
    public-prompt-injection-derived) and was never seen by any of these
    backbones during training -- a genuine OOD test."""
    p = ROOT / "external_semantic_eval" / "external_corpus.json"
    if not p.exists():
        return None, None, None
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = data["entries"]
    texts = [e["text"] for e in entries]
    labels = [1 if e["label"] == "MALICIOUS" else 0 for e in entries]
    families = [e["family"] for e in entries]
    return texts, labels, families


def main():
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train = load_jsonl(HERE / "data" / "train.jsonl")
    test = load_jsonl(HERE / "data" / "test.jsonl")
    test_texts = [r["text"] for r in test]
    test_labels = [r["label"] for r in test]
    test_families = [r["attack_family"] for r in test]

    ood_texts, ood_labels, ood_families = load_ood_corpus()

    print(f"device={device}, train n={len(train)}, test n={len(test)}, "
          f"ood n={len(ood_texts) if ood_texts else 0}")

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

    results = {}
    predictions_by_backbone = {}
    ood_predictions_by_backbone = {}

    def train_and_eval(hf_name, seed, use_fp16):
        torch.manual_seed(seed)
        tok = AutoTokenizer.from_pretrained(hf_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            hf_name, num_labels=2).to(device)
        nparams = sum(p.numel() for p in model.parameters())

        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()

        amp_enabled = use_fp16 and device.type == "cuda"
        dl = DataLoader(DS(train, tok), batch_size=BATCH_SIZE, shuffle=True)
        opt = torch.optim.AdamW(model.parameters(), lr=LR)
        scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)

        t0 = time.perf_counter()
        model.train()
        for ep in range(EPOCHS):
            for batch in dl:
                batch = {k: v.to(device) for k, v in batch.items()}
                opt.zero_grad()
                with torch.autocast(device_type=device.type, enabled=amp_enabled):
                    out = model(**batch)
                scaler.scale(out.loss).backward()
                scaler.step(opt); scaler.update()
        train_s = time.perf_counter() - t0

        peak_vram_mb = (torch.cuda.max_memory_allocated() / 1e6) if device.type == "cuda" else None

        def run_inference(texts):
            preds = []
            model.eval()
            with torch.no_grad():
                for i in range(0, len(texts), 32):
                    enc = tok(texts[i:i+32], max_length=MAX_LENGTH, padding=True,
                              truncation=True, return_tensors="pt").to(device)
                    preds.extend(model(**enc).logits.argmax(dim=1).cpu().tolist())
            return preds

        preds = run_inference(test_texts)
        m = prf1(preds, test_labels)
        ood_preds, ood_m = None, None
        if ood_texts:
            ood_preds = run_inference(ood_texts)
            ood_m = prf1(ood_preds, ood_labels)

        def one():
            with torch.no_grad():
                enc = tok(test_texts[0], max_length=MAX_LENGTH, padding=True,
                          truncation=True, return_tensors="pt").to(device)
                model(**enc)
        lat = measure_latency(one)

        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return {**m, "latency_ms": lat, "parameters": nparams, "train_seconds": train_s,
                "peak_vram_mb": peak_vram_mb, "seed": seed, "used_fp16": amp_enabled,
                "ood_metrics": ood_m}, preds, ood_preds

    for display_name, hf_name in BACKBONES.items():
        print(f"\n{'='*70}\n{display_name} ({hf_name})\n{'='*70}")
        seed_runs = []
        last_preds, last_ood_preds = None, None
        for seed in SEEDS:
            try:
                run_result, preds, ood_preds = train_and_eval(hf_name, seed, use_fp16=True)
                seed_runs.append(run_result)
                last_preds, last_ood_preds = preds, ood_preds
                ood_str = f"  OOD_F1={run_result['ood_metrics']['f1']*100:.2f}" if run_result["ood_metrics"] else ""
                print(f"  seed={seed}  F1={run_result['f1']*100:.2f}  acc={run_result['accuracy']*100:.2f}  "
                      f"p95={run_result['latency_ms']['p95']:.2f}ms  VRAM={run_result['peak_vram_mb']}  "
                      f"params={run_result['parameters']/1e6:.1f}M  train={run_result['train_seconds']:.1f}s{ood_str}")
            except Exception as e:
                print(f"  seed={seed} fp16 run FAILED: {e} -- retrying in fp32 (disclosed deviation)")
                try:
                    run_result, preds, ood_preds = train_and_eval(hf_name, seed, use_fp16=False)
                    run_result["fp16_fallback_reason"] = f"{type(e).__name__}: {e}"
                    seed_runs.append(run_result)
                    last_preds, last_ood_preds = preds, ood_preds
                    ood_str = f"  OOD_F1={run_result['ood_metrics']['f1']*100:.2f}" if run_result["ood_metrics"] else ""
                    print(f"  seed={seed} (fp32 fallback)  F1={run_result['f1']*100:.2f}  "
                          f"acc={run_result['accuracy']*100:.2f}  p95={run_result['latency_ms']['p95']:.2f}ms  "
                          f"VRAM={run_result['peak_vram_mb']}  params={run_result['parameters']/1e6:.1f}M  "
                          f"train={run_result['train_seconds']:.1f}s{ood_str}")
                except Exception as e2:
                    seed_runs.append({"error": f"{type(e2).__name__}: {e2}", "seed": seed})
                    print(f"  seed={seed} FAILED even in fp32: {e2}")

        ok_runs = [r for r in seed_runs if "error" not in r]
        if ok_runs:
            ood_runs = [r["ood_metrics"] for r in ok_runs if r.get("ood_metrics")]
            agg = {
                "accuracy_mean": statistics.mean(r["accuracy"] for r in ok_runs),
                "precision_mean": statistics.mean(r["precision"] for r in ok_runs),
                "recall_mean": statistics.mean(r["recall"] for r in ok_runs),
                "f1_mean": statistics.mean(r["f1"] for r in ok_runs),
                "f1_stdev": statistics.stdev(r["f1"] for r in ok_runs) if len(ok_runs) > 1 else 0.0,
                "latency_p95_mean_ms": statistics.mean(r["latency_ms"]["p95"] for r in ok_runs),
                "latency_p50_mean_ms": statistics.mean(r["latency_ms"]["p50"] for r in ok_runs),
                "peak_vram_mb_mean": statistics.mean(r["peak_vram_mb"] for r in ok_runs) if ok_runs[0]["peak_vram_mb"] is not None else None,
                "parameters": ok_runs[0]["parameters"],
                "train_seconds_mean": statistics.mean(r["train_seconds"] for r in ok_runs),
                "n_seeds_ok": len(ok_runs),
                "used_fp16": ok_runs[0].get("used_fp16"),
                "fp16_fallback_reason": next((r["fp16_fallback_reason"] for r in ok_runs if "fp16_fallback_reason" in r), None),
                "ood_accuracy_mean": statistics.mean(r["accuracy"] for r in ood_runs) if ood_runs else None,
                "ood_precision_mean": statistics.mean(r["precision"] for r in ood_runs) if ood_runs else None,
                "ood_recall_mean": statistics.mean(r["recall"] for r in ood_runs) if ood_runs else None,
                "ood_f1_mean": statistics.mean(r["f1"] for r in ood_runs) if ood_runs else None,
            }
        else:
            agg = {"error": "all seeds failed"}
        results[display_name] = {"hf_name": hf_name, "seed_runs": seed_runs, "aggregate": agg}
        if last_preds is not None:
            predictions_by_backbone[display_name] = last_preds
        if last_ood_preds is not None:
            ood_predictions_by_backbone[display_name] = last_ood_preds

    # ---- production incumbent, reference only (not part of controlled comparison) ----
    try:
        from inference import get_predictor
        model_dir = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"
        predictor = get_predictor(str(model_dir), max_length=MAX_LENGTH)
        inc_results = predictor.predict(test_texts, batch_size=32)
        inc_preds = [1 if r.label_id == 1 else 0 for r in inc_results]
        inc_m = prf1(inc_preds, test_labels)
        nparams_inc = sum(p.numel() for p in predictor.model.parameters())

        def one_inc():
            predictor.predict([test_texts[0]], batch_size=1)
        inc_lat = measure_latency(one_inc)
        inc_ood_m = None
        if ood_texts:
            inc_ood_results = predictor.predict(ood_texts, batch_size=32)
            inc_ood_preds = [1 if r.label_id == 1 else 0 for r in inc_ood_results]
            inc_ood_m = prf1(inc_ood_preds, ood_labels)
            ood_predictions_by_backbone["INCUMBENT_reference_only"] = inc_ood_preds
        results["INCUMBENT_reference_only"] = {
            "hf_name": "production semantic_gate_v3 (custom 6-layer DeBERTa-v2)",
            "note": "NOT part of the controlled comparison -- different training data/budget/depth. Reference only.",
            "metrics": inc_m, "ood_metrics": inc_ood_m, "latency_ms": inc_lat, "parameters": nparams_inc,
        }
        predictions_by_backbone["INCUMBENT_reference_only"] = inc_preds
        ood_str = f" OOD_F1={inc_ood_m['f1']*100:.2f}" if inc_ood_m else ""
        print(f"\nINCUMBENT (reference) F1={inc_m['f1']*100:.2f} acc={inc_m['accuracy']*100:.2f}{ood_str}")
    except Exception as e:
        print(f"\n[INCUMBENT reference skipped: {e}]")

    out = {
        "manifest": {
            "experiment": "backbone_comparison",
            "backbones": BACKBONES,
            "epochs": EPOCHS, "batch_size": BATCH_SIZE, "lr": LR, "max_length": MAX_LENGTH,
            "seeds": SEEDS,
            "n_train": len(train), "n_test": len(test), "n_ood": len(ood_texts) if ood_texts else 0,
            "note": "Identical dataset, preprocessing, training budget, and metrics across all 5 backbones. No architecture change to the trust pipeline.",
        },
        "results": results,
        "test_labels": test_labels,
        "test_families": test_families,
        "ood_labels": ood_labels,
        "ood_families": ood_families,
        "predictions_by_backbone": predictions_by_backbone,
        "ood_predictions_by_backbone": ood_predictions_by_backbone,
    }
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "backbone_comparison_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {HERE / 'results' / 'backbone_comparison_results.json'}")


if __name__ == "__main__":
    main()
