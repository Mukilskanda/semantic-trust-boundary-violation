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

**CP status, stated once here plainly so it cannot be missed: the CP bug
found in `VERIFICATION_ADDENDUM.md` §4 was diagnosed only. It was never
fixed. Every benchmark in this document (STBV-Bench v1 and v2, the
kinematic bench, the mixed-threat bench) was run with CP inert, confirmed
directly in all four, including the mixed-threat bench where this was
re-verified this round after the first write-up left it as an inference
rather than a direct measurement.**

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
recombines what it's given), and CP is currently non-functional due to a
confirmed implementation bug (`VERIFICATION_ADDENDUM.md` §4), not because
cooperative perception is a bad idea.

## Claim-by-claim evidence map

| Claim | Evidence | Caveat to state alongside it |
|---|---|---|
| B3 is necessary and sufficient for detecting text-only semantic (STBV) attacks; MBD/CP contribute essentially nothing to this threat class | `ABLATION_STUDY.md` config 4 (B3 alone, no fusion): F1=0.715, precision=1.000, on n=10,000. Config 2→3 (MBD→MBD+CP) is byte-identical (0 flips) | B3's detection is uneven across families — 8/20 at 100% recall, 6/20 at ≤9% (v1); state both, not just the average |
| MBD is necessary and sufficient for detecting real kinematic/behavioral attacks; B3 contributes essentially nothing to this threat class | `results/veremi_kinematic/analysis_summary.json`: MBD per-message recall 77.5% (ConstPos 91.2%, DoS 80.3%, DataReplay 60.0%), FPR 52.4%. Config 3/4 (CP, B3) byte-identical to config 2 (MBD alone) on all 13,511 messages — B3 confirmed contributing zero, exactly as expected on text-free messages | MBD's FPR (~52% per-message, ~99% per-vehicle "ever flagged") is high; state this precisely — MBD is a recall-oriented signal meant to feed fusion/CAUTION, not a standalone precise classifier |
| B3 and MBD cover complementary, non-overlapping threat classes, verified in BOTH directions on real evidence | Semantic case: `ABLATION_STUDY.md`. Kinematic case: `results/veremi_kinematic/`. Both point the same way — each layer is strong exactly where the other has no signal | This is the core, well-supported claim — cite both benchmarks together, never one alone |
| Two independent, single-vehicle detectors (B3, MBD) each correctly score their own vehicle's own evidence even when co-present in a shared multi-vehicle scene with a different attacker type | `results/mixed_threat/`: in windows containing BOTH a real kinematic attacker and an independently-injected semantic attacker on different vehicles, kinematic rows detected 90.3% (MBD), semantic rows detected 70.3% (B3), with 0/431 vehicles ever double-counted | **Do not** describe this as "layers interacting" or "cooperative/complementary detection within a scene" — CP is the only component that could carry cross-vehicle influence and it is confirmed inert (§ CP status above), so these are two uncoupled single-vehicle scores that merely happen to share a JSON window, not evidence of architectural synergy. The ~16pp semantic-recall gap vs. the semantic-only control (86.7%) is **resolved**, not open: it traces to a family-mix sampling confound (mixed windows' semantic-attacker rows are 89% drawn from just 3 families, with `semantic_narrative_poisoning` alone — a lower-recall family — supplying 35.5% of the sample from only 2 real vehicles, an artifact of only 14 raw `mixed`-composition windows existing in a 120-window run). A larger, family-stratified run is needed for a publication-quality mixed-threat number; see `FOLLOWUP_VERIFICATION_2.md` §3. |
| Fusion (Trust Decision Engine) adds a small, real, statistically significant effect beyond B3 alone, structured around routing uncertainty through CAUTION | `VERIFICATION_ADDENDUM.md` §2: 1,713 real 3-way decision changes (config 4→5), 0 of which are direct ACCEPT↔REJECT reversals; 92.5% are CAUTION→REJECT escalations on genuine attacks. Cohen's h=-0.026 (negligible on the binary scale) but p=3.06e-29 (real, systematic, not noise) | State both the effect size (negligible, binary) and the transition-level finding (real, structural) together — neither alone is the full picture |
| Realistic multi-vehicle context measurably improves B3's detection of previously-weak semantic attack families, with zero regressions | `STBV_BENCH_V2_DESIGN.md`: 12/20 families improved (up to +75pp), 8/20 already at ceiling stayed there, 0/20 regressed | **Do not** attribute this to "more realistic/accurate detection" without qualification. `FOLLOWUP_VERIFICATION_2.md` §2 found a direct causal example (identical payload text, decision flips from ACCEPT to CAUTION purely as filler context accumulates from 0→10 cluster-peer sentences) and that 22.7% of multi-message attacker sequences show this same within-sequence flip with unchanged payload text — confirming a real, non-negligible **context-volume/composition sensitivity** in B3 (candidate explanation "b") is a genuine contributor. But the same check found the context-volume-vs-detection correlation **reverses direction** for 2 of 6 weak families (semantic_narrative_poisoning, mixed_semantic_attacks: undetected messages had MORE context, not less), which a pure length-artifact story does not predict — so real-world representativeness (candidate explanation "a") is not ruled out either. State both mechanisms as real contributors whose relative weight is not resolved; do not pick one. |
| Cooperative Perception (CP), as a *concept*, remains architecturally motivated for cross-source contradiction/corroboration attacks | `THREAT_CLASS_COVERAGE_MATRIX.md`'s "blocked pending CP fix" section — the multi-source injection strategy (STBV-Bench v2) is implemented and ready to evaluate CP the moment the fix lands | Do **not** claim CP currently works or currently contributes anything — it is confirmed inert (`VERIFICATION_ADDENDUM.md` §4, reconfirmed independently in 3 separate harnesses this session: the 120-message empirical check, STBV-Bench v2 at 5,062 messages, and the mixed-threat bench at 4,123 messages — `cp_confidence == 1.0` on literally every message evaluated all session) |

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
remains open. Cooperative Perception remains a motivated but currently
non-functional component of the architecture: an implementation bug
(the orchestrator never supplies the event label CP's fusion gate
requires) was identified and precisely root-caused, but not fixed, in
this evaluation, and every benchmark reported here — including the
mixed-threat result above — was run with this bug confirmed present.
This is disclosed as an open limitation, not a validated capability, and
no claim in this evaluation should be read as demonstrating working
cooperative perception.*

## Do not cite without checking currency

If the CP fix referenced in `VERIFICATION_ADDENDUM.md` §4 lands in a
future session, **re-run the affected benchmarks** (the empirical CP
check, STBV-Bench v1/v2, the kinematic bench, the mixed-threat bench)
before updating any claim that currently says "CP is inert" — do not
assume the fix works without re-measuring, per this repo's established
evidence standard.
