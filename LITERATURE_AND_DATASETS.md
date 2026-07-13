# Literature Positioning & Dataset Plan (Parts 2 and 4)

All citations below were verified against live sources during preparation
(arXiv/IEEE/ACM/dataset sites). No invented references. Where I could not
verify a detail (e.g., a license), it is marked VERIFY rather than asserted.

---

## Part 2 — Where this work sits in the literature

### 2.1 The evaluation methodology used by the closest field (misbehavior detection)

The misbehavior-detection (MBD) literature converged on a shared methodology
after van der Heijden et al. introduced **VeReMi** (SecureComm 2018,
arXiv:1804.06701): simulated V2X message logs with per-message ground-truth
labels, evaluated via precision/recall (and later F1/accuracy/ROC-AUC), with
explicit per-attack-type breakdowns. **VeReMi Extension** (Kamel et al.,
IEEE ICC 2020) added a sensor-error model, more attack types (DoS, constant/
random position, disruptive, data replay, traffic Sybil, eventual stop) and
~4.4M samples; **VeReMi NextGen** (Hermann et al., IEEE VNC 2026,
veremi-dataset.github.io) adds Eclipse MOSAIC/SUMO/OMNeT++ generation,
urban+highway conditions and predefined train/val/test splits.

Key methodological takeaways this repository already matches:
per-message labels, per-attack-family metric breakdown, seeded generation.
Key gaps relative to that literature (all fixable): (a) results on a
*recognized* dataset, not only self-generated scenarios; (b) comparison
against at least the standard plausibility-check baselines (VeReMi's own
acceptance-range-threshold and speed-check baselines are the canonical
ones — notably, the original VeReMi paper's conclusion is literally that
"fusion can lead to better results," which is a direct motivation citation
for this work's fusion-centric contribution).

### 2.2 Evidence fusion lineage

Subjective-logic / DS-theoretic fusion for V2V misbehavior detection is
established: Dietzel, van der Heijden, Decke, Kargl, "A flexible,
subjective logic-based framework for misbehavior detection in V2V
networks" (IEEE WoWMoM 2014). This is the closest prior fusion framework
and MUST be cited and differentiated. Differentiation available to this
work: (1) fusion here spans a *semantic* (LLM) evidence source, which the
2014-era work could not have; (2) the Yager-vs-Dempster choice under
high-conflict security evidence is explicitly motivated and tested
(Zadeh's counterexample regime), with an ablation of the fusion rule
itself possible. The paper should also cite Yager (Information Sciences,
1987) and Smets & Kennes' pignistic transform (Artificial Intelligence,
1994) for the exact operators used — both already documented in
`trust_engine/dempster_shafer.py`.

### 2.3 The novelty position (be precise, not broad)

The defensible claim is NOT "a new trust architecture" (layered
PKI→MBD→fusion stacks exist) and NOT "LLM anomaly detection" (crowded).
The defensible claim is the **STBV threat class + the demonstration that a
semantic layer catches attacks that are jointly invisible to
crypto+behavioral+consistency layers, fused with principled conflict
handling**. Everything in the evaluation should serve exactly that claim.
The strongest available evidence artifacts in this repo for it: the
flagship two-stage scenario, the Phase-B V2X-grounded semantic attack set,
and the McNemar-tested full-vs-no_b3 ablation (which REQUIRES a GPU run to
be meaningful — see the manifest warnings).

### 2.4 What reviewers at the named venues will demand (from the field's norms)

1. Evaluation on VeReMi/VeReMi-Extension (or a stated reason why not).
2. The two canonical plausibility baselines + at least one ML baseline.
3. Multi-seed results with CIs (framework now does this).
4. Adaptive-attacker discussion: what does an attacker who KNOWS about B3
   do? (The template-sensitivity work in
   `validation/run_b3_b6_synthesizer_robustness.py` is the seed of this.)
5. Latency justified against ETSI CAM rates (10 Hz): the stack's non-B3
   stages are sub-millisecond (measured); B3's inference latency on real
   hardware is THE deployment-critical number and must be reported from a
   GPU run, batch and single.

---

## Part 4 — Dataset plan

### 4.1 Honest correction on dataset fit

The mandate prioritizes OPV2V / DAIR-V2X / V2X-Sim / V2X-Set. Those are
**perception datasets** (LiDAR/camera frames, 3D boxes) for cooperative
*object detection*. This repository's stack consumes **CAM-style trust
messages with per-message misbehavior labels** — which is exactly what the
**VeReMi family** provides and what the MBD literature evaluates on.
Recommendation: make VeReMi Extension the primary external dataset;
use OPV2V-class data only for the CP layer's realism (deriving message
streams from its scenario trajectories), clearly labeled as derived.

