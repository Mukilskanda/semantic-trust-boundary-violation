# B3 Semantic Gate — Data Provenance Forensic Report

Prepared in response to a direct reproducibility requirement: the paper
cannot be submitted until B3's training-data provenance is completely
documented. This report is a read-only forensic investigation — **no code
was modified to produce it.** Every claim below is cited to a specific
file, git object, or command output. Where a fact cannot be recovered,
that is stated explicitly, with the search performed to establish its
absence.

**Scope note on method:** this report investigates what is *recoverable
from this repository* (working tree, full git history across all refs,
LFS objects, checkpoint-embedded metadata, and every markdown document).
It cannot investigate systems outside this repository (the original
author's local machine, any external storage, or any process that ran
before the first commit). Where the evidence points to material existing
only outside the repository, that is stated as such, not glossed over.

---

## Executive summary

B3 (`semantic_gate_v3`, a 6-layer DeBERTa-v2 sequence classifier) is a
**materialized, runnable, real checkpoint** in this repository — this is
not in question. What **cannot** be recovered from this repository, after
an exhaustive search of the working tree, the complete git history on all
refs, and every LFS object, is **the raw dataset the checkpoint was
fine-tuned on**. The training script itself has never existed in this
repository's git history. The only training-time evidence that survives
is what the checkpoint's own serialized `training_args.bin` records
(hyperparameters, not data), plus indirect traces in downstream analysis
scripts that reference a training/test split whose files are themselves
absent.

This is not a case of "the data was deleted" — the evidence (an
absolute path baked into `training_args.bin`, and a relative-path comment
in `verify_cases_1_4.py`) indicates the training run happened in a
**different project directory on a different machine**
(`/home/harshitvaish123/v2x-pi-project/...`), and only the finished
checkpoint, tokenizer, and a handful of downstream analysis/inference
scripts were ever copied into this repository. The raw dataset was never
part of this repository at any commit.

**Confidence level: HIGH that the raw training corpus is unrecoverable
from this repository. HIGH that no direct train/eval file-level overlap
exists (because no benchmark in this repo touches the training files —
they aren't here). MEDIUM-LOW confidence that indirect/distributional
leakage can be fully ruled out**, because a *related, deprecated* corpus
in this same repository explicitly declares its text was written to match
B3's training-family taxonomy — direct, self-documented evidence of a
leakage *mechanism*, even though it affects a different (already
superseded) evaluation than the paper's canonical benchmark.

---

## 1. What dataset was B3 trained on?

**Answer: unknown — not recoverable from this repository.**

No training script, no raw corpus file, and no training-time data
manifest for B3 exists anywhere in this repository, in the current working
tree or in any commit across the full git history. The strongest direct
evidence of what the training data *looked like* is indirect:

- `b3/solution_stb/b3_semantic_gate/error_analysis.py` (lines 1–24)
  references `outputs/splits/test1_stbv_unseen_families.json` — a labeled
  test split with columns `text`, `label`, `attack_family`, `persona`,
  `template_idx` — implying the training data used the same schema
  (text + binary label + attack-family + persona + template index). This
  file **does not exist** anywhere in this repository (confirmed by
  `Glob`/`find` across the full working tree).
- `training_args.bin` (embedded in the checkpoint directory, see §7)
  records `output_dir` and `logging_dir` as
  `/home/harshitvaish123/v2x-pi-project/solution_stb/b3_semantic_gate/outputs/checkpoints_Proposed_A+B+C`
  and `.../logs_Proposed_A+B+C` — confirming the training run happened
  inside a project named **`v2x-pi-project`**, under a **different user's
  home directory on a different machine**, not this repository.
- `b3/solution_stb/b3_semantic_gate/verify_cases_1_4.py` (lines 1–20)
  states explicitly in its own docstring: *"Run from:
  `~/v2x-pi-project/solution_stb/b3_semantic_gate/`... paths below assume
  case folders are two levels up, per your project layout"* and reads
  `../../case1_perc/case1_results.json` — confirming this repository is a
  **partial extract** of a larger original project (`v2x-pi-project`)
  that contained the training data, the case-study folders, and
  presumably the training script, none of which were carried into this
  repository.
- The checkpoint's label scheme (`config.json`: `0=BENIGN`,
  `1=MALICIOUS_SEMANTIC_MANIPULATION`) and the family names referenced in
  `error_analysis.py`'s rationale comments and the deprecated
  `semantic_evaluation/semantic_attack_dataset.py` corpus (`AF1`–`AF9`,
  `Case 1`–`Case 5`) are the only surviving description of what the
  training taxonomy covered. These are **labels/category names copied
  into downstream scripts**, not the training data itself.

