# Ablation Audit: Why the Original Ablation Made B1/B2 Look Useless

This audit was performed before building any new benchmark or rerunning any evaluation, to determine whether B1/B2's near-zero contribution on STBV-Bench v1 reflects a real weakness, a benchmark-scope limitation, or an evaluation-protocol bug. **It found both a benchmark-scope limitation (already known) and a previously-undiscovered evaluation-protocol bug**, the latter more consequential than the former.

## 1. Attack taxonomy and responsible layer

| Threat class | Responsible layer | Real, checkable trigger in this codebase |
|---|---|---|
| Certificate/identity/structural violations, replay, out-of-range physical values | **B1 (SCSV)** | `b1_scsv/scsv.py::check_stateful()`: missing mandatory fields, negative/stale timestamps, replay-cache hits, certificate-rotation churn (>3 rotations/60s), out-of-range lat/lon/speed/accel/heading (fatal per `isce_config.yaml`), station_type×message_type policy violations |
| Kinematic implausibility, temporal/behavioral inconsistency, Sybil, collusion | **B2 (MBD + CSIA)** | `mbd/mbd_layer.py::mbd_layer()`: speed >180 km/h, acceleration/heading-rate jump beyond threshold, position-vs-claimed-speed inconsistency, Sybil (near-identical position from a different sender within 1s), collusion (≥1 other sender reporting the same `event` within 5s/100m), replay (duplicate timestamp) |
| Meaning-level manipulation with no kinematic or structural signature | **B3 (Semantic Trust Gate)** | Free-text scene content read by the fine-tuned classifier |

## 2. Current coverage on STBV-Bench v1

STBV-Bench v1 attacks **only** the semantic layer by explicit threat-model construction (paper §III): "The adversary holds valid or compromised-but-unrevoked credentials sufficient to pass PKI and structural validation... deliberately generous at the communication and behavioral layers, isolating the semantic gap by construction." Concretely:
- **B1 attacks currently never triggered on STBV-Bench v1**: no sample carries an invalid certificate, malformed field, replay, or out-of-range kinematic value. This is intentional benchmark scoping, not an oversight — v1 exists to isolate B3.
- **B2 attacks currently never triggered on STBV-Bench v1**: real VeReMi kinematics are carried through unmodified; the semantic transformation only touches free text. B2's own genuine kinematic-attack coverage exists elsewhere (the VeReMi kinematic companion benchmark, paper §VI.C), not in v1.
- **B3 is the only layer STBV-Bench v1 exercises**, by design.

**Conclusion for B1's "near-zero" ablation row**: this is a real, previously-explained benchmark-scope limitation (already stated in the paper's threat model), not a defect. Confirmed independently: B1's own unit test suite (`b1_scsv/test_bad_actors.py`, `test_scsv.py`, `test_b1_limitations.py`) — 137/137 passing — exercises exactly the attacks STBV-Bench v1 excludes, and B1 correctly blocks every one.

## 3. A second, previously-undiscovered cause: the evaluation protocol itself

This is the audit's more significant finding. Even setting benchmark scope aside, **the ablation harness used to produce Table I (`rerun_ablation_configs45_*.py`) cannot exercise B1's or MBD's history-dependent checks even if the benchmark contained history-dependent attacks**, for a structural reason found by direct code inspection:

- Each sample gets a **fresh `ISCEPipeline` instance**, so MBD's `VehicleHistoryStore` starts empty every time.
- `pipeline.run(messages)` only ever feeds `messages[-1]` (the target) through B1 (`orchestrator.py` line 344: `b1_res = self.scsv.check_stateful(target_msg, ...)`) — earlier messages in a passed-in window are **never** validated by B1 at all.
- `orchestrator.py::_run_mbd()`'s pre-population of MBD history from `peer_messages` explicitly **skips messages from the same sender as the target** (`if peer_flat["sender"] == target_sender: continue` — this path exists only for cross-sender Sybil/collusion context, not same-vehicle temporal history).

**Consequence**: B1's replay cache and certificate-rotation tracking, and MBD's per-sender kinematic/temporal history, can only ever see a message's own immediately-preceding history if that history was fed through the **same persistent pipeline instance** via **sequential single-message `.run()` calls**, in chronological order — exactly the "stateful per-vehicle replay" protocol the paper already uses for the VeReMi companion benchmark (§VI.C), but **not** the protocol the STBV-Bench v1 ablation harness uses.

This means: even a benchmark containing genuine B1/B2-triggering attacks would still show near-zero B1/B2 contribution under the *old* harness, for a reason unrelated to either layer's actual detection capability. This was confirmed empirically during benchmark construction (see `ABLATION_DATASET_AUDIT.md` §2): an early draft of the new benchmark's B2-focused windows, evaluated with a single `pipeline.run(full_window)` call, showed MBD detecting nothing (`mbd_evid=1`, cold-start boilerplate only) on samples specifically constructed to trigger MBD's kinematic checks. Switching to sequential per-message calls on one persistent pipeline (matching the VeReMi companion protocol) immediately produced the expected detections with real evidence strings (e.g. `"Speed out of bounds: 240.66 km/h (limit: [0, 180.0])"`, `"Replay check: Duplicate message timestamp 5000.0 detected."`, `"Sybil check: Co-located vehicle identity '103451' reported position within 0.03m."`).

## 4. What this means for the ablation study

- STBV-Bench v1's ablation (Table I) remains **valid for what it measures**: it correctly shows that a benchmark built to contain only semantic attacks is detected only by the semantic layer. This is not wrong; it is scoped narrowly, and the paper already says so.
- It is **not** valid evidence that B1/B2 are weak or poorly implemented components of the architecture — the ablation study never gave them a threat class or an evaluation protocol capable of exercising them.
- **New benchmark and new harness required, together**: a benchmark containing genuine B1/B2 attacks (Part 2 below) evaluated under the *same* stateless-per-sample protocol as before would still show near-zero B1/B2 contribution, for the protocol reason above, not a benchmark-content reason. Both were fixed together for this pass (`ite_bench/build_ite_bench.py` + `ite_bench/run_ite_ablation.py`).

## 5. Missing coverage this pass closes, and what remains open

**Closed by ITE-Bench**: B1-focused single-message attacks (structural, kinematic-plausibility, identity-policy, certificate-rotation, replay) and B2-focused windowed attacks (kinematic jump, Sybil, collusion, temporal replay pattern), evaluated under a sequential stateful protocol that lets both layers' real detection logic fire.

**Still open, disclosed not fabricated as solved**:
- ITE-Bench's B2 windows are synthetic (constructed kinematic sequences), not drawn from real vehicular trajectory data the way STBV-Bench v1 and the VeReMi companion benchmark are. This is a genuine limitation: it demonstrates the mechanism works, not that it generalizes to real-world driving kinematics at the same fidelity as VeReMi-derived data.
- Cross-source (multi-vehicle) B2 attacks (Sybil, collusion) use only 2-4 synthetic vehicles per window; a larger, denser multi-vehicle scene (closer to the paper's existing CP full-evaluation corpus, §VI.D) was not attempted here.
- B1's identity-spoofing check is a *recoverable* penalty in this implementation, not a fatal one (confirmed by code inspection: `is_policy_blocked` affects `validation_score`, categorized as "Step 6: Rule-table check (Recoverable)" in `scsv.py`) — so spoofed-identity samples correctly produce Caution, not Reject, and this should not be reported as a B1 "miss."
