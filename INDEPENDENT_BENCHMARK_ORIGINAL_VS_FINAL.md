# INDEPENDENT_BENCHMARK_ORIGINAL_VS_FINAL.md

Standalone, informational comparison — **not a manuscript update**;
`stbv_paper.tex` was not touched for this. Both checkpoints evaluated on
the identical 216-message independent in-scope benchmark
(`indep_bench/independent_corpus.jsonl`, `INDEPENDENT_BENCHMARK.md`),
identical protocol (`pipeline.b3_bridge.classify_text`, same
`isce_config.yaml` thresholds, only `model_path` swapped via the same
override mechanism used throughout this project), identical message order
(verified: 0 order mismatches between the two runs).

- **Original checkpoint**: `b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3` — raw output `indep_bench/independent_results_original.json`, metrics `indep_bench/independent_metrics_original.json`.
- **Final checkpoint**: `semantic_gate_v3_mixed_lora_merged` (SHA-256 `638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`) — raw output `indep_bench/independent_results.json` (already produced for the paper's `tab:indep`), metrics `indep_bench/independent_metrics.json`.

## Comparison table

| Metric | Original checkpoint | Final (mixed-corpus) checkpoint |
|---|---|---|
| Accuracy | 0.421 [95% CI 0.356, 0.491] | 0.472 [95% CI 0.412, 0.542] |
| Precision | 0.952 | 0.969 |
| Recall | 0.139 | 0.215 |
| **F1** | **0.242** [95% CI 0.157, 0.328] | **0.352** [95% CI 0.260, 0.440] |
| ROC-AUC | 0.646 | 0.683 |
| PR-AUC | 0.812 | 0.829 |
| ECE | 0.494 | 0.490 |
| Brier | 0.487 | 0.493 |
| Confusion (TP/FP/FN/TN) | 20/1/124/71 | 31/1/113/71 |

(95% CIs: 2,000-resample percentile bootstrap, seed 42, matching this
project's standard protocol throughout.)

## McNemar's test (paired, n=216, same messages/order, only checkpoint differs)

$b_{01}$ (original-correct / final-wrong) = 10, $b_{10}$ (original-wrong /
final-correct) = 21, $n_{\text{discordant}} = 31$.

Continuity-corrected $\chi^2(1) = 3.226$, **$p = 0.072$**.

## Verdict

The final checkpoint scores higher on every metric except Brier and ECE
(both ties within noise), most notably F1 (0.352 vs. 0.242, a 0.110
absolute improvement) and recall (0.215 vs. 0.139). **The difference is
not statistically significant at the conventional $\alpha=0.05$
threshold** ($p=0.072$), though it is suggestive — the discordant pairs
favor the final checkpoint roughly 2:1 (21 vs. 10). Both checkpoints
remain far below the in-distribution benchmarks reported in the paper
(STBV-Bench v1: F1=0.995; external corpus: F1=0.920) on this specific,
leakage-verified, fully in-scope, novel-content corpus — the mixed-corpus
fine-tune provides a real but modest, not decisive, improvement on this
particular generalization axis, and does not close the gap this benchmark
was built to measure.
