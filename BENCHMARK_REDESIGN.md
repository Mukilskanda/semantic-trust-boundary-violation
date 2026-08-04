# STBV-Bench v2.5: Redesign

This document describes what changed in the corpus and why. The measurements
that justify each change are in [BENCHMARK_AUDIT.md](BENCHMARK_AUDIT.md) and
[LEXICAL_LEAKAGE_ANALYSIS.md](LEXICAL_LEAKAGE_ANALYSIS.md); nothing here is
asserted without a number behind it.

## Why v1 failed

STBV-Bench v1's benign class was **10 unique strings repeated 2,993 times**.
Five bag-of-words models with no semantic capacity separated it from the
malicious class at F1 = ROC-AUC = 1.0000. The benchmark measured whether a
model had memorized a ~550-string lookup table, not whether it could reason
about message semantics. Full statistics in BENCHMARK_AUDIT.md §2.

## Design principle: "same surface, different pragmatics"

The label must be recoverable **only** from the pragmatic relation a message
asserts (who is entitled to assert what, on what evidential basis) —
never from vocabulary, length, register, or grammatical mood. Concretely:

- Every label-independent constituent (message opening, warrant clause,
  closing, road/hazard/weather/time lexicon, station naming) is drawn from a
  **shared pool** used by both classes.
- Every semantic act is authored in **both** a second-person/imperative
  ("direct") and a third-person/declarative ("report") form, with the form
  sampled **independently of the label**.
- Benign messages deliberately include **hard negatives**: legitimate
  clearances, legitimate priority grants, legitimate authority instructions,
  legitimate corroboration — i.e. messages that use each attack family's
  characteristic vocabulary in a context where it is true and verified,
  rather than asserted without evidence.

## What generates the corpus

- [`benchmark/v25_compositional.py`](benchmark/v25_compositional.py) — the
  compositional grammar: 11 benign intents (4 routine + 7 "legit_*" hard
  negatives targeting specific attack families) and 13 malicious attack
  families, each with 3–5 core sentence patterns x 2 moods, combined with a
  shared slot lexicon (35 road names, 12 lanes, 22 hazards, 16 weather
  conditions, 12 traffic conditions, 16 timestamps, randomized
  station/vehicle/RSU identifiers) and 10 message frames.
- [`benchmark/stbv_bench_v25.py`](benchmark/stbv_bench_v25.py) — generation +
  quality control, single command: `python benchmark/stbv_bench_v25.py`.

## Attack family coverage (13 families, all requested families present)

authority_override, false_clearance, fabricated_consensus,
sensor_discreditation, priority_manipulation, goal_manipulation,
traffic_efficiency_lure, context_inversion, narrative_poisoning,
indirect_prompt_injection, instruction_hiding, role_confusion,
cross_source_contradiction — 447 to 559 accepted messages per family
(`data/stbv_bench/v25/manifest.json`).

## Benign coverage (11 intents, including 7 hard-negative intents)

routine_status, hazard_report, rsu_advisory, telemetry (routine); plus
legit_clearance, legit_authority, legit_priority, legit_corroboration,
legit_context_update, legit_routing, legit_sensor_caveat,
legit_bridge_disregard, legit_bridge_precedence,
legit_bridge_fleet_detection (hard negatives, added across iterations 1 and
3 of the leakage analysis) — 338 to 428 accepted messages per intent.

## Meeting the stated diversity requirements

| Requirement | Delivered |
|---|---|
| ≥1,000 unique benign messages | **5,612** unique benign messages (56x the floor) |
| ≥1,000 unique malicious realizations, every family preserved | **6,632** unique malicious messages across 13 families |
| Different sentence structures / grammar / syntax | 10 message frames x 2 moods (direct/report) x per-intent core variation |
| Formal / informal, RSU- / vehicle-generated, CAM/DENM-style, long/short | Frame and opener pool includes bulletin, advisory-channel, telemetry-sync, and CAM/DENM-style registers; length ranges 6–47 tokens |
| Passive / active voice, synonyms, paraphrase, context change | "report" mood is predominantly passive/declarative, "direct" mood active/imperative; slot lexicon randomizes road, hazard, weather, time, and identifier context per instance |
| No two messages differ by only one word | Enforced by quality control (below); 0% of accepted pairs have normalized edit distance < 0.20, vs. 19.6% in v1's benign class |

## Quality control (Task 4)

Implemented in `stbv_bench_v25.py::quality_control`. Every candidate message
is checked against the accepted pool for its family (near-duplication only
matters **within** a family — two different attack families sharing surface
form is the generator's explicit design goal, not a defect, so cross-family
similarity is not penalized). A cheap token-Jaccard prefilter (gate = 0.45)
runs before the expensive checks; anything below the gate is already
lexically distant and cannot trip a threshold.

| Filter | Threshold | Rejections (this run) |
|---|---|---|
| Exact duplicate | — | included in self_bleu/edit bucket below |
| Self-BLEU vs. nearby accepted messages | > 0.60 | 1,156 |
| Normalized edit distance | < 0.25 | 204 |
| 4-gram containment | > 0.70 | 188 |
| **Total rejected** | | **1,548 / 13,792 raw (11.2%)** |

Every rejected message, its family, and its specific rejection reason are
logged verbatim to `data/stbv_bench/v25/rejected.jsonl` (not summarized —
the full record is kept for audit).

## What did NOT fully work, and the actual fix (Task 5 summary)

Corpus-diversity engineering (iterations 1–3) eliminated the **length**
shortcut (AUC 0.98 → 0.53) and the **grammatical mood** shortcut, and
measurably reduced the **vocabulary** shortcut, but could not fully
eliminate lexical separability under a **random** train/test split: the
strongest bag-of-words models still reached F1 = 1.0000 in iteration 3. The
root cause is structural — a finite number of hand-authored sentence
skeletons is memorizable by any sufficiently expressive n-gram model
regardless of vocabulary overlap. The corpus now tags every message with a
`template_id`; evaluating under **template-disjoint `GroupKFold` splitting**
(never testing on a skeleton seen during training) brings the same models'
F1 down to 0.57–0.76 and AUC to 0.59–0.86 — under the 0.90/0.95 acceptance
thresholds for every model tested. Full iteration-by-iteration numbers,
including the ones that did not work, are in
[LEXICAL_LEAKAGE_ANALYSIS.md](LEXICAL_LEAKAGE_ANALYSIS.md).

**Practical consequence for downstream evaluation**: any result computed on
STBV-Bench v2.5 that is used to support a semantic-vs-lexical claim must use
the template-disjoint split (`template_id` column, `GroupKFold`), not a
random split. This is now the benchmark's canonical protocol for that class
of claim.

## What remains open

- B3 has not yet been re-evaluated on v2.5 under the template-disjoint
  protocol (tracked separately; not claimed complete here).
- The manuscript's dataset/methodology/results sections have not yet been
  rewritten to describe v2.5 and the template-disjoint protocol end-to-end.
- v1 is retained in `data/stbv_bench/v1/` for provenance and is not deleted;
  it must not be used for any semantic-reasoning claim going forward.
