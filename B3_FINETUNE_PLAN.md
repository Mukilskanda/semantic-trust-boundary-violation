# B3 Fine-Tuning Plan for STBV-Bench v2.5

**No training has been run.** This is a plan only, per the request. Every
fact below (paths, config values, param counts, hardware) was inspected
directly from the repository and this machine, not assumed.

## 1. Is incremental fine-tuning from the current checkpoint supported?

**Weight-level continuation: yes. Optimizer-state-level resumption: no —
that capability does not exist in this artifact.**

The checkpoint at
`b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/` contains:

```
config.json            model architecture + label mapping
pytorch_model.bin       567,622,450 bytes -- real weights (not an LFS pointer)
tokenizer.json, spm.model, tokenizer_config.json, special_tokens_map.json
added_tokens.json
training_args.bin      pickled HF TrainingArguments from the ORIGINAL run
onnx/                   exported inference-only copy (irrelevant to training)
```

It does **not** contain `optimizer.pt`, `scheduler.pt`, `trainer_state.json`,
or `rng_state.pth` — the four files `Trainer(resume_from_checkpoint=...)`
requires to resume a run bit-for-bit (Adam first/second moment estimates,
LR-schedule step position, epoch/global-step counters, RNG state). I
searched the full repository for these filenames and for any training
script (`grep` for `DebertaV2ForSequenceClassification`, `Trainer(`,
`TrainingArguments(` across all `.py` files outside `.venv`) — **no
training script exists in this repository at all.** `training_args.bin`
records that the checkpoint was originally produced on a different
machine (`output_dir=/home/harshitvaish123/v2x-pi-project/...`); only the
resulting artifacts were delivered here, not the code that produced them.

**Practical consequence**: "resuming" here can only mean *initializing a
new training run from these weights* (a completely standard and fully
supported fine-tuning pattern in `transformers`/PyTorch), not *continuing
the original optimizer trajectory*. The original recipe is still fully
known (see §2) and can be replicated as a fresh run initialized from this
checkpoint.

## 2. Everything needed to resume training safely

| Item | Value | Source |
|---|---|---|
| Checkpoint path | `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/` | inspected directly |
| Architecture | `DebertaV2ForSequenceClassification`, 6 hidden layers, hidden=768, 12 heads, intermediate=3072, `pos_att_type=[p2c,c2p]`, disentangled relative attention | `config.json` |
| Total parameters | **141,896,450** (141.9M) — embeddings 98.8M (70%), encoder 42.5M, pooler+classifier head 592K | measured via `sum(p.numel() ...)` |
| Tokenizer | SentencePiece, `spm.model` + `tokenizer.json`, vocab 128,100, load via `AutoTokenizer.from_pretrained(path, local_files_only=True)` | `inference.py:102` |
| Label mapping | `{0: "BENIGN", 1: "MALICIOUS_SEMANTIC_MANIPULATION"}` (`id2label`/`label2id` in `config.json`); `pipeline/b3_bridge.py` folds `MALICIOUS_SEMANTIC_MANIPULATION` → `"MALICIOUS"` for downstream consumers only — **the underlying model's own labels are the two above**, use them for training targets | `config.json`, `pipeline/b3_bridge.py:299` |
| v2.5 label → model label | v2.5 `label: 0` → id 0 (BENIGN); v2.5 `label: 1` → id 1 (MALICIOUS_SEMANTIC_MANIPULATION) | direct match, no remapping needed |
| max_length | 256 tokens | `inference.py:80`, `isce_config.yaml` |
| Optimizer state | **absent** — start AdamW fresh | confirmed by directory listing |
| Original recipe (for reference / replication) | AdamW, lr=**2e-5**, linear schedule, warmup_ratio=0.1, weight_decay=0.01, batch=16/device, 15 epochs, `metric_for_best_model=f1`, `load_best_model_at_end=True`, seed=42, max_grad_norm=1.0 | `training_args.bin` (unpickled) |
| Existing temperature scaling | 2.1446 (fitted post-hoc; ECE 0.062→0.028 on whatever split that calibration run used — **not the same corpus as v2.5**, will need refitting after any fine-tune) | `isce_config.yaml` |
| Existing splits in repo | `b3_eval/data/{train,test,calibration,id,ood}_split.jsonl` — **from the original/v1-era pipeline, not v2.5**; do not reuse for v2.5 fine-tuning | `b3_eval/data/` |
| Closest reusable training-loop code | `b3_eval/run_model_benchmark.py:184-220` — AdamW + `torch.autocast`/`GradScaler` AMP loop, currently used to fine-tune *comparison* backbones from HF hub IDs. Trivially adaptable: point `AutoModelForSequenceClassification.from_pretrained(name, ...)` at the local checkpoint path instead of a hub ID. Not a drop-in `resume_from_checkpoint` path — a new script is still needed for the actual plan below. | inspected directly |

