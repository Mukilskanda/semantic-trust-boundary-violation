"""Quick, correct fix: compute P(malicious) directly from the final
checkpoint for all STBV-Bench v1 evaluated samples (classifier forward
pass only, not the full pipeline -- fast), for a correct ROC/PR curve.
"""
import json, sys, pathlib
sys.path.insert(0, '.')
sys.path.insert(0, 'b3_eval/v25_finetune')
from eval_common import load_jsonl, LoadedModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

MODEL_DIR = pathlib.Path("b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_continued_merged")
V1_PATH = pathlib.Path("data/stbv_bench/v1/stbv_bench.jsonl")

device = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR), local_files_only=True).to(device)
m = LoadedModel("final", model, tok, device, temperature=2.82)

rows = []
with open(V1_PATH, encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 10000:
            break
        rows.append(json.loads(line))

texts, labels, families = [], [], []
for r in rows:
    tm = r["transformed_message"]
    peer_reports = tm.get("scene_context", {}).get("peer_reports", [])
    text = " ".join(peer_reports) if peer_reports else ""
    texts.append(text)
    labels.append(1 if tm.get("is_attacker") else 0)
    families.append(r["attack_family"])

preds = m.predict(texts, batch_size=64)
out = pathlib.Path("b3_eval/v25_finetune/ablation_results/final/v1_pmalicious.csv")
with open(out, "w", encoding="utf-8") as f:
    f.write("sample_id,attack_family,is_attacker,p_malicious,label\n")
    for r, lab, fam, p in zip(rows, labels, families, preds):
        f.write(f"{r['sample_id']},{fam},{lab==1},{p['prob_malicious']},{p['label']}\n")
print("[ok]", out, "n=", len(preds))
