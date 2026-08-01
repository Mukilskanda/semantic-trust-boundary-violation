# Threat-Class Coverage Matrix

Maps every attack family evaluated so far to the layer(s) actually
responsible for detecting it, with the evidence source for each claim.
"Responsible" means: verified by ablation/divergence analysis to be the
layer whose presence/absence changes the decision, not merely "runs
before the decision." Where a layer is architecturally intended to help
but is currently blocked by a known bug, that is stated explicitly rather
than left to look like a design gap.

Status markers: ✅ verified working · ⚠️ works partially / honest gap ·
❌ verified NOT working (bug, not benchmark artifact) · ⏳ pending
(benchmark/run in progress at time of writing).

---

## Semantic (STBV) threat families — evidence: `ABLATION_STUDY.md`, n=10,000

| Attack family | Detecting layer | Recall | Why |
|---|---|---|---|
| authority_override | B3 | 100% | Direct command/authority-claim phrasing; B3's strongest category |
| instruction_injection | B3 | 100% | " |
| hazard_suppression | B3 | 100% | " |
| false_clearance | B3 | 100% | " |
| infrastructure_semantic_manipulation | B3 | 100% | " |
| priority_manipulation | B3 | 100% | " |
| cross_source_contradiction | B3 | 100% | Detected even though CP (the layer architecturally "supposed to" catch cross-source contradiction) is non-functional — see CP row below; B3's text-level pattern is sufficient here in v1's phrasing |
| collaborative_semantic_agreement | B3 | 100% | Same caveat — B3 catches the textual pattern; true multi-source corroboration is not yet tested (STBV-Bench v2 territory) |
| context_inversion | B3 (partial) | 65% | Mid-band: some phrasings evade B3 |
| planner_manipulation | B3 (partial) | 55% | " |
| role_manipulation | B3 (partial) | 54% | " |
| temporal_context_drift | B3 (partial) | 54% | " |
| context_poisoning | B3 (partial) | 50% | " |
| hazard_amplification | B3 (partial) | 42% | " |
| semantic_narrative_poisoning | B3 (weak) | 9% | Subtle narrative framing evades B3 almost entirely — genuine, reported weakness |
| goal_manipulation | none effective | 1% | ❌ B3 essentially never fires; MBD/CP have no kinematic signal (attack is pure text) |
| traffic_efficiency_lure | none effective | 1% | Same as above |
| indirect_prompt_injection | none effective | 2% | Same as above |
| multi_message_context_poisoning | none effective | 2% | By definition needs a real multi-message narrative; v1 cannot express this faithfully — see STBV-Bench v2 |
| mixed_semantic_attacks | none effective | 2% | Combines patterns that individually evade B3 |
| **MBD** | ⚠️ small, real, off-target | 1.9pp | Fires occasionally on real VeReMi kinematic side-effects, NOT on the semantic payload — see `ABLATION_STUDY.md` Step 6 |
| **CP** | ❌ verified inert | 0% | Confirmed bug (see below), not a benchmark limitation alone |

## Kinematic/behavioral threat families — evidence: `results/veremi_kinematic/` (Task 2), n=13,511 real VeReMi messages, 360 vehicles (180 attacker/180 benign), stateful per-vehicle replay

