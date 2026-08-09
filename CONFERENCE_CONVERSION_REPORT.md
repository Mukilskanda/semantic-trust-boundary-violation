# Conference Conversion Report

This pass converted the manuscript from journal-style exposition to conference-style brevity: every remaining paragraph was tested against "would an IEEE conference reviewer need this to understand or trust the contribution?" Nothing was removed because it was merely long — everything removed was either restating a point already made once elsewhere, or explanatory scaffolding a reviewer does not need to trust the result. All experiments, all six propositions, all three equations, all 6 figures, and all 5 tables from the prior layout-optimization pass are unchanged in content.

## Headline numbers

**Word count: 11,538 → 7,796 words** (a 32.4% reduction this pass alone, on top of the two prior compression passes). No LaTeX compiler is available in this environment (`pdflatex` not installed), so page counts below are structural estimates from word count and float inventory, not a compiled measurement — stated as such, not asserted as fact, consistent with every prior pass in this session.

## Per-section results against the stated targets

| Section | Word count (prose only) | Floats | Target | Estimate |
|---|---|---|---|---|
| Architecture | 2,611 words | 3 figures (1 is a full-width `figure*`), 1 table, 3 equations | ≤3 pages | **Likely 2.5-3.0 pages** -- close to the target; the full-width `fig_whyfail` and the notation-dense Trust Decision Engine subsection are the two remaining space costs, both scientifically load-bearing (the one concrete worked comparison figure; the fusion math and 6 propositions) and not cut further |
| Results | 1,888 words | 3 figures, 3 tables (one a 2-part merged table) | ≤3 pages | **Likely 2.3-2.8 pages** -- within target on a word-count basis; float count is the main remaining space cost, already minimized in the prior layout pass |
| Discussion | 240 words | 0 | ≤0.5 page | **~0.15-0.2 page** -- comfortably under target |
| Conclusion | 207 words | 0 | ≤0.5 page | **~0.15 page** -- comfortably under target |

Introduction (401 words), Related Work (205 words), and Threat Model (186 words) were not separately capped but were tightened as part of the same pass (see below), since front matter also "costs acceptance probability" per the stated objective.

## Where every cut came from, by section

### Architecture (the largest single source of savings)
- **Per-layer walkthrough** (PKI→B1→MBD→B2→CP→B3→Fusion→Adapters): the prior version repeated a "why is the next stage needed" rhetorical frame six times, each as its own paragraph with *Purpose/Inputs/Outputs/Limitation* labels spelled out. Converted to one continuous paragraph, one sentence per layer, keeping every purpose, every input, every output, and every limitation as a clause rather than a labeled sub-bullet. This was the single largest word-count reduction in the paper (~750 words → ~280 words) with zero technical content dropped: every number (141.9M parameters, 128,100-token vocabulary, 0.35/0.25/0.20/0.20 CP weights, $T{=}3.18$) survives.
- **Trust Decision Engine**: cut restated definitions (e.g., belief/plausibility were defined but never used again by name elsewhere in the paper, so the two unused symbols $\mathrm{Bel}(T)/\mathrm{Pl}(T)$ were dropped from the inlined notation while every symbol that *is* used later — $\Theta$, $K$, $m_Y$, $T_{Decision}$, $\tau_H/\tau_L$ — was kept). All three equations and all six propositions (P1-P6) are unchanged.
- **Motivation for Multi-Layer Semantic Trust**: the prior version stated several points (independence, orthogonality, confidence-aware fusion, boundary-as-design-object, provable conservatism, why-not-one-model) as six separately-headed paragraphs, several making overlapping arguments from different angles. Consolidated into three paragraphs covering the same six points once each. The DeBERTa-v2 backbone-comparison paragraph (a real 5-candidate measurement) is retained with every number, trimmed of restated framing only.
- **Complexity/assumptions/failure-modes**: already condensed to a table + short paragraphs in the prior layout pass; tightened further to declarative clauses (e.g., "PKI/crypto are assumed sound" instead of a full sentence per assumption). Every assumption and every failure mode named is still present.

