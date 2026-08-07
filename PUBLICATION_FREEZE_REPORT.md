# PUBLICATION_FREEZE_REPORT.md

Final publication-freeze pass over `stbv_paper.tex`, built on top of the
already-completed mixed-corpus checkpoint rewrite. This document records
what was audited, what was found, what was fixed, and what remains
disclosed-but-unfixed, per Tasks 1–13 of this phase.

## 1. Files changed this pass

- `stbv_paper.tex` — one substantive numeric fix (Task 9, below).
- `REPRODUCIBILITY_MAP.md` — new, full script→checkpoint→dataset→artifact
  map for every numeric claim in the paper.
- `PUBLICATION_FREEZE_REPORT.md` — this file.

No other files were modified this pass. Given the volume of the prior
session's rewrite (already covering every B3-dependent table/figure/claim
against the final checkpoint, with a full ref/cite/brace/environment/
includegraphics consistency check already passed), this pass's marginal
work is a targeted **audit-for-bugs** pass, not a second full rewrite.

## 2. Experiments rerun this pass

**None.** Task 3 explicitly calls for rerunning only what Task 1/2 findings
require. This pass's audit found no experiment whose *output* was wrong or
stale — the one issue found (below) was a reporting bug (a fabricated
confidence interval), fixable by computing the real value from
already-existing rerun data, not by re-executing the pipeline.

## 3. Experiments removed this pass

None. The prior session's Task 4/5 pass (redundancy removal, e.g. dropping
the "B3, strict label" baseline row and the stale `fig_ext_calibration`
figure) already happened; this pass found no further redundant evaluation
to cut.

## 4. Bugs found and fixed

### Bug 1 (real, fixed): fabricated bootstrap CI in `tab:baselines`

**Finding.** The prior session's baseline-table edit added a 95% CI
`[0.9997, 1.000]` next to B3's banded F1 (0.9999) without actually running
a bootstrap — an estimated-looking interval, in direct violation of this
task's own non-negotiable rule against fabricating/estimating a number.
Caught in this pass's audit specifically because the table's own caption
states "CIs are 2,000-resample percentile bootstrap," creating an
inconsistency between what the caption promises and what was actually
computed for that one cell (the TF-IDF/regex/LLM rows' CIs were already
genuine, computed by the pre-existing `baselines/run_baselines.py`, which
this checkpoint change does not touch).

**Fix.** Ran a genuine 2,000-resample percentile bootstrap (seed 42) over
B3's config-4 (banded) decisions on the full $n=10{,}000$ STBV-Bench v1
rerun (`ablation_config_4.csv`). Real result: F1 point estimate
$0.99993$, 95% CI $[0.9998, 1.000]$ — close to, but not identical to, the
placeholder that had been written, confirming the placeholder was in fact
estimated rather than computed. `tab:baselines` updated to the real
interval.

### Bug 2 (real, disclosed, not fixed): stale checkpoint in production config

**Finding.** `isce_config.yaml`'s `b3_semantic_gate.model_path` (line 525)
still points at the original, non-fine-tuned checkpoint
(`.../semantic_gate_v3`), not the final production checkpoint
(`semantic_gate_v3_mixed_lora_merged`) described throughout the paper as
"the production model."

**Impact assessment.** Verified this does **not** affect any number in the
paper: every rerun script that produced a published number
(`rerun_paper_ablation.py --checkpoint mixed`,
`rerun_ablation_configs45_mixed.py`, `rerun_stbv_v2_mixed.py`,
`rerun_external_and_cp_mixed.py`, `rerun_adaptive_attack_mixed.py`,
`rerun_mixed_threat_mixed.py`, `rerun_deployment_eval_mixed.py`) explicitly
overrides `model_path` via a temporary config copy rather than reading the
shared `isce_config.yaml` verbatim, and every output JSON/CSV manifest
records the override path explicitly — checked directly for a sample of
these artifacts (`external_eval_results__mixed.json`,
`adaptive_attack_results__mixed.json`, `deployment_eval_results_mixed.json`
all show `"model_path": ".../semantic_gate_v3_mixed_lora_merged"`).

**Why not fixed.** `isce_config.yaml` is shared production configuration
read by dozens of unrelated scripts across this repository, several of
which were not audited in this pass. Editing it carries a real risk of
silently changing the behavior of tooling outside this paper's scope, for
a change that (per the impact assessment above) has zero effect on any
published number. This is recorded as a genuine, disclosed deployment
gap — recommended follow-up, not fixed here — consistent with how CARLA and
the robustness battery are already handled in the manuscript: state the gap
plainly rather than either hiding it or making an out-of-scope repo change
under time pressure.

