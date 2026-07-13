# Code Audit & Standards Compliance Report
## Semantic Trust Boundary Violation (STBV) Repository

**Scope:** Parts 1 and 3 of the publication-readiness mandate. Everything in
this document is grounded in direct inspection of the repository as uploaded
(102 Python files, ~33,400 lines). No claim below is speculative; each cites
the file it was verified in.

---

## PART 1 — IMPLEMENTATION MAP AND AUDIT

### 1.1 Implementation map (module → responsibility → size → status)

| Module | Responsibility | Lines | Status |
|---|---|---|---|
| `pki/` | SCMS-style CA simulation, RSA-PSS sign/verify | 150 | Active, minimal |
| `b1_scsv/` | B1: stateful cryptographic/structural validation (SCSV) | 4,928 | Active, largest single layer |
| `mbd/` | Misbehavior detection over flat kinematic reports | 351 | Active |
| `b2_explain/` | B2: explainability + trust evidence blending | 416 | Active |
| `b2_csia/` | **Legacy** CSIA implementation (superseded by b2_explain) | 7,646 | Deprecated; imported only by legacy validation scripts |
| `cp/` | Cooperative perception fusion (spatial/speed/heading/diversity) | 165 | Active |
| `pipeline/` | Orchestrator, synthesizer (3 templates), B3 bridge | 5,106 | Active |
| `trust_engine/` | DS/Yager fusion, policy, models | 602 | Active (fusion rewritten this cycle) |
| `adapters/` | Logging/API/DS-MASS output adapters | 218 | Active |
| `bridges/` | ETSI-CAM → flat-report projection (`to_flat_report`) | 171 | Active, load-bearing |
| `contracts/` | `TrustEvidence` shared view (B1/MBD/CP → B2) | 100 | Active, clean |
| `scenario_generation/` | Seeded, parameterized held-out scenario generator | 635 | Active |
| `simulation/` | Simulation dispatcher | 183 | **Orphaned** — zero imports from anywhere else in the repo |

### 1.2 Verified weaknesses

**W1 — 7,646 lines of deprecated code shipped in the artifact (`b2_csia/`).**
Only legacy `validation/run_phase2_*.py` scripts import it; the pipeline does
not. A reviewer diffing "architecture described in paper" vs "code in repo"
will find an entire second explainability subsystem. Recommendation: move to
`legacy/` with a README, or excise for the artifact release. Do NOT delete the
phase-2 validation scripts' history silently — they document B2's lineage.

**W2 — `simulation/` is orphaned.** No module imports it (verified by grep).
Either wire the final Dispatcher stage into the orchestrator's adapter output
(the architecture diagram claims Simulation/Decision Dispatcher as the last
stage) or exclude it from the artifact. As-is it is an unimplemented claim.

**W3 — In-memory-only PKI.** `pki/pki_layer.py` is an explicit simulation
(single in-memory CA, no certificate chains, no CRL distribution, no
IEEE 1609.2 pseudonym certificates, no butterfly key expansion). Fine for a
research artifact **if the paper says so**; a silent gap otherwise. The
"compromised but not revoked" state is a genuinely good modeling choice —
keep it and feature it in the threat model section.

**W4 — MBD constants are hardcoded, not context-aware** (`mbd/mbd_layer.py`:
`MAX_ACCEL=6.0`, `MAX_SPEED_KMH=180`, `MAX_HEADING_RATE=90`). The B1 layer
has context-adaptive envelopes; MBD does not. A highway scenario at
185 km/h (legal in Germany) would be flagged. Not fatal, but an
inconsistency reviewers who read both layers will notice.

**W5 — `MAX_HISTORY = 5` in MBD.** Behavioral evidence quality saturates
after 5 messages per sender. All temporal reasoning (replay, sybil,
collusion) operates over an extremely short horizon. This bounds the
sophistication of detectable behavioral attacks and should be stated as a
limitation and/or swept as a parameter (the new sweep framework in
`evaluation/` supports this).

