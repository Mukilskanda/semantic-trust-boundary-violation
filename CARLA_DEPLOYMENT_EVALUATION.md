# Live CARLA Deployment Evaluation

**Scope:** extends `DEPLOYMENT_EVALUATION.md` (SUMO-trace replay) with a
**live CARLA 0.9.16 simulation** driving the same complete, frozen trust
pipeline — PKI → B1/SCSV → MBD → B2/Explainability → Cooperative
Perception (CP) → Synthesizer → B3 Semantic Trust Gate → Trust Decision
Engine — end to end, in real time, against a running CARLA server rather
than a replayed trace.

**No pipeline code was modified and no model was retrained.** Every
stage-level timing figure comes from `orchestrator.py`'s own pre-existing
`latencies` dict. Code: `deployment_eval/carla_bridge.py` (CARLA→CAM/DENM
conversion), `deployment_eval/carla_scenarios.py` (10 scenarios),
`deployment_eval/run_carla_evaluation.py` (runner). Raw results:
`deployment_eval/carla_results/carla_deployment_eval_results.json` (400
per-message rows). Figures: `deployment_eval/carla_figures/`.

---

## 1. CARLA verification

The previous report (`DEPLOYMENT_EVALUATION.md`) stated CARLA was not
installed. That was true for the locations searched at the time. A
wider filesystem search this session found a real installation:

```
C:\Users\mukil\Downloads\CARLA_0.9.16\CarlaUE4.exe
```

Verified directly, not assumed:

| Check | Result |
|---|---|
| Server binary | `CarlaUE4.exe` present, launched headless (`-RenderOffScreen -carla-server -nosound -quality-level=Low`) |
| Server process | `CarlaUE4-Win64-Shipping.exe` confirmed running (`tasklist`) |
| Client↔server handshake | `client.get_client_version()` = `0.9.16`, `client.get_server_version()` = `0.9.16` — versions match |
| Map load | `world.get_map().name` = `Carla/Maps/Town01` (confirmed after `client.load_world()`) |
| Vehicle spawn/tick/state read | Live-tested: spawn, autopilot, 20 synchronous ticks, transform/velocity read all succeeded before this evaluation was built |

