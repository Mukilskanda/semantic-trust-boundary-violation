# HARD_OOD_DATASET.md

## Addendum — audit-driven revision (scope-correction phase)

A full per-message scope audit (`HARD_OOD_BENCHMARK_AUDIT.md`) classified
the 72 `cb_informal` (CB-radio-slang) messages as genuinely out-of-scope
for this paper's stated ETSI CAM/DENM deployment model (human voice-radio
idiom has no plausible path into a machine-generated free-text field).
Those 72 messages were replaced with 72 freshly-generated, fully
grammatical, ETSI-plausible "formal_report_v2" messages (same 18 concepts,
same 4-per-concept count, same generation mechanism, zero leakage
re-verified against all five relevant corpora). **This did not improve the
result: F1 fell from 0.446 to 0.345** — the removed stratum was, honestly,
the *easiest* one in the original corpus (F1=0.633), so scope-correcting
the benchmark made the reported gap larger, not smaller. Full changelog
below; revised results in `HARD_OOD_RESULTS.md`.

### Replacement changelog (Task 2)

- **Removed:** 72 messages, `sample_id`s `hoo-0005`–`hoo-0008`,
  `hoo-0021`–`hoo-0024`, ... (all messages tagged `"style": "cb_informal"`
  in `hard_ood_bench/hard_ood_corpus.jsonl`) — CB-radio voice-slang
  register, judged out-of-scope per `HARD_OOD_BENCHMARK_AUDIT.md`.
- **Added:** 72 messages, `sample_id`s `hoor-0001`–`hoor-0072`
  (`hard_ood_bench/hard_ood_replacement_batch.jsonl`), style
  `formal_report_v2` — same 18 concepts (12 malicious + 6 benign, 4
  messages each), generated fresh from the same one-line concept
  descriptions (never paraphrasing any existing sentence, including the
  messages being replaced), in a fully grammatical, professional,
  third-person V2X-report register with sentence-structure variation
  explicitly requested across the 4 messages per concept. Same seeded
  (20260808) 35%-subsample structural-noise pass as the original corpus
  construction (GPS/timestamp jitter, abbreviation substitution,
  dropped-field marker, single-character typo).
