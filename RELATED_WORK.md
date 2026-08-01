# Related Work

Every paper cited below was located via live web search this session and
is a real, externally verifiable publication (URL given for each). This
section is a genuine, evidence-grounded literature review, but it is
scoped by a single session's search depth, not an exhaustive systematic
review — stated honestly rather than padded with unverified citations.
Where a subsection's search turned up fewer directly-on-topic papers than
the others (notably "Semantic Trust for V2X" — see §5), that scarcity is
itself reported as evidence of the gap this paper addresses, not
smoothed over.

## 1. PKI-Based Communication Trust

Standardized V2X security (IEEE 1609.2, ETSI TS 102 940/102 941/103 097)
establishes certificate-based authentication, message integrity, and
pseudonym-based privacy through a hierarchical PKI (root CA → enrollment
CA → authorization CA). Sedar et al.'s survey, "PKIs in C-ITS: Security
functions, architectures and projects" (*ScienceDirect*,
[link](https://www.sciencedirect.com/science/article/abs/pii/S221420962200078X)),
catalogs the security functions and deployed PKI architectures across
major C-ITS projects. A direct 2025 comparison of the North American and
European credential-management standards is given in "Performance
Comparison of Security Credential Management Systems for V2X" (arXiv:2501.03237,
[link](https://arxiv.org/abs/2501.03237)).

**Limitation.** PKI verifies *who sent* a message and *that it was not
altered*, by design; none of this literature claims PKI evaluates
message *content*. This is the literature's own stated boundary, not a
gap we are the first to notice — but existing V2X security architectures
built on top of PKI (surveyed in §2–§4 below) also stop short of content
verification, which is the specific gap this paper's B3 layer targets.

## 2. Misbehavior Detection Systems (MBD)

MBD complements PKI by analyzing behavioral/kinematic plausibility over
time rather than cryptographic validity at a single instant. Yuce's 2025
survey, "Misbehavior Detection With Collective Perception in V2X Networks"
(*Trans. Emerging Telecom. Technologies*,
[link](https://onlinelibrary.wiley.com/doi/10.1002/ett.70267?af=R)),
and the IEEE Communications Surveys \& Tutorials 2023 survey "A Survey on
Machine Learning-Based Misbehavior Detection Systems for 5G and Beyond
Vehicular Networks" (arXiv:2201.10500,
[link](https://arxiv.org/pdf/2201.10500)) both catalog ML-based MBD as a
necessary complement to PKI, since internal, credentialed attackers pass
PKI trivially. "Knowledge Transfer for Collaborative Misbehavior Detection
in Untrusted Vehicular Environments" (arXiv:2409.02844,
[link](https://arxiv.org/pdf/2409.02844)) addresses cross-domain MBD
knowledge transfer.

**Limitation, stated in this literature itself and confirmed by our own
Section IV-D:** MBD reasons over kinematics, timing, and behavioral
consistency, not message semantics. It is, by design, blind to a
grammatically fluent, kinematically-consistent message whose *meaning* is
adversarial. Our companion kinematic benchmark (Section IV-D) provides
direct, quantitative confirmation of this boundary on real VeReMi data
(MBD recall 60–91% on kinematic attacks it is designed for; ≈0%
contribution on the purely semantic attacks in Section IV-A).

## 3. Cooperative Perception Security

Zhang et al., "On Data Fabrication in Collaborative Vehicular Perception:
Attacks and Countermeasures" (USENIX Security 2023/2024, arXiv:2309.12955,
[link](https://arxiv.org/pdf/2309.12955)), is the most directly relevant
work: it demonstrates that V2X security standards "cannot block data
fabrication attacks because attackers can modify data before wrapping it
into protocol messages where protection is enforced" — i.e., the same
structural gap this paper's threat model formalizes as the Semantic Trust
Boundary, independently identified from a cooperative-perception-attack
angle rather than a trust-architecture angle. Related detection work
includes "Cooperative Trust Based Detection Mechanism for Fake Objects in
Collective Perception Messages" ([link](https://link.springer.com/chapter/10.1007/978-3-031-87775-9_16))
and consistency-check-based misbehavior detection for collective
perception messages (US patent filing,
[link](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12418778)).

**Limitation.** This body of work detects fabricated *objects/positions*
in cooperative perception (data fabrication, ghost objects) — a kinematic
and cross-source-consistency problem our CP layer and MBD's collusion/
Sybil checks (Section II-C1, verified in Phase 2 of our evaluation)
address. It does not address semantically valid but deceptively-framed
*text content* injected into scene-context fields, which is this paper's
specific contribution.

## 4. Context-Aware Trust Models

"Context-Aware Trust-Based Management of Vehicular Ad-Hoc Networks" (IEEE,
[link](https://ieeexplore.ieee.org/document/7518235)) and CARES,
"Context-Aware Trust Estimation for Realtime Crowdsensing Services in
Vehicular Edge Networks" (*ACM TOIT*,
[link](https://dl.acm.org/doi/10.1145/3514243)), incorporate
spatial-temporal context and purpose-of-communication into trust
scoring, closely paralleling this paper's B2/CSIA layer's design intent.
A 2022 comprehensive review, "On trust management in vehicular ad hoc
networks" (*Frontiers*,
[link](https://www.frontiersin.org/journals/the-internet-of-things/articles/10.3389/friot.2022.995233/full)),
surveys the broader design space including reputation- and
context-based schemes.

**Limitation.** Context-aware trust in this literature evaluates whether
a message is plausible *given the traffic situation* (e.g., is this speed
report consistent with an intersection context) — it does not evaluate
whether the message's own *stated content* (a claim, an instruction, an
assertion about authority) is internally coherent or benign. Our CSIA
layer performs the former; only B3 performs the latter.

## 5. Semantic Trust for V2X

This is, deliberately, the thinnest subsection in this review, and that
scarcity is itself evidence for this paper's contribution rather than a
gap in our search: direct prior work specifically on *semantic* trust
verification for V2X cooperative messages (as opposed to cryptographic,
behavioral, or cross-source-consistency trust) was not found in this
session's search. The closest adjacent work is in semantic
*communication* systems generally — e.g., "Detecting Backdoor Attacks via
Similarity in Semantic Communication Systems" (arXiv:2502.03721,
[link](https://arxiv.org/pdf/2502.03721)) — which addresses backdoor
attacks on the semantic *encoder/decoder* of a communication channel, a
different threat model from ours (we assume the encoder/channel is
trusted and evaluate whether the *decoded content itself* is
semantically deceptive).

## 6. LLM/VLM-Enabled Autonomous Driving

LLM4Drive, "A Survey of Large Language Models for Autonomous Driving"
([link](https://openreview.net/pdf?id=ehojTglbMj)), and "Large Language
Models for Human-like Autonomous Driving: A Survey" (arXiv:2407.19280,
[link](https://arxiv.org/pdf/2407.19280)) document the rapid adoption of
LLMs/VLMs for scene understanding, reasoning, and planning in autonomous
driving stacks, motivating exactly the AI-reasoning attack surface this
paper's threat model targets: as noted in these surveys, VLMs are
increasingly used to "assist in decision-making and provide intuitive
explanations" from cooperative and sensor input, meaning any semantic
manipulation of that input has a direct path to influencing driving
decisions.

**Limitation.** This literature focuses on capability and integration,
not adversarial robustness of the cooperative-perception input these
models consume — which is where our threat model and B3 gate are
positioned in the pipeline.

## 7. Prompt Injection Against Autonomous Systems

"A Study on Prompt Injection Attack Against LLM-Integrated Mobile
Robotic Systems" ([link](https://www.researchgate.net/publication/386401634_A_Study_on_Prompt_Injection_Attack_Against_LLM-Integrated_Mobile_Robotic_Systems))
and "Adversarial Attacks on Robotic Vision Language Action Models"
(arXiv:2506.03350, [link](https://arxiv.org/pdf/2506.03350)) directly
demonstrate prompt-injection-style attacks against LLM-integrated
robotic control, the same attack family this paper's `instruction_injection`,
`authority_override`, and related STBV-Bench attack families formalize
for the V2X cooperative-message setting specifically. OWASP's LLM Top 10
now ranks prompt injection (LLM01:2025) as its highest-priority LLM
application vulnerability, underscoring the real-world severity of this
attack class.

**Limitation.** This literature targets LLM agents receiving instructions
through direct user/tool-call channels or documents; it does not address
the specific case of adversarial content arriving through an
authenticated, cryptographically-valid V2X cooperative message — the gap
this paper's threat model and STBV-Bench are built to test.

## 8. Trust Fusion Architectures

"Cyber-Resilient Perception: Safeguarding Autonomous Vehicles With
Trust-Aware Sensor Fusion" (IEEE,
[link](https://ieeexplore.ieee.org/document/10971200/)) proposes dynamic,
Dirichlet-distribution-based trust modeling across sensor sources to
mitigate cyber-physical attacks on AV perception — architecturally
similar in spirit to our multi-layer evidence fusion, but at the
sensor-fusion level (camera/LiDAR/radar redundancy) rather than the
V2X-communication-trust level (PKI/behavioral/semantic evidence, our
setting).

**Limitation.** This work fuses *sensor* trust; our Trust Decision Engine
fuses *communication-layer* trust evidence (cryptographic, behavioral,
cooperative, semantic), a distinct evidence space with different failure
modes (a compromised sensor vs. an authenticated-but-deceptive message).

## 9. Dempster-Shafer-Based Trust Models

Improved Dempster-Shafer evidence-combination methods for multi-sensor
and multi-source fusion are well established: "Research on improved
evidence theory based on multi-sensor information fusion" (*Scientific
Reports*, [link](https://www.nature.com/articles/s41598-021-88814-3)),
"Multisensor Data Fusion in IoT Environments in Dempster–Shafer Theory
Setting" (*PMC*, [link](https://pmc.ncbi.nlm.nih.gov/articles/PMC10255415/)),
and "Paradox Elimination in Dempster–Shafer Combination Rule with Novel
Entropy Function" (*PMC*, [link](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6865203/))
all address the classical Dempster combination rule's known failure mode
under high source conflict, generally by re-weighting sources via
distance/entropy measures before combination. Yager's original
conflict-to-ignorance reassignment rule, which this paper adopts directly
(Section II-E2), is the specific alternative these more recent works
compare against or extend.

**Limitation/positioning.** These works focus on *sensor* evidence
combination and on more sophisticated conflict-redistribution schemes
than the Yager rule this paper uses. We deliberately adopt the simpler
Yager rule, not a more recent entropy-weighted variant, because its
conservative behavior (conflict → ignorance, never → resolved confidence)
is precisely the property Section II-E4's conservative decision policy
requires; adopting a more aggressive conflict-resolution scheme from this
literature is noted as a concrete avenue for future comparison, not
adopted here.

## 10. Decision-Level Trust Systems

The "decision-level fusion" framing in multi-sensor AV literature (see
the 2025 "Review of Multi-Sensor Fusion in Autonomous Driving,"
[link](https://www.mdpi.com/1424-8220/25/19/6033)) integrates independent
per-sensor predictions at a high level of abstraction to improve
robustness — conceptually parallel to this paper's Decision Trust
output, but again at the sensor-perception level rather than the V2X
trust-verification level.

## Positioning Summary

| Existing Work | Comm. Trust | Behavioral Trust | Semantic Trust | Decision Trust | LLM-aware | Inter-layer Reasoning | Evidence Fusion | Semantic Attacks | Decision-Level Protection |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| PKI / SCMS surveys (§1) | ✔ | -- | -- | -- | -- | -- | -- | -- | -- |
| MBD surveys (§2) | -- | ✔ | -- | -- | -- | -- | partial | -- | -- |
| CP security (Zhang et al., §3) | -- | ✔ (kinematic) | -- | -- | -- | -- | -- | -- (data fabrication, not text) | -- |
| Context-aware trust (§4) | -- | ✔ | -- | -- | -- | partial | ✔ | -- | -- |
| Semantic communication security (§5) | -- | -- | partial (channel-level) | -- | partial | -- | -- | -- (encoder attack, not content) | -- |
| LLM4Drive-style surveys (§6) | -- | -- | -- | -- | ✔ | -- | -- | -- | -- |
| Prompt injection literature (§7) | -- | -- | ✔ (general LLM) | -- | ✔ | -- | -- | ✔ (general, not V2X-specific) | -- |
| Trust-aware sensor fusion (§8) | -- | -- | -- | ✔ (sensor-level) | -- | ✔ | ✔ | -- | ✔ (sensor-level) |
| DS/Yager fusion literature (§9) | -- | -- | -- | -- | -- | -- | ✔ | -- | -- |
| **This paper** | **✔** | **✔** | **✔** | **✔** | **✔** | **✔** | **✔** | **✔ (V2X-specific)** | **✔** |

**Where this work is precisely novel**, per this comparison: no single
reviewed work combines PKI-grounded communication trust, behavioral/MBD
trust, an LLM-based *semantic content* verification layer, and a unified
Dempster-Shafer decision-level fusion, evaluated specifically against
V2X cooperative-message semantic manipulation. The closest individual
pieces exist in adjacent literatures (cooperative-perception data
fabrication, §3; LLM prompt injection generally, §7; trust-aware sensor
fusion, §8; DS/Yager fusion, §9) but none combine them for this threat
class in this domain. This is stated as a claim about *combination and
domain application*, not a claim that any individual technique (PKI, MBD,
Dempster-Shafer fusion, or a fine-tuned text classifier) is itself new —
none of those are, and the manuscript should not imply otherwise.
