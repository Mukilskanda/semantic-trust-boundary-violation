# Manuscript Framing: The Architecture's Actual Contribution

This document states, precisely and with evidence citations, what can and
cannot be claimed about the trust architecture based on everything
measured this session. It supersedes the "narrower framing" note at the
end of `ABLATION_STUDY.md` Step 6 — that note is still correct as far as
it went, but it was written before the companion kinematic benchmark,
STBV-Bench v2, and the mixed-threat benchmark existed. Every claim below
has a specific evidence citation; do not state anything in the manuscript
that isn't traceable to one of these.

**Updated after a second verification round — see `FOLLOWUP_VERIFICATION_2.md`
for the full investigation.** Two claims below were corrected as a result
(the mixed-threat "independent firing" wording, and the v2-improvement
explanation), not merely re-worded — read that document if you need the
reasoning, not just the conclusion.

**Updated again after the CP wiring bug was fixed (commit `6dc7df80c`).
Read this status carefully — it now has three distinct parts, and
conflating them will misstate the result:**

1. **The wiring bug itself (`_run_cp` never passing `event_label` to
   `cp_layer()`) is fixed and verified working.** Re-running the same
   120-message empirical check on `scenarios/collusion` (which carries a
   real `event` field) now shows genuine, varying `cp_confidence`
   (0.8/0.835/0.879, previously flatlined at 1.0) and a real `trust_score`
   delta between CP-on and CP-off. CP's consistency-scoring logic
   genuinely activates given real event data.
2. **Every benchmark number in this document is unaffected by the fix and
   was not re-run** — checked before applying the fix, not assumed:
   none of STBV-Bench v1/v2, the kinematic bench, or the mixed-threat
   bench's generated messages ever carry an `event` field, so
   `event_label` still evaluates to `None` for every one of them, exactly
   as before the fix. Every number cited below from those four benchmarks
   is accurate whether or not the fix exists.