- **Kept unchanged:** all 216 other messages (`plain_nonnative`,
  `terse_telemetry` — in-scope; `radio_abbrev` — borderline, retained per
  the audit's explicit instruction not to replace borderline samples).
- **Leakage re-check on the 72 new messages:** 0 exact-text overlap against
  the original hard-OOD corpus (including the 72 being replaced), STBV-Bench
  v1 (15,000 rendered rows), all STBV-Bench v2.5 splits (20,749 texts),
  the external corpus (117 entries), and the exact mixed-corpus training
  pool (18,938 texts) — same rigor, same corpora, as the original corpus's
  leakage audit.
- **Revised corpus file:** `hard_ood_bench/hard_ood_corpus_v2.jsonl`
  (288 messages: 216 original + 72 replacement). The original
  `hard_ood_corpus.jsonl` is retained on disk, unmodified, for audit
  traceability.

## Task 1 — Classification of existing benchmarks

| Benchmark | Class | Why |
|---|---|---|
| STBV-Bench v1, full stack ($n=10{,}000$) | **A + D** | Standard/necessary as the paper's canonical, statistically powered benchmark, but (per `ROOT_CAUSE_REPORT.md`) the final checkpoint's training data includes a disjoint slice from the *same generator*, so a near-ceiling result here is real but in-distribution to a narrow template engine — the single most vulnerable result in the paper to a "too easy / too close to training distribution" objection, already disclosed as such throughout the manuscript. |
| STBV-Bench v1, B3-alone | **D** | Same root cause as above, diagnostic/supplementary rather than a second independent claim. |
| STBV-Bench v2 (windowed) | **A** | Standard/necessary — the only regime with genuine ambient bystander traffic; not near-ceiling (F1=0.521), so it is not vulnerable to the same critique, but it draws on the same generator's phrasing, so it does not answer the "too easy" objection either. |
| External semantic corpus | **A**, closest existing answer to "too easy" | Standard/necessary and *already* the paper's best defense against the training-distribution critique — independently authored, five disjoint sources, F1=0.920 (the weakest result in the paper). But it is still LLM-authored *for this evaluation* by the same small set of providers/prompts, at $n=117$, so per-family statistical power is thin and its own stylistic diversity (formal, coherent, grammatical) does not stress-test informal/abbreviated/noisy real-world V2X phrasing at all. |
| Mixed-threat case study | **B** | Useful — demonstrates the recall/FPR trade under realistic ambient kinematics — but is not itself a semantic-generalization benchmark; B3's text inputs there are still STBV-Bench-generator text. |
| Adaptive-attack | **A** | Standard/necessary and genuinely OOD *relative to the training distribution's specific sentences* (iterative mutation search), but it starts from external-corpus seeds and mutates them with 9 fixed rule-based strategies — it stress-tests robustness to adversarial perturbation of already-known-detectable text, not linguistic/stylistic generalization to genuinely novel phrasing. |
| CP full evaluation | **B** | Useful, narrow, architecturally motivated (isolates CP's own contribution); not a semantic-generalization claim at all. |
| Deployment (SUMO/CARLA) | **A** | Standard/necessary for a systems contribution; not a semantic-generalization claim. |

**Conclusion driving Task 2:** the external corpus is the paper's best existing answer to "is this too easy," but it is small, stylistically narrow (coherent LLM prose, not abbreviated/noisy/colloquial real-world radio traffic), and does not include hard-negative benign messages that lexically resemble the malicious classes (e.g., genuine emergency-vehicle announcements vs. false authority claims). A new, harder, deliberately stylistically-diverse OOD benchmark closes exactly this gap.

## Task 2/3 — Hard-OOD benchmark design and construction

**Design principle.** Keep the same 12 attack *concepts* as STBV-Bench (for
family-level comparability) but generate text that is: (a) never
LLM-paraphrased *from* any existing STBV-Bench/external-corpus sentence —
generated fresh from a one-line concept description instead; (b) spread
across four genuinely different linguistic registers never used in any
existing corpus (heavily-abbreviated radio-dispatch shorthand, informal
CB-radio trucker slang, plain non-native-English phrasing, terse
telemetry-log style); (c) includes six benign concept categories, three of
which are explicit **hard negatives** — truthful messages that lexically
resemble a malicious concept (a real police checkpoint, a real emergency
vehicle, a real resolved hazard) specifically to test whether the model
distinguishes truthful content from manipulative framing, not just
keyword presence; (d) a deterministic post-processing pass (seeded,
`random.Random(20260807)`) applies realistic communication noise —
GPS/timestamp jitter annotations, abbreviation substitution, a
programmatically-dropped-field marker, and single-character typos — to a
seeded ~35% subsample.

**Generation mechanism.** Local LLM (Mistral 7B via Ollama, already used
elsewhere in this project for the zero-shot-LLM baseline), 72
(concept × style) batched prompts, 4 messages requested per prompt. No
sampling from, editing of, or paraphrasing of any existing corpus sentence
— every prompt supplies only a one-line abstract concept description, never
a seed sentence. Script: `hard_ood_bench/build_hard_ood_corpus.py`, fully
reproducible (fixed model, fixed prompts, fixed seed for the noise pass;
LLM sampling itself is not temperature-seeded by Ollama's default API, so
exact text is not byte-reproducible on a rerun — disclosed, consistent with
this project's existing disclosure for its other LLM-generated corpus
components).

## Corpus statistics

- **Size:** 288 messages (192 malicious / 96 benign, 2:1 ratio) — 18
  concept families × 16 messages each (4 styles × 4 messages).
- **Family distribution:** exactly 16 per family (12 malicious + 6 benign
  concepts), by construction — perfectly balanced per family, unlike
  STBV-Bench's naturally-imbalanced family counts.
- **Length distribution:** message length ranges from very short (3–5
  words, terse-telemetry style, e.g. "Battery level: 85%") to full sentences
  (20–35 words, CB-radio narrative style) — genuinely bimodal/wide, unlike
  STBV-Bench's comparatively uniform template-driven sentence length.
- **Mutation coverage:** 92/288 (32%) messages carry a structural-noise
  mutation (GPS/timestamp jitter annotation, abbreviation substitution,
  dropped-field marker, or single-character typo).

## OOD analysis

- **Template overlap with STBV-Bench v1/v2/v2.5, the external corpus, and
  the mixed-corpus training pool: 0 exact-text matches**, verified directly
  (not assumed) by rendering the relevant portions of every corpus to plain
  text and computing set intersections — see the leakage-check section
  below for exact counts per corpus.
- **Stylistic OOD:** none of the four styles used here (heavy-abbreviation
  radio shorthand, CB-radio slang, plain non-native English, terse
  telemetry log lines) appears anywhere in STBV-Bench's rule-based template
  bank or the external corpus's five sources (which are uniformly
  grammatical, third-person-report-style prose).
- **Lexical diversity:** informal spot-check confirms far more varied
  sentence openers, punctuation conventions (all-caps abbreviation strings,
  CB-radio "ten-four"/"breaker one-nine" idiom, dropped articles typical of
  non-native phrasing) than any existing corpus in this project.

## Leakage check (Task 3 requirement, all existing splits/corpora)

| Corpus checked | Rows/entries compared against | Exact-text overlap |
|---|---|---|
| STBV-Bench v1 (rendered, first 15,000 rows — covers both the eval region and the full mixed-corpus v1 training pool) | 15,000 rendered texts | **0** |
| STBV-Bench v2.5 (all `*split*.jsonl` files: train/val/test) | 20,749 texts | **0** |
| STBV-Bench v2 (windowed) | full windows file, substring-checked | **0** |
| External semantic corpus | 117 entries | **0** |
| Mixed-corpus training pool (`mixed_train_split.jsonl` + `mixed_val_split.jsonl`, the exact data the final checkpoint trained on) | 18,938 texts | **0** |

All five checks run directly against raw files in this session (script
logic embedded in this document's construction process, reproducible via
the commands recorded in `hard_ood_bench/build_hard_ood_corpus.py`'s
companion verification — the exact leakage-check code is preserved in
`HARD_OOD_RESULTS.md`'s methodology section for full reproducibility).

## Difficulty justification

This corpus is designed to be hard along three independent axes
simultaneously: (1) stylistic distance from every corpus used anywhere in
this project, including training data; (2) explicit hard-negative benign
messages that share surface vocabulary with malicious concepts (police,
emergency, priority, clearance) while being truthful; (3) realistic
communication noise applied post-hoc. None of these axes were chosen to
manufacture a specific pass/fail outcome — the corpus was built once,
evaluated once, and the results (Task 4/5, below and in
`HARD_OOD_RESULTS.md`) were not used to iterate on the corpus design.
