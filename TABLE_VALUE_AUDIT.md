# Table Value Audit

Every numerical value in every evaluation table in `stbv_paper.tex`, audited before any change was made, against: benchmark, dataset split, checkpoint, evaluation script, confidence threshold, calibration, decision policy, configuration.

All rows below use the **current final checkpoint** (`semantic_gate_v3_mixed_lora_hardmine_merged`, temperature $T{=}3.18$) unless a row explicitly names an earlier checkpoint (Table `tab:v25b`'s progression rows).

## Former `tab:ablation` (the table this task's Problem 1 flags -- now split, see below)

| Row | Benchmark | Split | Checkpoint | Script | Threshold/Calib. | Decision policy | Config |
|---|---|---|---|---|---|---|---|
| Existing Pipeline | -- | -- | -- | -- | -- | -- | Not implementable (`enable_b1` does not exist) |
| B1 only | ITE-Bench | full ($n{=}9{,}900$) | final | `ite_bench/run_ite_ablation.py` | n/a (B1 has no confidence threshold) | rule-based, not fused | `enable_mbd=F,enable_cp=F,enable_b3=F` |
| B1+B2 | ITE-Bench | full | final | same | n/a | rule-based | `enable_mbd=T,enable_cp=F,enable_b3=F` |
| B1+B2+CP | ITE-Bench | full | final | same | n/a | rule-based | `enable_mbd=T,enable_cp=T,enable_b3=F` |
| B3 only | STBV-Bench v2.5b | full ($n{=}10{,}098$) | final | `b3_eval/v25_finetune/run_v25b_full_ablation_hardmine.py` | $T{=}3.18$ | B3-only short-circuit (not full fusion) | `enable_mbd=F,enable_cp=F,enable_b3=T` |
| B1+B2+B3 (no CP) | STBV-Bench v2.5b | full | final | `run_v25b_config6_hardmine.py` | $T{=}3.18$ | Full Trust Decision Engine (Yager fusion) | `enable_mbd=T,enable_cp=F,enable_b3=T` |
| **Full STBV / ITE-Bench** | ITE-Bench | full | final | `ite_bench/run_ite_ablation.py` | $T{=}3.18$ | Full Trust Decision Engine | `enable_mbd=T,enable_cp=T,enable_b3=T` |
| **Full STBV / v2.5b** | STBV-Bench v2.5b | full | final | `run_v25b_full_ablation_hardmine.py` | $T{=}3.18$ | Full Trust Decision Engine | `enable_mbd=T,enable_cp=T,enable_b3=T` |

**These two "Full STBV" rows are two different, independently-run experiments on two different benchmarks, both using the identical checkpoint, threshold, and decision policy.** They are not two measurements of the same quantity and are not expected to agree -- this is the central finding of `TABLE_CONSISTENCY_REPORT.md`.

## `tab:v25b` (checkpoint progression, direct classifier, unchanged this pass)

| Row | Benchmark | Checkpoint | Script | Note |
|---|---|---|---|---|
| Untuned base | v2.5b | base model, no fine-tuning | `eval_v25b_final.py` | Direct classifier (raw text in, argmax out), not the full pipeline |
| Mixed corpus (pre-cont.) | v2.5b | `semantic_gate_v3_mixed_lora_merged` | same | Direct classifier |
| Continued (prior final) | v2.5b | `semantic_gate_v3_mixed_lora_continued_merged` | `eval_hardmine_v25b.py` | Direct classifier |
| Hard-mined (final) | v2.5b | `semantic_gate_v3_mixed_lora_hardmine_merged` | same | Direct classifier -- **not the same measurement as any pipeline row**: no MBD/CP/fusion/decision policy involved at all. |

**Important, previously-implicit distinction now made explicit:** the "Continued (prior final)" row's F1 (0.945) and the former unified table's "Full STBV / ITE-Bench" F1 (0.945) are the **same number by coincidence, not by relationship** -- one is a direct-classifier score on the prior checkpoint, the other is a full-pipeline score on the current checkpoint, on a different benchmark. Flagged here as a genuine risk of visual confusion for a skimming reviewer, even though the two numbers are individually correct and unambiguous in context (each row/sentence names its own checkpoint and evaluation type). No action taken beyond this disclosure, since renumbering either value would be scientifically dishonest (both are real, correct, independently-verified numbers that happen to share a decimal value).

## `tab:veremi`, `tab:carla`, `tab:complexity`

Audited and unchanged this pass -- no configuration in these tables is duplicated elsewhere in the manuscript with a different reported value. `tab:veremi` (MBD on real VeReMi traces, 5 seeds) and `tab:carla` (10 live-CARLA scenarios, current final checkpoint) each report a benchmark/configuration combination that appears in exactly one table.

## Conclusion of value audit

No value in any table was found to be internally inconsistent (F1 vs.\ precision/recall all checked, all consistent to floating-point precision), and no configuration/benchmark pair was found reported with two *different* values anywhere in the manuscript. The scientific issue Problem 1 correctly identifies is a **presentation** issue (two different research questions sharing one table), not a **correctness** issue -- addressed in `TABLE_REDESIGN_REPORT.md`.