**Conclusion:** the dataset's existence is well-attested indirectly (label
scheme, family taxonomy, split-file naming convention, expected columns),
but the actual text-label pairs used to fine-tune the checkpoint are not
present in this repository and cannot be reconstructed from what is
present.

---

## 2. Does the dataset still exist in the repository?

**No.** Confirmed by:

- `find`/`Glob` for `outputs/splits/*`, `*train*.json`, `*test1*` anywhere
  under `b3/` — zero hits.
- Full git history search (`git log --all --pretty=format: --name-only`,
  every ref, every commit) for any file matching
  `train.*\.py$|finetune|fine_tune|dataset_gen|corpus.*\.py$` — **zero
  hits outside `.venv` (third-party packages).** No training script has
  ever been committed to this repository, at any point in its history.
- `git log --diff-filter=D` (files ever deleted) for training/dataset-
  named files — zero hits. The dataset was not deleted from this repo;
  it was **never added** to this repo.

The only B3-related file objects that exist in git history are the
tokenizer files, the checkpoint (`pytorch_model.bin`, via Git LFS —
verified materialized, not a pointer stub: 567,622,450 bytes, SHA-256
`9ee7475e...c2f5d2`, matching `README.md`'s documented expected hash), and
the three downstream analysis scripts (`error_analysis.py`,
`verify_cases_1_4.py`, `new_qualitative_test.py`) — all of which assume
the split files exist at run time and fail with a clear `FileNotFoundError`
when they don't (`error_analysis.py`'s own `__main__` block catches this
case explicitly).

**A separate, structurally unrelated dataset does exist:
`data/v1/{train,val,test}.json`.** This was checked carefully because it
initially looked like a candidate. It is **not** B3's training data:

| Property | `data/v1/train.json` | B3's actual input |
|---|---|---|
| Input schema | Structured numeric fields (`b2.trust`, `cam.speed`, `cam.heading`, `path_history[]`, …) | Raw natural-language V2X message text |
| Output labels | 3-class `{ACCEPT, CAUTION, REJECT}` + free-text `reason` | 2-class `{BENIGN, MALICIOUS_SEMANTIC_MANIPULATION}` |
| Sample count | 100 total (80/10/10 split, `dataset_metadata.json`) | Unknown, but the family-level per-class F1 numbers referenced in `error_analysis.py` imply a materially larger corpus |
| Committed | Initial commit `79018fe83`, present since the repository's first commit | Never present |

This dataset's free-text `reason` fields do use some of the same case
labels seen elsewhere (`CGOF` — Coordinated Ghost Object Fabrication — is
one example), suggesting it belongs to the same broader threat-taxonomy
effort as B3's training corpus, but its input schema (structured
CAM/B2 numeric features, not raw message text) is incompatible with a
text sequence classifier — B3 cannot have been trained on this file. It
is most plausibly training data for a **different, LLM-based reasoning/
decision component**, not the DeBERTa text classifier. This distinction
is stated explicitly because conflating the two would misrepresent
provenance rather than clarify it.

---

## 3. Was it generated using the same STBV-Bench generator?

**No — and this can be stated with fairly high confidence, for two
independent reasons:**

1. **Chronology.** `training_args.bin`'s embedded `output_dir` places the
   training run under a directory literally named
   `checkpoints_Proposed_A+B+C`, inside the separate `v2x-pi-project`
   directory tree — a naming convention (`Proposed A+B+C`) that predates
   and is unrelated to this repository's `stbv_bench/` module, which
   (per its own commit history) was built later, specifically as an
   independent evaluation corpus (`stbv_bench/build_stbv_bench.py`,
   `stbv_bench/transformations.py`).
