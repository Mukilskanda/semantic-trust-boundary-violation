# INDEPENDENT_BENCHMARK.md — construction methodology and leakage verification

## Purpose

Build the strongest single piece of independent generalization evidence for
`semantic_gate_v3_mixed_lora_merged`: a corpus that is (a) fully disjoint
from every existing corpus in this project and (b) fully **inside** the
paper's declared deployment scope — the inverse of `hard_ood_bench`, which
was deliberately constructed *outside* scope to probe register robustness.
This benchmark instead tests genuine content/scenario novelty (new
locations, entities, narratives) while holding register fixed at the
paper's own claimed register (grammatical, professional, ETSI CAM/DENM-style
third-person report text).

## Construction

- Script: `indep_bench/build_independent_corpus.py`. Local LLM (Mistral 7B
  via Ollama), one consistent in-scope register throughout ("formal,
  fully grammatical, professional ETSI CAM/DENM-style scene-report... no
  slang, no idiom"), deliberately *not* varied by style (unlike
  `hard_ood_bench`) since this benchmark's job is content novelty, not
  register robustness.
- Same 18 concepts as `hard_ood_bench` (12 malicious STBV-Bench-taxonomy
  attack families + 6 benign concepts, 3 of them explicit hard negatives)
  for family-level comparability with the rest of the paper, but every
  individual message is generated fresh, seeded with a **randomly assigned,
  never-repeated scenario context** (one of 12 cities never referenced in
  any existing corpus, one of 8 fictional-but-plausible road names, one of
  4 entity-ID naming schemes with randomized numbers) explicitly to force
  new narrative content rather than superficial synonym substitution of an
  existing template.
- 216 messages (144 malicious / 72 benign, 12 per concept), 53 distinct
  city/road scenario pairs used across the corpus (verified: no repeated
  scenario combination reused for two different concepts).
- Seed 20260810, fully reproducible generation procedure and prompt
  template documented in the script itself.

## Leakage verification (six corpora, three methods)

### Method 1 — exact-text duplicate check

Direct set-intersection on lowercased, stripped text against:

| Corpus | Reference size | Exact-text overlap |
|---|---|---|
| STBV-Bench v1 (rendered, 15,000 rows — covers the eval region and mixed-corpus training pool) | 15,000 | **0** |
| STBV-Bench v2 (windowed, substring-checked against full serialized windows) | full file | **0** |
| STBV-Bench v2.5 (all `*split*.jsonl` files) | 20,749 | **0** |
| Mixed-corpus training pool (`mixed_train_split.jsonl` + `mixed_val_split.jsonl` — the exact data this checkpoint trained on) | 18,938 | **0** |
| External semantic corpus | 117 | **0** |
| Hard-OOD benchmark (both original and audit-revised versions) | 288 + 288 | **0 + 0** |

### Method 2 — template/scenario overlap check

No STBV-Bench template ID, v2.5 template ID, or external-corpus source
sentence skeleton was ever supplied to the generator (only one-line
concept descriptions plus freshly-assigned scenario context) — by
construction, not merely by post-hoc check. The 53 city/road scenario
pairs used were selected from lists containing no city or road name that
appears in STBV-Bench's VeReMi-derived kinematic records, the external
corpus, or hard-OOD's content.

### Method 3 — semantic-similarity check (embedding cosine similarity)

Reused this project's established methodology
(`b3_eval/v25_finetune/audit_leakage.py`'s `part1_3_semantic_leakage`):
`all-MiniLM-L6-v2` sentence embeddings, cosine similarity, thresholds
0.95/0.90/0.85 (identical thresholds to every prior semantic-leakage check
in this project). Reference pool: 800-message random samples from
STBV-Bench v1 (rendered) and v2.5 (all splits) and the mixed-corpus
training pool, plus the full external corpus (117) and full audit-revised
hard-OOD corpus (288) — 2,805 reference texts total.

**Result: 0 of 216 independent-corpus messages exceed similarity 0.85
against any reference text (let alone 0.90 or 0.95).** The single highest
nearest-neighbor similarity found across the entire corpus is 0.697 (a
v2.5 message sharing only generic V2X-report vocabulary, not content) —
well below every threshold used anywhere in this project.

## Family coverage and composition

12 malicious attack families (all 12 of STBV-Bench's core taxonomy used
elsewhere in this paper) + 6 benign concepts, 12 messages each, perfectly
balanced. Mean length 34.4 words / 231 characters (well within B3's
256-token inference limit — max message is 64 words/405 characters,
verified not to risk truncation).

## Reproducibility

`python indep_bench/build_independent_corpus.py`, seed 20260810. LLM
sampling itself is not temperature-seeded by Ollama's default API (same
disclosed limitation as every other LLM-generated corpus in this project),
so exact text is not byte-reproducible on a rerun, but the construction
procedure, concept list, scenario-seed lists, and evaluation methodology
are fully deterministic and documented.
