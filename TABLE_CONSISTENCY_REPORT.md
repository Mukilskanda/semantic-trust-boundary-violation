# Table Consistency Report

Directly addresses "Problem 2" from this task's request: does "Full STBV" report different accuracy in two places, and if so, why?

## The specific check requested

> Full STBV has different accuracy in Table II and Table III. If they are evaluated on the same benchmark, then they must not disagree... Otherwise one of the tables is wrong.

## Finding: not the same benchmark, so not a disagreement

The former unified table reported **two** "Full STBV Framework" rows:

| Benchmark | Acc. | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|---|
| ITE-Bench ($n{=}9{,}900$) | 0.913 | 0.896 | 1.000 | 0.945 | 0.349 |
| STBV-Bench v2.5b ($n{=}10{,}098$) | 0.852 | 0.782 | 0.999 | 0.877 | 0.315 |

Checked against every item on the request's own root-cause checklist:

- **Different dataset split?** No -- both are the full benchmark, no held-out subset.
- **Different checkpoint?** No -- both use `semantic_gate_v3_mixed_lora_hardmine_merged` (verified via each run's `run_manifest.json` / config override, `TABLE_VALUE_AUDIT.md`).
- **Different decision threshold?** No -- both use $\tau_H{=}0.70,\tau_L{=}0.40$ (the fixed, paper-wide fusion thresholds, unchanged across all experiments).
- **Different confidence policy?** No -- both use the identical Trust Decision Engine (Dempster-Shafer/Yager fusion, the same floor rules, the same $T{=}3.18$ calibration temperature).
- **Different evaluation script?** Different script *file* (`ite_bench/run_ite_ablation.py` vs.\ `run_v25b_full_ablation_hardmine.py`), but both instantiate the identical `ISCEPipeline(enable_mbd=True, enable_cp=True, enable_b3=True)` from `pipeline/orchestrator.py` -- confirmed by reading both scripts in full; neither reimplements pipeline logic, both call the same class.
- **Different definition of "Full STBV"?** No -- identical: `enable_mbd=True, enable_cp=True, enable_b3=True`, the complete pipeline, in both.

**The one and only difference is the benchmark itself: ITE-Bench (balanced across communication/behavioral/semantic attacks) vs.\ STBV-Bench v2.5b (semantic-only).** Different attack mixes on the same detector necessarily produce different aggregate metrics -- this is expected, correct behavior, not an inconsistency. ITE-Bench's Full-STBV row scores higher precisely *because* it includes the communication/behavioral attacks B1/B2/CP catch at 1.000 recall (Table `tab:ite_ablation`), which v2.5b structurally does not contain.

## Why the request's suspicion was still the right instinct

The former single table made this indistinguishable from an actual bug at a glance -- exactly the failure mode the request's Problem 1 identifies. A reviewer skimming a table with two "Full STBV" rows and two different F1 values, without a large, obvious benchmark-name column break, has no fast way to rule out a copy-paste error or a stale rerun. The fix is structural (split the table so each one only ever contains one benchmark, Problem 1's own recommendation), not numerical -- no value was wrong, so no value was changed.

## Second, adjacent finding: a coincidental duplicate value, disclosed

`tab:v25b`'s "Continued (prior final)" row (direct-classifier F1 on the *prior* checkpoint) is **also** 0.945 -- the same digits as the Full-STBV/ITE-Bench F1, by coincidence: different checkpoint (prior vs.\ current final), different evaluation type (direct classifier vs.\ full pipeline), different benchmark (v2.5b vs.\ ITE-Bench). Verified these are genuinely two separate real numbers, not a copy-paste duplication, by tracing each to its own generating script and confirming the checkpoint SHA-256 differs (Appendix A). Flagged in `TABLE_VALUE_AUDIT.md` as a real, if coincidental, source of visual confusion; not changed, since both numbers are independently correct.

## Every other "Full STBV" / "B3" / "B1+B2+B3" occurrence, cross-checked

Grepped the full manuscript (tables, figure captions, Discussion, Appendix) for every mention of these three configuration names and verified each traces to exactly one of the two source experiments above, with matching numbers:

- `fig_v25b_confusion_grid` caption: FN=6, FP=1,491 $\Rightarrow$ recall $5358/5364{=}0.999$, FPR $1491/4734{=}0.315$ -- matches the v2.5b Full-STBV row exactly.
- `fig_attack_family_v25b` caption and Results prose: "only 3 of 13 families contribute any false negative," summing to 6 -- matches FN=6 above.
- Section V-B prose ("Full-stack F1 on v2.5b is 0.877... On ITE-Bench, the identical Full STBV Framework reaches F1=0.945"): now explicitly states these are two different benchmarks in the same sentence, removing the ambiguity a bare table pairing could create.
- Discussion (Section VI): references RQ1/RQ2 findings in aggregate, does not restate either specific F1 value -- no risk of drift there.

**No mismatch found anywhere in the manuscript once benchmark identity is tracked correctly.**