2. **Taxonomy mismatch.** `stbv_bench/transformations.py` defines its
   attack families with descriptive string names —
   `authority_override`, `instruction_injection`, `goal_manipulation`,
   `priority_manipulation`, `context_inversion`, `context_poisoning`,
   `traffic_efficiency_lure`, `false_clearance`, `hazard_suppression`,
   `hazard_amplification`, `role_manipulation`,
   `indirect_prompt_injection`, `semantic_narrative_poisoning`,
   `planner_manipulation`, `cross_source_contradiction`,
   `multi_message_context_poisoning`,
   `collaborative_semantic_agreement`,
   `infrastructure_semantic_manipulation`, `temporal_context_drift`,
   `mixed_semantic_attacks`, `benign_control` — **none of which are named
   `AF1`–`AF9`** or `Case 1`–`Case 5`, the taxonomy that downstream B3
   analysis scripts (§1) and the deprecated 120-scenario corpus use to
   describe B3's *training* families.

This taxonomy mismatch is the same finding an earlier verification round
in this project reached independently (documented in
`DISCUSSION_AND_LIMITATIONS.md`, L12): STBV-Bench's generator and B3's
training corpus were built by **different, apparently independent
processes with no shared naming taxonomy** — which is evidence *against*
STBV-Bench v1 being the same generator, but is not, by itself, proof of
zero textual/stylistic similarity (see §13 for the residual risk this
leaves open).

---

## 4. Total training samples

**Unknown — not recoverable.** `training_args.bin` (a `TrainingArguments`
object) does not serialize dataset size; the HF `Trainer` reads sample
counts from the dataset object at run time, and that number is not
persisted anywhere the checkpoint or its metadata carries forward. No
training log file, no `trainer_state.json`, and no dataset manifest for
B3 exists in this repository.

The only indirect signal is qualitative: `error_analysis.py` references
"the 68 missed AF7/AF8 malicious samples from Test-1" out of what its own
computed percentages imply is a Test-1 malicious-class count in roughly
the several-hundred range (68 missed at a reported miss rate would put
total malicious Test-1 samples in the low hundreds, though the exact
percentage was never captured in any surviving document, so this is
an order-of-magnitude inference, not a citation-backed number). This is
explicitly flagged as an inference, not a fact, and should not be quoted
as a training-set size in the paper.

## 5. Validation samples

**Unknown — not recoverable.** Same reasoning as §4. `training_args.bin`
confirms `eval_strategy=EPOCH` (the model was evaluated every epoch
during training against *some* validation set), but the validation set's
size, composition, and file location are not recorded anywhere reachable
from the checkpoint or this repository.

## 6. Test samples

**Unknown in exact count — partially attested by name only.**
`error_analysis.py` references a file named
`test1_stbv_unseen_families.json` implying a **named, deliberately
constructed "Test-1" split with an unseen-attack-family design** (i.e.,
attack families held out of training and only appearing at test time —
a leave-one-family-out-style methodology). This is a meaningful positive
finding: **the split methodology, by name, appears to have been designed
against exactly the leakage concern this report investigates** — but the
file itself is absent, so this cannot be verified directly, only inferred
from the filename and the surrounding script's usage pattern.

---

## 7. Split methodology

**Partially recoverable, from naming conventions only.**

- The file name `test1_stbv_unseen_families.json` (note: this filename
  itself contains "stbv," which is this project's own naming convention —
  suggesting this split file was generated or renamed as part of *this*
  project's work, not simply inherited unchanged from `v2x-pi-project`;
  this is a subtle but real point in favor of the split having been
  constructed with STBV-style unseen-family evaluation in mind).
- `training_args.bin` confirms `eval_strategy=IntervalStrategy.EPOCH` and
  `save_strategy=SaveStrategy.EPOCH` with `load_best_model_at_end=True`,
  `metric_for_best_model="f1"` — standard epoch-wise validation-driven
  checkpoint selection, implying a conventional train/validation split
  used during training, separate from the "Test-1 unseen families" split
  used for held-out evaluation after training.
