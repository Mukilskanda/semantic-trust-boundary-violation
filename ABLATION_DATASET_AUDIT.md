# ITE-Bench Dataset Quality Audit

Quality audit of the Integrated Trust Evaluation Benchmark (ITE-Bench, `ite_bench/data/ite_bench.jsonl`) performed before any evaluation run, per the "verify before evaluate" requirement.

## 1. Composition

- **n = 9,900** total samples (layer targets of ~3,300 hit exactly; a small shortfall from the nominal 10,000 target is disclosed, not padded).
- **Balance**: B1 3,300 / B2 3,300 / B3 3,300 (exactly even, by construction).
- **Label balance**: 7,425 attack samples (75.0%) / 2,475 benign (25.0%) — a deliberately attack-heavy split matching STBV-Bench v1's own convention (70.07%/29.93%) rather than a claimed operational prevalence; FPR, not precision, should anchor deployment-relevance reading of this benchmark, consistent with how the paper already treats STBV-Bench v1.
- **Family balance within each layer**: roughly even (9 B1 families ≈275 each, 7 B2 families ≈353 each, 6 B3 families ≈412 each, plus 825 benign per layer) — verified by direct count, not assumed.

## 2. Duplicate and leakage checks

- **Exact-duplicate message windows**: 0 of 9,900 (SHA-256 over each sample's full serialized message list).
- **B3 text leakage against v2.5b** (the held-out evaluation benchmark used elsewhere in this paper): **0 overlapping texts** — critical, since any overlap would silently contaminate v2.5b's status as a genuinely unseen evaluation set.
- **B3 text leakage against v2.5** (training corpus): **0 overlapping texts**.
- **B3 text leakage against v2.5c** (training-augmentation corpus, itself never used for evaluation elsewhere): **1 coincidental exact match** out of 2,478 unique ITE-Bench B3 texts — a single combinatorial coincidence from independently sampling the same slot-filling template bank with a different seed, not a systematic leakage mechanism. This does not compromise ITE-Bench's validity as an ablation benchmark (it was never intended as a held-out generalization test — v2.5b already serves that role), but is disclosed rather than silently ignored.

## 3. A real bug found and fixed during this audit (not merely disclosed after the fact)

The first draft of the B2-focused window generator used near-zero position deltas between consecutive messages for **both** attack and benign windows — realistic for the deliberate attack case (a vehicle claiming a speed its GPS displacement doesn't support is itself a valid MBD-detectable pattern), but a genuine defect for benign windows, where it would have spuriously triggered MBD's "constant position vs. claimed speed" check on **legitimate** traffic, inflating benign-class false positives for reasons having nothing to do with the ablation study's actual question. Caught during the smoke-test pass (`ite_bench/smoke_test.py`) before any full evaluation run: benign B2 windows showed `CAUTION` with spurious "Constant Position check" evidence. **Fixed** by adding a kinematically-consistent displacement helper (`_advance_position()`, real-world meters-to-ETSI-fixed-point conversion) and applying it to all benign window generation; re-verified post-fix that benign B2 windows now correctly `ACCEPT` with zero evidence entries.

## 4. ETSI/CAM plausibility

All messages use the repository's native nested CAM schema (matching `data/stbv_bench/v1`'s own `transformed_message` shape exactly): real ETSI station-type codes (5=passengerCar, 15=roadSideUnit), real message-type codes (1=CAM, 5=MAPEM, 6=SPATEM, 7=SREM, 28=RTCMEM), 1e-7-degree fixed-point coordinates, 0.01 m/s speed units, 0.1-degree heading units. B1-focused attack samples deliberately violate these bounds (that is the point of testing B1's plausibility checks); B2/B3-focused samples and all benign samples stay within realistic bounds by construction, confirmed by the smoke test.

## 5. Correct labels

Each sample's `is_attacker` label matches its generator's intent by construction (attack generators always emit `True`, benign generators always `False`); spot-verified via the smoke test that intended-malicious samples produce non-`ACCEPT` decisions and intended-benign samples produce `ACCEPT` under the full-stack configuration, for every one of the 22 attack families plus benign controls sampled.

## 6. What this audit does NOT claim

- ITE-Bench's B2 windows are synthetic constructions, not real vehicular trajectories (unlike STBV-Bench v1's VeReMi-derived kinematics or the VeReMi companion benchmark). This is a scope limitation stated in `ABLATION_AUDIT.md` §5, not resolved here.
- This audit verifies internal consistency and non-leakage; it does not independently verify that every synthetic B1/B2 attack is representative of a real-world attacker's full capability (e.g., a real certificate-chain attack would involve actual cryptographic material this codebase does not implement/verify — see `ABLATION_AUDIT.md`'s note on B1's real, checkable scope).

## Verdict

**Suitable for the ablation study it was built for.** Zero duplicates, zero leakage against the held-out v2.5b set, balanced across layers and families, one real bug found and fixed before evaluation (not after), and every family confirmed to produce its intended layer-appropriate signal via direct smoke test.
