# Semantic Trust Boundary Violation (STBV)
## A Multi-Layer Trust Architecture for Secure V2X Communication

![Python](https://img.shields.io/badge/Python-3.12-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![GitHub Actions](https://img.shields.io/github/actions/workflow/status/Mukilskanda/semantic-trust-boundary-violation/ci.yml?branch=main)

---

## Overview

**Semantic Trust Boundary Violation (STBV)** is a layered trust architecture for Cooperative Intelligent Transportation Systems (C-ITS) and V2X communication.

The central problem addressed by this project is:

> **A V2X message can be cryptographically authentic and physically plausible while still carrying misleading or malicious semantic information.**

Traditional V2X security mechanisms primarily answer questions such as:

* Who sent the message?
* Is the sender's certificate valid?
* Was the message modified?
* Is the message structurally valid?

Those checks are necessary, but they do not establish that the **information being communicated is trustworthy**.

STBV therefore combines multiple forms of evidence:

* PKI / SCMS authentication
* Hard structural and physical validation
* Behavioral and kinematic analysis
* Context-aware evidence reasoning
* Cooperative perception
* Semantic analysis
* Uncertainty-aware evidence fusion
* Policy-based final decision making

The architecture is designed so that no single layer is expected to determine trust by itself.

---

# Core Problem

Consider a vehicle broadcasting:

```text
Vehicle 101
Certificate: VALID
Signature: VALID
Speed: 60 km/h
Heading: 90°
Event: Road ahead is clear
```

The message may be completely valid from a cryptographic perspective.

However, the vehicle could still be deliberately reporting false information.

Therefore:

```text
Cryptographic authenticity
        ≠
Information truthfulness
```

STBV extends traditional V2X trust evaluation across the **semantic trust boundary**.

---

# Architecture

The current integrated pipeline is:

```text
                         V2X CAM / DENM
                               │
                               ▼
                     ┌──────────────────┐
                     │   Orchestrator   │
                     │  Pipeline Control│
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │    PKI / SCMS    │
                     │ Authentication   │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ B1 — SCSV        │
                     │ Hard Validation  │
                     └────────┬─────────┘
                              │
                    fatal? ───┤
                    yes │     │ no
                        ▼     ▼
                      REJECT  │
                              ▼
                     ┌──────────────────┐
                     │ MBD              │
                     │ Behavioral       │
                     │ Analysis         │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ B2 — Explain-    │
                     │ ability /       │
                     │ Evidence Layer  │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ CP               │
                     │ Cooperative      │
                     │ Perception       │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ Scene Synthesizer│
                     │ Factual semantic │
                     │ representation   │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ B3               │
                     │ Semantic Trust   │
                     │ Gate / Classifier│
                     └────────┬─────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ Trust Decision Engine  │
                  │ Evidence Fusion +      │
                  │ Policy                 │
                  └────────────┬───────────┘
                               │
                               ▼
                    ACCEPT / CAUTION / REJECT
```

The **Orchestrator controls this execution flow**. It is not itself a detection algorithm.

---

# Layer Responsibilities

| Layer             | Primary responsibility                                 |
| ----------------- | ------------------------------------------------------ |
| PKI / SCMS        | Cryptographic identity and credential validation       |
| B1 / SCSV         | Objective structural, temporal and physical validation |
| MBD               | Behavioral and kinematic consistency                   |
| B2                | Evidence normalization and explainable reasoning       |
| CP                | Cooperative/contextual consistency                     |
| Scene Synthesizer | Converts structured V2X information into factual text  |
| B3                | Semantic maliciousness / consistency analysis          |
| Trust Engine      | Final evidence fusion and decision                     |
| Orchestrator      | Controls execution and data flow                       |

---

# 1. Orchestrator

Implementation:

```text
pipeline/orchestrator.py
```

The orchestrator is the **control layer of the system**.

It is responsible for:

1. Receiving a message sequence.
2. Identifying the target message.
3. Maintaining the required history/context.
4. Running PKI when credentials are available.
5. Running B1.
6. Stopping the pipeline when a fatal B1 condition occurs.
7. Running MBD.
8. Converting layer outputs into common evidence representations.
9. Running B2.
10. Running CP when enabled.
11. Creating the factual scene representation.
12. Running B3.
13. Passing the resulting evidence to the Trust Decision Engine.
14. Returning the complete pipeline result.

The pipeline can therefore be invoked through a single interface:

```python
result = orchestrator.run(messages)
```

The orchestrator does **not** independently decide whether a vehicle is trustworthy.

Its role is:

```text
"What should run next,
and what data should that component receive?"
```

The analysis layers answer:

```text
"What does the evidence mean?"
```

The Trust Decision Engine answers:

```text
"What is the final trust decision?"
```

---

# 2. PKI / SCMS

Implementation:

```text
pki/
```

PKI provides cryptographic identity validation.

When a message contains the necessary signature, certificate, and public-key material, the pipeline can perform cryptographic validation.

The PKI path checks information such as:

* Signature validity
* Certificate validity
* Certificate expiration
* Certificate revocation
* Certificate chain / identity information

A cryptographically invalid message is propagated into the B1 validation result as a fatal failure.

For example:

```text
Invalid signature
      ↓
PKI failure
      ↓
B1 fatal validation failure
      ↓
REJECT
```

The pipeline does not fabricate a successful PKI result when the message does not contain the required cryptographic material.

Fixtures without PKI material can therefore skip meaningful PKI verification rather than pretending that verification succeeded.

---

# 3. B1 — Secure Cooperative Safety Validation (SCSV)

Implementation:

```text
b1_scsv/
```

B1 is the **hard validation boundary**.

Its purpose is to reject messages that are objectively invalid before expensive downstream reasoning is performed.

B1 handles checks including:

### Structural validity

Checks:

* Required fields
* Data types
* Message structure
* Valid encodings

### Replay protection

Detects messages that have already been observed or otherwise violate replay constraints.

### Timestamp validation

Checks:

* Freshness
* Future timestamps
* Scenario-relative temporal consistency

### Certificate-related checks

Integrates relevant PKI/certificate failures into the validation assessment.

### Physical plausibility

Checks objective constraints such as:

* Latitude range
* Longitude range
* Speed limits
* Longitudinal acceleration limits
* Heading encoding
* Other objectively invalid values

For example:

```text
latitude = 200°
```

is objectively impossible.

B1 can therefore return:

```json
{
  "valid": false,
  "fatal": true,
  "score": 0.0,
  "confidence": 1.0
}
```

and the orchestrator terminates the pipeline.

---

# Fatal vs Recoverable Findings

A major design principle is the distinction between **fatal validation failures** and **recoverable evidence**.

```text
Objective invalidity
        ↓
      FATAL
        ↓
      REJECT
```

versus:

```text
Behavioral anomaly
        ↓
   Evidence / uncertainty
        ↓
 Continue downstream
```

This prevents every unusual behavior from being treated as an immediate cryptographic-style failure.

---

# 4. MBD — Misbehavior Detection

Implementation:

```text
mbd/
```

MBD evaluates the **behavior of a vehicle over time**.

Unlike B1, which primarily checks objective validity, MBD uses message history to determine whether a vehicle behaves consistently with its previous observations.

Example:

```text
t = 1.0 s → 50 km/h
t = 1.1 s → 52 km/h
t = 1.2 s → 54 km/h
```

is broadly plausible.

But:

```text
t = 1.0 s → 50 km/h
t = 1.1 s → 150 km/h
```

may indicate a behavioral anomaly.

MBD evaluates evidence such as:

* Kinematic consistency
* Temporal consistency
* Speed changes
* Acceleration
* Heading behavior
* Replay indicators
* Identity consistency
* Sybil-related evidence
* Other behavioral anomalies

MBD maintains historical vehicle state through its history store.

---

# Persistent Coordinate Projection

MBD and CP need to compare positions from different messages.

The pipeline therefore maintains a **persistent projection origin** for a pipeline instance.

This is important because every message must be represented in a common coordinate frame.

Without a persistent origin, comparing distances between messages projected relative to different origins would be meaningless.

---

# 5. B2 — Explainability and Evidence Layer

Implementation:

```text
b2_explain/
```

The **active B2 implementation in the integrated pipeline is ****`b2_explain`**.

B2 does not directly receive the raw CAM/DENM message.

Instead, it receives standardized evidence from upstream layers.

For example:

```text
B1
 │
 └── validation score
     confidence
     findings
     checks

MBD
 │
 └── behavioral score
     anomaly evidence
     confidence
```

These are converted into a common representation:

```python
TrustEvidence
```

Conceptually:

```text
B1 result ─────┐
               ├──► TrustEvidence ──► B2
MBD result ────┘
```

This allows B2 to explain and combine evidence without depending on every internal implementation detail of B1 or MBD.

---

# Historical B2-CSIA Research Modules

The repository also contains:

```text
b2_csia/
```

This is the earlier/full CSIA research implementation.

It contains research modules including:

```text
adaptive_thresholds.py
context_aware.py
behavior_reasoning.py
observability_graph.py
evidence_quality.py
trust_propagation.py
uncertainty.py
behavior_profile.py
```

These modules are important to the project's research development and explain the earlier context-aware B2 design.

However:

> **`b2_csia.CSIA`**** is deprecated and is not the active B2 implementation used by the current orchestrator.**

The current orchestrator uses:

```python
from b2_explain.explainability import ExplainabilityEngine
```

A legacy `csia` argument exists only as a compatibility shim.

This distinction prevents the README from incorrectly claiming that the old CSIA implementation is currently executed as the production B2 path.

---

# 6. Context-Aware and Adaptive Threshold Research

The earlier B2-CSIA implementation explored a more sophisticated approach to behavioral thresholds.

Instead of:

```python
THRESHOLD = 0.5
```

for every environment, the system can infer the operating context from observed traffic.

Conceptually:

```text
Current observations
        ↓
Context inference
        ↓
Urban / Highway / Rural
        ↓
Adaptive threshold
        ↓
Behavior evaluation
```

The adaptive threshold can account for:

* Operating context
* Traffic density
* Vehicle diversity
* Historical stability
* Robust statistical estimates

This is important because normal behavior is not identical in every environment.

For example:

```text
Urban traffic
→ naturally higher speed/heading variation

Highway traffic
→ more structured motion
```

Therefore a single universal behavioral threshold can produce excessive false positives or false negatives.

---

# Robust Statistics

The B2-CSIA research implementation supports robust threshold estimation, including **median/MAD-based reasoning**.

This helps prevent a small number of extreme observations from redefining the normal operating range.

For example:

```text
10, 11, 10, 12, 11, 10, 1000
                           ↑
                         outlier
```

A mean-based estimate can be heavily affected by the extreme value.

Median/MAD is substantially more resistant to such outliers.

This is particularly relevant in adversarial V2X environments where attackers may intentionally inject extreme observations.

---

# 7. CP — Cooperative Perception

Implementation:

```text
cp/
```

CP evaluates whether observations from multiple sources are mutually consistent.

For example:

```text
Vehicle 101 → 60 km/h
Vehicle 102 → 61 km/h
Vehicle 103 → 59 km/h
```

suggests strong agreement.

CP considers evidence such as:

* Spatial consistency
* Speed consistency
* Heading consistency
* Temporal/contextual consistency
* Source diversity
* Peer observations

The distinction between **contradictory evidence** and **missing corroboration** is important.

For example:

```text
No nearby vehicles
```

does not automatically mean:

```text
Vehicle is malicious
```

It means that there is insufficient independent corroboration.

The architecture therefore treats uncertainty differently from explicit contradictory evidence.

---

# 8. Scene Synthesizer

Implementation:

```text
pipeline/synthesizer.py
```

The Scene Synthesizer converts structured V2X information into a deterministic factual representation for B3.

Example structured information:

```text
Vehicle 101
speed = 60 km/h
heading = 90°
```

can become:

```text
Vehicle 101 is traveling at 60 km/h
with heading 90 degrees.
```

The synthesizer is deliberately separated from B3.

It should report facts from the V2X data rather than make the final trust decision.

---

# DENM Event Handling

DENM events are not simply hardcoded into the message.

The synthesizer first attempts to extract event information from the incoming message.

It can use fields such as:

```python
target_msg.get("event")
```

or extract a DENM event/cause value from the structured DENM message.

The repository contains a mapping from known cause codes to human-readable event names.

For example:

```text
DENM cause_code = 2
        ↓
"accident"
```

The important distinction is:

```text
Event value
    = comes from the input message

Cause-code → human-readable name
    = deterministic mapping in the implementation

Sentence template
    = deterministic
```

Therefore the synthesizer does not invent the event.

---

# 9. B3 — Semantic Trust Gate

Implementation:

```text
b3/
pipeline/b3_bridge.py
```

B3 performs semantic analysis after the structured V2X information has been converted into a factual scene representation.

The flow is:

```text
CAM / DENM
     ↓
Structured data
     ↓
Scene Synthesizer
     ↓
Factual scene text
     ↓
B3
```

B3 can produce information such as:

```json
{
  "label": "BENIGN",
  "confidence": 0.96,
  "p_malicious": 0.04,
  "risk_level": "none"
}
```

or:

```json
{
  "label": "MALICIOUS",
  "confidence": 0.91,
  "p_malicious": 0.91,
  "risk_level": "high"
}
```

The semantic layer therefore addresses a different question from B1:

```text
B1:
"Is this message objectively valid?"

B3:
"Does the semantic information represented by this message
indicate malicious or inconsistent behavior?"
```

A valid certificate does not guarantee truthful semantic content.

---

# 10. Trust Decision Engine

Implementation:

```text
trust_engine/
```

The Trust Decision Engine is the **final fusion point**.

It receives evidence from the upstream layers and determines the final trust state.

Conceptually:

```text
B1
 │
MBD
 │
B2
 │
CP
 │
B3
 │
 └───────────────┐
                 ▼
        Trust Decision Engine
                 │
                 ▼
         Evidence Fusion
                 │
                 ▼
        Policy / Decision Rules
                 │
                 ▼
      ACCEPT / CAUTION / REJECT
```

The engine uses uncertainty-aware evidence handling rather than relying exclusively on one model prediction.

---

# Dempster-Shafer Evidence

The system represents evidence in terms of:

```text
A   = Trustworthy
¬A  = Suspicious / not trustworthy
Θ   = Unknown / unresolved uncertainty
```

This allows the system to distinguish:

```text
"I have evidence that this is malicious"
```

from:

```text
"I don't have enough evidence to determine whether it is malicious."
```

This distinction is important in V2X because lack of corroboration should not automatically become a malicious classification.

The architecture also allows evidence from different sources to conflict.

For example:

```text
B1/B2:
strong evidence of technical validity

B3:
strong evidence of semantic manipulation

        ↓

Evidence conflict
        ↓

Trust Decision Engine
        ↓

Final policy decision
```

---

# 11. Common Evidence Representation

The repository uses a common evidence abstraction:

```text
contracts/trust_evidence.py
```

The purpose is to prevent every layer from needing to understand every other layer's internal data structures.

Conceptually:

```python
TrustEvidence(
    source_layer="MBD",
    passed=False,
    score=0.42,
    confidence=0.84,
    findings=[...],
    raw={...}
)
```

This creates a common interface between heterogeneous detectors.

---

# 12. Scenario-Relative Time

The offline evaluation framework uses **scenario-relative timestamps**.

Instead of depending on the host machine's wall clock:

```text
2026-08-08 13:00:00
```

scenario messages use:

```text
0 ms
100 ms
200 ms
300 ms
...
```

where:

```text
0 ms = scenario start
```

This makes experiments:

* Deterministic
* Reproducible
* Independent of execution date
* Easier to compare across runs

The repository uses scenario-relative integer milliseconds for offline temporal reasoning.

Cryptographic certificate validity remains separate and continues to use normal UTC validity intervals.

---

# 13. End-to-End Example

Consider the following V2X message:

```text
Vehicle ID       = 101
Speed            = 60 km/h
Heading          = 90°
Timestamp        = 5200 ms
Certificate      = valid
DENM cause       = accident
```

### Step 1 — PKI

```text
Certificate valid
Signature valid
        ↓
PASS
```

### Step 2 — B1

```text
Structure        ✓
Replay           ✓
Timestamp        ✓
Physical limits  ✓
Certificate      ✓
        ↓
B1 = valid
```

### Step 3 — MBD

Previous observations:

```text
50 km/h
55 km/h
58 km/h
60 km/h
```

The current behavior is plausible.

```text
MBD = low anomaly
```

### Step 4 — B2

B1 and MBD become standardized evidence.

```text
B1 evidence
     +
MBD evidence
     ↓
B2 explanation
```

### Step 5 — CP

Nearby vehicles report:

```text
59 km/h
60 km/h
61 km/h
```

The observations are mutually consistent.

```text
CP = strong corroboration
```

### Step 6 — Synthesizer

The structured DENM information becomes:

```text
Vehicle 101 reports an accident.
```

### Step 7 — B3

The semantic model evaluates the factual scene representation.

```text
label      = BENIGN
confidence = 0.96
```

### Step 8 — Trust Engine

All available evidence is fused.

```text
B1       → valid
MBD      → plausible
B2       → strong evidence
CP       → corroborated
B3       → benign
```

Final:

```text
ACCEPT
```

---

# 14. Example of a Semantic Attack

Consider a different case.

The vehicle has:

```text
Valid certificate
Valid signature
Plausible speed
Plausible position
```

Therefore:

```text
PKI ✓
B1  ✓
MBD ✓
```

However, the vehicle's semantic report contradicts the broader scene.

B3 may produce:

```json
{
  "label": "MALICIOUS",
  "confidence": 0.91,
  "risk_level": "high"
}
```

The final decision engine receives:

```text
Technical evidence
        +
Behavioral evidence
        +
Cooperative evidence
        +
Semantic evidence
```

A high-confidence semantic attack can therefore cause:

```text
REJECT
```

even when the sender's certificate is valid.

This is the central STBV concept.

---

# 15. Repository Structure

```text
.
├── adapters/              # Logging/API/Dempster-Shafer adapters
├── b1_scsv/               # Secure Cooperative Safety Validation
├── b2_explain/            # Active B2 explainability/evidence layer
├── b2_csia/               # Earlier CSIA research implementation
├── b3/                    # Semantic trust model
├── b3_eval/               # B3 evaluation and experiments
├── bridges/               # Data/model interface adapters
├── contracts/             # Shared interfaces and evidence contracts
├── cp/                    # Cooperative perception
├── data/                  # Dataset-related resources
├── evaluation/            # Evaluation utilities
├── mbd/                   # Misbehavior Detection
├── pki/                   # PKI / cryptographic validation
├── pipeline/              # Orchestrator and synthesizer
├── scenarios/             # Attack scenarios
├── test_messages/         # Test message fixtures
├── tests/                 # Unit/integration tests
├── tools/                 # Dataset/time conversion utilities
├── trust_engine/          # Final trust fusion and policy
├── isce_config.yaml       # Configuration
├── manual_pipeline_test.py
├── run_classifier.py
├── run_veremi_evaluation.py
└── requirements.txt
```

---

# 16. Installation

## Clone

```bash
git clone https://github.com/Mukilskanda/semantic-trust-boundary-violation.git
cd semantic-trust-boundary-violation
```

## Create a virtual environment

### Linux / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

For reproducible dependency installation:

```bash
pip install -r requirements_pinned.txt
```

---

# 17. B3 Model Weights

The B3 checkpoint is stored using Git LFS.

After cloning:

```bash
git lfs pull
```

The expected checkpoint is located under:

```text
b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3/
```

If the checkpoint is unavailable, B3 evaluation paths are designed to report the unavailable state rather than fabricate a semantic prediction.

---

# 18. Running the Pipeline

The main manual harness is:

```bash
python3 manual_pipeline_test.py
```

For a specific pipeline input:

```bash
python3 manual_pipeline_test.py \
    --pipeline test_messages/benign/normal_car.json \
    --verbose
```

A directory of messages can also be supplied where supported by the harness.

The manual harness is intended to expose the pipeline's intermediate reasoning, including:

```text
PKI
 ↓
B1
 ↓
MBD
 ↓
B2
 ↓
CP
 ↓
Synthesizer
 ↓
B3
 ↓
Trust Decision
```

---

# 19. Attack Scenarios

The repository contains scenario suites for several threat classes.

```text
scenarios/
├── sybil/
├── replay/
├── collusion/
├── fabrication/
├── semantic/
└── mixed/
```

Examples:

### Sybil

```bash
python3 manual_pipeline_test.py \
    --pipeline scenarios/sybil
```

### Replay

```bash
python3 manual_pipeline_test.py \
    --pipeline scenarios/replay
```

### Collusion

```bash
python3 manual_pipeline_test.py \
    --pipeline scenarios/collusion
```

### Fabrication

```bash
python3 manual_pipeline_test.py \
    --pipeline scenarios/fabrication
```

### Mixed attacks

```bash
python3 manual_pipeline_test.py \
    --pipeline scenarios/mixed
```

---

# 20. Dataset and VeReMi Evaluation

The repository contains utilities for working with V2X/VeReMi-style data and scenario-relative timestamp conversion.

Relevant components include:

```text
tools/
run_veremi_evaluation.py
run_capped_veremi_test.py
evaluation/
```

Dataset processing should preserve the distinction between:

```text
Raw dataset timestamp
        ↓
Scenario-relative timestamp
        ↓
Behavioral evaluation
```

The scenario-relative representation is used to make offline experiments reproducible.

---

# 21. Testing

The repository contains multiple levels of validation:

```text
Unit tests
Integration tests
Layer tests
Interface tests
Scenario tests
Benchmark evaluations
Ablation studies
```

Useful checks include:

```bash
python3 tests/verify_dependency_graph.py
```

and targeted test modules under:

```text
tests/
pipeline/tests/
b2_csia/
```

The project has also been subjected to broader integration, regression, benchmark, and ablation evaluations documented throughout the repository.

Because some evaluation paths require the B3 model and GPU/ML dependencies, the full test surface should be distinguished from lightweight unit tests.

---

# 22. Continuous Integration

GitHub Actions configuration:

```text
.github/workflows/ci.yml
```

The CI pipeline performs automated architecture and regression validation.

The workflow includes checks such as:

* Dependency graph verification
* Unit tests
* Layer/interface tests
* Integration validation
* Regression tests

The exact CI matrix should be treated as the authoritative source for the currently executed automated checks.

---

# 23. Design Principles

The architecture follows several important principles.

### 1. Hard validation before semantic reasoning

Objectively invalid messages should not reach expensive semantic reasoning.

```text
Invalid message
      ↓
B1
      ↓
REJECT
```

---

### 2. Authentication is not truth

A valid certificate establishes sender authenticity, not semantic truthfulness.

```text
Valid identity
      ≠
Valid information
```

---

### 3. Evidence should retain uncertainty

A missing observation should not automatically be treated as malicious.

```text
No evidence
      ≠
Evidence of attack
```

---

### 4. Behavioral thresholds should reflect context

The research implementation explores adaptive thresholds rather than relying exclusively on universal fixed limits.

---

### 5. Semantic analysis should remain separated from lower-layer validation

B3 receives a synthesized factual representation rather than directly rewriting or overriding B1/MBD results.

This reduces the risk of allowing semantic reasoning to bypass lower-level security boundaries.

---

### 6. The Trust Decision Engine is the fusion point

Individual layers produce evidence.

The final engine determines the overall trust state.

---

### 7. The Orchestrator controls execution but does not perform detection

This keeps pipeline control separate from trust reasoning.

---

# 24. Current Architectural Boundary

The active pipeline is:

```text
PKI
 ↓
B1 / SCSV
 ↓
MBD
 ↓
B2 / Explainability
 ↓
CP
 ↓
Scene Synthesizer
 ↓
B3
 ↓
Trust Decision Engine
```

The repository also contains the earlier:

```text
b2_csia/
```

research implementation.

It should not be confused with the current active B2 path.

The legacy CSIA implementation is retained for research history, experiments, and compatibility, while the current orchestrator uses:

```text
b2_explain/
```

as its B2 implementation.

---

# 25. Known Scope and Integration Considerations

The architecture is intentionally explicit about boundaries and limitations.

### B3 availability

Real B3 inference requires the semantic model checkpoint and its ML runtime.

If the checkpoint is unavailable, the system should report B3 as unavailable rather than inventing a classification.

### PKI fixtures

Meaningful PKI verification requires actual cryptographic material in the input message.

Fixtures without signatures/certificates cannot provide meaningful cryptographic verification.

### Cooperative perception

The current orchestrator validates one target message per `run()` call. CP can therefore use peer observations, but complete trust-weighted validation of every peer would require independently running the relevant validation stack for every peer before fusion.

### Legacy B2-CSIA

`b2_csia.CSIA` is retained but is not the active B2 implementation in the current orchestrator.

### Collusion integration

The repository contains collusion-detection logic in MBD, but its integration depends on the event information available through the current message representation. This should not be described as universally active across every input path.

---

# 26. Research Contribution

The project investigates a fundamental extension to V2X trust:

```text
Traditional V2X security

"Is the sender authentic?"
            │
            ▼
         TRUST
```

versus:

```text
STBV

Is the sender authentic?
        +
Is the message valid?
        +
Is the behavior plausible?
        +
Do other observations agree?
        +
Is the semantic content trustworthy?
        │
        ▼
Final evidence-based trust decision
```

The main contribution is therefore not simply an LLM classifier.

It is a **layered evidence-based trust architecture** in which semantic reasoning becomes another controlled source of trust evidence rather than an unquestioned replacement for conventional V2X security mechanisms.

---

# 27. Summary

STBV separates V2X trust into multiple complementary questions:

```text
PKI
Who sent this?

B1
Is the message objectively valid?

MBD
Is the sender behaving plausibly?

B2
What does the combined evidence tell us?

CP
Do independent observations support the claim?

Synthesizer
What factual scene does the V2X data describe?

B3
Does the semantic information indicate malicious behavior?

Trust Engine
What should the final trust decision be?
```

The resulting decision is:

```text
                    ┌──────────┐
                    │  ACCEPT  │
                    └──────────┘

                    ┌──────────┐
                    │ CAUTION  │
                    └──────────┘

                    ┌──────────┐
                    │  REJECT  │
                    └──────────┘
```

The objective is to move V2X security from:

> **"Is this message authentic?"**

toward:

> **"Given all available technical, behavioral, cooperative, contextual, and semantic evidence, should this information actually be trusted?"**

---

# License

MIT License.

---

# Acknowledgements

This project builds upon concepts from:

* ETSI Intelligent Transport Systems standards
* IEEE 1609 WAVE
* Cooperative Intelligent Transportation Systems (C-ITS)
* V2X misbehavior detection
* Transformer-based semantic analysis
* Dempster-Shafer evidence theory
* Cooperative perception