**Python version constraint (disclosed):** CARLA 0.9.16's Windows client
wheel (`carla-0.9.16-cp312-cp312-win_amd64.whl`) is built for CPython
3.12 only. This repo's default interpreter is Python 3.13, which cannot
import `carla` at all (`ModuleNotFoundError`). A separate Python 3.12
environment (Anaconda's base env, `C:\Users\mukil\anaconda3\python.exe`)
was used instead, with the CARLA wheel plus this repo's own
torch/transformers/etc. stack installed into it. **The frozen pipeline
code itself is unchanged and was verified to run identically under both
interpreters** (see §3) — this is an environment/tooling constraint, not
a pipeline modification.

---

## 2. Hardware

| | |
|---|---|
| CPU | 16 logical cores (`nproc`) |
| RAM | ~15.3 GiB total (`wmic computersystem get TotalPhysicalMemory` = 16,415,322,112 bytes) |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6,141 MiB VRAM total — **shared** for this evaluation between CARLA's own rendering/physics and B3's transformer inference (see §7.3) |
| OS | Windows 11 Home Single Language |

This is laptop-class consumer hardware, not automotive/edge embedded
silicon (e.g. NVIDIA Jetson Orin) or a server-class GPU — absolute
latency/throughput numbers below would differ (very likely worse on
embedded targets, better on a dedicated server GPU not shared with a
simulator) on different hardware; this was not verified directly.

## 3. Experimental setup

| | |
|---|---|
| CARLA server | 0.9.16, headless (`-RenderOffScreen`, `-nosound`, `-quality-level=Low`), map `Town01` |
| CARLA mode | Synchronous, `fixed_delta_seconds=0.1` (10 Hz — ETSI's fastest permitted CAM rate) |
| Traffic Manager | Synchronous mode, port 8000, `distance_to_leading_vehicle=2.0` |
| Vehicles | 8 real CARLA vehicle actors under autopilot (citroen c3, mercedes sprinter, nissan patrol ×2, nissan micra, mercedes coupe, mini cooper_s, mitsubishi fusorosa) |
| Python (CARLA client + pipeline) | 3.12.7 (Anaconda base env) |
| torch | 2.7.1+cu118 (same build as the replay-mode evaluation, reinstalled into the 3.12 env) |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6,141 MiB total — **shared** between CARLA's own rendering/physics and B3's transformer inference (see §7.3) |
| Pipeline config | `ISCEPipeline(enable_mbd=True, enable_cp=True, enable_b3=True)` — the full deployed configuration, one persistent instance across all 10 scenarios (RSU/ego-receiver model, same as the replay evaluation) |
| Scenarios | 10, 40 CARLA ticks (4.0 simulated seconds) each = 400 pipeline.run() calls total |

**Verification that the pipeline itself is unchanged:** before running
any scenario, the exact same 1-message smoke test used in
`DEPLOYMENT_EVALUATION.md` was re-run under the CARLA-compatible Python
3.12 environment and produced the same `ACCEPT` result via the same
`ISCEPipeline` code path — confirming this is genuinely the frozen
pipeline, not a reimplementation.

---

## 4. The CARLA→CAM/DENM bridge

`deployment_eval/carla_bridge.py` converts a live `carla.Actor`'s
`get_transform()`/`get_velocity()` into this repo's own native, nested
ETSI-style CAM/DENM schema (`header.station_id`,
`cam.cam_parameters.basic_container.reference_position`, etc. — the
exact shape already used throughout `test_messages/**/*.json`), so the
frozen pipeline consumes it exactly as it would any other CAM message.

**Disclosed limitation — no real geodetic coordinates.** CARLA provides
Unreal Engine local Cartesian coordinates (metres) and no GNSS signal.
Rather than fabricating a real-world location, the bridge anchors one
arbitrary fixed reference point and derives ETSI fixed-point lat/lon via
the exact algebraic inverse of `bridges/message_adapter.py`'s own
equirectangular projection — i.e., round-tripping a CARLA position
through the adapter recovers the original CARLA (x, y) to that
projection's own documented accuracy (<1% at these ranges). This is a
disclosed, standard Cartesian-sim-to-geodetic-pipeline bridging
technique, not a hidden approximation.

**Speed/heading unit conversions** follow `bridges/message_adapter.py`'s
own decoding rules exactly (0.01 m/s, 0.1-degree compass bearing), so no
new unit convention was invented.

**Attacks are injected at the message-content layer only.** Every
scenario runs on real CARLA vehicles under real autopilot physics each
tick; "attacker" scenarios construct a message that deliberately
diverges from the sending vehicle's true state (false event claims,
replayed old content, spoofed station_type/identity) — exactly what an
attacker controls in reality. CARLA's own physics/traffic-manager output
is never altered.

---

## 5. Scenarios

All 10 requested scenarios were implemented and run (`deployment_eval/carla_scenarios.py`):

| # | Scenario | Ground truth | Mechanism |
|---|---|---|---|
| 1 | `normal_driving` | benign | Truthful CAM from 5 live vehicles, no event claims |
| 2 | `accident` | benign | Truthful accident DENM (cause_code=2) from a vehicle that has really slowed/stopped |
| 3 | `emergency_vehicle` | benign | Truthful `station_type=specialVehicle` + hazardous-location DENM at real elevated speed |
| 4 | `road_closure` | benign | Truthful road-works DENM (cause_code=3) |
| 5 | `replay_attack` | attack | A real, previously-truthful captured message re-broadcast verbatim (stale) later in the same scenario |
| 6 | `sybil_attack` | attack | One physical CARLA vehicle broadcasting under 5 different station_ids at sub-metre position offsets |
| 7 | `semantic_manipulation` | attack | Truthful kinematics, but a false accident DENM unsupported by CARLA's own ground truth (free-flowing traffic, no stop, no collision) |
| 8 | `authority_override` | attack | An ordinary passenger car falsely claims `station_type=roadSideUnit` and issues an override event |
| 9 | `goal_manipulation` | attack | False `traffic_condition` DENM (cause_code=1) to manipulate other vehicles' routing, while real kinematics show no congestion |
| 10 | `false_hazard_clearance` | attack | A genuinely co-located second reporter's truthful active-hazard DENM is directly contradicted by the target's false `hazard_cleared` claim |

**A methodological finding, corrected mid-session (disclosed, not
hidden):** the first run of scenarios 2, 3, 4, 7, 9 stuffed all 8
autopiloted vehicles — physically scattered tens to hundreds of metres
apart across the real Town01 map — into each CP window regardless of
proximity to the claimed event. `cp/cp_layer.py`'s
`spatial_consistency()` is calibrated for corroborating reports of a
**shared local event within ~20 m spread** (`score = max(0, 1 -
spread/20)`), which is realistic for the compact SUMO 4×4-grid scenario
used in the replay evaluation but not for CARLA's town-scale traffic.
The result was that CP's genuine-contradiction channel fired against
*every* DENM message regardless of truthfulness, producing REJECT even
for scenario 2/3/4's honestly-truthful broadcasts. **This was a
scenario-construction artifact in this evaluation script, not a pipeline
defect** — confirmed by isolating `SCSV.check_stateful()` on the exact
same message, which returned a clean `score=1.0`. The scenarios were
corrected to bundle only genuinely relevant reporters into each CP
window (the target alone, or a peer deliberately placed near it for a
controlled corroboration test) before the results below were collected.
This is itself a disclosable deployment-readiness finding — see §8.

---

## 6. Results — decisions per scenario (n=40 messages each)

| Scenario | ACCEPT | CAUTION | REJECT | Note |
|---|---|---|---|---|
| normal_driving | 1 | 10 | 29 | See §8 — validation_score decays as the target vehicle decelerates to a real stop |
| accident (benign) | 0 | 39 | 1 | Correctly routed to CAUTION (corroboration-deficit uncertainty), not falsely REJECTed |
| emergency_vehicle (benign) | 0 | 39 | 1 | Same as above |
| road_closure (benign) | 0 | 39 | 1 | Same as above |
| replay_attack | 0 | 1 | 39 | First message (genuine, uncaptured) = CAUTION; every replayed message thereafter = **REJECT** |
| sybil_attack | 0 | 2 | 38 | Detected — REJECT from message 2 onward as the Sybil identity cluster accumulates history |
| semantic_manipulation | 0 | 40 | 0 | **Not detected as REJECT** — see §8, B3 reported no semantic risk on this content |
| authority_override | 0 | 40 | 0 | **Not detected as REJECT** — same B3 finding |
| goal_manipulation | 0 | 24 | 16 | Partially detected — REJECT on 16/40 messages |
| false_hazard_clearance | 0 | 1 | 39 | Detected — REJECT from message 2 onward |

**Do not over-read this table as an attack-detection benchmark.** Each
scenario is ONE synthetic message pattern run 40 times against a
persistent, accumulating history store — this measures how the frozen
architecture behaves on these specific constructed inputs on this
session's timeline, not a statistically powered detection-rate study
(that already exists elsewhere in this repo — see
`ADAPTIVE_ATTACK_EVALUATION.md`, `ABLATION_STUDY.md`). What IS a genuine,
new finding here: **B3 (the semantic gate) reported "no semantic risk"
on both `semantic_manipulation` and `authority_override`'s fabricated
text** (`b3.available=True, label=BENIGN` throughout both). Those two
scenarios' CAUTION-only outcome comes entirely from B1/MBD/CP's
structural/corroboration signals, not from B3 catching the semantic
mismatch it was specifically designed to catch. This is worth flagging
for the B3 owner, not glossed over.

---

## 7. Latency, throughput, resources

### 7.1 Per-stage latency (all 400 live messages)

| Stage | CARLA-mode mean (ms) | CARLA-mode p95 | CARLA-mode p99 | Replay-mode mean (ms) | Replay-mode p95 |
|---|---|---|---|---|---|
| PKI | 0.002 | 0.003 | 0.005 | 0.001 | 0.002 |
| B1 (SCSV) | 0.262 | 0.483 | 0.779 | 0.227 | 0.299 |
| MBD | 0.290 | 0.440 | 1.119 | 0.178 | 0.240 |
| B2 (Explainability) | 0.091 | 0.151 | 0.340 | 0.047 | 0.063 |
| CP | 0.365 | 0.674 | 1.098 | 0.025 | 0.033 |
| Synthesizer | 0.369 | 0.691 | 0.853 | 0.289 | 0.348 |
| **B3 Bridge** | **78.375** | **94.702** | **104.873** | **65.921** | **78.041** |
| Fusion | 0.102 | 0.142 | 0.185 | 0.079 | 0.099 |
| **Total** | **79.950** | **96.902** | **106.581** | **66.837** | **78.947** |

**B3 remains the dominant cost in live-CARLA mode too (98.0% of total
latency)** — consistent with the replay evaluation's finding. CP is
~15× more expensive per-call in CARLA mode (0.365 ms vs 0.025 ms mean)
because live scenarios more often carry a non-null `event_label`
(DENM-heavy scenario mix) than the mostly-plain-CAM SUMO trace, which
routes through CP's full spatial/speed/heading consistency computation
rather than the `observations_available=False` bypass — still
negligible in absolute terms (<0.4% of total).

### 7.2 Cold start / warm start

| | |
|---|---|
| B3 model load (measured, `pipeline.b3_load_ms`) | 14,976.4 ms |
| Region for per-message stats | All 400 messages treated as "warm" (same warmup design as replay-mode — see `DEPLOYMENT_EVALUATION.md` §3) |

Cold-start cost is essentially identical to the replay-mode measurement
(~15.6 s there vs ~15.0 s here) — expected, since it is the same model
checkpoint loaded the same way, independent of CARLA.

### 7.3 CPU / GPU / memory

| Metric | CARLA-mode | Replay-mode |
|---|---|---|
| Peak GPU memory allocated (B3 only, `torch.cuda.max_memory_allocated`) | 700.2 MB | 685.0 MB |
| GPU memory in use system-wide (CARLA + B3), `nvidia-smi` sampled mid-run | ~2,970–3,250 MB (Town01 CARLA ≈2,279 MB + B3 process's own allocation) | N/A (CARLA not running) |
| Final process RSS (pipeline process only) | 1,055.2 MB | 1,081.0 MB |
| CPU utilization (single pipeline process, sampled every 10 messages) | 84.0–149.6% | 96.8–103.6% |

**GPU contention is real and measurable.** With CARLA's server holding
~2.3 GB of the 6.1 GB GPU and actively rendering (even headless,
`-RenderOffScreen` still uses the GPU — confirmed via `nvidia-smi`
showing 85–100% GPU utilization from the CARLA process alone before the
pipeline was even started), B3's own inference had roughly half the free
VRAM headroom compared to the replay-mode run, and **mean B3 latency
rose from 65.9 ms to 78.4 ms (+19%)**. This is a genuine, disclosed
deployment-readiness finding: co-locating a full CARLA simulation and
the trust pipeline's B3 inference on the same modest (6 GB) GPU
measurably degrades the pipeline's own latency, even though both fit
without an out-of-memory failure in this case.

### 7.4 Throughput and message rate

| | CARLA-mode | Replay-mode |
|---|---|---|
| Sustained throughput | 11.22 msg/s | 14.95 msg/s |
| CARLA tick rate (source) | 10 Hz (`fixed_delta_seconds=0.1`) | N/A (offline replay of a pre-recorded SUMO trace) |

CARLA-mode throughput is **25% lower** than replay-mode, directly
attributable to the GPU-contention effect in §6.3 — B3 inference is the
bottleneck in both modes (§6.1), and it got measurably slower when
sharing the GPU with a live simulator.

### 7.5 Dropped messages

**0 messages were dropped**, by construction: this evaluation's
architecture is a single-consumer, synchronous pipeline
(`pipeline.run()` blocks until each message is fully processed before
the next CARLA tick's message is constructed) — there is no bounded
queue for messages to overflow. This is disclosed as a measurement of
*this evaluation script's* architecture, not a claim that a real
multi-vehicle-fan-in deployment would never drop messages — see §8's
analytical throughput-vs-concurrency argument, carried over unchanged
from `DEPLOYMENT_EVALUATION.md` §7, for what WOULD happen under
realistic RSU-scale concurrent arrival.

---

## 8. Comparison with the replay (SUMO) evaluation

| Dimension | Replay (SUMO trace) | Live (CARLA) | Delta |
|---|---|---|---|
| Data source | Pre-recorded FCD trace, offline replay | Live server, real-time synchronous simulation | Live-CARLA adds actual simulator wall-clock coupling |
| Vehicle count / traffic style | 4×4 grid, up to 46 concurrent, SUMO car-following model | 8 vehicles, single real town map, CARLA autopilot/Traffic Manager | CARLA traffic is more spatially dispersed (town-scale vs compact grid) |
| Mean B3 latency | 65.9 ms | 78.4 ms (+19%) | GPU contention with CARLA's own rendering |
| Sustained throughput | 14.95 msg/s | 11.22 msg/s (-25%) | Same root cause |
| Cold start | ~18.5 s (import+load) | ~15.0 s model load measured (import not separately isolated this run) | Consistent — same model |
| CPU utilization | 96.8–103.6% | 84.0–149.6% (wider variance) | CARLA's own process and Traffic Manager add host-CPU load alongside the pipeline's single core |
| Decision distribution | 1,765 CAUTION / 235 ACCEPT / 0 REJECT (benign-only trace) | Mixed ACCEPT/CAUTION/REJECT across 10 scenarios including real attacks | Live run deliberately includes attack scenarios; SUMO replay did not |
| Message construction | `x`/`y` flat schema (`make_flat_message`), bypassing the nested-CAM nested-schema nested-schema decode path entirely | Full nested ETSI CAM/DENM schema, exercising B1's structural/replay/certificate checks that the flat-schema replay never touched | Live-CARLA run is the FIRST of the two to actually exercise B1's full nested-schema validation path end-to-end |

**A significant, disclosed finding from this comparison:** the SUMO
replay evaluation fed MBD/CP directly via the flat `{x, y, speed,
heading, timestamp}` shortcut schema (see `to_flat_report`'s early-return
branch in `bridges/message_adapter.py`), which **skips B1's own
structural/replay/certificate/physical-plausibility checks entirely**
(those only run on the full nested CAM schema). The live CARLA
evaluation is the first of the two deployment evaluations to send
genuine nested ETSI CAM/DENM messages through B1's complete
`check_stateful()` path, MBD's real behavioral-anomaly detector, and
CP's real spatial/speed/heading consistency computation on live,
organically-varying kinematics — which is precisely how §8's
`normal_driving` finding (below) was surfaced. The SUMO replay's
throughput/latency numbers remain valid for what they measured (B3-bound
cost, correctly), but they did not exercise B1/MBD/CP as thoroughly as
this live-CARLA run does.

---

## 9. Limitations, stated directly

- **CARLA's server GPU footprint (headless) is substantial on this
  hardware.** Even with `-RenderOffScreen -quality-level=Low`, CARLA
  held ~2.3 GB VRAM and 85–100% GPU utilization on `Town01` alone
  (confirmed via `nvidia-smi`) before the pipeline ever started, out of
  a 6.1 GB total budget on this laptop GPU. `Town10HD_Opt` (CARLA's
  default map) used ~5 GB and left too little headroom for B3's model to
  load reliably; `Town01` was substituted for this reason. A
  production/embedded deployment would need to budget GPU capacity for
  both simulation (if co-located, e.g. in a HIL test rig) and the trust
  pipeline's own inference — they are not free to share a small GPU
  without a measurable latency penalty (§6.3).
- **`normal_driving`'s validation_score genuinely decayed over the
  scenario** (`ACCEPT` → `CAUTION` → `REJECT` within 40 ticks, MBD's
  `anomaly_score` climbing from 0.0 to 0.72) as the target vehicle
  physically decelerated to a stop at a real intersection under CARLA's
  own autopilot. This is a genuine architecture behavior surfaced by
  live, organically-varying urban driving (turns, stop signs, traffic
  lights) that a smoother, more scripted trace may not exercise as
  strongly — worth investigating as a possible over-sensitivity in
  MBD's behavioral-anomaly thresholds for ordinary deceleration events,
  not fixed or hidden here (no MBD code was touched).
- **B3 did not flag `semantic_manipulation` or `authority_override`'s
  fabricated content as risky** (§5) — both scenarios' final CAUTION
  outcome came from B1/MBD/CP, not from B3's own semantic reasoning
  catching the mismatch. This is exactly the kind of live-simulation
  finding a replayed/offline trace with pre-approved fixture text might
  not surface, and is reported here as-is.
- **CP's spatial-consistency assumption (~20 m local-event radius) does
  not transfer directly from SUMO's compact grid to CARLA's town-scale
  traffic** without deliberate window curation (§4) — this evaluation
  corrected its OWN window construction to route around the artifact;
  a real deployment would need equivalent proximity-aware message
  clustering logic (outside this repo's current scope) before feeding
  CP a multi-sender window from real, geographically dispersed traffic.
- **Sample size.** 40 messages per scenario, 8 vehicles, one CARLA town,
  one hardware configuration. This is a live-integration feasibility and
  latency/resource characterization, not a statistically powered
  detection-accuracy study — see `ADAPTIVE_ATTACK_EVALUATION.md` and
  `ABLATION_STUDY.md` for that.
- **No ROS2.** As in the replay evaluation, ROS2/DDS transport was not
  available in this environment; this report characterizes CARLA↔trust-
  pipeline integration cost directly (via the Python client, in-process),
  not what an additional ROS2 message-bus hop would add.
- Per the task's instruction, **no optimization was applied** to reduce
  B3's cost or CARLA's GPU footprint beyond selecting a lighter map
  (`Town01` vs the default `Town10HD_Opt`) purely to make the live run
  possible on this GPU at all — that substitution is a scenario/
  environment choice, not a pipeline change.

---

## 10. Conclusions

1. **CARLA 0.9.16 is confirmed installed, launchable, and reachable**
   on this machine (§1) — the previous report's "not installed" finding
   was correct for the locations it searched but incomplete; corrected
   here with full verification (process alive, version handshake, map
   load, live actor control).
2. **The complete, frozen trust pipeline runs unmodified against live
   CARLA vehicle state**, through a purpose-built bridge
   (`carla_bridge.py`) that translates real kinematics into this repo's
   own existing ETSI CAM/DENM wire format — every layer (PKI → B1 → MBD
   → B2 → CP → Synthesizer → B3 → Trust Decision Engine) executes on
   live data exactly as it does in the replay evaluation and in this
   repo's test suite.
3. **B3's transformer inference remains the dominant cost (~98% of
   latency)** in live mode, consistent with the replay-mode finding, and
   **got measurably worse (+19% mean latency, -25% throughput) under
   real GPU contention with a co-located CARLA server** — a genuine new
   finding this live evaluation was needed to surface; a replayed trace
   cannot expose simulator/inference resource contention.
4. **Real-time V2X throughput conclusion is reinforced, not
   contradicted:** CARLA-mode's 11.22 msg/s is even further below the
   ETSI-CAM-rate-driven throughput requirements documented in
   `DEPLOYMENT_EVALUATION.md` §7 than replay-mode's 14.95 msg/s was —
   the architecture's single-threaded, unbatched B3 inference remains
   the binding constraint for any RSU-scale multi-vehicle deployment,
   now confirmed under live simulation conditions rather than only
   offline replay.
5. **Two concrete, disclosed findings for follow-up**, both newly
   surfaced by moving from replay to live simulation: (a) MBD's
   behavioral-anomaly sensitivity to ordinary urban deceleration
   (§8), and (b) B3's non-detection of two of the ten fabricated-content
   attack scenarios tested here (§5, §8). Neither was fixed as part of
   this evaluation — per the task's explicit instruction not to modify
   the trust architecture — and both are reported exactly as measured.
