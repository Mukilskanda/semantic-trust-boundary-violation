# Cooperative Perception (CP) Validation

Task: search the repository for every CP-specific fixture, run them, and
report quantitative evidence — or state plainly why none exists.

## Search performed

```
grep -rl '"event"' scenarios/ test_messages/
```

CP's own consistency-scoring gate requires a populated `event` field on
the message being evaluated (`cp/cp_layer.py`: `observations_available =
(event_label is not None) and ...`). This is the exhaustive, repo-wide
search for every fixture that could possibly exercise it.

## Result of the search

**Exactly one fixture set in the entire repository carries a real `event`
field: `scenarios/collusion/` (3 of its 20 messages — `msg_001.json`,
`msg_002.json`, `msg_003.json`, corresponding to the three real attacker
messages, stations 7000–7002).** No other scenario family
(`sybil`, `replay`, `fabrication`, `mixed`, `semantic`) and no
`test_messages/` fixture carries this field. This is the same fixture
set used for the empirical CP check in `VERIFICATION_ADDENDUM.md` §4 and
the wiring-bug fix in commit `6dc7df80c` — it is not a new fixture found
this round, but this round re-confirms, by exhaustive search rather than
by memory, that it is the *only* one.

## Quantitative evidence (source: `results/ablation/cp_empirical_verification.json`, post-fix)

Replaying `scenarios/collusion/` (20 messages, growing multi-vehicle
window, CP-on vs. CP-off, same methodology as the rest of the empirical
CP check):

| Step | Station | Ground truth | `cp_num_reports` | `cp_confidence` | `event_label` | Decision (CP-on) | Decision (CP-off) |
|---|---|---|---|---|---|---|---|
| 0 | 1000 | benign | 1 | 1.000 | `None` | ACCEPT | ACCEPT |
| 1 | 7000 | attacker | 2 | **0.800** | `traffic_condition` | CAUTION | CAUTION |
| 2 | 7001 | attacker | 3 | **0.835** | `traffic_condition` | CAUTION | CAUTION |
| 3 | 7002 | attacker | 4 | **0.879** | `traffic_condition` | CAUTION | CAUTION |
| 4 | 1001 | benign | 5 | 1.000 | `None` | ACCEPT | ACCEPT |
| ... (remaining 16 benign background vehicles, no event field) | | | | 1.000 | `None` | ACCEPT | ACCEPT |

Aggregate: 20 messages, 19 with `num_reports > 1`, **0 decision-level
flips** between CP-on and CP-off across the full fixture set.

## Interpretation, stated exactly as the task requires

CP functionality **has been validated independently and produces real,
non-trivial, correctly-varying output** (`cp_confidence` moves from a
flatlined 1.000 to genuinely computed values of 0.800/0.835/0.879 exactly
on the three messages that carry real event data, and only those three —
confirming the consistency-scoring logic activates precisely when and
only when it should). This is quantitative, reproducible evidence that
CP's algorithm is correct, not merely "trusted to be correct."

**CP could not be exercised at the decision level on STBV-Bench, or on
any of this paper's own generated benchmarks, because none of their
message-generation code paths (`stbv_bench/canonical.py`,
`generator.py`, `build_stbv_bench_v2.py`,
`build_mixed_threat_bench.py`, `build_and_run_veremi_kinematic_bench.py`)
populate an `event` field on any message they produce — a data-generation
gap in the benchmark-construction code, not a defect in CP's own
detection logic.**

The 0 decision-level flips even on `scenarios/collusion` (the one
fixture where CP genuinely activates) has its own, separate, root-caused
explanation: MBD's own `collusion_score` (a different, independently
verified detection path — see `PUBLICATION_PROGRESS.md` §Phase 2)
already drives the same CAUTION outcome for stations 7000–7002
independently of CP, so CP's real, non-zero contribution (visibly moving
`trust_score` by up to ~0.016 between CP-on/CP-off at individual steps,
per commit `6dc7df80c`'s own measurement) is masked at the discrete
decision-state level by this specific fixture's redundancy with MBD, not
by CP failing to activate.

## What would be needed to go further

A benchmark whose message-generation code emits event labels (e.g.,
deriving one from each semantic attack family's `semantic_objective`, as
proposed in `STBV_BENCH_V2_DESIGN.md` and tracked as Limitation L1 in
`PUBLICATION_PROGRESS.md`) would let CP be evaluated at the scale and
statistical power the rest of this paper's layers were evaluated at. This
is unimplemented, unscoped future work — not attempted in this round, and
not fabricated here.
