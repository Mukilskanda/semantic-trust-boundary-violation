# Expanded Discussion and Limitations

This document supersedes the short Discussion subsection previously
drafted (in the Section IV rewrite) with a fuller synthesis addressing
deployment implications, failure modes, trade-offs, threat model
boundaries, and research implications, and expands Limitations with
every item requested. Every claim here is traceable to a result already
established and cited in `HANDOFF_SUMMARY.md`, `MANUSCRIPT_RESULTS_DISCUSSION.md`,
`REPRODUCIBILITY_PARAMETER_APPENDIX.md`, and `CP_VALIDATION.md`.

## Discussion

### Why B3 dominates semantic-attack detection
STBV-Bench's honesty contract keeps kinematics real and unmodified
(`DATASET_INTEGRATION.md`); only the free-text scene-context is
attacked. B1/MBD/CP reason exclusively over cryptography, timing, and
kinematics — they have no representation of message *content* at all, so
they are structurally incapable of reacting to a purely textual attack,
independent of how sophisticated their kinematic reasoning is. This is
not a weakness of those layers; it is outside their designed scope by
construction, confirmed directly by config-3→4's F1 jump from 0.034 to
0.715 (Table I).

### Why MBD dominates kinematic-attack detection
The converse holds by the same logic: the VeReMi companion benchmark
carries no injected text at all, so B3 has nothing to read (confirmed:
config-3/4 byte-identical on all 13,511 messages, Section IV-D). MBD's
recall (60–91%, by attack type) comes from comparing a sender's current
report against its own history — a fundamentally different reasoning
mode than B3's single-message text classification, and one STBV-Bench's
independent-message design cannot even offer B3 an analog of (there is
no "semantic history" concept implemented in this architecture).

### Why fusion changes more decisions than binary F1 shows
Binary F1 treats CAUTION and REJECT identically (both "positive"), so it
is blind to the majority of what fusion actually does: 92.5% of its
decision changes are CAUTION→REJECT escalations, invisible to the binary
metric (Section IV-B). This is a *methodological* point with implications
beyond this paper: any V2X trust study reporting only binary detection
metrics on a three-state decision architecture is at risk of
systematically under-crediting exactly the mechanism (graded escalation)
such architectures are designed to provide. We recommend three-way
transition analysis as standard practice for any future work on
graded-trust decision engines, not just for this paper's own reporting.

### Why realistic multi-vehicle traffic lowers full-corpus F1
This is the least intuitive finding and the one most likely to be
misread if reported without its full explanation. STBV-Bench v1's
single-message design has no concept of an "innocent bystander" — every
sample is either a designated attacker or a designated `benign_control`.
The multi-vehicle regime (Section IV-F) introduces, for the first time,
real ambient vehicles that are neither: ordinary VeReMi traffic that
happens to be co-located with an attacker (or with nothing at all). MBD's
real, independently-measured ≈52–58% false-positive rate on ordinary
VeReMi kinematics (Section IV-D, confirmed twice, independently, on two
different benchmarks) now applies to a much larger fraction of evaluated
traffic than v1 ever exposed. This is not evidence the architecture
"got worse" — it is evidence that v1's F1 was measured on a data
distribution that never contained the false-positive source the
multi-vehicle regime reveals. **Reporting only v1's F1 would overstate
real-world precision; reporting only the multi-vehicle F1 would obscure
the real detection improvement it also shows. Both must be reported.**

### Why richer context helps semantic detection
The direct causal example (Section IV-F, window `stbv2-00008`) shows one
fixed attack sentence's classification changing purely as neutral,
genuine co-located-vehicle context accumulates around it, with
zero change to the attack text itself. Two candidate mechanisms remain
only partially distinguished, per `FOLLOWUP_VERIFICATION_2.md` §2: (a)
B3's classifier may be sensitive to overall scene-description length or
composition somewhat independent of semantic content (a possible
training-distribution artifact, since B3's training text — per
`RELATED_WORK.md` §6's observation that VLM-integrated pipelines
typically operate over populated scenes — may itself have rarely
contained the "no other vehicles" isolated phrasing v1 uses); or (b)
richer context genuinely disambiguates attacker intent for a
human-legible reason (an isolated claim reads more suspiciously once
surrounded by corroborating or contradicting real traffic, which is a
form of implicit cross-source reasoning even without CP's explicit
mechanism). The evidence (§ same document) shows the context-volume
correlation direction is inconsistent across 2 of 6 improved families,
which rules out (a) as a *complete* explanation but does not rule it out
as a *partial contributor*. This is reported as open, not resolved,
because it is open.

### Trade-offs
The central trade-off this evaluation surfaces is precision vs.
ecological validity: STBV-Bench v1's isolated-message design buys clean,
high-precision, easily-interpretable per-attack metrics at the cost of
never exposing the architecture to realistic ambient false-positive
sources; the multi-vehicle regime buys realism at the cost of a
messier, harder-to-attribute aggregate metric. Neither is strictly
"more correct" — they answer different questions (Section IV-F,
Discussion in the prior draft), and a deployment decision should weight
both.