| Attack family (VeReMi) | Detecting layer | Recall | FPR | Why |
|---|---|---|---|---|
| Constant-position falsification (ConstPos) | MBD | 91.2% | 57.4% | Displacement-vs-reported-speed consistency check; confirmed firing directly on sender 8193 before the full run |
| DoS/flooding (DoS) | MBD | 80.3% | 49.7% | Rate/behavioral anomaly checks |
| Data replay (DataReplay) | MBD (+ B1 exact-match cache) | 60.0% | 50.1% | Weakest of the three; dual detection path (B1+MBD) per Phase 2's `PUBLICATION_PROGRESS.md` finding on `scenarios/replay`, but per-message recall on real VeReMi replay traffic is markedly lower here than the earlier small-fixture check suggested |
| (all three, pooled) | MBD | 77.5% | 52.4% | Overall per-message. All three types cluster in the same 50-57% FPR band, suggesting FPR is a general property of MBD's plausibility-check sensitivity on real, noisy VeReMi kinematics, not specific to one mechanism |
| (all three, pooled) | MBD, per-vehicle "ever flagged" | 99.2% | **99.4%** | Confirmed verified NOT working as a standalone decision policy: almost every benign vehicle is ALSO flagged at least once over a 40-message sequence. MBD's signal is real (see per-message numbers) but not currently well-calibrated for a naive cumulative "flag if ever suspicious" rule — this is a genuine, reportable tuning/policy gap, not a detection failure |
| (all three) | B3 | 0% (structural) | 0% | Confirmed: config 4 (full stack) is byte-identical to config 3 (no B3) on every one of 13,511 messages — B3 contributes nothing, exactly as expected on text-free VeReMi messages. This is the clean converse of the semantic case (B3 100%, MBD ~0% on text-only attacks) and is the direct empirical basis for the "complementary, not overlapping, coverage" claim |
| (all three) | CP | 0% (bug) | — | Config 3 (CP) identical to config 2 (MBD-only) on every message — same wiring bug as the semantic case, confirmed a third time in a third independent harness |

## STBV-Bench v2 — genuine multi-vehicle windows, n=5,062 messages (150 windows, `results/stbv_bench_v2/`)

| Finding | Evidence |
|---|---|
| Every family weak in v1 improved in v2; none regressed; all 8 families already at 100% in v1 stayed at 100% | See table in `STBV_BENCH_V2_DESIGN.md`; largest gains: goal_manipulation +75pp, indirect_prompt_injection +60pp, semantic_narrative_poisoning +53pp, multi_message_context_poisoning +52pp, traffic_efficiency_lure +49pp |
| Root cause confirmed by direct text inspection (not assumed) | v1's synthesized text always ends `"No other vehicles in cooperative cluster."`; v2's real windows produce genuine `"Cluster peer N..."` context sentences — B3 classifies the identical injected payload more reliably when embedded in richer, realistic scene context |
| CP still confirmed inert (3rd independent harness) | `cp_confidence == 1.0` on all 5,062 messages despite `cp_num_reports` reaching 212 |

## Mixed-threat benchmark — semantic + real kinematic attackers in the SAME scene, n=4,123 messages (120 windows, `results/mixed_threat/`)

| Composition | n | Result |
|---|---|---|
| `mixed` windows, kinematic-attacker rows | 154 | 90.3% detected (via MBD) |
| `mixed` windows, semantic-attacker rows | 138 | 70.3% detected (via B3) |
| `kinematic_only` windows, kinematic-attacker rows (control) | 90 | 81.1% detected |
| `semantic_only` windows, semantic-attacker rows (control) | 633 | 86.7% detected |

**This is the direct empirical demonstration Task 3 asked for**: in a
single shared multi-vehicle scene containing both a real kinematic
attacker and an independently-injected semantic attacker on a *different*
vehicle, MBD and B3 each correctly flag their respective attacker at a
rate consistent with their threat-class-pure benchmarks (§ above), with
no vehicle ever double-counted as both attacker types (0/431 by
construction). The ~16pp lower semantic recall in mixed windows (70.3%
vs. 86.7% in semantic-only) is reported honestly as an **open, unresolved
question** rather than a confirmed interaction effect — with CP inert,
there is currently no mechanism in the codebase that could cause the two
attacker vehicles to influence each other's decision, so sampling
variance (n=138 vs n=633) is the more likely explanation, but this was
not conclusively ruled out and should not be asserted either way without
a larger run.

## Cooperative-perception-dependent families — CP wiring fixed, still blocked pending event-label generation