3. **CP still does not — and cannot yet — contribute to STBV-Bench's own
   `collaborative_semantic_agreement`/`cross_source_contradiction`
   families**, which is the multi-source scenario CP is conceptually
   *for*. The wiring fix was necessary but is not sufficient: those
   families inject free text into `scene_context`, not a structured
   `event` field, so a further, separate, unscoped follow-up (adding
   event labels to the semantic transformation engine's output) is still
   required before CP can be evaluated on STBV-Bench's own content. Do
   not describe CP as "now working" in the manuscript without this
   qualifier — describe it as "wiring-fixed and verified on real
   event-bearing traffic; not yet evaluable on this paper's own generated
   semantic-attack benchmarks."

## The claim to make

**The complete trust architecture is necessary because its layers cover
complementary, largely non-overlapping threat classes — B3 (semantic) for
attacks that manipulate meaning/narrative with clean kinematics, and MBD
(behavioral/kinematic) for attacks that falsify position/motion/timing
with no textual content — not because every layer contributes comparably
to detecting any single attack.**

## The claim NOT to make

Do not claim "every layer contributes to every decision" or "the
architecture's value is uniform across layers." The ablation study
directly falsifies this for this architecture as currently implemented
(`ABLATION_STUDY.md`): B2 adds no independent evidence of its own (it
recombines what it's given), and CP contributes zero to every benchmark
in this paper's evaluation corpus — its wiring bug is now fixed
(`VERIFICATION_ADDENDUM.md` §4), but none of the generated benchmarks
carry the event data CP needs, so its reported contribution here is
correctly zero regardless of the fix, not because cooperative perception
is a bad idea.

## Claim-by-claim evidence map

| Claim | Evidence | Caveat to state alongside it |
|---|---|---|
| B3 is necessary and sufficient for detecting text-only semantic (STBV) attacks; MBD/CP contribute essentially nothing to this threat class | `ABLATION_STUDY.md` config 4 (B3 alone, no fusion): F1=0.715, precision=1.000, on n=10,000. Config 2→3 (MBD→MBD+CP) is byte-identical (0 flips) | B3's detection is uneven across families — 8/20 at 100% recall, 6/20 at ≤9% (v1); state both, not just the average |
| MBD is necessary and sufficient for detecting real kinematic/behavioral attacks; B3 contributes essentially nothing to this threat class | `results/veremi_kinematic/analysis_summary.json`: MBD per-message recall 77.5% (ConstPos 91.2%, DoS 80.3%, DataReplay 60.0%), FPR 52.4%. Config 3/4 (CP, B3) byte-identical to config 2 (MBD alone) on all 13,511 messages — B3 confirmed contributing zero, exactly as expected on text-free messages | MBD's FPR (~52% per-message, ~99% per-vehicle "ever flagged") is high; state this precisely — MBD is a recall-oriented signal meant to feed fusion/CAUTION, not a standalone precise classifier |
| B3 and MBD cover complementary, non-overlapping threat classes, verified in BOTH directions on real evidence | Semantic case: `ABLATION_STUDY.md`. Kinematic case: `results/veremi_kinematic/`. Both point the same way — each layer is strong exactly where the other has no signal | This is the core, well-supported claim — cite both benchmarks together, never one alone |
| Two independent, single-vehicle detectors (B3, MBD) each correctly score their own vehicle's own evidence even when co-present in a shared multi-vehicle scene with a different attacker type | `results/mixed_threat/`: in windows containing BOTH a real kinematic attacker and an independently-injected semantic attacker on different vehicles, kinematic rows detected 90.3% (MBD), semantic rows detected 70.3% (B3), with 0/431 vehicles ever double-counted | **Do not** describe this as "layers interacting" or "cooperative/complementary detection within a scene" — CP was inert (confirmed directly) for this specific run, and is the only component that could carry cross-vehicle influence, so these are two uncoupled single-vehicle scores that merely happen to share a JSON window, not evidence of architectural synergy. This benchmark was run and reported BEFORE the CP wiring fix and was not re-run after (correctly — its messages carry no `event` field, so the fix would not change it; see CP status above). The ~16pp semantic-recall gap vs. the semantic-only control (86.7%) is **resolved**, not open: it traces to a family-mix sampling confound (mixed windows' semantic-attacker rows are 89% drawn from just 3 families, with `semantic_narrative_poisoning` alone — a lower-recall family — supplying 35.5% of the sample from only 2 real vehicles, an artifact of only 14 raw `mixed`-composition windows existing in a 120-window run). A larger, family-stratified run is needed for a publication-quality mixed-threat number; see `FOLLOWUP_VERIFICATION_2.md` §3. |
| Fusion (Trust Decision Engine) adds a small, real, statistically significant effect beyond B3 alone, structured around routing uncertainty through CAUTION | `VERIFICATION_ADDENDUM.md` §2: 1,713 real 3-way decision changes (config 4→5), 0 of which are direct ACCEPT↔REJECT reversals; 92.5% are CAUTION→REJECT escalations on genuine attacks. Cohen's h=-0.026 (negligible on the binary scale) but p=3.06e-29 (real, systematic, not noise) | State both the effect size (negligible, binary) and the transition-level finding (real, structural) together — neither alone is the full picture |
| Realistic multi-vehicle context measurably improves B3's detection of previously-weak semantic attack families, with zero regressions | `STBV_BENCH_V2_DESIGN.md`: 12/20 families improved (up to +75pp), 8/20 already at ceiling stayed there, 0/20 regressed | **Do not** attribute this to "more realistic/accurate detection" without qualification. `FOLLOWUP_VERIFICATION_2.md` §2 found a direct causal example (identical payload text, decision flips from ACCEPT to CAUTION purely as filler context accumulates from 0→10 cluster-peer sentences) and that 22.7% of multi-message attacker sequences show this same within-sequence flip with unchanged payload text — confirming a real, non-negligible **context-volume/composition sensitivity** in B3 (candidate explanation "b") is a genuine contributor. But the same check found the context-volume-vs-detection correlation **reverses direction** for 2 of 6 weak families (semantic_narrative_poisoning, mixed_semantic_attacks: undetected messages had MORE context, not less), which a pure length-artifact story does not predict — so real-world representativeness (candidate explanation "a") is not ruled out either. State both mechanisms as real contributors whose relative weight is not resolved; do not pick one. |
| Cooperative Perception (CP)'s wiring bug is fixed and its consistency-scoring logic verified working on real event-bearing data | `VERIFICATION_ADDENDUM.md` §4 update: `_run_cp` now passes `event_label`; re-running the 120-message check shows `scenarios/collusion` producing genuine varying `cp_confidence` (0.8/0.835/0.879) and a real `trust_score` delta between CP-on/CP-off, where every prior measurement was flatlined at `cp_confidence==1.0` | Do **not** extend this to "CP now contributes to the paper's results" — every benchmark number reported in this paper (STBV-Bench v1/v2, kinematic, mixed-threat) was generated by code that never attaches an `event` field to its messages, so CP's measured contribution to every one of those remains correctly zero, fix or no fix. The fix only changes behavior on hand-authored fixtures that carry real `event` data (`scenarios/collusion`, similar Phase 2 fixtures) — none of which are part of this paper's reported benchmark numbers. |
| Cooperative Perception (CP), as a *concept*, remains architecturally motivated for cross-source contradiction/corroboration attacks, and is now one fix closer to being evaluable | `THREAT_CLASS_COVERAGE_MATRIX.md`'s "blocked pending CP fix" section — the multi-source injection strategy (STBV-Bench v2) is implemented; the wiring bug is fixed; what remains is adding event labels to the semantic transformation engine's own output | This is future work, not a result. Do not claim CP has been evaluated on any STBV-Bench-generated content — it hasn't, and can't yet, because that content still carries no event data for the (now-working) CP logic to act on. |

## One-paragraph version for the manuscript's architecture-evaluation section

*The trust architecture's contribution is best understood as complementary
threat-class coverage rather than uniform per-layer participation in
every decision. On a benchmark of purely semantic (STBV) attacks with
real, unaltered kinematics, the semantic classifier (B3) alone accounts
for nearly all detection capability (F1=0.715 without fusion, n=10,000),
while the behavioral/kinematic layer (MBD) contributes negligibly — as
expected, since these attacks carry no kinematic signal. The converse
holds precisely on a companion benchmark of real VeReMi kinematic attacks
(constant-position falsification, replay, DoS): MBD alone detects 60-91%
of these attacks depending on attack type, while B3 contributes nothing,
since these messages carry no text. A mixed-threat benchmark placing both
attack types on different vehicles within the same shared multi-vehicle
scene confirms each detector continues to correctly score its own
vehicle's own evidence under these conditions (90.3% kinematic recall via
MBD, 70.3% semantic recall via B3); this should be read as evidence that
co-locating threat classes does not break either detector, not as
evidence of cross-vehicle architectural synergy, since cooperative
perception — the only component that could carry influence between the
two attacker vehicles — is confirmed non-functional in the evaluated
codebase (below). Fusion itself contributes a small but statistically
significant effect on top of either layer alone, structured specifically
around routing uncertain evidence through an intermediate CAUTION state
rather than forcing binary calls (0 of 1,713 fusion-attributable decision
changes were direct ACCEPT↔REJECT reversals). A secondary benchmark using
real multi-vehicle traffic windows instead of independent single messages
found substantially higher B3 recall on several previously-weak semantic
attack families (up to +75 percentage points, zero regressions); a
targeted follow-up traced part of this improvement to B3's sensitivity to
the surrounding scene-context volume rather than to the attack content
alone (a directly observed causal example, and 22.7% of multi-message
attacker sequences, showed detection changing with identical attack text
as context accumulated), while the correlation's direction was
inconsistent across families — so this result is reported as a real,
partially-understood improvement whose full explanation (realistic-
traffic representativeness, classifier input-sensitivity, or both)
remains open. Cooperative Perception's contribution to every result
reported above is zero: an implementation bug that prevented CP's
consistency-scoring logic from ever activating (the orchestrator never
supplied the event label CP's own fusion gate requires) was identified,
precisely root-caused, and fixed during this evaluation, and the fix was
verified to correctly activate CP's scoring on real event-bearing traffic
after the change. However, none of the benchmark data reported in this
paper carries the event information CP requires — a separate, independent
limitation of the benchmark-generation pipelines, not the CP fix — so
every number above was measured, and remains valid, with CP's actual
contribution at zero regardless of the fix. This is disclosed as an open
limitation of the evaluation corpus, not of the fix, and no claim in this
evaluation should be read as demonstrating CP contributing to any reported
result.*

## Do not cite without checking currency

**The CP wiring fix has landed** (`pipeline/orchestrator.py`, commit
`6dc7df80c`) and is verified working on event-bearing traffic — do not
describe it as "diagnosed but not fixed" going forward. What remains
true is that **no benchmark number in this document changed or needs
re-running because of it** (verified before applying the fix, by
inspecting every generator for `event`-field usage; verified after, by
re-running only the fixture-based check that could possibly be affected).
If a future session adds event-label generation to the semantic
transformation engine (the remaining, separate, unscoped follow-up) and
CP begins contributing to STBV-Bench's own multi-source families, **that
would be new evidence requiring new benchmark runs** — do not assume CP
contributes to any of this paper's own generated content without such a
re-run, and do not conflate "the wiring bug is fixed" with "CP has been
evaluated on this paper's benchmarks," which remains false.