### 4.2 Dataset table

| Dataset | Paper / venue | What it provides | Access | Fit | Limitations |
|---|---|---|---|---|---|
| **VeReMi** | van der Heijden, Lukaseder, Kargl, SecureComm 2018 (arXiv:1804.06701) | Simulated BSM logs, ground-truth misbehavior labels, 5 position-attack types, 3 densities (LuST + VEINS) | veremi-dataset.github.io (public; license: VERIFY on site) | Direct: message-level trust evaluation | Position-attacks only; 2018-era realism |
| **VeReMi Extension** | Kamel et al., IEEE ICC 2020 | +sensor error model, 9+ attack types incl. DoS, replay, Sybil, eventual stop; ~4.4M samples (F2MD/VEINS/LuST) | veremi-dataset.github.io (public; license: VERIFY) | Direct; replay/Sybil families map 1:1 to this repo's scenario families | Still simulation; single city scenario |
| **VeReMi NextGen** | Hermann et al., IEEE VNC 2026 | MOSAIC/SUMO/OMNeT++, urban+highway, density + driver-profile diversity, predefined splits | veremi-dataset.github.io | Direct; best-practice splits | Very new; fewer published comparison points |
| **OPV2V** | Xu, Xiang, Xia, Han, Li, Ma, ICRA 2022 (DOI 10.1109/ICRA46639.2022.9812038) | 11,464 frames, 232,913 3D boxes, 73 scenes, CARLA + digital Culver City; OpenCOOD toolchain | Google Drive via github.com/DerrickXuNu/OpenCOOD | Indirect: source of realistic multi-vehicle *trajectories* from which CAM streams can be derived for CP-layer realism | Perception dataset — no misbehavior labels; any trust labels would be injected by us (must be labeled synthetic-on-real-trajectories) |
| **DAIR-V2X** | Yu et al., CVPR 2022 | Real vehicle-infrastructure cooperative 3D detection data | thudair website (registration; China-hosted; license: VERIFY) | Indirect (same as OPV2V, adds real-world V2I) | No trust labels; access friction |
| **V2X-Sim** | Li et al., IEEE RA-L 2022 | Multi-agent simulated perception benchmark | ai4ce.github.io/V2X-Sim | Indirect | Same as above |

### 4.3 Required preprocessing (VeReMi Extension → this repo)

VeReMi logs are per-vehicle JSON traces of received BSMs
(pos/speed/heading/time + attacker type ground truth). Mapping needed:
BSM → this repo's CAM-subset schema (`bridges/message_adapter.to_flat_report`
already consumes almost exactly VeReMi's field set — sender, x, y, speed,
heading, timestamp), so an importer is a ~100-line adapter: group receiver
logs into windows, map `attackerType != 0` → `is_attacker`, preserve the
official train/test split where present (NextGen). This importer is the
single highest-value next engineering task and requires the dataset
download (network), so it could not be built-and-verified in this sandbox;
build it against the real files rather than a guessed schema.

### 4.4 Synthetic/real separation rule (per mandate)

Every results table must carry a `data_source` column ∈
{`self_generated_synthetic`, `veremi_extension`, `derived_from_opv2v`},
and no aggregate may pool across sources. The manifest's dataset
fingerprints (already implemented) make each table's provenance checkable.
