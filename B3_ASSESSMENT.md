# B3 Semantic Gate — Assessment & Sufficiency Determination

Prepared per the "determine with evidence before improving" mandate. This
report separates what is **verifiable from the artifact as delivered** from
what **cannot be measured here** and therefore must be run by you. I have not
retrained, replaced, or modified B3 — the mandate requires justification
first, and the decisive justification (a real evaluation) is not runnable in
this environment. See §0.

---

## §0 — Two blocking facts (read first)

**B0.1 — The model weights are not in this artifact.**
`b3/.../model/semantic_gate_v3/pytorch_model.bin` is a **134-byte Git LFS
pointer**, not weights:
```
version https://git-lfs.github.com/spec/v1
oid sha256:9ee7475e08f76ce6961c55204657a380d5ef1c2c9dac6a9d46543a7c42c2f5d2
size 567622450   # 542 MB — the real file, stored in LFS, not included
```
`training_args.bin` is likewise a 129-byte pointer. The **tokenizer is
real and present** (spm.model 2.4 MB, tokenizer.json 8.7 MB, full vocab
config). So the classifier cannot be loaded or run from this zip at all,
independent of hardware. **Action:** ship the artifact with `git lfs pull`
materialized, or host the checkpoint and document the fetch — reviewers who
download the artifact will hit exactly this wall.

**B0.2 — This environment has no torch/GPU.**
Every run this session records `b3_available: false`. Even with the weights,
Parts 5–8 (benchmarking, robustness, calibration, latency) require executing
the real model. I therefore cannot produce those numbers; I provide the
**runnable harnesses** for each and state precisely what to run.

**Consequence:** the correct, honest answer to "is B3 sufficient?" is
**"cannot be certified sufficient yet, on the evidence present in the
artifact"** — not because the model is known to be weak, but because the
evidence needed to certify it (materialized checkpoint + the eval outputs
its own scripts reference) is absent from what was delivered. §3 gives the
conditional determination.

---

## §1 — What B3 actually is (from code; fully verified)

**Architecture (config.json):** `DebertaV2ForSequenceClassification`,
**6 hidden layers**, hidden 768, 12 heads, intermediate 3072, vocab 128,100,
`max_position_embeddings` 512, disentangled attention (`pos_att_type
[p2c, c2p]`, `relative_attention: true`, `position_buckets 256`). This is a
**6-layer DeBERTa-v3 (base-width, reduced-depth)** — roughly a distilled/
compact v3, ~44–70 M params range (exact count needs the weights). float32.

**Labels:** binary — `0=BENIGN`, `1=MALICIOUS_SEMANTIC_MANIPULATION`
(normalized to `MALICIOUS` downstream in b3_bridge).

**Preprocessing/tokenizer:** SentencePiece (spm.model) via `AutoTokenizer`,
`max_length=256`, padding + truncation, batched.

**Inference (inference.py):** softmax over logits; `confidence = max prob`;
`local_files_only=True` (documented ~12.3 s/proc saving by skipping HF Hub
metadata checks); predictor cached by (path, max_len, device); CUDA if
available else CPU.

**Confidence → risk mapping (b3_bridge.py, `B3RiskPolicy`):** malicious &
conf ≥ 0.85 → `high`; ≥ 0.60 → `medium`; < 0.60 → `low`; benign → `none`;
unavailable → `unavailable`. Thresholds are config-overridable.

**Integration:** B3 emits `SemanticResult{available,label,confidence,
risk_level,status}` only; the Trust Engine consumes `risk_level` as opaque
(verified — no caller pattern-matches raw labels). Loss, optimizer, training
schedule: **not in the artifact** (training script absent; only `error_
analysis.py`, `new_qualitative_test.py`, `verify_cases_1_4.py` remain, and
they import a checkpoint + `outputs/splits/*` that are also absent).

**Calibration:** none in the inference path — raw softmax `max prob` is used
directly as confidence. No temperature scaling, no calibration layer. (This
is a concrete, fixable gap — §7.)

---

## §2 — Literature positioning (verified sources, 2024–2025)

- **Architecture choice is sound and does NOT warrant replacement.** Antoun
  et al. 2025 (arXiv:2504.08716), a *controlled same-data* comparison, find
  **DeBERTaV3 still exceeds ModernBERT on accuracy and sample efficiency**;
  ModernBERT wins only on long-context (8k) and raw speed. For a
  ≤256-token V2X message gate, long context is irrelevant. A deployment-
  aware prompt-injection study (arXiv:2605.26999) further finds **DeBERTa
  stronger than RoBERTa at the strict low-FPR operating point** — precisely
  the regime a safety gate runs in. => Switching to ModernBERT/RoBERTa is
  **not justified** on current evidence; the burden of proof (a measured win
  on THIS task) is not met, and the mandate forbids swapping on novelty
  alone.
- **The real, field-wide risk is evaluation validity, not architecture.**
  Multiple 2024–2026 works (Open-Prompt-Injection benchmark survey;
  arXiv:2602.14161 "When Benchmarks Lie"; arXiv:2606.22659) converge on:
  in-distribution splits **overstate** detector quality by several AUC
  points vs leave-one-dataset-out; generic injection classifiers **collapse
  under paraphrase/adaptive attacks** (ProtectAI DeBERTa defeated on 89% of
  paraphrase-to-evade cases in one healthcare study); and over-defensive
  detectors spike FPR on trigger-word-laced benigns (NotInject/InjecGuard).
