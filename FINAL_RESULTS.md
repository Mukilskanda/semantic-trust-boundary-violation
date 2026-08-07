# FINAL_RESULTS.md — consolidated final results, `semantic_gate_v3_mixed_lora_merged`

This is the single reference document for every headline number in the
submitted paper. It supersedes (without deleting — see `PAPER_CHANGELOG.md`
for full history) `UPDATED_RESULTS_FINAL.md` from the results-rewrite phase.

## Classification model surface

- 6-layer DeBERTa-v2, 768 hidden, 141.9M dense params post-merge.
- Production checkpoint: `semantic_gate_v3_mixed_lora_merged`, SHA-256
  `638ed0fada07808317ddadb3e7d8ab76ff2895a9b344946e263b5c5f925d15b3`
  (independently rehashed twice across this task chain — matches both
  times).
- LoRA fine-tune (r=16/α=32/dropout=0.05) on a mixture of STBV-Bench v2.5
  (8,535 rows) and a disjoint, leakage-checked slice of STBV-Bench v1
  (7,229 rows). Best epoch 6/8, val F1 0.899.

## STBV-Bench v1 (canonical benchmark, $n=10{,}000$)

| Config | Acc | Prec | Rec | F1 | FPR |
|---|---|---|---|---|---|
| B1 only | 0.299 | -- | 0.000 | -- | 0.000 |
| B1+B2 (=B1+B2+CP) | 0.305 | 0.643 | 0.018 | 0.034 | 0.023 |
| B3 alone | 0.9999 | 0.9999 | 1.000 | 0.9999 | 0.0003 |
| **Full stack** | **0.993** | **0.990** | **1.000** | **0.995** | **0.023** |

Confusion (full stack): TP=7,007, FP=70, FN=0, TN=2,923. All 20 attack
families reach 100% recall. **Root-caused and independently re-verified**
(checkpoint SHA, zero training/eval overlap, threshold trace, row-ID
integrity, arithmetic consistency — full evidence in
`ROOT_CAUSE_REPORT.md`) — this is a genuine result driven by the training
mixture's inclusion of a same-generator (but disjoint) v1 slice, i.e. an
in-distribution result for this narrow-vocabulary generator, not a bug and
not open-domain generalization evidence. The paper states this caveat at
every point the number appears.

Fusion's marginal effect (config 4→5, McNemar $\chi^2=67.0$, $p<10^{-15}$,
n=10,000 paired): 84 transitions, 100% escalations (69 Accept→Caution, 15
Caution→Reject), 0 de-escalations, 0 direct Accept↔Reject reversals —
purely conservative, exactly matching the architecture's designed
floor-rule behavior.

## STBV-Bench v2 (windowed, contextual, $n=5{,}062$/150 windows)

F1 0.521, Recall 1.000, Precision 0.353, FPR 0.693 — perfect recall bought
at a real, disclosed false-positive cost, not a free improvement.

## External semantic corpus ($n=117$, frozen checkpoint)

Acc 0.880 / Prec 0.931 / Rec 0.910 / F1 0.920 / ROC-AUC 0.897 / PR-AUC 0.932.
**B3's weakest benchmark in this paper** — stated as such throughout.
Weakest family: `phantom_hazard_fabrication` (0.700 recall).

## Adaptive-attack robustness ($n=51$ seeds)

ASR 21.6% (11/51) — the paper's strongest robustness result. Detection
probability: 1.000 (round 0) → 0.922 (round 2) → 0.784 (round 10). No
family reaches ≥50% ASR. Explicitly scoped: this is a bound against a fixed
9-strategy deterministic mutation battery, not a general adversarial
robustness guarantee.

## Mixed-threat case study ($n=4{,}123$ messages/120 windows)

Semantic-attacker recall 1.000, kinematic-attacker recall 0.873, benign FPR
0.673. Genuine recall/FPR trade, reported as such.

## CP full evaluation ($n=142$, isolated `enable_cp` delta)

33/142 decision changes, all escalations, 11/21 previously-missed attacker
messages recovered, 22 benign messages spuriously escalated to Caution
(never Reject). **Verified byte-identical** to the delta measured under the
prior checkpoint (independently recomputed twice across this task chain).

## Deployment feasibility

