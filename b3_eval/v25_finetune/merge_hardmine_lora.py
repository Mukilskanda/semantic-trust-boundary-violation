"""Merges the hardmine-continued LoRA adapter (semantic_gate_v3_mixed_lora_hardmine,
produced by train_lora_hardmine.py resuming semantic_gate_v3_mixed_lora_continued
on the leakage-audited hard-example batch) into a standalone dense checkpoint,
for evaluation with eval_v25b_final.py's dense-model loader. Base and prior
checkpoints on disk are never modified."""
import pathlib
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from peft import PeftModel

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ORIGINAL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"
LORA_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_hardmine"
OUT_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_hardmine_merged"

tok = AutoTokenizer.from_pretrained(str(LORA_DIR), local_files_only=True)
base = AutoModelForSequenceClassification.from_pretrained(str(ORIGINAL_DIR), local_files_only=True)
peft_model = PeftModel.from_pretrained(base, str(LORA_DIR))
merged = peft_model.merge_and_unload()
OUT_DIR.mkdir(parents=True, exist_ok=True)
merged.save_pretrained(str(OUT_DIR))
tok.save_pretrained(str(OUT_DIR))
print(f"Merged model written to {OUT_DIR}")