- **Encouraging sign already in the repo:** B3's own retained scripts show
  the team evaluated on **unseen attack families (Test-1) and LOFO
  (leave-one-family-out)** with per-family F1 (AF4 91.27, AF6 89.23, AF7
  92.13, AF8 91.00). That is *exactly* the OOD-style methodology the
  literature demands — a genuine strength, IF those numbers can be
  reproduced from a materialized checkpoint. They currently cannot be, from
  this artifact.

---

## §3 — Sufficiency determination (conditional, honest)

**If** (a) the LFS checkpoint is materialized, (b) the `outputs/splits/*`
and the LOFO/Test-1 result files are restored, and (c) those per-family F1
numbers reproduce, **then B3 is plausibly sufficient for a workshop-to-
mid-tier venue without retraining**, because: the architecture is
appropriately chosen (§2), the label scheme and integration are clean (§1),
and the team already did unseen-family + LOFO evaluation (§2) that most
comparable papers omit.

**Retraining is NOT justified on current evidence.** No measured weakness of
the *model* is in hand — only missing evidence. Retraining before
reproducing the existing numbers would be working blind.

**What IS justified now (evidence-supported, low-risk, no retrain):**
1. **Calibration (Part 7)** — raw softmax is used as confidence with no
   calibration; temperature scaling is a standard, cheap post-hoc fix that
   the risk-band thresholds (0.85/0.60) directly depend on. Harness added:
   `b3_eval/run_calibration.py`.
2. **Robustness battery (Part 6)** — the literature's central threat
   (paraphrase/adaptive/trigger-word FPR) is untested here. Harness added:
   `b3_eval/run_robustness.py` (generates the adversarial variants;
   executes against the real model when present).
3. **Latency (Part 8)** — harness added: `b3_eval/run_latency.py`
   (cold/warm, CPU/GPU, single/batch, p50/p90/p95/p99, VRAM).
4. **Model benchmarking (Part 5)** — harness added:
   `b3_eval/run_model_benchmark.py` (compares the current checkpoint vs
   named HF baselines on the SAME held-out split, so any swap decision is
   evidence-based).

All four are **runnable as-is on your GPU box** and **degrade honestly**
(skip-with-reason) when the model is absent — none fabricate numbers.

---

## §4 — Dataset audit (from evidence present)

Verifiable: label space is binary; the retained scripts reference a
train/test split with **unseen-family** and **LOFO** structure and an
attack-family taxonomy (AF4 Emergency Override, AF6 Perception Denial, AF7
Infrastructure CPM, AF8 Traffic Efficiency, plus others) — good semantic/
attack diversity design. **Not verifiable from the artifact:** dataset
size, class balance, duplicate rate, hard-negative coverage — the dataset
files themselves are absent. **Action:** include a dataset card (size, per-
family counts, dedup method, license) and the split files; the literature
(NotInject/InjecGuard) specifically requires reporting benign-with-trigger-
word coverage to defend against over-defense claims.

---

## §5–§8 — Benchmarking / Robustness / Calibration / Latency

Cannot be executed here (no weights, no GPU). Delivered as runnable
harnesses under `b3_eval/` — see that directory's README for exact commands
and what each reports. Each writes a manifest (versions/hardware/checkpoint
hash) so results are reproducible and traceable.

## §9 — Training review

**Retraining not justified yet** (§3). The retraining *pipeline* is also not
reconstructable from the artifact (training script absent). If, after
running §5–§8, calibration or robustness proves inadequate AND post-hoc
fixes (temperature scaling; hard-negative-augmented threshold tuning) are
insufficient, then retraining becomes justified — at which point the absent
training script must be recovered from the original project, not
reverse-engineered.

## §11 — Reviewer scorecard (artifact as delivered)

| Axis | Score | Why below 9 |
|---|---|---|
| Novelty | 6 | STBV framing is good; the classifier itself is a standard fine-tuned DeBERTa-v3 — novelty is the *task/threat*, not the model. |
| Accuracy | **N/A** | Unmeasurable: checkpoint is an LFS stub, eval outputs absent. |
| Robustness | 3 | No adversarial/paraphrase/OOD tests present; literature says this is where such classifiers fail. Harness now provided. |
| Calibration | 2 | Raw softmax used as confidence; no ECE/Brier/temperature. Directly affects the 0.85/0.60 risk bands. Harness provided. |
| Explainability | 5 | Emits label+confidence+risk_level; no token attribution/rationale. Adequate but not strong. |
| Latency | N/A | Unmeasurable here; harness provided (and a warmup/preload path already exists). |
| Deployment readiness | 4 | LFS stub + no calibration + untested robustness block deployment claims. |
| Research contribution | 6 | The LOFO/unseen-family evaluation design is genuinely above average — *if* reproducible. |
| **Overall readiness** | **4** | Gated almost entirely by missing artifacts (weights, splits, results) and untested robustness/calibration — NOT by any demonstrated model weakness. |

**Bottom line:** Do **not** retrain and do **not** swap architectures on
current evidence — both are unjustified. Do materialize the checkpoint,
restore the eval outputs, and run the four `b3_eval/` harnesses on GPU. The
single highest-value additions that need no retraining are **calibration**
(temperature scaling) and a **paraphrase/adaptive robustness battery** —
the two things the 2024–2026 literature says decide whether a detector like
this survives review.