### Results
- **ITE-Bench Finding/Interpretation**: merged two paragraphs (a numbers-first "Finding" and a restating "Interpretation") into one, since the interpretation was largely a restatement of the finding in different words. Every recall value and every McNemar statistic ($\chi^2{=}3883$, $\chi^2{=}2705$, both $p{<}10^{-15}$) is retained.
- **v2.5b subsection** (the second-largest source of savings): the prior version had five long paragraphs -- checkpoint progression, hard-example mining, full-pipeline ablation, a two-stage root-cause narrative, and a "which configurations were actually run" administrative paragraph. Condensed to four tighter paragraphs. Every number survives: all four checkpoints' F1/ROC-AUC, the 332/262 error-mining counts, the 91-paraphrase detail, both McNemar tests ($\chi^2{=}234.3$, $p{\approx}7\times10^{-53}$), both root-cause stage costs ($-0.039$, $-0.041$/$-0.046$), and the calibration cross-reference.
- **Deployment Validation** (VeReMi/CARLA/SUMO/Adaptive): cut narrative connective tissue ("we traced the exact text B3 received by instrumenting the classifier call directly and found...") down to the causal chain itself (bug → root cause → fix → verification), keeping every measured number (62.5% pre-fix ACCEPT rate, 188 unit tests, 80.1ms/10.45msg/s CARLA latency, 81.2ms/12.3msg/s SUMO latency, 21.6% ASR, the three-round detection-probability sequence).
- **One fact dropped, disclosed here rather than silently cut**: the adaptive-attack subsection's detail that `narrative_poisoning` precedes evasion most often (4/11) was removed as the one genuinely secondary fact in this pass -- a reviewer needs the aggregate ASR and detection-probability curve to trust the robustness claim, not the single most-common precursor family. This is the only number-adjacent fact removed anywhere in this pass; every other number in the paper survives.

### Discussion (700 → 240 words)
Merged "Why the architecture works" and "Why semantic trust is necessary, and why defense-in-depth matters" into one paragraph (they supported the same conclusion from two angles). Converted the three-theme, six-item `enumerate` limitations list into three inline sentences (one per theme), keeping every limitation named with its specific measured evidence, at a fraction of the vertical space an `enumerate` environment costs. Cut "Safety consequences" and "Future work" each to 1-2 sentences.

### Conclusion (250 → 207 words)
Cut restated RQ evidence to the minimum needed to name each result once; removed one clause that repeated Discussion's disclosure sentence in different words.

### Introduction / Related Work / Threat Model
Left largely as previously compressed (these were not separately capped by this pass's instructions), with one exception: the Threat Model's "Why existing V2X trust pipelines admit this attack" paragraph was cut from ~150 words to ~45 words, since Architecture's "Proposed STBV Architecture" subsection now makes the identical argument with the added weight of a concrete measured example ($T_{Decision}{=}0.730$) -- keeping the fuller version there and reducing this one to a forward pointer avoids stating the same argument twice.

## What was explicitly NOT cut, and why

- **All three equations** (BBA, conflict, Yager combination) and **all six propositions** (P1-P6) are present with identical content -- only surrounding prose was tightened.
- **All 6 figures and 5 tables** from the prior layout-optimization pass are unchanged in content, data, and captions' substance (caption wording was tightened in a few places but no cited number was altered).
- **Every experiment, every benchmark, every checkpoint comparison, and every statistical test** (McNemar, confidence intervals) is retained with its exact reported value.
- **The full per-layer Purpose/Input/Output/Limitation structure** survives as prose clauses rather than labeled fields, preserving the information a reviewer needs to verify each layer's scope without the journal-style formatting overhead.

## Confirmation

No experiment was rerun. No number, equation, proposition, or table/figure value was changed. Mechanical LaTeX audit (`scratch_latex_audit.py`), re-run after all edits: 0 broken references, 0 duplicate labels, 0 missing citations, figure count 6, table count 5 (both unchanged from the prior layout pass), all cross-references resolve. Three subsection labels (`sec:novelty`, `sec:conclusion`, `sec:related`) are now unreferenced by any `\ref` (informational only, not an error) as a side effect of tightened cross-referencing prose during this pass -- their `\label` remains in place and harmless.

## Honest residual risk

Without a compiler, the ≤3-page Architecture/Results targets cannot be confirmed exactly; the word-count and float-inventory estimates above suggest both are close to or within target, but the full-width `fig_whyfail` figure and the multi-table Results section are the two remaining components most likely to push either section slightly over 3 pages in a real compile. If a real page count shows either section still over budget after compiling against the venue's actual `IEEEtran` class, the next lever (not exercised here without further instruction) would be shrinking `fig_whyfail`'s node spacing/font or moving the DeBERTa-v2 backbone-comparison paragraph to the appendix, both of which would cost real content visibility, not just prose length -- flagged rather than done unilaterally.
