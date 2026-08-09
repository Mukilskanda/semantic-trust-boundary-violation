# Result Sanity Audit (this pass, scoped)

Checked the one raw dataset directly examined in this pass — the CARLA
final-checkpoint JSON (400 messages):
- n=400 matches manuscript's stated n=400. No duplicate message IDs sampled
  for the fields checked. Per-scenario n=40 uniformly, matching the design
  (10 scenarios x 40 messages).
- No 1.000/perfect suspicious values found in the recomputed numbers used
  (mean latency 76.61 ms; scenario decision counts all traced to plausible,
  non-degenerate distributions — e.g. `goal_manipulation` is 11 Reject/29
  Caution/0 Accept, not a suspicious all-one-class result).
- `authority_override`/`false_hazard_clearance` both 40/40 REJECT — verified
  the underlying `b3_label` is genuinely MALICIOUS-driven for these (not
  just B1-driven), consistent with the manuscript's claim.
- `sybil_attack`/`semantic_manipulation` 40/40 REJECT but B3 label BENIGN in
  all cases — matches the manuscript's disclosed "B3-invisible, MBD backstop"
  claim; no contradiction.
- The three benign-but-Rejected scenarios were investigated further (see
  `CARLA_FALSE_POSITIVE_ROOT_CAUSE.md`) rather than accepted at face value —
  this is the one "looked suspicious, investigated before accepting" case in
  this pass.

Not checked in this pass: v2.5b/ITE-Bench/VeReMi raw CSVs for leakage,
duplicate templates, or class-imbalance artifacts — these were not
re-examined; the manuscript's prior audit trail (`LEXICAL_LEAKAGE_ANALYSIS.md`,
`ABLATION_DATASET_AUDIT.md`, `BENCHMARK_REDESIGN.md`) already exists in-repo
from earlier sessions and was not reproduced here.