- No stratification method, no random-split fraction, and no
  documentation of how "unseen families" were selected (which families
  were held out, how many, whether by attack family, persona, or
  something else) is recoverable. `error_analysis.py`'s own groupby
  operations (`missed.groupby("attack_family")`,
  `.groupby("persona")`, `.groupby("template_idx")`) confirm the split
  file carries these columns, which is the strongest evidence for what
  dimensions the split was stratified or held out along, but not the
  actual split logic.

## 8. Random seed

**Training seed: known and verified. Dataset-construction seed: unknown.**

`training_args.bin`, loaded directly with `torch.load(...,
weights_only=False)` in this investigation, records:
```
seed = 42
data_seed = None
```
`seed=42` controls model initialization and the Trainer's data-loader
shuffling *given* a dataset object; it does **not** tell us what seed (if
any) was used to *generate* or *sample* the raw dataset itself before it
reached the Trainer, since `data_seed` (a separate HF Trainer field for
that purpose) is `None`/unset. If the dataset was itself synthetically
generated (as its family/persona/template-index columns suggest), the
generation-time seed is unrecorded and unrecoverable.

## 9. Whether train/validation/test overlap exists

**Cannot be directly tested — the files needed for the test don't exist.**
No raw train, validation, or test file is present in this repository, so
no direct hash/text-overlap check between them is possible. This is
stated as an evidentiary gap, not resolved by inference.

What **can** be said: the file-naming convention (`test1_stbv_unseen_
families.json`, containing `template_idx` and `persona` columns
explicitly used to check "unseen families") indicates the original team
was aware of and actively designing against overlap/leakage between
training and this particular test split — a positive procedural signal —
but a named intention is not the same as a verified absence of overlap,
and this report does not have the files needed to verify it directly.

## 10. Whether attack template families overlap between training and evaluation

**Cannot be directly tested for B3's own train/test split** (files
absent, per §9). **Can be tested, and is a confirmed "no," for B3's
training taxonomy vs. this paper's canonical STBV-Bench v1 benchmark** —
see §3: STBV-Bench v1's 20 family names share zero string overlap with
the `AF1`–`AF9`/`Case 1`–`Case 5` taxonomy associated with B3's training
data and the deprecated evaluation corpus.

## 11. Whether only instances differ while templates remain identical

**This is the specific, already-identified leakage mechanism for the
deprecated 120-scenario corpus — confirmed directly from that corpus's
own source code, not inferred.**
`semantic_evaluation/semantic_attack_dataset.py`'s module docstring
(lines 10–13) states outright:

> *"The payload texts are aligned to the phrasing styles of the model's
> actual training distribution (AF1-AF9 families, Case 1 - Case 4, and 30
> new qualitative test messages), ensuring high-fidelity evaluation."*

This is a **direct, first-party admission that this corpus's authors
deliberately wrote evaluation text to match B3's training phrasing
style**, not independently authored text later found to overlap by
chance. Every one of that file's 120 `SemanticAttackScenario` entries
carries a `rationale` field explicitly naming which `AF#` template it
corresponds to (e.g., `"AF6 statistical denial template using math
jargon to discredit sensors"`, `"AF7 short CPM template: fakes hazard
detection to slow traffic"` — verified by direct grep across all 120
entries, §12 evidence table below). This means, for this **specific,
already-deprecated** corpus: **templates are shared by design; only
surface instances (personas, coordinates, specific numbers) differ.**

This does **not** extend to STBV-Bench v1 (the paper's canonical
benchmark), whose generator (§3) uses an independently-named, disjoint
taxonomy with no `AF#`/`Case #` references anywhere in
`stbv_bench/transformations.py` (verified by grep — zero matches).

## 12. Whether any data leakage exists

**Yes, a confirmed leakage risk exists — but scoped to a specific,
already-deprecated corpus, not the paper's canonical benchmark.**