**SUMO replay, final checkpoint, $n=2{,}000$ (fresh, protocol-identical
rerun):** mean 73.9~ms, $p_{95}=90.4$~ms, $p_{99}=100.2$~ms (at, not
comfortably inside, the 100~ms ETSI CAM budget — a real finding, stated
plainly), B3 share 98.7%, throughput 13.51~msg/s, RSS 1,109~MB, GPU peak
685~MB.

**Live CARLA:** **not rerun this cycle.** CARLA is confirmed genuinely
absent from this environment (exhaustive re-verification: no `carla`
module, no install directory, no Docker image, Docker daemon itself not
running, no executable on PATH — full evidence in `ROOT_CAUSE_REPORT.md`).
`tab:carla_scenarios` and the "B3 detected zero of 3,585 live attack
messages" finding are carried forward from the prior checkpoint's
evaluation and flagged as such at every point of use.

## Statistical backing summary

| Claim | Test | Result |
|---|---|---|
| Fusion's effect on STBV-Bench v1 is real, not noise | McNemar (continuity-corrected) | $\chi^2=67.0$, $p<10^{-15}$ |
| B3-banded F1 on STBV-Bench v1 | 2,000-resample bootstrap (seed 42) | F1 0.9999 [0.9998, 1.000] |
| CARLA per-scenario recall/FPR/reject-rate | 15-run, 10,000-resample bootstrap | see `tab:carla_scenarios` (prior checkpoint) |
| CARLA aggregate latency/throughput | 10,000-resample bootstrap | see `tab:deployment` (prior checkpoint, CARLA column) |
| Adaptive-attack ASR | point estimate only, **no CI computed** | disclosed as an open item in `PUBLICATION_FREEZE_REPORT.md`/`ROOT_CAUSE_REPORT.md` |
| Live-CARLA zero-detection count ($n=3{,}585$) | point count only, **no formal significance test** | disclosed as an open item |

## What was intentionally not rerun this cycle, and why

- Live CARLA (no CARLA-capable environment; verified exhaustively, twice).
- The STBV-Bench v2 threshold-sensitivity sweep (time-scoped; disclosed via
  in-text caveat) — **the 11-family robustness-perturbation battery gap is
  now closed** (see addendum below).
- B3's strict-argmax baseline operating point (removed from `tab:baselines`
  rather than recomputed with a stale value, since the raw argmax label is
  not retained in the current rerun artifact).

## Addendum — presentation/structure phase

**Robustness battery, now closed (new in this phase):** reran against the
final checkpoint ($n=66$ paired seed×family variants, zero leakage
re-verified against every corpus). 6/11 families improved, 4 unchanged, 1
(`contradictory`) regressed to 100% over-defense (from 0%). Aggregate
accuracy 0.833→0.864 — **not statistically significant** (McNemar exact
binomial, $p=0.727$). Integrated into the paper's existing Results text,
not a new table (Task 4's honest appendix/main-text call: the aggregate
delta doesn't support a headline claim, so it stays as prose in its
existing location). Full detail: `ROBUSTNESS_EVAL_REPORT.md`.

**Hard-OOD benchmark repositioned, not deleted or softened:** moved from a
main-Results subsection to a Limitations/Future-Work subsection, framed as
an exploratory scope-boundary probe rather than a core capability claim
(its own audit already established this is a real generalization gap
deliberately measured *outside* the paper's declared deployment register,
not a data-quality artifact — a natural Future-Work/Limitations item, not
a headline result). **All numbers unchanged and fully intact**: F1=0.345
[0.267, 0.418], accuracy=0.458, the full failure-cluster analysis, and the
scope-audit finding that correcting the benchmark made the result worse,
not better. Full detail: `HARD_OOD_RESULTS.md`, `FAILURE_ANALYSIS.md`,
`HARD_OOD_BENCHMARK_AUDIT.md`, all unchanged this phase.

## Addendum 2 — independent in-scope benchmark (new primary result)

A new, independent evaluation corpus ($n=216$) was built to be the
inverse of hard-OOD: fully **inside** the paper's declared deployment
scope (grammatical, professional ETSI CAM/DENM register) but testing
genuinely novel scenario content (new cities, roads, entities, narratives
never used anywhere in this project). Three-method leakage audit
(exact-text, template-construction independence, embedding-similarity at
thresholds 0.95/0.90/0.85 against a 2,805-message pool spanning all six
existing corpora) found **zero** exact or near-duplicates at any threshold
(max similarity found: 0.697).

