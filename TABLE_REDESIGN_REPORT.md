# Table Redesign Report

Implements Step 4 (split the unified table) and the structure requested in Problem 1, using the real values verified in `TABLE_VALUE_AUDIT.md` -- no value was recomputed or changed, only reorganized.

## Before

One `table*` (`tab:ablation`, full-width, 9 columns including a "Benchmark" column) mixing ITE-Bench and STBV-Bench v2.5b rows, including two differently-scoped "Full STBV" rows side by side.

## After: two single-column tables, each answering exactly one question

**Table II -- `tab:ite_ablation`, "Architectural Validation on ITE-Bench."** Purpose stated in the caption itself: "Can the architecture detect communication and behavioral attacks?" Rows: Existing Pipeline (documented not implementable, with the reason in a footnote), B1, B1+B2, B1+B2+CP, Full STBV. Columns: Acc./Prec./Rec./F1/FPR -- exactly the 5 metrics requested, matching the request's suggested structure. The Latency column was dropped from this table (it was an estimated, not directly-measured, per-configuration value -- see `TABLE_VALUE_AUDIT.md`) and is noted in the footnote as available once, for all configurations, in the existing `tab:complexity`, avoiding a second, redundant latency column now that the table no longer needs to distinguish two benchmarks' worth of stage-timing.

**Table III -- `tab:v25b_pipeline`, "Semantic Validation on STBV-Bench v2.5b."** Purpose stated in the caption: "Does semantic validation improve the trust stack?" Rows: B3, B1+B2+B3 (no CP), Full STBV -- exactly the request's suggested row set, since B1/B1+B2/B1+B2+CP are structural non-results on a semantic-only benchmark (footnote explains why, pointing to Table II for their real performance rather than showing a row of zeros).

Both tables keep their real, audited values unchanged from the former unified table's corresponding rows (verified in `TABLE_VALUE_AUDIT.md`).

## Why this is scientifically better, not just cosmetically different

A reviewer reading Table II sees only ITE-Bench numbers and can ask "does B1 alone catch communication attacks" without first figuring out which rows belong to which benchmark. A reviewer reading Table III sees only v2.5b numbers and can ask "does adding B3 help" in isolation. Neither table can be misread as comparing B1-on-ITE-Bench against B3-on-v2.5b, because they are no longer in the same table -- the exact confusion Problem 1 describes is now structurally impossible, not just explained away in prose.

## Cross-references updated

- Section V-A's "Finding" paragraph now cites `tab:ite_ablation` (was `tab:ablation`).
- Section V-B's "Full-pipeline ablation" paragraph now cites `tab:v25b_pipeline` for the v2.5b numbers and `tab:ite_ablation` for the cross-benchmark ITE-Bench comparison, with an explicit sentence stating these are two separate experiments on two separate benchmarks (directly answering Problem 2).
- The Layer-wise Threat Coverage Matrix's caption (Section IV, unrelated to this task otherwise) referenced the old `tab:ablation` label three times; updated to point at whichever of the two new tables actually supports each claim (`tab:ite_ablation` for Cryptographic/Behavioral Trust rows, `tab:v25b_pipeline` + `tab:ite_ablation` for the Semantic Trust row) -- this is a cross-reference fix only, not a change to that figure's content, consistent with the immediately preceding task's "do not modify other figures" instruction.
- Novelty subsection's "zero-cost layering" sentence (Section IV) updated from `tab:ablation` to `tab:ite_ablation`.

## Confirmation

`scratch_latex_audit.py`, final run: 0 broken references, 0 duplicate labels, all citations resolve, table count 6 (was 5; net +1 from the 1-table-into-2 split). No table value was fabricated, interpolated, or manually edited -- every cell traces to the same real per-sample source data as before this pass.