| Corpus | Leakage status | Evidence |
|---|---|---|
| `semantic_evaluation/semantic_attack_dataset.py` (120 hand-authored scenarios) | **Confirmed leakage risk.** Text explicitly authored to match B3's training-family phrasing (§11). Already flagged in this project's own documentation (`PUBLICATION_PROGRESS.md`'s 0.859/0.990/98.8%-figure caveats; `HANDOFF_SUMMARY.md` §4) as superseded — **not used as the paper's headline detection-accuracy result.** | Module docstring, per-scenario `rationale` fields (120/120 checked) |
| STBV-Bench v1 (canonical, $n=10{,}000$) | **No template-taxonomy overlap found.** Independently-named family taxonomy (§3), built from real VeReMi kinematics + this project's own seeded transformation engine, with no reference anywhere to B3's `AF#`/`Case #` scheme. | `stbv_bench/transformations.py` (zero `AF`/`Case` matches, grep-verified) |
| STBV-Bench v2, VeReMi kinematic companion bench, mixed-threat bench | Same generator lineage as v1 (`stbv_bench/build_stbv_bench_v2.py`, `build_and_run_veremi_kinematic_bench.py`, `build_mixed_threat_bench.py`) — same "no taxonomy overlap" finding applies. | Same generator source files |
| `data/v1/{train,val,test}.json` | **Not applicable to B3** — different input schema (§2), cannot have leaked into or out of a text classifier's training. | Direct schema inspection |

**Direct train/test file overlap for B3 itself (§9) cannot be checked**
because neither file exists in this repository. This is the report's
single largest open item, stated plainly: the absence of overlap between
B3's *own* original train and test files is asserted by the training
team's naming convention (`unseen_families`), not independently verified
by this investigation, because the files to verify it are not present.

## 13. Whether indirect leakage exists through shared generation logic

**Partially — one confirmed indirect mechanism, scoped narrowly.**

- The confirmed mechanism (§11) is a form of indirect leakage: not file-
  level duplication, but **deliberate stylistic/distributional alignment**
  between a downstream evaluation corpus and B3's training distribution.
  This is real, documented, and already accounted for in this project's
  publication decisions (the corpus is not used for the headline
  detection-accuracy claim).
- For STBV-Bench v1/v2 and the kinematic/mixed-threat benches: there is
  **no shared code path** between the module that built B3's training
  data (unknown — likely inside `v2x-pi-project`, not present here) and
  `stbv_bench/`'s generator, which was written independently, in this
  repository, using VeReMi Extension kinematics and its own transformation
  rule set. No shared generator function, shared template file, or shared
  constant/taxonomy list exists between the two (verified by the same
  grep sweep as §3/§11 — the two codebases do not import from each
  other and share no string literals in the family/template names).
- **What cannot be ruled out**, because the training corpus itself is
  absent: whether the *style* of V2X CAM/DENM message formatting (field
  names like `StationID`, `CauseCode`, `RelevanceDistance`) that both
  B3's original training messages (as reflected in `error_analysis.py`'s
  handcrafted qualitative examples, which mimic this format) and
  STBV-Bench's synthesizer (`pipeline/synthesizer.py`) both use is a
  **generic V2X/ETSI message-format convention** (highly plausible — these
  are standard CAM/DENM field names defined by the ETSI/SAE standards
  documents both projects would plausibly follow) or a **specific
  convention copied from one project to the other**. This cannot be
  resolved from the repository alone; it requires knowing the actual
  training text, which is absent.

## 14. Whether evaluation text resembles training text

- **For the deprecated 120-scenario corpus: yes, by explicit design**
  (§11 — this is not a resemblance found by analysis, it is a stated
  authorial intent).