**Result: F1=0.352 [95% CI 0.260, 0.440], accuracy=0.472** — comparably
low to hard-OOD's 0.345 despite staying fully in-scope. This triggered a
mandatory root-cause investigation (checkpoint SHA, thresholds/config,
message-length truncation, character encoding, label mapping, and
failure-mode shape) before being accepted; **no bug was found** — the
failure mode (uniformly high-confidence false negatives, a graded
0%–66.7% per-family recall spread rather than a uniform collapse) is
consistent with genuine semantic difficulty, not a pipeline defect.

**This result was integrated as a primary Results table/subsection**
(`tab:indep`, Section~\ref{sec:indepbench}), not appendix or exploratory,
per this phase's explicit criterion: a scientifically sound, leakage-clean,
root-caused benchmark earns primary status regardless of the number it
produces. Combined with hard-OOD, two structurally different corpora
(one varying register, one varying content) now independently confirm the
same conclusion: STBV-Bench v1's near-ceiling result does not represent
general semantic-attack detection capability. Full detail:
`INDEPENDENT_BENCHMARK.md`, `INDEPENDENT_BENCHMARK_RESULTS.md`.

**Hard-OOD status reconfirmed unchanged**: still in Limitations/Future
Work (Section~\ref{sec:limitations}), framed as an exploratory
scope-boundary probe, all numbers intact (F1=0.345 [0.267, 0.418]) — not
re-moved or altered this phase.

## Addendum 3 — controlled surface-attribute-only confirmation

Built a second independent corpus (`indom_bench/`, $n=216$) specifically
to close a methodological gap in the first independent benchmark: whether
its low score (F1=0.352) reflected content novelty alone or was
confounded with added narrative complexity (its messages were 34.4 words
on average, notably longer than STBV-Bench's own templates). This second
corpus is calibrated directly to STBV-Bench's own short, direct message
complexity (mean 15.2 words) and varies **only** surface attributes
(city, road, entity ID, weather, lane) — same taxonomy, same leakage
rigor (zero exact/near duplicates against all seven corpora used anywhere
in this project, thresholds up to 0.85).

**Result: F1=0.314 [95% CI 0.224, 0.409]** — statistically
indistinguishable from the first independent benchmark (CIs overlap
substantially). Same mandatory root-cause quality check applied
(checkpoint SHA, truncation, encoding, label mapping, failure-mode
shape) — **no bug found**.

**Decision: both corpora are kept in main Results, neither replaces the
other.** Their agreement — comparably low F1 whether novelty is content-rich
or purely surface-level — is itself the important, strengthened finding:
it rules out narrative complexity as an alternative explanation for
either result. Integrated as a confirmatory paragraph within the existing
`sec:indepbench` subsection, not a new standalone table (avoiding
redundant table proliferation for a result whose value is confirmatory,
not novel). Full detail: `INDOMAIN_BENCHMARK.md`,
`INDOMAIN_BENCHMARK_RESULTS.md`.

## Addendum 4 — six-part quality audit of the in-domain confirmatory benchmark

Full audit (`INDOMAIN_BENCHMARK_AUDIT.md`): scope (89.8% clearly in-scope,
4.6% borderline/retained, 5.6% out-of-scope/rewritten), difficulty
leveling (0% Level-4 research-grade adversarial content, well under the
20% threshold — no redesign triggered), simulated inter-annotator
agreement (12/216 messages flagged <80%, the same 12 identified by the
scope audit), ETSI realism (12 messages contained unrealistic
self-narrating meta-commentary or degenerate content), distributional
comparison (this benchmark's messages are ~half the length of every other
corpus — a genuine, disclosed, uncorrected limitation, root-caused to
STBV-Bench's telemetry-preamble structure), and vehicle-solvability (all
messages solvable from content alone post-correction).

**12 of 216 messages (5.6%) rewritten** — self-narrating meta-commentary
removed, degenerate/mislabeled content corrected — leakage re-verified
(zero overlap against all seven corpora used anywhere in this project).
**Result: F1=0.294 [95% CI 0.204, 0.384], essentially unchanged from the
pre-audit 0.314** — CIs overlap almost entirely. The audit confirmed,
rather than manufactured, that this benchmark was already largely sound.
`stbv_paper.tex` updated to report the post-audit, final number.

