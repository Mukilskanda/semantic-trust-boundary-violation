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

## Kinematic/behavioral threat families — evidence: `results/veremi_kinematic/` (Task 2), n≈14,400 real VeReMi messages, stateful per-vehicle replay

*(Filled in once the background run completes — see `PUBLICATION_PROGRESS.md`
for the numbers; the row shape is fixed here so the matrix's structure does
not depend on the exact figures.)*

| Attack family (VeReMi) | Detecting layer | Recall | Why |
|---|---|---|---|
| Constant-position falsification (ConstPos) | MBD | ⏳ | Displacement-vs-reported-speed consistency check; confirmed firing directly on sender 8193 before the full run (see `stbv_bench/build_and_run_veremi_kinematic_bench.py` docstring) |
| Data replay (DataReplay) | MBD (+ B1 exact-match cache) | ⏳ | Dual detection path per Phase 2's `PUBLICATION_PROGRESS.md` finding on `scenarios/replay` |
| DoS/flooding (DoS) | MBD | ⏳ | Rate/behavioral anomaly checks |
| (all three) | B3 | expected null | No text present in pure-kinematic VeReMi messages; B3 has structurally nothing to classify — confirms the complementary (not overlapping) coverage claim from the other direction |
| (all three) | CP | expected null (bug) | Same wiring bug as the semantic case — CP cannot contribute regardless of threat class until fixed |

## Cooperative-perception-dependent families — blocked pending CP fix

| Attack family | Intended layer | Status |
|---|---|---|
| collaborative_semantic_agreement (true multi-source variant) | CP + B3 | ⏳ blocked — needs both the CP fix AND STBV-Bench v2's multi-source injection (`STBV_BENCH_V2_DESIGN.md`) |
| cross_source_contradiction (true multi-source variant) | CP + B3 | ⏳ blocked — same |
| Sybil (co-location) | MBD | ✅ verified working — Phase 2 (`PUBLICATION_PROGRESS.md`): fixed a projection-origin bug this made possible to verify; sybil_score correctly discriminates attacker (0.87→CAUTION) from benign (0.0→ACCEPT) on `scenarios/sybil` |
| Collusion | MBD | ⚠️ verified working, but only when an explicit `event`/DENM cause-code is present (Phase 2 finding) — a data-availability limitation on plain CAM-only traffic, not an algorithm defect |
| Fabrication | MBD (Sybil+Replay signals) | ⚠️ verified reaching CAUTION, not REJECT, on `scenarios/fabrication` — Phase 2 finding, reported as a real limitation |

## Root-caused negative findings (report honestly, do not omit)

1. **CP is structurally non-functional in the current codebase, in every
   evaluation harness tried this session** (STBV-Bench v1, the 120-message
   empirical multi-vehicle check, STBV-Bench v2's prototype with real
   cp_num_reports up to 42, and the kinematic companion bench). Root cause
   (`VERIFICATION_ADDENDUM.md` §4, confirmed by direct code inspection):
   `pipeline/orchestrator.py::_run_cp` never passes `event_label` to
   `cp/cp_layer.py::cp_layer()`, so `observations_available` is always
   `False` and CP always returns neutral values (`cp_confidence == 1.0`
   exactly, on every message, in every harness). This is independent of
   window size, sender count, or threat class. **Not fixed this session**
   (explicit instruction not to alter/re-run existing numbers); precisely
   scoped fix documented, pending its own follow-up commit + re-validation.
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

- Kinematic companion bench numbers (running; Task 2).
- STBV-Bench v2 numbers at a real scale beyond the 15-window smoke test
  (Task 1 prototype; needs a larger run once GPU is free).
- Mixed-threat benchmark numbers (Task 3; script written, not yet run).
- Everything CP-dependent, until the CP fix lands and is independently
  re-validated (explicitly out of scope for this session).