A second trade-off is recall vs. precision within MBD itself: MBD's
kinematic checks are tuned (implicitly, via fixed thresholds — see
`REPRODUCIBILITY_PARAMETER_APPENDIX.md` §2) toward high sensitivity.
This is defensible *given* that MBD's output feeds a three-state fusion
engine that can route uncertain signals to CAUTION rather than forcing a
binary call (Section IV-B) — but it would be a poor design choice if MBD
's output were consumed directly as a binary accept/reject gate, as the
per-vehicle "ever flagged" policy analysis shows directly (99.4% FPR,
Section IV-D).

### Deployment implications
1. **Latency budget is workable but not generous.** Mean end-to-end
   latency (110 ms) fits inside the nominal 100 ms / 10 Hz CAM interval
   only at the median; $p_{95}$ (189 ms) and $p_{99}$ (254 ms) exceed it.
   A production deployment needs either a faster inference path for
   latency-critical messages, selective invocation of the semantic layer
   (e.g., only for messages that fail cheaper checks or carry non-empty
   scene-context text), or an explicit tolerance for occasional
   above-budget processing with a defined fallback (e.g., treat
   still-processing messages as CAUTION by default).
2. **The over-defense finding (instruction-hiding/role-confusion, 100%
   false-positive rate under those two perturbations) is operationally
   serious**: a deployment that surfaces CAUTION/REJECT decisions to a
   human operator or downstream automated response would generate a
   severe, narrow false-alarm burden under exactly these two, plausible,
   non-adversarial phrasing patterns (e.g., a benign message that merely
   *discusses* roles or instructions without attacking). This should be
   fixed or explicitly mitigated (e.g., a phrase-pattern allowlist,
   targeted fine-tuning data) before any deployment that acts on B3's
   output without a human in the loop for CAUTION-band decisions.
3. **CP's current non-contribution is a deployment-readiness gap, not
   just an evaluation gap.** Since CP's wiring is fixed and verified
   correct given event data (`CP_VALIDATION.md`), the remaining blocker
   is entirely in the message-generation/labeling pipeline, not in the
   trust architecture itself — meaningfully lower risk to close than a
   fundamental algorithmic redesign would be, but it must be closed
   before any claim of complementary cooperative-perception protection
   can be operationalized.

### Failure modes
- **Silent under-detection on six specific attack families** phrased as
  narrative indirection (Section IV-A) — an adversary aware of this
  architecture's weak spot could deliberately phrase attacks to avoid
  the eight well-detected, direct-instruction-style families.
- **Over-defense on two robustness perturbation families** (Section
  IV-G) — an adversary could, in principle, exploit this as a
  denial-of-service vector against legitimate traffic by embedding
  role/instruction-adjacent phrasing in benign messages to trigger false
  CAUTION/REJECT at scale, though this was not tested as an explicit
  attack in this evaluation (see Limitations, below).
- **MBD's real ≈52–58% baseline false-positive rate** on ordinary,
  unmodified real-world kinematics (Section IV-D/IV-F) means any
  downstream system treating MBD's raw flag as a strong signal, rather
  than routing it through the fusion engine's graded CAUTION mechanism,
  will over-trigger substantially on legitimate traffic.

### Threat model boundaries (restated precisely, not just referenced)
This work's threat model (Section III-D) explicitly excludes: compromise
of the STBV framework's own execution environment, modification of the
deployed semantic model's weights, post-verification tampering with
trust evidence, denial-of-service at the network/hardware layer, and
adaptive attackers who observe and iteratively evade the specific
deployed B3 classifier. The last exclusion is the most consequential for
a security venue: every attack family evaluated in this paper is a
single-shot, non-adaptive construction (Section III-C/`SEMANTIC_TRANSFORMATION_APPENDIX.md`).
No adversarial-search, gradient-based, or iterative red-team process was
used to specifically evade the deployed B3 checkpoint. This is stated
plainly as a Limitation (below), not implied away.

### Research implications
Three findings in this paper have implications beyond this specific
architecture. First, the three-way transition analysis methodology
(Section IV-B) is directly reusable by any graded/multi-state trust
system evaluation, and its absence from a large share of the reviewed
literature (`RELATED_WORK.md` §8–§10, which report binary or scalar trust
outputs) suggests it is under-used in this research area generally.
Second, the v1-vs-multi-vehicle finding (Section IV-F) suggests that
*any* V2X semantic-detection benchmark built from independent,
isolated messages should be treated with caution as a precision
estimate specifically, even if its recall/detection-capability claims
are sound — a methodological caveat with implications for benchmark
design in this subfield generally, beyond just STBV-Bench. Third, the
demonstrated non-overlap between B3 and MBD (Section IV-E) is direct,
quantitative evidence for a layered-defense design philosophy in V2X
trust architectures generally, as opposed to investing further
engineering effort into any single "best" detector.