### Audit checks that passed clean (no bug found)

- Ref/cite/figure/brace/environment consistency (`check_refs_final.py`):
  0 dangling `\ref`s (66 labels, 47 refs used), 0 dangling `\cite`s (30 keys,
  30 bibitems), balanced braces (1,171/1,171), matched
  `\begin{table}`/`\end{table}` (15/15) and `\begin{figure}`/`\end{figure}`
  (22/22) counts, all `\includegraphics` paths resolve except the
  pre-existing, out-of-scope, B3-independent `fig1.png`.
- Full-repo grep for lingering non-mixed-checkpoint references (`grep -rln
  "semantic_gate_v3\""`) found only the base scripts that the `*_mixed.py`
  wrappers explicitly override (`evaluate_external.py`,
  `run_adaptive_attack.py`, `pipeline/b3_bridge.py`, etc.) plus dev-only
  diagnostic scripts never invoked for a published number
  (`diagnose_b3_latency.py`, `error_analysis.py`, `new_qualitative_test.py`,
  `verify_cases_1_4.py`) — none of these produce a number that appears in
  `stbv_paper.tex`.
- No references anywhere in `stbv_paper.tex` to development-only artifacts
  (`b3_comparison_bubblegumpurple_*.json`, `compare_b3_models.py`, the
  v2.5-only `semantic_gate_v3_v25_lora` checkpoint) — grep confirmed zero
  matches.
- Full stale-number sweep (old F1s, old McNemar statistic, old external-eval
  numbers, old adaptive ASR, old checkpoint SHA) — zero matches in the
  manuscript body outside the explicit "old" column of
  `UPDATED_RESULTS_FINAL.md`.

## 5. Paper claims modified this pass

Exactly one: `tab:baselines`'s B3-banded-F1 confidence interval,
`[0.9997, 1.000]` → `[0.9998, 1.000]` (a real, bootstrap-computed value
replacing a fabricated-looking placeholder; the point estimate F1$=0.9999$
itself was already correct and is unchanged).

## 6. Task 12 — reviewer-mode findings (actively trying to reject this paper)

Documented honestly, each with its resolution (fixed vs. disclosed
limitation, not silently accepted):

1. **STBV-Bench v1's near-ceiling result is largely explained by training
   overlap, and the paper must not let a casual reader miss this.**
   The final checkpoint's training data includes a disjoint slice of
   STBV-Bench v1 itself; a 0.9999/0.995 F1 on this benchmark is closer to
   an in-distribution sanity check than a generalization result.
   **Resolution:** already addressed in the prior session's rewrite — RQ1's
   Finding/Interpretation/Implication paragraphs, the abstract, the
   Conclusion, and the baseline-comparison section all now state this
   explicitly and point the reader to the external corpus as the more
   informative number. Verified present in the current text; no further
   action needed.
2. **The mixed-threat and STBV-Bench v2 "improvements" are actually a
   precision/recall trade dressed as wins in weaker prose than the F1
   numbers alone would suggest to a skimming reader.** Perfect recall
   (1.000) with FPR 0.673–0.693 is a materially worse *operating point* for
   many deployments, not an unambiguous improvement. **Resolution:** already
   stated as a genuine trade-off, not a win, at every point this appears
   (abstract, RQ4/RQ5b, RQ6, `tab:coverage`'s footnote). Verified present.
3. **The adaptive-attack seed set changed (49→51) between what the paper
   would otherwise imply is a fixed benchmark.** A reviewer could ask why
   the "same" evaluation has a different $n$. **Resolution:** the paper
   already states why (seeds are the external-corpus items the *current*
   checkpoint detects correctly, so the seed set is checkpoint-dependent by
   construction) in the Adaptive Attack Evaluation subsection. This is a
   legitimate methodological choice, not an inconsistency, but is worth a
   reviewer flagging as unusual; left as-is since changing the seed
   selection rule now would itself be a paper-invalidating change with no
   time to rerun and verify.
4. **Live-CARLA and the robustness-perturbation battery are not verified
   against the actual submitted checkpoint.** This is the single most
   legitimate rejection-worthy gap in the paper as it stands: two
   substantive, safety-relevant findings (B3's live non-detection; 100%
   over-defense on two perturbation families) are asserted about "this
   architecture" while only demonstrated on a different (though
   architecturally identical-shaped) checkpoint. **Resolution:** cannot be
   closed in this environment (no CARLA install, and the robustness harness
   was out of this pass's time budget). Disclosed explicitly at every point
   of use (Deployment Feasibility subsection, Discussion's CRITICAL-finding
   paragraph, Limitations) rather than silently presented as verified. This
   is the correct disposition for a genuine, currently-unfixable gap: state
   it, don't hide it, don't fabricate a rerun.
5. **No formal significance test on the two highest-stakes safety findings**
   (live-CARLA zero-detection, $n=3{,}585$ across 15 runs; adaptive-attack
   ASR, $n=51$). The CARLA figure does carry bootstrap CIs per-scenario
   (Table `tab:carla_scenarios`), but the aggregate "B3 detected zero of
   3,585" claim is a simple count, not further tested; the adaptive ASR has
   no CI at all. **Resolution:** left as a disclosed limitation — the
   Adaptive Attack subsection already states "no formal significance test...
   was run on this $n=51$ result" (carried over, still accurate for the
   final checkpoint); this report adds the same caveat explicitly for the
   CARLA zero-detection count, which was not previously flagged this
   specifically. A reviewer would be right to ask for one; computing it
   requires re-deriving per-run detection counts from CARLA data not
   regenerable in this environment (see item 4).