**W6 — CP weighting scoping limitation** (documented in
`pipeline/orchestrator.py`'s docstring, confirmed in code): only the target
sender's CP observation weight comes from real B1+MBD+B2 evidence; all peers
default to weight 1.0. This means a collusion ring's *other* members are
fused at full weight. Honest and documented, but it materially weakens the
CP-poisoning defense claims — the paper must scope its CP claims accordingly.

**W7 — MBD state is per-pipeline-instance and unbounded across senders.**
`VehicleHistoryStore` grows with every new station_id, no eviction. A Sybil
flood is therefore also a memory-exhaustion vector against the detector
itself. Scalability bottleneck at fleet scale; acceptable at evaluation
scale; state it.

**W8 — Latency accounting is wall-clock `perf_counter` around stages with
shared mutable state.** Single-threaded assumption everywhere (SCSV state,
MBD history, CP fusion). No thread-safety anywhere. Fine for the evaluation;
must be listed as a deployment limitation.

**W9 — Mathematical: fusion input independence.** Yager/DS combination
assumes independent evidence sources. B1's score and MBD's scores are *not*
independent (both derive from the same kinematic fields), and CP's
target-sender weight is derived from B2's calibration which already blends
B1+MBD. The current architecture mitigates this by folding MBD/CP into ONE
crypto/structural mass (so DS combination happens only between two
plausibly-independent frames: structural evidence vs semantic evidence) —
this is defensible, and the paper should state exactly this argument, but a
reviewer WILL ask. Do not claim more than two-source independence.

**W10 — Duplicated kinematic thresholds.** B1's context envelopes, MBD's
constants, and `scenario_generation`'s context parameters each encode their
own notion of plausible speed/acceleration. Three places to update, no
shared constants module. Code smell; consolidation candidate post-paper.

### 1.3 Hidden assumptions (verified)

1. **One target message per `run()` call** — window's last message is the
   only one fully validated; peers are context (documented, but every
   experiment design must respect it — the evaluation framework below does).
2. **`is_attacker` ground truth is message-level, not event-level.** A
   collusion attack's harm is the *joint narrative*; per-message labels
   under-credit detection that fires on the cluster.
3. **Timestamps:** fixtures use absolute epoch in `generation_delta_time` —
   see Part 3 (this is a standards deviation with real consequences: the
   benign fixtures now trip B1's staleness check purely from file age).
4. **B3 label space** is assumed binary-normalizable
   (`MALICIOUS_SEMANTIC_MANIPULATION` → `MALICIOUS`); multi-class attack
   typing is not surfaced to fusion.

---

## PART 3 — STANDARDS COMPLIANCE AUDIT (ETSI EN 302 637-2 / SAE J2735 / IEEE 1609)

Message schema verified against `scenarios/*/msg_*.json` and
`scenario_generation/generator.py`.

### 3.1 What is present and conformant in spirit

- ITS PDU header with `station_id` (EN 302 637-2 `StationID`) ✓
- `generation_delta_time` field exists ✓ (semantics deviate — below)
- `basic_container.station_type` uses genuine ETSI `StationType` codes
  (5=passengerCar, 8=heavyTruck, 4=motorcycle, 15=roadSideUnit) ✓
- `reference_position.latitude/longitude` in 1e-7 degree integer units
  (matches ETSI `Latitude`/`Longitude` encoding) ✓
- `high_frequency_container` with speed (cm/s), heading (0.1°), yaw rate,
  steering wheel angle, lateral/longitudinal acceleration ✓ — unit choices
  match ETSI value ranges.

### 3.2 Deviations from EN 302 637-2 (CAM) — ranked by evaluation impact

**S1 (HIGH, causes real measurement error today):
`generation_delta_time` semantics.** ETSI defines GenerationDeltaTime as
`TimestampIts mod 65536` (milliseconds, wrapping ~65.5 s). Fixtures store
either absolute epoch seconds or small floats. Consequence already observed
in this audit cycle: `test_messages/benign/*.json` fail B1's staleness check
purely because the files are days old — i.e., **evaluation results on those
fixtures partially measure file age, not detector quality.** Fix options
(choose one, document it): (a) make the generator emit true mod-65536
values and update B1's staleness logic to wrap-aware comparison; (b) declare
repository time semantics explicitly ("relative seconds from scenario
start") and regenerate fixtures. Option (b) is smaller and evaluation-safe.

**S2 (MEDIUM): missing mandatory BasicContainer/HF fields.** No
`protocolVersion`, no position `confidenceEllipse`
(`semiMajorConfidence` etc.), no `altitude`, no `driveDirection`, no
`vehicleLength`/`vehicleWidth`, no `curvature`. None are load-bearing for
the trust stack's logic, but "CAM-compliant" cannot be claimed in the paper
without either adding them (generator-only change, defaults per ETSI
"unavailable" sentinel values) or wording the claim as "CAM-inspired subset."

**S3 (MEDIUM): no DENM/CPM message types.** The Phase-B semantic attack
scenarios *narratively reference* DENM cause codes in synthesized text, but
no actual DENM (EN 302 637-3) or CPM (TS 103 324) structured messages exist.
For the STBV story (false road closure, emergency abuse) real DENM structures
would materially strengthen the claim that attacks are standards-plausible.

**S4 (LOW): no IEEE 1609.2 security envelope.** Signatures are detached
RSA-PSS over canonical JSON rather than 1609.2 SignedData with ECDSA and
pseudonym certs. Acceptable simulation choice; must be a stated limitation
(RSA vs ECDSA also changes the latency numbers you report for PKI).

**S5 (LOW): replay protection.** B1 does detect repeats, but ETSI-style
protection is timestamp-window + sequence-based; the current check is
content-similarity-based. Different mechanism, overlapping goal — describe
what is actually implemented rather than citing the standard's mechanism.

### 3.3 Recommended minimal generator update (preserves architecture)
Add ETSI-default values for the S2 fields in
`scenario_generation/generator.py` **only** (single function, additive keys;
B1/MBD/bridges ignore unknown keys — verified `to_flat_report` reads a fixed
key set). Adopt option (b) for S1 with a `time_semantics` note written into
every generated scenario's manifest. Both changes are additive and cannot
regress existing consumers.

---

*Prepared as Parts 1 and 3 of the evaluation-framework mandate. Parts 5–12
are implemented under `evaluation/` (see `evaluation/README.md`); Part 13
critique is in `PAPER_READINESS_CRITIQUE.md`.*
