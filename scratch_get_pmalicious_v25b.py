"""Per-sample P(malicious) for v2.5b, direct classifier (raw text, no
pipeline wrapping), final checkpoint -- needed to pair against the
pipeline's config_5 CSV for a genuine sample-by-sample comparison."""
import json, sys, pathlib
sys.path.insert(0, '.')
sys.path.insert(0, 'b3_eval/v25_finetune')
from eval_common import LoadedModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

MODEL_DIR = pathlib.Path("b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_mixed_lora_continued_merged")
V25B_PATH = pathlib.Path("data/stbv_bench/v25b/stbv_bench_v25b.jsonl")

device = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR), local_files_only=True).to(device)
m = LoadedModel("final", model, tok, device, temperature=2.82)

rows = [json.loads(l) for l in open(V25B_PATH, encoding="utf-8") if l.strip()]
texts = [r["text"] for r in rows]
labels = [r["label"] for r in rows]

preds = m.predict(texts, batch_size=64)
out = pathlib.Path("b3_eval/v25_finetune/ablation_results/v25b_full/direct_classifier_pmalicious.csv")
with open(out, "w", encoding="utf-8") as f:
    f.write("sample_id,attack_family,is_attacker,p_malicious,label,text_token_count,text\n")
    for r, lab, p in zip(rows, labels, preds):
        ntok = len(tok.encode(r["text"]))
        text_escaped = r["text"].replace('"', "'")
        f.write(f'{r["sample_id"]},{r["attack_family"]},{lab==1},{p["prob_malicious"]},{p["label"]},{ntok},"{text_escaped}"\n')
print("[ok]", out, "n=", len(preds))