**Nothing above is inferred from documentation** — the label mapping,
parameter counts, and hyperparameters were all read from the checkpoint's
own files or computed by loading the model.

## 3. Which parameters to train — recommendation

### Why the obvious default (classifier head only) is probably not enough

UPDATED_RESULTS.md shows B3's failure mode is not a miscalibrated decision
threshold — recall varies from 0.97 (`sensor_discreditation`) down to 0.08
(`goal_manipulation`) and 0.16 (`role_confusion`) across attack families
that all currently share the same frozen encoder. A single linear
classifier head sits on top of a fixed `[CLS]` (pooler) representation; if
that representation does not separate `goal_manipulation` messages from
benign ones in the first place (which near-chance recall suggests), no
re-weighting of the head can fix it — **the encoder itself needs to move**,
at least for some layers, or this failure mode will persist unchanged.

### Why full fine-tuning is the wrong first move here

Full fine-tuning of all 141.9M parameters (i) has the highest catastrophic-
forgetting risk on the families where B3 currently does well
(`sensor_discreditation` 0.97, `fabricated_consensus` 0.80) — nothing in a
naive full fine-tune protects those, and losing them would just trade one
failure pattern for another rather than fixing the gap; (ii) is the most
memory-expensive option on a 6 GB GPU (§4); (iii) is unnecessary — the
encoder is only 6 layers, so even partial-depth adaptation reaches every
layer's *output*, and the embedding table (98.8M of the 141.9M — 70% of
the model) essentially never needs to move for a fine-tune this small (the
domain's subword vocabulary is standard English/route-report English, not
a new language or script).

### Recommendation: **LoRA on all 6 encoder layers' attention and FFN projections, plus a fully-trainable classifier head and pooler.**

| Component | Trainable? | Why |
|---|---|---|
| Word/position/relative-position embeddings (98.8M) | **Frozen** | No new vocabulary or language; embeddings are the least likely source of the family-specific recall gap and the most expensive to retrain safely |
| Encoder layers 0–5, `query_proj`/`key_proj`/`value_proj`/`dense` (attention) and `intermediate.dense`/`output.dense` (FFN) | **LoRA adapters, rank r=8–16, α=16–32, on all 6 layers** | Reaches every layer's representation (unlike gradual unfreezing of only the top 1–2 layers, which cannot fix a pragmatic distinction the model fails to encode even at layer 2–3), while the frozen base weights are mathematically unchanged — this is the direct, principled way to satisfy "preserve previously learned semantic knowledge": the original 141.9M weights are never touched, only a low-rank additive delta is learned and can be disabled/ablated later to recover the exact original model |
| `pooler.dense` (590K) | **Fully trainable** | Small, directly feeds the classifier, cheap to adapt fully |
| `classifier` (1,538 params) | **Fully trainable** | Must always be trainable — this is the actual decision boundary |

**Trainable parameter count**: LoRA (r=16) on 6 layers × 6 projected
matrices (`query_proj`, `key_proj`, `value_proj`, attention `dense`,
`intermediate.dense`, `output.dense`) ≈ 6 layers × 6 matrices ×
2×(768×16) ≈ **~1.06M** LoRA parameters, plus pooler (590K) + classifier
(1.5K) ≈ **~1.65M trainable parameters total — 1.16% of the 141.9M full
model.**

**Fallback if LoRA underperforms**: gradual unfreezing as a second
experiment, not a replacement — freeze embeddings + layers 0–3, fully
unfreeze layers 4–5 + pooler + classifier (≈ 14.2M trainable, 10% of the
model). Try this only if LoRA's rank-16 adapters can't close the gap on
the near-chance families; it costs more memory and forgetting risk than
LoRA, so it is the second experiment, not the first.

**Not recommended as the first attempt**: full fine-tuning (forgetting
risk on already-working families, highest memory footprint, and the
problem as currently characterized does not obviously require moving
70% of the parameters that live in the embedding table).

`peft` (the library needed for LoRA on `transformers` models) is **not
currently installed** in this environment — `pip install peft` would be a
prerequisite, noted here rather than done, since no training is being run.

## 4. Estimated GPU memory usage

Hardware on this machine: **NVIDIA GeForce RTX 4050 Laptop GPU, 6,141 MiB
total VRAM, currently 5,920 MiB free** (measured via `nvidia-smi`); 16 GB
system RAM. This is a small laptop GPU and the binding constraint on every
option below.