- **For STBV-Bench v1/v2 (the paper's canonical benchmarks): cannot be
  directly measured**, because there is no surviving copy of B3's actual
  training text to compare against. The only evidence bearing on this
  question is negative/indirect: the taxonomy names don't overlap (§3),
  and the two generators are code-independent (§13). Absence of taxonomy
  overlap is evidence of low resemblance, not proof of it — natural-
  language V2X messages describing similar underlying attack concepts
  (e.g., "infrastructure claims sensor is wrong") could independently
  converge on similar phrasing even from unrelated generators, simply
  because the threat concept itself constrains the plausible phrasing
  space. This report does not claim to rule that out.

## 15. Whether leakage can be ruled out

**Cannot be ruled out with certainty for STBV-Bench v1/v2 — but the
identified risk is bounded and indirect, not the direct template-sharing
mechanism confirmed for the deprecated corpus.** Stated precisely:

- **Ruled out:** direct file-level overlap between B3's original
  training/test files and STBV-Bench v1/v2/kinematic/mixed-threat corpora
  — because STBV-Bench's benchmarks are built from real VeReMi kinematics
  synthesized through this repository's own pipeline, and B3's original
  training files are not present in, and were never part of, this
  repository (there is no file to overlap with).
- **Ruled out:** shared-taxonomy/template-ID leakage between B3's
  training families and STBV-Bench's families (§3, §11) — confirmed by
  direct comparison of the two family-naming schemes.
- **NOT ruled out:** convergent phrasing at the level of generic V2X
  message-format conventions or generic attack-concept phrasing (§13,
  §14) — because this would require comparing against B3's actual
  training text, which does not exist in this repository to compare
  against.
- **NOT ruled out, and separately already documented as a limitation
  in this project** (`DISCUSSION_AND_LIMITATIONS.md`, L12): STBV-Bench
  itself is an internally-generated benchmark with no external ground
  truth to validate against — a related but distinct concern from
  training/eval leakage specifically.

---

## Training pipeline (what is and is not known)

| Element | Status | Evidence |
|---|---|---|
| Architecture | **Fully known** | `config.json`: `DebertaV2ForSequenceClassification`, 6 layers, hidden 768, 12 heads, intermediate 3072, vocab 128,100, `pos_att_type=[p2c,c2p]`, `relative_attention=true` |
| Parameter count | **Fully known** | 141,896,450 (`b3_eval/results/model_benchmark.json`, `INCUMBENT`) |
| Tokenizer | **Fully known, real files present** | `spm.model` (SentencePiece), `tokenizer.json`, `tokenizer_config.json`, `added_tokens.json`, `special_tokens_map.json` |
| Checkpoint weights | **Present, materialized, hash-verified** | `pytorch_model.bin`, 567,622,450 bytes, SHA-256 `9ee7475e08f76ce6961c55204657a380d5ef1c2c9dac6a9d46543a7c42c2f5d2` (verified this investigation via direct hash, matches `README.md`) |
| Training hyperparameters | **Fully known, read from checkpoint metadata** | `training_args.bin`: lr=2e-5, epochs=15, batch=16/16, AdamW, linear schedule, warmup ratio 0.1, weight decay 0.01, fp16, seed=42, `metric_for_best_model=f1`, `load_best_model_at_end=True` |
| Training script | **Absent — never in this repo's git history** | `git log --all` full-history search, zero hits |
| Raw training/val/test data | **Absent — never in this repo** | Working-tree search + full git history search, zero hits; `training_args.bin`'s embedded paths point to a different machine/project (`/home/harshitvaish123/v2x-pi-project/...`) |
| Dataset size (train/val/test counts) | **Unknown** | Not serialized in `training_args.bin`; no manifest exists |
| Data-generation seed | **Unknown** (distinct from `training_args.bin`'s model-init seed 42) | `data_seed=None` in `training_args.bin` |
| Split methodology | **Named convention known (unseen-family Test-1), mechanics unknown** | Filename + `error_analysis.py`'s usage pattern only |

---

## Data lineage (reconstructed)

```
[Original project: v2x-pi-project, on a machine under /home/harshitvaish123/]
        |
        |  (raw dataset + training script: NEVER copied into this repo)
        v
[fine-tuning run: DeBERTa-v2, 15 epochs, lr=2e-5, seed=42]
        |
        v
[checkpoint: semantic_gate_v3 (pytorch_model.bin + tokenizer files)]
        |
        |  (copied into this repository, via Git LFS, at initial commit)
        v
[THIS REPOSITORY: b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/]
        |
        +--> inference.py, b3_bridge.py (production inference path — verified working)
        |
        +--> error_analysis.py, verify_cases_1_4.py, new_qualitative_test.py
        |      (downstream analysis scripts, ALSO copied from v2x-pi-project,
        |       but reference split files and case folders that were NOT copied
        |       — these scripts cannot currently run to completion)
        |
        +--> [SEPARATE LINEAGE, built later, in this repo]
             semantic_evaluation/semantic_attack_dataset.py
               (120 hand-authored scenarios, explicitly styled to match
                B3's training distribution per its own docstring —
                confirmed leakage risk, already deprecated as a headline
                metric in this project's own documentation)
        |
        +--> [FULLY INDEPENDENT LINEAGE, built in this repo, no shared code/taxonomy]
             stbv_bench/ (STBV-Bench v1/v2, VeReMi kinematic bench, mixed-threat bench)
               — real VeReMi Extension kinematics + this repo's own seeded
                 transformation engine — THE PAPER'S CANONICAL BENCHMARK
```

---

## Dataset statistics

No dataset statistics for B3's original training/validation/test data can
be reported, because the data does not exist in this repository (see
§4–§6). The only dataset statistics available for anything touching B3
are for the **regenerated, explicitly-not-original** benchmark split used
by `b3_eval/run_model_benchmark.py`:

- Source: `b3_eval/data/split_manifest.json`, generated by
  `export_semantic_split.py` from this repository's own
  `semantic_evaluation.semantic_attack_generator.generate_corpus` +
  `pipeline.orchestrator.ISCEPipeline` (i.e., this is NOT the deprecated
  120-scenario corpus at §11/§12 either — it is a third, separate,
  freshly-generated split, built specifically to give the model-swap
  comparison a controlled, apples-to-apples split).
- Seed: 20260713. Test fraction: 0.2. Class-balanced (majority
  downsampled).
- Train: $n=96$ (84 malicious / 12 benign after balancing). Test:
  $n=24$ (21 malicious / 3 benign after balancing).
- `train_sha256_16=49d10e58a4c8597b`, `test_sha256_16=ed9a73505c4d12bc`.
- The manifest's own `paper_caveats` field states, verbatim: *"Newly
  generated split; NOT B3's training data,"* and *"Report B3 on this
  split WITH the caveat that overlap with its unavailable original
  training corpus cannot be excluded (B3 may have seen similar text)."*
  This self-documented caveat is the project's own prior acknowledgment
  of exactly the uncertainty this forensic report also concludes in §15.

---

## Confidence levels (summary table)

| Question | Confidence | Verdict |
|---|---|---|
| 1. What dataset was B3 trained on | High confidence in what's *not* recoverable | Unknown; only indirect schema/taxonomy evidence survives |
| 2. Does it still exist in the repo | High | No — confirmed absent, full history search |
| 3. Same STBV-Bench generator | High | No — taxonomy and chronology both rule this out |
| 4. Total training samples | N/A | Unrecoverable |
| 5. Validation samples | N/A | Unrecoverable |
| 6. Test samples | Low | Named "Test-1 unseen families" split existed; count unrecoverable |
| 7. Split methodology | Low-Medium | Epoch-wise train/val known; unseen-family test split named but mechanics unknown |
| 8. Random seed | High (model seed) / None (data seed) | seed=42 (model init); data-generation seed unknown |
| 9. Train/val/test overlap | Cannot test | Files absent; only the team's own naming convention suggests intent to avoid it |
| 10. Template family overlap (training vs. paper's benchmark) | High | No overlap — confirmed by direct taxonomy comparison |
| 11. Instance-only vs. template-identical | High (for deprecated corpus only) | Confirmed by the corpus's own docstring |
| 12. Data leakage exists | High (for deprecated corpus) / Low risk (for canonical benchmark) | Scoped and bounded, not present in the paper's headline result |
| 13. Indirect leakage via shared generation logic | Medium | One confirmed mechanism (deprecated corpus); ruled out for canonical benchmark's code path; generic V2X-format convergence not ruled out |
| 14. Evaluation text resembles training text | High (deprecated corpus, by design) / Cannot measure (canonical benchmark) | No training text survives to compare against |
| 15. Can leakage be ruled out | No, not completely | Direct/taxonomy leakage ruled out for the canonical benchmark; stylistic convergence cannot be ruled out without the original training text |

---

## Recommendations

1. **State this provenance gap explicitly in the manuscript**, in the
   Reproducibility appendix and as a named limitation, rather than
   implying the training corpus is available or fully characterized.
   Suggested wording direction: *"B3's original fine-tuning corpus was
   produced in an antecedent project and is not part of this
   repository's reproducibility package; its size, exact split
   composition, and generation seed cannot be recovered. Taxonomy-level
   analysis rules out direct template overlap with the paper's canonical
   STBV-Bench benchmark, but stylistic convergence at the level of
   generic V2X message-format conventions cannot be excluded without the
   original corpus."* This directly extends the existing L12 limitation
   in `DISCUSSION_AND_LIMITATIONS.md` rather than duplicating it —
   consider merging this report's findings into L12 as a cited sub-point.
2. **Do not claim a specific training-set size, split ratio, or
   generation seed for B3 anywhere in the manuscript** — none of these
   are recoverable, and any number without the citation trail this report
   was unable to establish would not survive a reviewer's request for
   the underlying file.
3. **If possible, retrieve the original `v2x-pi-project` directory** (the
   machine path `/home/harshitvaish123/...` suggests this may exist on a
   collaborator's machine or an original submission archive outside this
   git repository) and, at minimum, commit the `outputs/splits/*` files
   referenced by `error_analysis.py` — even without the raw pre-split
   corpus, having the actual test split would let a hash/text-overlap
   check against STBV-Bench actually be run, converting §9/§15 from
   "cannot test" to a verified result.
4. **Do not use `semantic_evaluation/semantic_attack_dataset.py`'s
   headline numbers as a detection-accuracy claim** — this project's own
   prior documentation already reached this conclusion; this report adds
   the specific, first-party textual evidence (the docstring, §11) as a
   citable justification for that decision, which strengthens rather than
   changes the existing recommendation.
5. **If a reviewer presses on training-data provenance**, the honest,
   defensible answer this report supports is: *"the original training
   corpus is not part of the released artifact; we have verified no
   taxonomy-level or file-level overlap with our evaluation benchmarks,
   and we disclose that stylistic-convergence leakage cannot be fully
   excluded without the original corpus"* — not a claim of a clean,
   fully-verified split.

---

## Evidence index (file paths and commands used)

- `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/config.json` — architecture
- `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/training_args.bin` — loaded via `torch.load(..., weights_only=False)` this investigation, yielding `seed=42`, `data_seed=None`, `num_train_epochs=15`, `output_dir`/`logging_dir` paths
- `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/pytorch_model.bin` — hash-verified (567,622,450 bytes, SHA-256 `9ee7475e08f76ce6961c55204657a380d5ef1c2c9dac6a9d46543a7c42c2f5d2`)
- `b3/solution_stb/b3_semantic_gate/error_analysis.py` (lines 1–24) — references absent `outputs/splits/test1_stbv_unseen_families.json`
- `b3/solution_stb/b3_semantic_gate/verify_cases_1_4.py` (lines 1–20) — confirms original project layout `~/v2x-pi-project/...`
- `semantic_evaluation/semantic_attack_dataset.py` (lines 1–14, and all 120 `rationale=` fields) — confirmed leakage-by-design docstring and per-scenario `AF#` references
- `stbv_bench/transformations.py` (all `family=` fields) — confirmed independent taxonomy, zero overlap with `AF#`/`Case #`
- `b3_eval/data/split_manifest.json`, `export_semantic_split.py` — confirmed regenerated (not original) benchmark split, with self-documented caveats
- `b3_eval/results/model_benchmark.json` — checkpoint hash cross-check, 24-sample test split confirmation
- `data/v1/train.json`, `data/v1/dataset_metadata.json` — investigated and ruled out as B3's training data (incompatible schema)
- `README.md` (lines 382–393) — documented expected checkpoint size/hash, Git LFS instructions
- `B3_ASSESSMENT.md` — prior-round assessment (written before this investigation's checkpoint-hash verification; that document's §0.1 described the checkpoint as an unmaterialized LFS pointer, which this investigation found to now be resolved/materialized — noted here so the two documents are not read as contradictory without explanation)
- `DISCUSSION_AND_LIMITATIONS.md` (L12) — pre-existing, related limitation this report extends
- `git log --all --pretty=format: --name-only` (full history, all refs) — zero training-script or raw-dataset commits ever found
- `git log --diff-filter=D --all` — zero deleted training/dataset files found
- `git lfs ls-files`, `.gitattributes` — confirmed LFS tracking and materialization status
