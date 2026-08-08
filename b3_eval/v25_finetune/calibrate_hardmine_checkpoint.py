"""
b3_eval/v25_finetune/calibrate_hardmine_checkpoint.py
========================================================
Fits temperature scaling for the new hardmine-continued checkpoint
(semantic_gate_v3_mixed_lora_hardmine_merged), using the IDENTICAL
methodology already deployed for the prior final checkpoint
(calibrate_final_checkpoint.py's single-template fit on
b3_eval/data/calibration_split.jsonl) -- deliberately NOT the ensembled
variant, since the calibration-methodology question itself was already
investigated, verified, and closed this session (CALIBRATION_FIX_REPORT.md).
This script only re-applies the existing, already-decided methodology to
a new checkpoint, which is required because temperature is checkpoint-
specific (a new set of LoRA weights has a different logit scale) --
it does not reopen the calibration investigation.
"""
from __future__ import annotations
import json, math, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from b3_eval.v25_finetune.eval_common import load_jsonl  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402
import torch  # noqa: E402

MODEL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_hardmine_merged"
CALIB_SPLIT = ROOT / "b3_eval" / "data" / "calibration_split.jsonl"
MAX_LENGTH = 256


@torch.no_grad()
def get_logits(model, tok, texts, device, batch_size=32):
    model.eval()
    out = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        enc = tok(chunk, max_length=MAX_LENGTH, padding=True, truncation=True,
                   return_tensors="pt").to(device)
        out.extend(model(**enc).logits.float().cpu().tolist())
    return out


def nll(logits, labels, T):
    total = 0.0
    for lg, y in zip(logits, labels):
        scaled = [v / T for v in lg]
        m = max(scaled)
        z = sum(math.exp(v - m) for v in scaled)
        logp = scaled[y] - m - math.log(z)
        total -= logp
    return total / len(labels)


def ece(logits, labels, T, n_bins=15):
    confs, correct = [], []
    for lg, y in zip(logits, labels):
        scaled = [v / T for v in lg]
        m = max(scaled)
        exps = [math.exp(v - m) for v in scaled]
        z = sum(exps)
        probs = [e / z for e in exps]
        pred = probs.index(max(probs))
        confs.append(max(probs))
        correct.append(int(pred == y))
    bins = [[] for _ in range(n_bins)]
    for c, corr in zip(confs, correct):
        b = min(n_bins - 1, int(c * n_bins))
        bins[b].append((c, corr))
    n = len(confs)
    e = 0.0
    for b in bins:
        if not b:
            continue
        acc = sum(x[1] for x in b) / len(b)
        conf = sum(x[0] for x in b) / len(b)
        e += (len(b) / n) * abs(acc - conf)
    return e


def fit_temperature(logits, labels):
    best_T, best_nll = 1.0, nll(logits, labels, 1.0)
    for T in [round(0.5 + 0.02 * i, 3) for i in range(int((5.0 - 0.5) / 0.02) + 1)]:
        v = nll(logits, labels, T)
        if v < best_nll:
            best_nll, best_T = v, T
    return best_T, best_nll


def main():
    assert MODEL_DIR.exists(), f"hardmine checkpoint missing: {MODEL_DIR}"
    assert CALIB_SPLIT.exists(), f"calibration split missing: {CALIB_SPLIT}"
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR), local_files_only=True).to(device)

    rows = load_jsonl(CALIB_SPLIT)
    texts = [r["text"] for r in rows]
    labels = [int(r["label"]) for r in rows]
    logits = get_logits(model, tok, texts, device)

    T, best_nll = fit_temperature(logits, labels)
    ece_before = ece(logits, labels, 1.0)
    ece_after = ece(logits, labels, T)

    result = {
        "model_dir": str(MODEL_DIR),
        "calibration_split": str(CALIB_SPLIT), "n": len(rows),
        "fitted_temperature": T, "nll_at_fitted_T": best_nll,
        "ece_uncalibrated_T1": ece_before, "ece_calibrated": ece_after,
        "note": "Fitted specifically for semantic_gate_v3_mixed_lora_hardmine_merged using the "
                "SAME single-template methodology already deployed (calibrate_final_checkpoint.py); "
                "NOT interchangeable with the prior checkpoint's temperature (2.82).",
    }
    out_path = HERE / "results" / "hardmine_checkpoint_calibration.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\n[ok] {out_path}")


if __name__ == "__main__":
    main()