| Attack family | Intended layer | Status |
|---|---|---|
| collaborative_semantic_agreement (true multi-source variant) | CP + B3 | ⏳ blocked — CP's wiring bug is fixed and verified working on real event-bearing traffic (`scenarios/collusion`), but STBV-Bench v2's multi-source injection strategy (implemented) still doesn't attach an `event` field to its generated messages, so CP still cannot score it. Needs a further, unscoped follow-up (event-label generation in the transformation engine) |
| cross_source_contradiction (true multi-source variant) | CP + B3 | ⏳ blocked — same |
| Sybil (co-location) | MBD | ✅ verified working — Phase 2 (`PUBLICATION_PROGRESS.md`): fixed a projection-origin bug this made possible to verify; sybil_score correctly discriminates attacker (0.87→CAUTION) from benign (0.0→ACCEPT) on `scenarios/sybil` |
| Collusion | MBD | ⚠️ verified working, but only when an explicit `event`/DENM cause-code is present (Phase 2 finding) — a data-availability limitation on plain CAM-only traffic, not an algorithm defect |
| Fabrication | MBD (Sybil+Replay signals) | ⚠️ verified reaching CAUTION, not REJECT, on `scenarios/fabrication` — Phase 2 finding, reported as a real limitation |

## Root-caused negative findings (report honestly, do not omit)

1. **CP contributed zero to every benchmark number in this document**
   (STBV-Bench v1, the 120-message empirical multi-vehicle check,
   STBV-Bench v2's prototype with real cp_num_reports up to 42, and the
   kinematic companion bench). Root cause (`VERIFICATION_ADDENDUM.md` §4,
   confirmed by direct code inspection): `pipeline/orchestrator.py::_run_cp`
   never passed `event_label` to `cp/cp_layer.py::cp_layer()`, so
   `observations_available` was always `False` and CP always returned
   neutral values (`cp_confidence == 1.0` exactly, on every message, in
   every harness). **This wiring bug is now fixed** (commit `6dc7df80c`)
   and verified working: re-running the same 120-message check shows
   `scenarios/collusion` (real `event` field present) now producing
   genuine varying `cp_confidence` and a real `trust_score` delta between
   CP-on/CP-off. **None of the numbers in this document changed or needed
   re-running** — verified before applying the fix that no benchmark
   generator in this evaluation ever attaches an `event` field to its
   messages, so `event_label` is still `None` for every one of them,
   fix or no fix. CP's zero contribution to every number above is
   therefore still accurate, now for the separate, independent reason
   that this evaluation's own benchmark content carries no event data —
   not because the detection logic is broken.
2. **B3 and MBD have almost completely non-overlapping jurisdictions on
   the evidence gathered so far**: B3 detects text-only semantic attacks
   with zero kinematic signal; MBD detects kinematic attacks with zero
   text signal (confirmed both directions — semantic attacks show ~0%
   MBD-attributable recall beyond incidental side effects, and kinematic
   attacks are expected to show ~0% B3 contribution since there is no
   text). This supports "complementary threat-class coverage" as a
   factual claim, PROVIDED it is stated about B3-vs-MBD specifically, not
   about CP (which contributes to neither right now) or about "every
   layer" (B2 was shown, in the ablation audit, to add no independent
   evidence source of its own — it recombines what MBD/CP give it).
3. **~30% of STBV-Bench's detection gap (6/20 families at ≤9% recall) is
   a B3 model-capability limitation**, not a fusion or architecture
   defect — the Trust Decision Engine faithfully propagates whatever B3
   gives it (see the ablation's config 4 vs 5 comparison), so improving
   this requires improving B3's discriminative ability on subtle/indirect
   phrasing (a modeling problem), not re-architecting fusion.

## What is still missing before this matrix is complete

- Everything CP-dependent on this evaluation's own generated content:
  the wiring fix landed and was verified on hand-authored fixtures, but
  CP still needs event-label generation added to the semantic
  transformation engine before it can be scored on STBV-Bench's own
  multi-source families — that follow-up is unscoped and not started.
- Narrative-evolution / progressive-poisoning injection strategies
  (STBV-Bench v2 design strategies 3-4, specified but not implemented).
- The B3-training-distribution question flagged in `STBV_BENCH_V2_DESIGN.md`
  (does v1→v2's recall jump reflect real-world representativeness, B3's
  training-data composition, or both) — would require inspecting B3's
  actual training corpus, not attempted this session.
- The mixed-window semantic-recall gap (70.3% vs 86.7%) at a larger n, to
  determine whether it is sampling noise or a real, currently
  unexplained effect.
