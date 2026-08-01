# STBV-Bench v2 — Multi-Message Evaluation Windows (Design)

## Why v1 is not enough

STBV-Bench v1 (`stbv_bench/`, `DATASET_INTEGRATION.md`) evaluates each
sample as one independent, unrelated single message. The layer ablation
(`ABLATION_STUDY.md`) and its verification addendum
(`VERIFICATION_ADDENDUM.md`) showed this has real, structural consequences:

- CP never receives more than one report per window by construction, so
  it cannot be exercised at all on v1 (compounded by a separate,
  independently-confirmed wiring bug — see "Blocking prerequisite" below).
- MBD's temporal/history-dependent checks (constant-position, replay,
  cross-message trust decay) cannot fire meaningfully on a single
  isolated message — they need a sender's real prior reports.
- Attack families that are inherently about **multiple messages or
  multiple sources** (`multi_message_context_poisoning`,
  `cross_source_contradiction`, `collaborative_semantic_agreement`,
  `temporal_context_drift`) were, in v1, faked from a single vehicle's
  point of view by writing several strings into one message's own
  `scene_context.peer_reports` — a plausible approximation, but not a
  faithful test of the architecture's actual multi-source fusion path.

v2's purpose is to fix this: evaluate the architecture on genuine
multi-vehicle, multi-message, temporally-ordered windows, built from real
VeReMi trajectories, so CP, cross-message MBD history, and genuinely
distributed semantic narratives can all actually be exercised.

## Blocking prerequisite

`VERIFICATION_ADDENDUM.md` §4 found and root-caused a real implementation
bug: `pipeline/orchestrator.py::_run_cp` never computes or passes
`event_label` to `cp/cp_layer.py::cp_layer()`, so `cp_layer`'s
`observations_available` is always `False` and CP always returns its
neutral/vacuous values, **regardless of window size**. This was not fixed
in that session per the explicit instruction not to alter already-reported
numbers. **v2 cannot demonstrate CP activation until this fix lands**,
independently reviewed and re-validated on its own (the fix: derive
`event_str = target_msg.get("event") or _extract_denm_event(target_msg)`
the same way `_run_mbd` already does, and pass
`cp_layer(reports, event_label=event_str, observation_weights=weights)`).
Everything else in this design (MBD temporal checks, multi-source
narrative construction, trust propagation) does not depend on that fix
and can be built and evaluated now; CP-specific numbers should be
reported as "pending the CP fix" until it lands and is separately
re-validated, not silently assumed to work.

## Window construction (from real VeReMi data, no synthetic kinematics)

1. **Time-bucket + spatial cluster grouping.** Group each source VeReMi
   scenario's flat reports by 1-second timestamp bucket, then within each
   bucket find maximal clusters of senders within a fixed radius (default
   100m — chosen because a scan of 30 random ConstPos_1416 buckets found
   real clusters of 2-7 co-located senders at this radius, confirmed this
   session; see `stbv_bench/build_stbv_bench_v2.py`'s
   `find_spatial_clusters()`). A window is only eligible if its cluster
   has ≥3 distinct senders across ≥2 consecutive time buckets (so there is
   both real multi-vehicle co-presence AND real temporal continuity, not
   just a one-second snapshot).
2. **Window = ordered, multi-sender message sequence.** Unlike v1's one
   message per sample, a v2 sample is a whole window: every real message
   from every clustered sender, in real timestamp order, over the
   window's time span (a few seconds to tens of seconds depending on the
   cluster's own duration in the source data).
3. **Replay methodology (same principle as `build_and_run_veremi_kinematic_bench.py`
   and the Phase 2 audit):** each window is replayed through ONE fresh,
   persistent `ISCEPipeline` instance for the whole window (never reused
   across windows, to avoid the same cross-sample state leakage bug fixed
   in `run_stbv_bench_eval.py`), with the message list growing message-by
   -message in real timestamp order — this is what lets MBD accumulate
   real per-sender history and CP (once fixed) see genuinely co-located
   peer reports.

## Attack injection strategies (new relative to v1)

v1's 21 transformation rules (`stbv_bench/transformations.py`) are reused
unchanged — the injection *targets* change, not the payload library:

1. **Single-attacker-in-window** (the v1-equivalent case, now with real
   peers instead of an empty window): one clustered vehicle is designated
   attacker; its own messages carry the semantic payload. Tests whether
   real co-located peer traffic changes the outcome versus v1's
   no-peers case (isolates the value of CP/peer corroboration once the
   CP fix lands).
