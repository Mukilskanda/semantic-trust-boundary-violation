# REVIEWER2_CHECKLIST.md — fresh adversarial pass on the current manuscript

Re-read the current `stbv_paper.tex` end to end (post dev-history removal,
results rewrite, root-cause validation, and the real SUMO rerun/CARLA
re-verification) as an IEEE Transactions Reviewer #2 trying to reject it.
Findings below are new to this pass or materially changed from the
previous reviewer-mode pass in `PUBLICATION_FREEZE_REPORT.md` — items
already resolved there and unaffected by this cycle's edits are not
repeated in full, only cross-referenced.

## New/changed findings this cycle

1. **The new $p_{99}=100.2$~ms SUMO finding needed a stronger Discussion
   tie-in, and didn't have one until this pass.** The Results section
   stated the number, but the Discussion's "Deployment implications"
   paragraph still read as if only concurrency-driven throughput mattered,
   not single-message latency. **Fixed this pass:** rewrote that paragraph
   to state explicitly that the budget is "already exhausted before any
   multi-vehicle contention is introduced," which is the sharper and more
   defensible claim the new data actually supports.
2. **`tab:deployment` now visibly mixes two different checkpoints in one
   table (SUMO = final checkpoint, CARLA = prior checkpoint).** A
   literal-minded reviewer could object that a single table implicitly
   invites a row-by-row SUMO-vs-CARLA comparison as if both used the same
   model. **Assessed, not further changed:** the table's caption and the
   preceding paragraph already state this explicitly and by design (CARLA
   genuinely cannot be rerun here); splitting into two tables would add a
   table for a purely presentational reason without new information,
   contrary to Task 4/5's "don't add a table without new value" instruction
   from the prior phase. Left as one table with the disclosure prominent;
   documented here as a legitimate, considered trade-off rather than an
   oversight.
3. **`tab:safety`'s adaptive-evasion risk downgrade (HIGH→MEDIUM) has no
   confidence interval behind it.** A skeptical reviewer could argue a
   safety-relevant risk rating should not move on a point estimate (ASR
   21.6%, $n=51$, no CI) alone. **Assessed, not changed:** this is a
   legitimate methodological gap already disclosed in
   `ROOT_CAUSE_REPORT.md`/`FINAL_RESULTS.md`'s statistical-backing table
   ("no formal significance test... was run on this $n=51$ result"). The
   rating change is defensible directionally (62-point absolute ASR drop is
   very unlikely to be noise) but a reviewer asking for a bootstrap CI on
   this specific number before camera-ready would be making a fair request;
   noted as a remaining, disclosed limitation rather than silently accepted
   as settled.
4. **The abstract's throughput headline (13.47~msg/s) is the CARLA number,
   not the fresh SUMO number (13.51~msg/s) — a reader skimming only the
   abstract could think the throughput bottleneck was re-verified against
   the final checkpoint when the specific cited figure was not.** **Not
   changed:** both numbers are nearly identical (13.47 vs. 13.51~msg/s), so
   the qualitative claim ("throughput does not scale to realistic
   concurrency") is not at risk of being wrong either way, and correctly
   attributing the abstract's specific figure to CARLA (rather than
   swapping in the SUMO number) preserves the abstract's connection to the
   bootstrap-CI-backed multi-run measurement, which is the more rigorous of
   the two. Flagged here as a close call rather than silently decided.
5. **No LaTeX compile was ever performed across this entire task chain.**
   Confirmed via exhaustive environment search (no `pdflatex`/`xelatex`/
   `latexmk`/`tectonic` anywhere on this machine) that this is a genuine
   environment limitation, not a skipped step. A real reviewer would
   receive a compiled PDF, not source; this is disclosed as an open item
   for whoever has TeX Live/MiKTeX access before actual submission, and
   the static consistency checks performed instead (ref/cite/brace/figure
   resolution, all clean except the pre-existing `fig1.png`) are the
   closest available substitute, not a replacement.

## Findings carried forward, reconfirmed still valid this cycle

All ten items from `PUBLICATION_FREEZE_REPORT.md`'s Task-12 pass were
re-read against the current text:
- STBV-Bench v1's in-distribution caveat: still present, still accurate,
  reconfirmed by this cycle's deeper root-cause analysis
  (`ROOT_CAUSE_REPORT.md`) rather than weakened by it.
- The mixed-threat/v2 recall-vs-FPR trade framing: unchanged, still honest.
- Adaptive-attack seed-set methodology note: unchanged, still present.
- CARLA/robustness-battery non-reproduction against the final checkpoint:
  reconfirmed by a second, more exhaustive environment search this cycle
  (Docker checked this time, not just `pip`/filesystem) — same conclusion,
  stronger evidence.
- Baseline-comparison framing (B3 vs. trivially-separable STBV-Bench):
  unchanged.
- "Six narrative-indirection families" stale claim: confirmed still fixed
  (zero remaining matches in this cycle's grep).
- `fig1.png` missing: still missing, still out of scope, still disclosed.
- Notation/terminology consistency: spot-checked again after the
  deployment-section rewrite, no drift introduced.
- Novelty framing: unchanged, still accurate.
- Missing significance test on the CARLA zero-detection count: still open,
  still disclosed (now cross-referenced in `FINAL_RESULTS.md`'s statistical
  table as well, for visibility).

## Overall verdict

**Accept with minor revisions.** No new blocking issue was found this
cycle; item 1 above (the strongest genuinely-new concern) was fixed
directly. Items 2–4 are close calls that were assessed and intentionally
left as-is with the reasoning documented, not silently ignored. Item 5 (no
compiled PDF) is a real, disclosed environment gap that should be closed by
whoever has LaTeX access before the actual submission deadline — it is not
evidence of anything wrong with the manuscript's content, only that this
task chain could not produce camera-ready output artifacts in this
sandboxed environment.