| Configuration | Static (weights+grad+optimizer) | Est. activations @ batch 16, seq 256 | Est. total peak | Fits in 5.9 GB free? |
|---|---|---|---|---|
| **LoRA r=16 (recommended)**, bf16 base (frozen, no grad) + fp32 LoRA/head params + AdamW on LoRA/head only | base weights 142M×2B(bf16)=284MB (no grad/optimizer needed, frozen) + trainable ~1.65M×4B×(1+2)=~26MB | ~500–800MB (still runs full forward/backward through all 6 layers) | **~1.0–1.2 GB** | **Yes, comfortably** — room to raise batch size to 32+ |
| Gradual unfreeze (top 2 layers + head, ~14.2M trainable) | frozen part 128M×2B(bf16)=256MB + trainable 14.2M×4B×(1+1+2)=227MB (bf16 fwd, fp32 grad+optimizer) | ~500–800MB | **~1.0–1.3 GB** | Yes |
| Full fine-tune, fp32, AdamW | 142M×4B×(1weights+1grad+2optim)=**2.27 GB** | ~0.5–1.0GB (no gradient checkpointing) | **~2.8–3.3 GB** | Yes, but tight with OS/driver overhead (~300–500MB reserved outside PyTorch) — recommend `gradient_checkpointing=True` and batch size ≤8 if this path is ever used |
| Full fine-tune, fp16/bf16 AMP, AdamW | fp32 master 568MB + fp16 compute copy 284MB + fp16 grad 284MB + fp32 optimizer states 1,136MB ≈ **2.27 GB** (AMP mainly saves activation memory, not optimizer memory) | ~0.3–0.5GB (fp16 activations) | **~2.6–3.0 GB** | Yes, more headroom than plain fp32 |

**Bottom line**: LoRA leaves the most headroom by a wide margin on this
specific 6 GB card — full fine-tuning is not memory-infeasible here, but
it uses 2.5–3x the peak memory of LoRA for a change that carries
materially higher forgetting risk, which is the reason LoRA is the
recommendation in §3, not primarily a memory argument.

## 5. Estimated runtime

- **Corpus**: STBV-Bench v2.5, 12,244 messages (5,612 benign / 6,632
  malicious). Following the lexical-leakage findings, the fine-tuning
  split **must itself be template-disjoint** (group by `template_id`,
  already present in every row of
  `data/stbv_bench/v25/stbv_bench_v25.jsonl`) — otherwise B3 could simply
  memorize the same 180 skeletons the lexical baselines memorized, and
  the whole point of this re-training would be undermined by the exact
  failure mode BENCHMARK_AUDIT.md documents. Recommended split: 70/15/15
  train/val/test by `template_id` group (not by row), roughly 8,570 /
  1,837 / 1,837 messages.
- **Steps per epoch** at batch size 16: ⌈8,570/16⌉ ≈ 536 steps.
- **Per-step wall time** (RTX 4050 Laptop, 6-layer DeBERTa-v2, seq 256,
  LoRA — backward pass touches far fewer parameters than full fine-tune
  but still runs the full forward/backward graph through all 6 layers, so
  the per-step cost is close to, not dramatically less than, full
  fine-tune): estimated **~120–200 ms/step** based on this model's
  measured inference latency profile (`b3_eval/run_latency.py` results
  already in this repo) scaled up ~3x for backward pass + optimizer step.
- **Epochs**: LoRA typically needs *more* epochs than full fine-tuning to
  converge (smaller effective capacity, smaller per-step updates) —
  budget **8–12 epochs** rather than the original recipe's 15 (which was
  for full fine-tuning from a pretrained backbone, a harder problem than
  adapting an already-fine-tuned checkpoint).
- **Estimated total**: 536 steps/epoch × 10 epochs × ~0.16 s/step ≈
  **~860 s ≈ 14–15 minutes** of pure training compute, plus model/data
  loading (~30–60 s) and per-epoch validation passes (~1,837 val examples
  at inference batch 32 ≈ 58 batches × ~50 ms ≈ 3 s/epoch — negligible).
  **Realistic wall-clock estimate: 20–30 minutes end-to-end**, including
  warmup, checkpoint saving (`save_strategy=epoch`, keep best-by-F1), and
  a final calibration refit (`b3_eval/run_calibration.py`, needed because
  the existing `temperature_scaling: 2.1446` was fit on a different
  corpus and will not transfer to a re-trained model).
- If the gradual-unfreezing fallback (§3) is used instead, expect
  roughly **1.5–2x** this runtime (more trainable parameters, similar
  per-step forward cost, typically needs fewer epochs than LoRA but each
  epoch's backward pass is heavier) — still well under an hour on this
  hardware.

## 6. What this plan does not include (explicitly, not silently assumed)

- No training has been executed — no `train.py` was written or run.
- No `peft` installation has been performed.
- No template-disjoint train/val/test files for v2.5 have been materialized
  yet — the split *design* is specified above (group by `template_id`,
  70/15/15) but the actual `jsonl` files are not yet on disk.
- Calibration (`temperature_scaling`) will need refitting after any
  fine-tuning run — the current value (2.1446) is specific to the
  currently-deployed checkpoint and a different corpus, and must not be
  assumed to transfer.
- This plan intentionally stops at "ready to write the training script" —
  it does not start training, per the request.