## Expanded Limitations

Consolidating and extending `PUBLICATION_PROGRESS.md`'s L1–L11 list with
every item this task explicitly requires:

**L1–L11.** (Carried forward verbatim from `PUBLICATION_PROGRESS.md`;
summarized here for completeness, full text at that source): the
CP event-label data-generation gap (L1); collusion detection's
event-dependency (L2); the six-family B3 weak cluster (L3); the
mixed-threat benchmark's small-n sampling confound (L4); unimplemented
narrative-evolution/progressive-poisoning injection strategies (L5); the
instruction-hiding/role-confusion 100% over-defense finding (L6); the
model-benchmark near-degeneracy on a 24-sample split (L7); the
untraceable prior headline figures 0.859/98.8% (L8); STBV-Bench v1's
non-committed build manifest (L9); no formal significance test on the
v1-vs-v2 recall comparison (L10); STBV-Bench v2 has never been ablated
by layer (L11).

**L12 (new). Internally-generated semantic benchmark, no external
semantic-attack corpus.** STBV-Bench's semantic attack text is generated
by this paper's own seeded template engine (`SEMANTIC_TRANSFORMATION_APPENDIX.md`),
not drawn from an independently-authored, externally-published semantic
V2X attack corpus (no such corpus was identified in `RELATED_WORK.md`'s
search — this is, to our knowledge, a genuine gap in the field, not just
in this paper). This means STBV-Bench's headline numbers (Section IV-A)
are internally consistent and free of the specific leakage mechanism
found in the deprecated 120-scenario corpus (`PUBLICATION_PROGRESS.md`,
0.990-figure caveat) — the generator and the classifier were built by
different, independent processes with no shared taxonomy — but they are
not validated against any external ground truth of what real-world
semantic V2X deception looks like, since none is known to exist publicly.

**L13 (updated — partially closed this round).** A sensitivity sweep of
$\tau_H$, $\tau_L$, and the B3 risk bands has now been performed
(`REPRODUCIBILITY_PARAMETER_APPENDIX.md` §2, `stbv_bench/parameter_sensitivity_sweep.py`):
the architecture's aggregate output is unchanged across a wide tested
range of each, because the semantic-risk floor rules dominate the
outcome rather than the raw threshold cutoffs — a genuine robustness
finding, not merely an unstudied gap. What remains open: the CP
consistency weights (0.35/0.25/0.20/0.20) have not been swept (CP
contributes zero on every benchmark in this paper regardless — see L1 —
so a sweep would currently be measuring an inert parameter); the sweep
performed is a post-hoc reconstruction from logged per-message fields
with a disclosed 1.28% fidelity gap against a full pipeline re-run, not
a from-scratch re-run at each setting; and no joint/interaction sweep
across multiple parameters simultaneously was performed, only one
parameter varied at a time with the others held at their shipped values.

**L14 (new). No adaptive-attacker evaluation.** Every attack in this
paper (Section III-D) is a single-shot construction against a fixed,
already-deployed classifier — there is no adversarial-search,
query-based, or iterative red-teaming process that specifically targets
the deployed B3 checkpoint's decision boundary. The robustness results
(Section IV-G) test *incidental* and *generic adversarial-style*
perturbations (paraphrase, homoglyphs, instruction-hiding), which is a
meaningfully weaker guarantee than a dedicated adaptive attack campaign
would provide, and should not be conflated with one.

**L15 (new). Prevalence assumptions.** STBV-Bench v1's headline
precision/F1 figures are measured at a 70.07%/29.93% malicious/benign
corpus split (`VERIFICATION_ADDENDUM.md` §3), not at any claimed
real-world operational attack prevalence, which is almost certainly far
lower. FPR is the prevalence-robust number and should be preferred for
any deployment-relevance argument; precision/F1 at this corpus prevalence
should not be quoted as an operational precision estimate without this
caveat attached every time.

**L16 (new). Benchmark assumptions.** STBV-Bench's attacker model
assumes the attacker already possesses valid, unrevoked credentials
(Section III-D) — i.e., every evaluated attack is, by construction, a
post-authentication content attack. This is the correct scope for
testing the semantic layer specifically, but means this paper makes no
claim about detecting an attacker who has *not yet* obtained valid
credentials (a PKI-layer problem, out of scope by design, not omitted by
oversight).

## What Cannot Be Resolved From This Repository Alone

Per the mission's explicit instruction to separate what additional
in-repo experiments can fix from what genuinely requires new research:
L12 (no external semantic-attack corpus exists to validate against) and
L14 (adaptive-attacker evaluation) both require either new external data
that does not currently exist publicly, or a substantial new red-teaming
research effort beyond what a reproducible, seeded template engine can
provide by construction. These are listed as genuine future work, not
attempted here, and not fabricated.
