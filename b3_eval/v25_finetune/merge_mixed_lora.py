"""Merges the mixed-corpus LoRA adapter into a standalone dense checkpoint,
mirroring how semantic_gate_v3_v25_lora_merged was produced. Base checkpoint
weights on disk are never modified (merge happens in memory; only the new
output directory is written)."""
import pathlib
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from peft import PeftModel

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ORIGINAL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"
LORA_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora"
OUT_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_merged"

tok = AutoTokenizer.from_pretrained(str(LORA_DIR), local_files_only=True)
base = AutoModelForSequenceClassification.from_pretrained(str(ORIGINAL_DIR), local_files_only=True)
peft_model = PeftModel.from_pretrained(base, str(LORA_DIR))
merged = peft_model.merge_and_unload()
OUT_DIR.mkdir(parents=True, exist_ok=True)
merged.save_pretrained(str(OUT_DIR))
tok.save_pretrained(str(OUT_DIR))
print(f"Merged model written to {OUT_DIR}")
