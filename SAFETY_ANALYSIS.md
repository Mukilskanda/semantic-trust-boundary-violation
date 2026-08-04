# Safety Analysis — Autonomous Driving Implications of Documented Failure Modes

**Scope and method.** This document takes every failure cluster
established with real, quoted evidence in `FAILURE_ANALYSIS.md` and
asks the autonomous-driving-specific question `FAILURE_ANALYSIS.md`
deliberately does not: *if a real autonomous vehicle's planner consumed
this system's `trust_level` output as input to a driving decision, what
happens?* No new failure modes are introduced here — every scenario
below is a concrete instantiation of a cluster already measured with
real data. Where a consequence chain requires an assumption about how a
downstream planner would use `trust_level` (this repository does not
itself contain a planner), that assumption is stated explicitly, not
silently baked in.

**Assumed downstream consumption model, stated once.** Consistent with
how `ARCHITECTURE_DECISIONS.md` and `stbv_paper.tex` describe this
system's purpose (a pre-planner trust gate on cooperative V2X messages,
not the planner itself): ACCEPT → message content is available to the
planner at full weight; CAUTION → message content is down-weighted /
flagged for corroboration against onboard sensors before being acted on
/ routed to a human operator in a supervised deployment; REJECT →
message is discarded, not passed to the planner at all. This is the
standard, documented design intent (`decision_engine.py`'s "Conservative-
bias ceiling" comment; `DISCUSSION_AND_LIMITATIONS.md`'s "any deployment
acting on B3's output without a human in the loop for CAUTION-band
decisions"), not an invented consumption model.

**Risk-level definitions used throughout:**

| Level | Meaning |
|---|---|
| **CRITICAL** | Plausible direct path to a collision or a safety-relevant maneuver failure (e.g. failing to stop, entering a hazard) if the failure occurs at the wrong moment, with no architectural backstop within this system's own scope. |
| **HIGH** | Plausible path to an unsafe or significantly degraded maneuver, but a backstop exists (graded CAUTION rather than ACCEPT, or the failure requires an additional precondition to become safety-relevant). |
| **MEDIUM** | Degrades cooperative-perception quality or trust-system reliability without a direct, single-step path to an unsafe maneuver. |
| **LOW** | Nuisance-level (unnecessary caution, discarded-but-recoverable-elsewhere evidence) with no plausible safety path identified. |

---

## 1. B3 narrative-indirection / fabricated-clearance blind spot (Failure Clusters A, E)

**Real-world consequence.** An attacker broadcasts a message that does
not assert a *new* false hazard (which this architecture detects well —
`authority_override`, `false_clearance` both reach 100% recall on
STBV-Bench) but instead **cancels or supersedes an existing real
hazard warning** — exactly the phrasing pattern shown failing in
`FAILURE_ANALYSIS.md` Cluster A's real quoted examples (*"the debris in
lane 2 advisory... should be cancelled"*; *"conditions have improved and
no longer warrant the earlier... caution"*) and, more severely, in
Cluster E's live-CARLA `false_hazard_clearance` scenario, where a
fabricated `"hazard_cleared"` claim contradicting an active, genuinely
co-located hazard report was tested directly.

**Concrete scenario.** A work-zone or debris hazard is genuinely present
on a stretch of road and correctly reported by an infrastructure DENM or
a preceding vehicle. An attacker — a vehicle with valid, unrevoked
credentials (in scope for this threat model; see `stbv_paper.tex`
"Benchmark scope assumption") positioned nearby — broadcasts a follow-up
CAM/DENM asserting the hazard is now cleared, phrased as a routine
status update or fabricated multi-peer consensus (Cluster A's real
example text is directly this pattern). An approaching AV that has
already down-weighted or is about to clear its own internal hazard flag
based on the original warning receives this cancellation message. If B3
does not flag it (as measured: `BENIGN` at >0.9 confidence in the real
STBV-Bench examples; `BENIGN` on every single live-CARLA
`false_hazard_clearance` message per Cluster E) and B1/MBD/CP have
nothing anomalous to flag (the cancelling vehicle's own kinematics can
be entirely normal), the fused decision is ACCEPT or, at best, an
incidentally-triggered CAUTION from an unrelated behavioral signal (as
was in fact observed for `false_hazard_clearance` in the live run,
caught 39/40 times — but *not* by B3; see Cluster E).

**Risk level: CRITICAL** for the subset of this cluster where no
incidental B1/MBD/CP signal happens to co-occur (STBV-Bench's static
text-only version, Cluster A), since there kinematics carry no signal at
all by the benchmark's own construction — nothing downstream of B3
would catch it. **Reduces to HIGH** for the live-CARLA instantiation
specifically, only because that scenario's particular kinematic
construction happened to also trigger MBD/CP (an artifact of this
session's scenario design, not a general property of this attack class
— a more careful attacker matching truthful kinematics throughout, as
Cluster A's static text-only cases already are by construction, removes
this backstop).

**Planner impact.** A planner that clears an internal "hazard ahead"
flag based on an ACCEPTed cancellation message resumes normal-speed,
normal-path planning through a location that (per ground truth) still
contains the original hazard.

**Driver impact.** In a supervised/L2-L3 deployment where CAUTION
messages are surfaced to a human driver but ACCEPT messages are not,
the driver receives no alert at all — the failure is invisible to the
human backstop specifically because it is classified as high-confidence
benign, not as an uncertain case a driver would be asked to verify.

**Vehicle impact.** No degradation to onboard sensing (LiDAR/camera/
radar) — this is a cooperative-perception trust failure, not a
perception-hardware failure. A vehicle with functioning onboard sensors
retains an independent chance to detect the physical hazard directly,
which is this failure mode's only non-architectural backstop.

**Mitigation.** (i) Onboard-sensor cross-validation before clearing any
previously-elevated hazard state, regardless of a cooperative message's
trust level — architecturally, this means the planner layer (outside
this repository's scope) should treat hazard-*clearance* claims with an
asymmetric, higher corroboration bar than hazard-*assertion* claims,
since Cluster A shows this architecture's own asymmetry runs the wrong
way (assertion families detected at 100%, clearance/cancellation-style
families at 1–9%). (ii) Targeted B3 fine-tuning or a rule-based
supplementary check specifically for cancellation/supersession language
patterns (`"should be cancelled"`, `"no longer warrant"`, `"supersedes
prior report"`) — a scoped, tractable fix given the pattern is
lexically identifiable in every quoted real failure example. (iii)
Requiring multi-source corroboration specifically for clearance claims
(CP's existing mechanism, currently inert on this exact scenario shape
per Cluster H's dependency on CP receiving populated `event` data).

**Residual risk.** Even with (ii)/(iii) implemented, this remains an
open capability gap until independently re-measured — this document
does not claim a fix, only identifies the most tractable path to one.

---

## 2. Live-CARLA B3 total non-detection across constructed attacks (Failure Cluster E, full severity)

**Real-world consequence.** Beyond the clearance-specific case above,
Cluster E's finding is broader: across **240 live-simulated attack
messages spanning six distinct attack constructions**
(`semantic_manipulation`, `authority_override`, `goal_manipulation`,
`false_hazard_clearance`, `sybil_attack`, `replay_attack`), B3 assigned
essentially zero suspicion mass ($m_A \approx 0.93$–$0.94$, i.e.
confidently benign) to **every single one**, with no exception. Every
successful detection in that live run (`sybil_attack`, `replay_attack`,
`false_hazard_clearance` reaching REJECT) is independently attributable
to B1/MBD/CP, not to B3 — directly evidenced by every reasoning string
in that run containing the literal substring "B3 found no semantic
risk," including on messages that were ultimately REJECTed.

**Concrete scenario.** An `authority_override` attack — an ordinary
vehicle falsely claiming `station_type=roadSideUnit` and broadcasting an
"authority override, clear path" instruction — is exactly the pattern
STBV-Bench's own static `authority_override` family detects at **100%
recall** (Cluster A's table). In the live-simulated instantiation of the
*same conceptual attack*, using real CARLA kinematics and this
repository's own live message-construction bridge, B3 detected it **0%
of the time** (Cluster E). If an AV's cooperative-perception stack
grants elevated trust or right-of-way deference to a station claiming
`roadSideUnit` type (a reasonable, common design choice for
infrastructure-originated instructions), and this system is the only
gate checking whether that claim is itself trustworthy, an attacker
using this exact construction against a live system built the way this
one is deployed here would pass undetected by the layer specifically
designed to catch it.

**Risk level: CRITICAL.** This is the paper's own headline defense
mechanism (B3, "this architecture's principal contribution" per
`stbv_paper.tex`) measured at 0% live-attack recall in the only
live-simulator evaluation performed. The most plausible explanation
(Cluster E's diagnosis: likely training/synthesis distribution shift
between STBV-Bench's own generator output and the live bridge's
synthesized scene text) does not change the operational conclusion:
**this specific measured configuration provides no semantic defense in
a live-simulated deployment**, only the same B1/MBD/CP behavioral
defense this paper's own Discussion already documents as covering a
disjoint threat class (kinematic/behavioral, not semantic).

**Planner impact.** Identical to §1's mechanism, generalized across
every semantic attack type this architecture claims to defend against,
not only clearance-cancellation phrasing — a planner receiving an
ACCEPT (or B1/MBD/CP-incidental CAUTION not attributable to semantic
detection) for a fabricated authority instruction, a fabricated traffic
condition intended to manipulate routing (`goal_manipulation`), or
fabricated accident content (`semantic_manipulation`) has no
semantic-layer signal to weight its decision by.

**Driver impact.** Same invisibility problem as §1, at greater scope:
any of the six live-tested attack types could reach a human operator (if
CAUTION is surfaced) with the CAUTION label attributing risk to
"cryptographic/structural" concerns in the reasoning text (per the real
quoted strings), not to the actual semantic manipulation present — a
human reading the system's own explanation would be pointed at the
wrong evidence, undermining the explainability goal B2 is designed to
serve.

**Vehicle impact.** Same as §1 — no onboard-sensor degradation; the
vehicle's own perception remains the sole backstop for any hazard
component with a physical signature (a stopped vehicle, a real
obstacle). For attacks with **no physical signature at all**
(`authority_override`'s false right-of-way claim, `goal_manipulation`'s
false congestion claim intended purely to alter routing decisions rather
than local hazard perception), onboard sensors provide **no backstop**,
since there is nothing physically anomalous to sense.

**Mitigation.** (i) Immediate: do not deploy this specific B3 checkpoint
against live/simulated traffic without re-validation — the STBV-Bench
recall numbers this paper otherwise reports do not transfer to this
input distribution, measured directly, not inferred. (ii)
Retrain/fine-tune B3 on scene text generated by the same
synthesizer/bridge pathway a live deployment will actually use, not only
STBV-Bench's own generator's output — the distribution-shift hypothesis
in Cluster E, if correct, is directly addressable this way. (iii)
Until (ii), treat B1/MBD/CP as the *only* validated defense layer for
live traffic and architect the planner accordingly (i.e. do not
advertise or rely on semantic-attack coverage in a live deployment based
on STBV-Bench numbers alone).

**Residual risk.** High and unresolved. This is reported as the single
most consequential finding across all evaluations in this document, per
`FAILURE_ANALYSIS.md`'s own framing, precisely because no architectural
component in this codebase currently compensates for it.

---

## 3. MBD urban-deceleration over-sensitivity (Failure Cluster F)

**Real-world consequence.** A real, entirely benign vehicle decelerating
normally (traffic light, stop sign, yielding to a pedestrian) has its
own broadcast trust degrade from ACCEPT to REJECT within 4 simulated
seconds, purely from the magnitude of its own real speed change relative
to its brief prior history (measured: MBD `anomaly_score` 0.0→0.72,
target speed 638→0 in 0.01 m/s units, real quoted reasoning strings in
`FAILURE_ANALYSIS.md` Cluster F).

**Concrete scenario.** An AV approaching a signalized intersection
receives CAM broadcasts from a vehicle ahead of it that is braking to
stop for a red light or a crossing pedestrian. If this system's REJECT
verdict on that vehicle's broadcast causes the receiving AV's
cooperative-perception stack to **discard that vehicle's reported
position/speed entirely** (the documented consumption model above:
REJECT → not passed to planner), the AV loses the cooperative signal
specifically at the moment it is most safety-relevant — exactly when a
lead vehicle is stopping. The AV's own onboard sensors (camera/LiDAR/
radar) remain the backstop, so this is not a scenario where the AV would
fail to perceive the stopped vehicle at all — but it removes the
*redundant, earlier* V2X signal that cooperative perception exists
specifically to provide (e.g. detecting a stop initiated just beyond
sensor line-of-sight, around a curve or over a rise), degrading exactly
the safety margin V2X is designed to add on top of onboard sensing.

**Risk level: HIGH**, not CRITICAL, specifically because onboard sensing
remains a functioning backstop for this failure mode (unlike §§1–2,
where some attack constructions have no physical signature at all).
Downgraded further toward MEDIUM in any deployment where CAUTION/REJECT
routes to down-weighting rather than hard discarding (the "corroborate
against onboard sensors" branch of this document's stated consumption
model) — but the measured decision here was REJECT specifically (not
CAUTION), so the more conservative discard behavior is the one actually
observed in 29/40 messages of this scenario.

**Planner impact.** Loss of an early cooperative-braking cue for a
genuinely stopping lead vehicle; in the worst case (REJECT treated as
"ignore this sender entirely," the documented consumption model's
literal reading), the AV's cooperative-perception map of a real,
correctly-behaving neighboring vehicle goes empty exactly during its
deceleration event.

**Driver impact.** If a supervised deployment surfaces REJECT as "this
broadcast is untrustworthy" without further context, a human operator
monitoring a fused display could see a nearby vehicle's data
intermittently disappear during ordinary braking events — a
false-alarm/reliability-erosion cost more than a direct hazard, but one
with a "cry wolf" second-order effect: frequent unexplained REJECTs on
ordinary driving behavior risk operators learning to discount the
system's REJECT signal generally, weakening its value on the occasions
it is correct.

**Vehicle impact.** None to the vehicle whose broadcast is REJECTed —
this is entirely a receiver-side trust/perception-fusion effect on
*other* vehicles' view of it, not a control-authority effect on the
decelerating vehicle itself.

**Mitigation.** (i) Widen MBD's expected-kinematic-variance envelope for
sudden deceleration specifically, or condition it on map-context signals
(e.g. proximity to a mapped intersection/stop line) if available to the
deployment — outside this repository's current scope, but directly
actionable given the mechanism is now measured, not hypothesized. (ii)
Do not map REJECT to a hard "discard sender" policy for behavioral
(MBD-only, B3-clean) REJECTs in the same way as a crypto-fatal or
B3-HIGH REJECT — these are evidenced to have different underlying
reliability, and this document's own consumption-model assumption
(stated at the top) is itself a design choice worth revisiting given
this finding, not a fixed requirement. (iii) Extend the evaluation
(§`CARLA_DEPLOYMENT_EVALUATION.md` Limitations) across repeated runs,
alternate towns, and varied traffic-light/intersection density to
determine whether this is systematic or seed-specific before any fix is
prioritized.

**Residual risk.** Medium — this failure mode has a real backstop
(onboard sensing) unlike §§1–2, and a plausible, scoped mitigation path,
but is currently unconfirmed as systematic vs. incidental (single run,
single vehicle, single town — `CARLA_DEPLOYMENT_EVALUATION.md`
Limitations).

---

## 4. MBD physical-plausibility threshold false positives (Failure Cluster C)

**Real-world consequence.** A genuinely benign, real vehicle traveling
at a true recorded speed of 181.0 km/h (marginally above MBD's fixed
180.0 km/h ceiling) has its broadcast flagged CAUTION.

**Concrete scenario.** A high-speed highway/autobahn-class road segment
(180 km/h is close to, or within, legal operating speed on some real
European motorways, and is very plausibly exceeded briefly by real
non-attacker traffic, e.g. an overtaking maneuver or a downhill grade) —
this is not a synthetic edge case; it is drawn from real VeReMi
trajectory data. An AV's cooperative-perception stack on such a road
would systematically down-weight or discard legitimate fast-traffic
broadcasts from this cause alone.

**Risk level: MEDIUM.** The failure is a CAUTION, not a REJECT
(graceful degradation working as designed, per this document's own
Cluster D observation that the graded design limits severity), and the
underlying vehicle is not itself unsafe — the risk is a *reduced*
cooperative-awareness margin on high-speed roads specifically, which is
also where stopping distances and reaction-time margins are least
forgiving, a relevant aggravating factor even at CAUTION severity.

**Planner impact.** Down-weighted trust in a genuine fast-approaching
vehicle's reported speed/position on exactly the road class where
accurate closing-speed awareness matters most.

**Driver/vehicle impact.** Same reliability-erosion pattern as §3 if
this fires routinely on a specific road class/region — a systematic,
predictable false-alarm source specific to certain geographies (any
region with a legal or de facto operating speed near or above 180 km/h)
would be learned as "noisy" by any operator monitoring it there.

**Mitigation.** Raise the fixed ceiling with a documented margin (e.g.
200 km/h) or make it configurable per deployment region/road class
rather than a single global constant — the most directly actionable,
lowest-risk fix in this entire document, since it requires no retraining
and the exact failing value (181.0 vs. 180.0) is already known precisely.

**Residual risk.** Low, once the threshold is widened — this is a
calibration fix, not an algorithmic limitation.

---

## 5. Adaptive-attacker evasion via context-padding (Failure Cluster G)

**Real-world consequence.** An attacker with the ability to iteratively
observe this system's output (query access — e.g. a researcher-grade
adversary probing a fielded system's public behavior, or an attacker
with a local clone of the deployed model) can reliably evade B3 within a
median of ~3 rounds by padding genuinely malicious content with
generic, routine-sounding filler sentences (Cluster G's real quoted
example: fabricated peer-consensus content padded with *"Ambient
traffic density remains moderate..."*).

**Concrete scenario.** This requires a materially more capable attacker
than §§1–4 (query/observation access to the deployed classifier, not
merely valid V2X credentials), so it is a *lower-likelihood, higher-
sophistication* threat, not a mass-market one — but for that attacker
class, the 83.7% success rate within a 10-round budget means this
system's semantic defense should not be relied upon against a
determined, adaptive adversary at all, only against unsophisticated or
non-adaptive ones.

**Risk level: HIGH** for the specific attacker capability this requires;
correctly scoped as **not applicable** to attackers without query/probe
access to the deployed model (the large majority of the STBV-Bench and
live-CARLA scenarios in this document assume a single-shot, non-adaptive
attacker, consistent with this paper's own stated threat-model
boundary).

**Planner/driver/vehicle impact.** Identical mechanism to §§1–2 once
evasion succeeds — the padded, evasive message is ACCEPTed and
propagates the same way any other B3 false negative would.

**Mitigation.** (i) Do not expose per-message confidence scores or
detailed reasoning to any externally-observable channel in a fielded
deployment — this specific attack requires observing B3's own confidence
to guide the search; removing that feedback channel (returning only the
final trust_level, not confidence/reasoning, to any untrusted consumer)
meaningfully raises the attacker's cost, though it does not eliminate a
fully black-box or transfer attack. (ii) Detect the `context_poisoning`
padding pattern itself (generic filler sentences surrounding a shorter
substantive claim) as a distinct, learnable signal, since it is the
dominant evasion mechanism (18/41 evasions) and is a recognizable
structural pattern independent of the specific claim being smuggled
through it.

**Residual risk.** High and explicitly unresolved — `stbv_paper.tex`'s
own Limitations state this adaptive evaluation is "a first, not
exhaustive" pass; no mitigation above has been implemented or
re-measured in this repository.

---

## 6. CP low-sample-count corroboration confound (Failure Cluster H)

**Real-world consequence.** A genuinely honest, newly-arrived vehicle
(or one just entering communication range) whose first 1–2 corroborating
peer reports happen to agree with it has its trust temporarily
down-weighted to CAUTION purely because 2 reports cannot yet
statistically distinguish honest agreement from a hypothetical collusion
pattern.

**Concrete scenario.** A vehicle merging onto a highway or entering a
dense urban intersection, where its cooperative-perception window is
still populating with new neighbors, would see its own broadcasts
routinely capped at CAUTION for the first few hundred milliseconds of
any new multi-vehicle cluster, self-resolving once the window reaches 3+
reports (Cluster H: diversity climbs and the effect disappears by the
third report).

**Risk level: LOW.** Self-limiting, CAUTION-only (never REJECT, per the
real 142-message benchmark's own confirmed 0 false negatives), and
resolves within the same short window that created it.

**Planner/driver/vehicle impact.** Minor, transient trust down-weighting
on legitimate new-neighbor data — a nuisance-level cooperative-perception
cost during highway merges and intersection entry, not a safety-path
risk given the graded, self-correcting nature confirmed by real data.

**Mitigation.** Track window "maturity" (elapsed time or report count)
as an explicit corroboration-confidence modifier rather than treating a
2-report window identically to a mature window — a scoped, low-risk
refinement to CP's existing `diversity_score` computation.

**Residual risk.** Low — already the least severe cluster in
`FAILURE_ANALYSIS.md` by its own analysis, and the mitigation is
narrowly scoped.

---

## 7. MBD cold-start blind spot (Failure Cluster B)

**Real-world consequence.** An attacker's very first broadcast to a
given receiver (message index 0, no prior history) cannot be caught by
MBD's history-relative checks by construction (real quoted evidence:
`"No history yet; baseline assumed valid."`).

**Concrete scenario.** A ConstPos (constant-position falsification)
attacker entering a new AV's communication range for the first time has
its opening broadcast accepted regardless of content, since MBD has
nothing to compare it to yet. At a typical 10 Hz CAM rate, this window
is a single ~100 ms message — brief, but not zero, and specifically
concentrated at the highest-uncertainty moment of any new
vehicle-to-vehicle relationship (first contact).

**Risk level: MEDIUM.** Bounded in duration (resolves at the sender's
second message, per the same real data showing non-cold-start FNs are a
separate, larger population — Cluster B2), but occurs at exactly the
moment (first contact with an unknown sender) where independent
verification is least available.

**Planner/driver/vehicle impact.** A single-message window of
unverified trust for any newly-encountered sender; negligible for most
attack types requiring sustained false information to matter (e.g.
DoS/flooding), more relevant for attack types where a single
high-impact false position report could matter (e.g. a fabricated
"vehicle directly ahead, stopped" claim on message 1 specifically) —
this exact interaction (cold-start + a single high-consequence claim) is
not itself measured in this repository and is flagged as a gap, not
assumed to be low-risk by default.

**Mitigation.** A conservative default trust ceiling (e.g. cap at
CAUTION, never ACCEPT) for any sender's literal first message,
regardless of what B1/MBD/B3 individually report — a scoped,
directly-actionable policy change requiring no retraining.

**Residual risk.** Medium — bounded exposure window, but the
highest-consequence single-message-attack interaction is unmeasured.

---

## 8. Summary matrix

| # | Failure mode | Risk level | Physical-sensor backstop? | Requires elevated attacker capability? | Mitigation cost |
|---|---|---|---|---|---|
| 1 | Hazard-clearance/cancellation semantic blind spot | **CRITICAL** | No (for no-kinematic-signature variants) | No (valid credentials only) | Medium (targeted fine-tune / rule check) |
| 2 | Live-deployment B3 zero-detection (all constructed attacks) | **CRITICAL** | Partial (none for no-physical-signature attacks) | No | High (retrain on live-distribution text) |
| 3 | MBD urban-deceleration over-sensitivity | HIGH | Yes | No | Medium (retune / policy change) |
| 4 | MBD speed-threshold false positives | MEDIUM | Yes | No | **Low** (widen one constant) |
| 5 | Adaptive-attacker evasion | HIGH (scoped) | No | **Yes** (query access) | High (retrain + access control) |
| 6 | CP low-sample confound | LOW | Yes (self-resolving) | No | Low |
| 7 | MBD cold-start blind spot | MEDIUM | Partial | No | **Low** (policy default) |

**The two CRITICAL items (§1, §2) share a common thread**: both are B3
capability gaps with **no physical-sensor backstop** for the subset of
attacks carrying no kinematic signature — exactly the threat class this
architecture's semantic layer exists specifically to cover, and exactly
where `FAILURE_ANALYSIS.md`'s evidence shows it currently does not. This
is the single most important safety conclusion this document reaches:
**the failure modes with a physical backstop (§§3, 4, 6, 7) are
bounded by the vehicle's own sensing regardless of this architecture's
behavior; the failure modes without one (§§1, 2) are not bounded by
anything measured in this repository.**