2. **Multi-source collaborative/contradictory injection** (new): 2+
   distinct real vehicles in the same window each carry a PART of the
   attack narrative in their own separate messages — e.g. for
   `collaborative_semantic_agreement`, several senders' `peer_reports`
   each independently "confirm" the same false claim (matching the
   family's actual semantic objective); for `cross_source_contradiction`,
   two senders' messages carry mutually inconsistent claims about the
   same event. This is a faithful, distributed version of what v1 could
   only simulate from one vehicle's perspective.
3. **Narrative evolution across a sequence** (new): a single attacker
   vehicle's payload text is not static across the window — it is drawn
   from an ordered sequence of escalating/evolving variants of the same
   transformation rule (e.g. `temporal_context_drift`'s payload shifts
   from mild to urgent framing across consecutive messages). Tests
   whether the architecture's trust decisions track a slowly escalating
   attack, or only react to any single message's static content.
4. **Progressive multi-message poisoning** (new,
   `multi_message_context_poisoning`'s actual mechanism): the full
   poisoning narrative is split across several consecutive messages from
   the same attacker rather than delivered whole in one message, testing
   whether `synthesize_message`'s accumulation of `messages` (already
   passed as the full window per `pipeline/orchestrator.py:run`) lets the
   architecture connect a narrative that is spread across time.

## Schema (extends v1's per-sample schema to per-window)

```json
{
  "window_id": "stbv2-000001",
  "source_dataset": "VeReMi Extension / ConstPos_1416",
  "cluster_senders": [1234, 5678, 9012],
  "attacker_senders": [5678],
  "attack_family": "collaborative_semantic_agreement",
  "injection_strategy": "multi_source_collaborative",
  "transformation_rule": "...",
  "semantic_objective": "...",
  "expected_trust_layer": "B3+CP",
  "expected_decision_per_message": {"stbv2-000001-5678-000": "CAUTION", ...},
  "severity": "medium",
  "seed": 1300001,
  "messages": [ ... real+transformed canonical CAM messages, timestamp order ... ],
  "_veremi_provenance_per_sender": { "1234": {...}, "5678": {...}, "9012": {...} }
}
```

## What this design does NOT do (honesty notes)

- It does not alter VeReMi's own kinematics — identical honesty contract
  to v1 (`DATASET_INTEGRATION.md`).
- It does not claim CP will show any effect until the blocking
  prerequisite fix lands and is independently re-validated.
- It does not replace v1 — v1 remains the correct benchmark for
  "how does the architecture behave on independent, unrelated single
  messages" (a real deployment scenario: not every message arrives with
  known trajectory history). v2 is a second, complementary benchmark for
  "how does the architecture behave on real, continuous multi-vehicle
  traffic," not a superset that invalidates v1.

## Prototype status and results

The prototype (`stbv_bench/build_stbv_bench_v2.py`) was run at 150 windows /
5,062 messages (ConstPos_1416 alone; 261 eligible windows exist in that one
source dataset). Results: `results/stbv_bench_v2/` (raw per-message CSV,
window JSONL with full provenance, `analysis_summary.json`).

**Headline result — every previously-weak family improved, none regressed:**

| Family | v1 recall (n=10,000) | v2 recall (n as noted) | Δ |
|---|---|---|---|
| goal_manipulation | 0.01 | 0.76 (n=33) | +0.75 |
| indirect_prompt_injection | 0.02 | 0.62 (n=32) | +0.60 |
| semantic_narrative_poisoning | 0.09 | 0.62 (n=53) | +0.53 |
| multi_message_context_poisoning | 0.02 | 0.54 (n=13) | +0.52 |
| traffic_efficiency_lure | 0.01 | 0.50 (n=56) | +0.49 |
| context_poisoning | 0.50 | 0.92 (n=26) | +0.42 |
| role_manipulation | 0.54 | 0.88 (n=25) | +0.34 |
| planner_manipulation | 0.55 | 0.88 (n=33) | +0.33 |
| temporal_context_drift | 0.54 | 0.81 (n=27) | +0.27 |
| mixed_semantic_attacks | 0.02 | 0.24 (n=45) | +0.22 |
| hazard_amplification | 0.42 | 0.54 (n=41) | +0.12 |
| context_inversion | 0.65 | 0.71 (n=68) | +0.06 |
| (8 families already at 1.00 in v1) | 1.00 | 1.00 | +0.00 |

**Root cause, confirmed by direct text inspection** (not assumed): v1's
`synthesize_message()` output for an isolated single message always ends
with the literal sentence `"No other vehicles in cooperative cluster."`;
v2's genuine multi-vehicle windows instead produce real
`"Cluster peer N, (station ..., type=...), position=..., distance=... m
from ego, ..."` sentences describing the actual co-located traffic. The
exact same injected payload sentence is classified far more reliably by
B3 when embedded in this richer, more realistic scene description.

**Two honest interpretations, not yet distinguished (flagged, not
resolved):**
1. v1 may have systematically under-estimated real-world detection
   performance for these families, since real V2X traffic essentially
   never consists of a single, permanently isolated vehicle — v2's
   numbers would then be the more deployment-representative estimate.
2. B3's own training-data distribution may itself have been skewed toward
   "populated scene" phrasing (matching `semantic_evaluation`'s existing
   corpus conventions, which always include cooperative-cluster context),
   in which case v1's isolated-message phrasing was partly
   out-of-distribution for B3 rather than a harder-but-fair test.
   Distinguishing these requires inspecting B3's actual training corpus
   composition, which is out of scope for this session. **The manuscript
   should report the v1→v2 delta as an observed, reproducible fact and
   flag this open question explicitly, rather than picking an
   explanation without evidence.**

Narrative-evolution and progressive-poisoning injection (strategies 3-4 in
the design above) are specified but not yet implemented; the same
`generator.py`-reuse pattern extends directly to them, left as a future
increment. CP's `cp_confidence` was confirmed exactly `1.0` on all 5,062
messages despite `cp_num_reports` reaching 212 — a third, independent
confirmation of the wiring bug in `VERIFICATION_ADDENDUM.md`, still not
fixed this session.