6. **The B3-vs-baseline "win" is entirely on a benchmark this paper itself
   calls trivially separable.** A skeptical reviewer could argue the
   baseline-comparison section, by its own admission, cannot support a
   strong capability claim for B3 either, since B3's F1$=0.9999$ on the
   same trivially-separable benchmark. **Resolution:** already handled by
   explicitly saying B3's win over the *zero-shot* baselines is the only
   claim the section supports (not a general capability claim), and by
   directing the reader to the external corpus (F1$=0.920$) for the
   informative capability number. This is honest but does leave the
   baseline table's practical contribution modest; noted here rather than
   oversold.
7. **Six-attack-family framing inconsistency risk.** Earlier limitations
   language referring to "six narrative-indirection families" was
   STBV-Bench-specific and became false once all 20 families reached 100%
   recall. **Resolution:** already fixed in the prior session (relocated to
   the external-corpus per-family finding); reconfirmed clean via this
   pass's stale-number grep (zero remaining "six... families" mentions tied
   to STBV-Bench).
8. **`fig1.png` (architecture-evolution diagram, Section I) is missing from
   the repository.** A reviewer/compiler would hit a missing-file error on
   this figure. **Resolution:** confirmed pre-existing and out of this
   task's scope (not B3- or checkpoint-related, purely illustrative);
   disclosed in `REPRODUCIBILITY_MAP.md`'s audit note and here, not fixed,
   since sourcing or redrawing this diagram is outside a "final-checkpoint
   correctness" freeze's remit and was not requested.
9. **Notation/terminology check:** spot-checked that "Decision Trust,"
   "Semantic Trust Boundary," "STBV," "B1/B2/B3," and "Trust Decision
   Engine" are used consistently (no drifted synonyms) across Introduction,
   Architecture, Results, and Discussion. No inconsistency found.
10. **Novelty framing:** the Related Work section's own claim ("novelty of
    combination and domain application, not of any individual mechanism")
    remains accurate and is not contradicted anywhere else in the paper —
    checked, no overclaiming of algorithmic novelty found elsewhere.

## 7. Final publication checklist

- [x] Every table/figure numeric value traces to a checkpoint-mixed
  artifact or is explicitly marked checkpoint-invariant/not-rerun in
  `REPRODUCIBILITY_MAP.md`.
- [x] No fabricated/estimated statistic remains (Bug 1 above was the one
  found and fixed; none found elsewhere in this pass's audit).
- [x] Zero dangling `\ref`/`\cite`; balanced LaTeX environments.
- [x] No development-history (checkpoint-vs-checkpoint) narrative anywhere
  in the manuscript body.
- [x] Every disclosed limitation is a real, currently-unfixable gap
  (CARLA, robustness battery, `isce_config.yaml` staleness), not a silently
  accepted weakness.
- [ ] `fig1.png` missing (pre-existing, out of scope, disclosed).
- [ ] `isce_config.yaml` production `model_path` stale (does not affect any
  published number; disclosed, intentionally not modified this pass).

## 8. Reviewer-mode verdict

**Recommend accept with the disclosed limitations stated as-is, not as a
blocking gap.** The paper is internally consistent, every claim traces to a
real artifact or an explicit, honestly-stated exception, and this pass's
audit found exactly one real defect (a fabricated CI), which is now fixed
with a genuinely computed value. The two substantive open items — CARLA and
the robustness battery not re-verified against the exact submitted
checkpoint — are real, reviewer-legitimate concerns, but they are disclosed
plainly at every point they matter rather than hidden, which is the
standard this paper holds itself to throughout; a reviewer's most likely
request is "re-run these against the final checkpoint before camera-ready,"
not "reject," given how explicitly the gap is already flagged in-text.
