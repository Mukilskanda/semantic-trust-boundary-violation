# Results and Discussion (Research-Question-Organized Draft)

This document is a ready-to-adapt draft of the manuscript's Results and
Discussion sections, restructured around the research question each
completed experiment actually answers. No manuscript source file exists
inside this repository (the paper draft is held externally); this
document is the primary-source-grounded input for whoever writes that
section. Every number cites the file it comes from, per this project's
established evidence standard (`HANDOFF_SUMMARY.md`, `MANUSCRIPT_FRAMING.md`).

**Organizing principle, and the rule this document enforces throughout:**
every experiment in this repository answers one specific research
question, under one specific evaluation regime (dataset, methodology,
ground-truth definition). Two experiments that answer *different*
questions are never presented as competing measurements of the same
thing, even when their numbers are superficially comparable (e.g. both
are an "F1 score"). Where two experiments' numbers might tempt a reader
to rank them against each other, this document says explicitly why that
comparison is invalid.

## Research-question map

| RQ | Question | Experiment(s) | §below |
|---|---|---|---|
| RQ1 | Does the semantic classifier (B3) detect purely semantic trust-boundary violations that carry no kinematic signature? | STBV-Bench v1, ablation config 4 | §R1 |
| RQ2 | Does fusing B3 with the crypto/structural/behavioral layers (the complete Trust Decision Engine) change detection behavior beyond B3 alone, and how? | STBV-Bench v1 ablation configs 4→5, 3-way transition analysis | §R2 |
| RQ3 | Do the kinematic/behavioral layers (MBD, B1) detect real-world kinematic V2X attacks that carry no semantic content? | VeReMi kinematic companion bench | §R3 |
| RQ4 | Is Cooperative Perception (CP) functioning as designed within the architecture? | Empirical CP check, CP wiring-bug fix | §R4 |
| RQ5 | Are the semantic and kinematic detection capabilities complementary (non-overlapping), or does one subsume the other? | Cross-reference of RQ1+RQ3, plus the mixed-threat benchmark | §R5 |
| RQ6 | Does richer, real multi-vehicle context change semantic detection behavior relative to the isolated-single-message evaluation regime? | STBV-Bench v2 (two sub-questions: per-family attacker recall, and full-corpus Decision Trust) | §R6 |
| RQ7 | Is B3's classification robust to adversarial and incidental text perturbations? | `b3_eval/run_robustness.py` | §R7 |
| RQ8 | Is B3's confidence well-calibrated, and does it fail safely on unseen attack families? | `b3_eval/run_calibration.py`, `run_open_set_analysis.py` | §R8 |
| RQ9 | Is the deployed B3 backbone architecture justified relative to alternative pretrained models? | `b3_eval/run_model_benchmark.py` | §R9 |
| RQ10 (methodological validity, not an architecture finding) | Was the original 120-scenario hand-authored benchmark a valid, generalizable estimate of detection performance? | Dataset-leakage investigation | §R10 |

---

## Results

### §R1 — RQ1: Does B3 detect purely semantic STBV attacks with no kinematic signature?

**Experiment.** STBV-Bench v1 (`results/stbv_bench/v1/`, n=10,000, real
VeReMi Extension kinematics + 21 seeded semantic-transformation rules
across 20 attack families) evaluated with B1+B2+CP+B3 active but the
Trust Decision Engine's Dempster-Shafer fusion bypassed — B3's own risk
band alone determines the decision (ablation config 4,
`results/ablation/ablation_summary.json`, `table["4"]`).

**Findings.** Accuracy=0.6893, **Precision=1.0000**, Recall=0.5566,
F1=0.7151, FPR=0.0000 (tp=3,900, fp=0, fn=3,107, tn=2,993). B3 alone
never falsely flags a benign message on this benchmark. Recall is
uneven across attack families: 8 of 20 families reach 100% recall
(`instruction_injection`, `authority_override`, `false_clearance`,
`hazard_suppression`, `infrastructure_semantic_manipulation`,
`priority_manipulation`, `cross_source_contradiction`,
`collaborative_semantic_agreement`), while 6 families reach ≤9% recall
(`semantic_narrative_poisoning` 9%, `mixed_semantic_attacks`,
`multi_message_context_poisoning`, `indirect_prompt_injection`,
`traffic_efficiency_lure`, `goal_manipulation` all ≤2%) —
`results/stbv_bench/v1/stbv_bench_results.json` (`per_family`).

**Interpretation.** B3 is capable of near-perfect, zero-false-positive
detection of semantic attacks phrased as direct authority/instruction
claims or explicit multi-source contradiction, but is largely blind to
attacks phrased as subtle narrative framing, indirection, or content
spread implicitly across a conversational turn. This is a genuine
classifier-capability limitation, not a fusion or architecture defect
(confirmed in §R2 — the Trust Decision Engine faithfully propagates
whatever B3 provides; it does not independently re-detect what B3 misses).

**Implication for the architecture.** The semantic gate (B3) is a
necessary and largely sufficient component for the specific threat class
STBV-Bench v1 tests (semantic manipulation with clean kinematics), with
a known, bounded, honestly-reportable capability gap on subtler phrasing
styles. This result should NOT be compared against the 120-scenario
corpus's F1=0.990 (§R10) as if the two measure the same thing at
different quality levels — they use different (and, for the 120-scenario
corpus, methodologically compromised) evaluation regimes.

---

### §R2 — RQ2: Does the complete Trust Decision Engine (fusion) change detection beyond B3 alone, and how?

**Experiment.** Same STBV-Bench v1 n=10,000 slice, comparing ablation
config 4 (B3 alone, §R1) against config 5 (the full, deployed fusion
pipeline) — `results/ablation/ablation_summary.json`. A separate 3-way
(ACCEPT/CAUTION/REJECT) transition analysis was run specifically because
binary precision/recall/F1 cannot see transitions that stay within the
"positive" class (`results/ablation/ablation_3way_analysis.json`).

**Findings.** Binary metric: Accuracy=0.6883, Precision=0.9829,
Recall=0.5650, F1=0.7175, FPR=0.0231 — fusion trades a small precision
loss for a small recall gain relative to B3 alone (McNemar p=3.06e-29,
128/10,000 decisions cross the binary boundary; Cohen's h=-0.0262,
negligible effect size on this scale despite the significant p-value,
since n=10,000 gives high statistical power to detect even a tiny,
consistent shift). The 3-way analysis reveals what the binary metric
cannot: fusion causes **1,713** real decision-string changes, not 128.
Of these, **1,585 (92.5%) are CAUTION→REJECT** escalations on genuine
attacks, and **zero (0/1,713) are direct ACCEPT↔REJECT reversals** —
every transition moves through, or into/out of, an intermediate CAUTION
state. The remaining 128 (7.5%) are ACCEPT→CAUTION additions, 69 of
which are false positives on benign traffic and 59 of which are real
attacks B3 alone missed entirely.

**Interpretation.** Fusion's behavior matches its designed intent
(`trust_engine/policy.py`'s documented floor rules): it does not make
binary calls more aggressively; it routes uncertain or corroborating
evidence through an intermediate CAUTION state, escalating already-
suspicious signals to REJECT when crypto/structural evidence corroborates
them, and adding caution (not rejection) when crypto evidence alone
raises a concern B3's text analysis missed. This is direct empirical
support for a specific architectural design claim (graded-uncertainty
fusion), not merely a small accuracy delta.

**Implication for the architecture.** The Trust Decision Engine's value
is not well captured by a single aggregate metric — its real contribution
is in decision *structure* (escalation and graded caution) rather than
raw detection-rate improvement. This finding should be reported using the
3-way transition numbers, not the binary F1 delta alone, or it will read
as a much weaker result than it is.

---

### §R3 — RQ3: Do the kinematic/behavioral layers detect real V2X kinematic attacks with no semantic content?

**Experiment.** VeReMi kinematic companion bench (`results/veremi_kinematic/`,
n=13,511 real VeReMi messages, 360 vehicles, 180 confirmed VeReMi-labeled
attackers across three real attack types — constant-position
falsification/ConstPos, data replay/DataReplay, DoS/flooding —
and 180 benign, no semantic transformation applied at all, no injected
text). Evaluated with a stateful, per-vehicle replay methodology (a
fresh pipeline per vehicle, persistent within that vehicle's own real
message sequence), because kinematic/behavioral attacks are only
detectable by comparing a sender's reports against its own history —
confirmed necessary by a direct example before the full run (VeReMi
sender 8193 only triggers MBD's constant-position check given real
history; the same report evaluated in isolation has none).

**Findings.** MBD (config 2; configs 3/4 are byte-identical, see §R4):
per-message Recall=0.7752, Precision=0.6074, F1=0.6811, FPR=0.5237. By
attack type: ConstPos Recall=0.9117/FPR=0.5736 (best detected), DoS
Recall=0.8035/FPR=0.4968, DataReplay Recall=0.6002/FPR=0.5011 (weakest).
Per-vehicle "ever flagged at least once over the sequence": Recall=0.9925
but FPR=0.9935 — almost every benign vehicle is also flagged at least
once (`results/veremi_kinematic/analysis_summary.json`). B3 (config 4)
is byte-identical to config 3 (no B3) on every one of 13,511 messages —
confirms zero contribution, exactly as expected on text-free messages.

**Interpretation.** MBD demonstrably detects real kinematic/behavioral
attacks with substantial recall (60-91% depending on attack type), at
the cost of a real, honestly-reported precision limitation (~50-58%
per-message FPR). The per-vehicle "ever flagged" policy is not currently
usable as a standalone decision rule (99.4% FPR) — MBD's signal is
recall-oriented and intended to feed fusion/CAUTION, not act as a
standalone precise classifier (consistent with the fusion behavior found
in §R2).

**Implication for the architecture.** MBD is a necessary, working
component for the kinematic/behavioral threat class — the exact class
STBV-Bench (§R1) cannot exercise by design, since STBV-Bench keeps
kinematics real and unmodified. This result should never be compared
directly against §R1's numbers as a same-benchmark ranking; the two
measure detection on disjoint threat classes with disjoint ground truth.

---

### §R4 — RQ4: Is Cooperative Perception (CP) functioning as designed?

**Experiment.** An empirical check requested specifically to verify (not
assume) CP's contribution: 120 real multi-vehicle Phase-2 fixture
messages replayed with CP on vs. off (`stbv_bench/verify_cp_empirical.py`).

**Findings.** Initial result: 0/120 decision flips despite `num_reports`
reaching 20 real reports per window — `cp_confidence` was exactly 1.0 on
every single message across every scenario. Root-caused to a wiring bug:
`pipeline/orchestrator.py::_run_cp` never computed or passed an
`event_label` argument to `cp_layer()` (unlike the parallel `_run_mbd`
method, which does), so `cp_layer`'s `observations_available` flag was
permanently `False`, forcing CP into a neutral/vacuous branch regardless
of window size or sender count. **Fixed** (`pipeline/orchestrator.py`,
commit `6dc7df80c`), verified before applying that the fix changes zero
already-measured numbers (no benchmark generator in this evaluation ever
attaches an `event` field), and verified after applying that CP's scoring
genuinely activates on real event-bearing traffic (`scenarios/collusion`
now shows real, varying `cp_confidence` — 0.8, 0.835, 0.879 — and a real
`trust_score` delta between CP-on/CP-off; `results/ablation/cp_empirical_verification.json`).

**Interpretation.** CP's own consistency-scoring logic is correct and now
verified functional. However, **every benchmark constructed in this
evaluation effort — STBV-Bench v1/v2, the kinematic bench, the
mixed-threat bench — still measures zero CP contribution**, for a second,
independent, still-open reason: none of their message-generation code
paths attach event data for CP to act on. The wiring fix is necessary but
not sufficient for CP to be exercised on this paper's own generated
content.

**Implication for the architecture.** CP should be reported as a verified-
correct but not-yet-evaluated-on-this-paper's-benchmarks component, not
as either "broken" or "contributing." Closing this gap (adding event-label
generation to the semantic transformation engine) is future work.

---

### §R5 — RQ5: Are semantic and kinematic detection genuinely complementary?

**Experiment.** Two parts: (a) cross-referencing §R1 (B3 on semantic-only
attacks) against §R3 (MBD on kinematic-only attacks) — each measured on
its own disjoint benchmark; (b) the mixed-threat benchmark
(`results/mixed_threat/`, 120 windows, 4,123 messages), which places a
real kinematic attacker and an independently-injected semantic attacker
on *different* vehicles in the *same* shared multi-vehicle scene, so both
detectors can be observed operating simultaneously rather than only in
isolation.

**Findings.** (a) B3 shows ~0% contribution on kinematic-only content
(§R3: config 4 byte-identical to config 3); MBD shows only a small,
off-target contribution on STBV-Bench's semantic-only content (§R1's
ablation config 1→2: 124 true positives, attributed to incidental
kinematic side-effects of real VeReMi data, not the semantic payload
itself). (b) In the mixed-threat benchmark's 431 `mixed`-composition
messages: kinematic-attacker rows detected at 90.3% (139/154, via MBD);
semantic-attacker rows detected at 70.3% (97/138, via B3); 0/431 vehicles
were ever double-counted as both attacker types. Control comparisons:
`kinematic_only`-composition windows show 81.1% kinematic recall (90
rows); `semantic_only`-composition windows show 86.7% semantic recall
(633 rows).

**Interpretation.** Each detector operates on its own vehicle's own
evidence independently — this is NOT evidence of cross-vehicle
architectural synergy (Cooperative Perception, the only component that
could carry cross-vehicle influence, is confirmed inert per §R4 for this
benchmark's content). The correct claim is narrower but still real:
co-locating both threat types in a shared scene does not break either
detector. The mixed-composition sample's recall figures differ somewhat
from their pure-composition controls (90.3% vs. 81.1% kinematic; 70.3%
vs. 86.7% semantic); the semantic-side gap was investigated and resolved
as a family-mix sampling confound (only 14 raw `mixed`-composition
windows exist in this run, and 89% of their semantic-attacker message
volume is drawn from just 3 families, with a lower-recall family
supplying over a third of the sample from only 2 real vehicles) — not a
cross-vehicle interaction effect.

**Implication for the architecture.** The paper's complementary-
threat-class-coverage claim is supported specifically as: *B3 and MBD
cover non-overlapping threat classes, and neither one's detection is
degraded by the other threat type's presence in the same scene* — a
narrower, defensible claim, not "the architecture demonstrates
cross-layer synergy" (which would require CP, and is not yet supported).

---

### §R6 — RQ6: Does richer multi-vehicle context change semantic detection relative to isolated single messages?

**Experiment.** STBV-Bench v2 (`results/stbv_bench_v2/`, 150 real
multi-vehicle spatial-temporal windows built from VeReMi Extension
co-location clustering, 5,062 messages, single full-stack configuration
only — this benchmark has not been ablated). Two distinct metrics were
computed, answering two distinct sub-questions, and **must not be
conflated or ranked against each other or against §R1's number**:

**R6a — per-family attacker-sender recall** (does the designated attacker
vehicle's own detection improve with richer context?). Measured only on
the 1,387 attacker-sender messages (`results/stbv_bench_v2/analysis_summary.json`).
Every family that was weak in STBV-Bench v1 (§R1) improved, none
regressed, and every family already at 100% in v1 stayed at 100%:
`goal_manipulation` 0.01→0.76 (+75pp), `indirect_prompt_injection`
0.02→0.62 (+60pp), `semantic_narrative_poisoning` 0.09→0.62 (+53pp),
`multi_message_context_poisoning` 0.02→0.54 (+52pp), `traffic_efficiency_lure`
0.01→0.50 (+49pp), plus smaller gains on 7 other families. Root-caused by
direct text inspection, not assumed: v1's isolated-message synthesized
text always ends with the literal marker "No other vehicles in
cooperative cluster"; v2's real windows instead produce genuine
"Cluster peer N..." context sentences, and the identical injected
payload sentence is classified more reliably by B3 when surrounded by
this richer context. A direct causal example (window `stbv2-00008`)
shows one fixed payload sentence's decision flipping from ACCEPT to
CAUTION purely as filler context accumulates from 0 to 10 sentences,
with no change to the attack text itself; 22.7% of multi-message
attacker-sender sequences show this same within-sequence pattern.

**R6b — full-corpus Decision Trust metrics** (what is the architecture's
aggregate accuracy across ALL traffic in these windows, including real
ambient bystander vehicles, computed the identical way §R1's v1 metric
is computed?). `results/stbv_bench_v2/full_corpus_decision_trust_metrics.json`:
Accuracy=0.5476, Precision=0.3654, Recall=0.8839, **F1=0.5171**, FPR=0.5793
— computed over all 5,062 messages. This is a **worse** F1 than v1's
0.7175 (§R1/§R2), and this is not in tension with R6a — it measures a
different thing. 3,675 of v2's 5,062 messages are real, unmodified
bystander vehicles with no equivalent in v1 (every v1 sample is either
a designated `benign_control` or a designated attacker, never an
incidental bystander); MBD flags 57.9% of these bystanders as CAUTION
(fp=2,129 of 3,675), closely matching §R3's independently-measured ~52%
baseline per-message FPR on real VeReMi kinematics — the same real MBD
behavior, now visible in an aggregate metric specifically because v2 is
the first STBV-Bench harness to include genuine ambient real traffic.

**Interpretation.** Two real, non-contradictory findings: (R6a) B3's
detection of a specific semantic attacker measurably improves given
richer, realistic scene context — a genuine finding, though its full
causal explanation is only partially resolved (context-volume sensitivity
in B3 is confirmed as a real contributor by direct example, but the
correlation between context volume and detection is inconsistent in
direction for 2 of the 6 improved families, so a pure "more text helps"
explanation is not fully established either; real-world representativeness
remains a live alternative/contributing explanation). (R6b) The
architecture's aggregate false-positive behavior, measured honestly on
the same terms as v1, gets substantially worse once genuine ambient
multi-vehicle traffic is included, because MBD's real, independently-
confirmed FPR (§R3) now applies to a much larger fraction of the evaluated
traffic than v1's design ever exposed it to.

**Implication for the architecture.** STBV-Bench v1 (§R1) and STBV-Bench
v2 (§R6) answer different questions under different evaluation regimes
and must be reported side by side, not as competing rankings of "the"
architecture's performance: v1 measures detection under a controlled,
isolated-message regime; v2 measures detection AND aggregate false-positive
behavior under a more realistic, but also more MBD-FPR-exposed, ambient-
traffic regime. Citing only R6a (recall improvement) without R6b (FPR
degradation) — or vice versa — would misrepresent v2's actual net effect.

---

### §R7 — RQ7: Is B3 robust to adversarial and incidental text perturbations?

**Experiment.** `b3_eval/run_robustness.py` against the 120-scenario
corpus's payload texts, 11 perturbation families
(`b3_eval/results/robustness.json`).

**Findings.** Most perturbation families show low flip/over-defense
rates (`synonym_sub`, `formatting`, `long_prompt`, `context_poisoning`,
`contradictory`: 0.000 flip rate). Two families show a severe,
previously-unmeasured weakness: **`instruction_hiding`** and
**`role_confusion`** both show flip_rate=0.500 and **over_defense_fpr=1.000**
— every benign message perturbed this way, in this test, was misclassified
as malicious. `unicode_homoglyph` also shows a notable over-defense rate
(0.667). `paraphrase` and `mixed_benign_malicious` show a real evasion
rate of 0.333 (genuine attacks slipping past detection under paraphrase).

**Interpretation.** B3 exhibits the specific failure mode the 2024-2026
adversarial-robustness literature predicts for generic injection
classifiers: over-sensitivity to trigger-adjacent phrasing (discussing
instructions/roles without actually attacking) and some vulnerability to
paraphrase-based evasion.

**Implication for the architecture.** This must be reported as a
named, explicit limitation (not folded into an aggregate robustness
score) — `instruction_hiding`/`role_confusion`'s 100% over-defense rate
is a severe, narrow, and easily-overlooked finding relative to any
headline accuracy number, and a reviewer evaluating deployability will
look for exactly this class of result.

---

### §R8 — RQ8: Is B3's confidence calibrated, and does it fail safely on unseen attacks?

**Experiment.** `b3_eval/run_calibration.py` (n=85) and
`b3_eval/run_open_set_analysis.py` (85 in-distribution + 25
out-of-distribution/unseen-attack-family samples).

**Findings.** Calibration: ECE=0.0619 before temperature scaling,
0.0280 after (T=2.145, ~55% relative reduction); Brier score 0.0613→0.0553
(`b3_eval/results/calibration.json`). Open-set: miss rate on unseen
families=0.000, silent-failure rate (wrong AND confidence≥0.85)=0.000,
dead-zone occupancy=0.000; AUROC for OOD separation: MSP=0.154,
energy=0.098, but raw p_malicious=0.994 (`b3_eval/results/open_set_analysis.json`).
AURC=0.0082; coverage at risk≤0.01 is 0.800, at risk≤0.05 is 0.953.

**Interpretation.** Temperature scaling is a cheap, effective, no-retrain
calibration fix. On unseen attack families, B3 fails *loudly* (low
confidence) rather than silently (confidently wrong) — the existing
Theta-mass/CAUTION fusion path (§R2) already routes low-confidence cases
appropriately, so no additional abstain mechanism is needed. Notably, the
standard OOD-detection scores (MSP, energy) perform poorly here; the raw
calibrated malicious-class probability is a far better separator — a
specific, reportable finding about which score to trust for this model.

**Implication for the architecture.** No architectural change is
warranted for open-set safety; a one-line "apply temperature scaling
with T=2.145" recommendation should be adopted for calibration, and the
choice not to add an abstain mechanism should be stated as an evidence-
backed decision, not an oversight.

---

### §R9 — RQ9: Is the deployed B3 backbone justified relative to alternatives?

**Experiment.** `b3_eval/run_model_benchmark.py`: fine-tunes 5 candidate
architectures (DeBERTa-v3-base, RoBERTa-base, ModernBERT-base,
DistilRoBERTa-base, MiniLM-L12) on the same 96-example train split,
evaluated on a 24-sample test split, compared against the deployed
incumbent (`semantic_gate_v3`) — `b3_eval/results/model_benchmark.json`.

**Findings.** Incumbent: Accuracy=0.833, Precision=1.000, Recall=0.810,
F1=0.895 (tp=17, fp=0, fn=4, tn=3). Four candidates (RoBERTa, ModernBERT,
DistilRoBERTa, MiniLM) each scored a nominally higher F1=0.933
(Precision=0.875, Recall=1.000), but **each has tn=0** — each predicted
MALICIOUS unconditionally on all 24 test samples, correctly identifying
zero of the 3 truly-benign samples. `microsoft/deberta-v3-base` errored
during training (`ValueError: Attempting to unscale FP16 gradients`).

**Interpretation.** The 4 higher-F1 candidates are near-degenerate
always-positive classifiers on a class-imbalanced (21/24 malicious)
24-sample test split — their F1 advantage is a class-imbalance artifact,
not evidence of better semantic understanding. Only the incumbent
discriminates at all (tn>0, precision=1.000).

**Implication for the architecture.** The incumbent model choice is
justified relative to these candidates on the evidence available, but
the test split (n=24) is too small to be a strong architecture-selection
signal either way; this should be reported as "no evidence favoring a
switch," not "the incumbent was proven best," and never as a raw F1
leaderboard without the near-degeneracy caveat attached.

---

### §R10 — RQ10 (methodological validity check): Was the original 120-scenario benchmark valid?

**Experiment.** Investigated the 120-scenario `semantic_evaluation`
corpus (`semantic_evaluation/semantic_attack_dataset.py`) for
dataset-leakage risk, after its full-stack result (Accuracy=0.983,
F1=0.990, `results/semantic/20260801-005223/metrics_summary.json`) was
flagged as one of several conflicting "full architecture" headline
figures found across the project's history.

**Findings.** The corpus's own module docstring states its payload
texts are "aligned to the phrasing styles of the model's actual training
distribution (AF1-AF9 families, Case 1-Case 4...)". Every one of its 120
scenarios' `rationale` fields explicitly names the B3 training-family
template it was built to instantiate (18+ such lines, verified by grep).
That exact taxonomy is independently confirmed as B3's own internal
training/development vocabulary in three files under
`b3/solution_stb/b3_semantic_gate/`. Literal string-level duplication
against B3's actual raw training data could not be confirmed (that file
is not present in this checkout).

**Interpretation.** This corpus is not a valid disjoint external
evaluation of B3's generalization — its authors had direct visibility
into B3's training taxonomy and deliberately aligned scenario phrasing
to it. This does not prove literal duplication, but it establishes a
real, non-hypothetical train/test distribution-matching mechanism that
would inflate F1 relative to a genuinely disjoint benchmark such as
STBV-Bench.

**Implication for the architecture.** The 0.990 figure must not be
reported as a headline detection-accuracy result. It remains valid as
the underlying corpus for the robustness (§R7), calibration, and
open-set (§R8) sub-studies, which measure B3's own behavior under
perturbation/uncertainty rather than making a comparative detection
claim, and are not compromised by this concern in the same way a
detection-accuracy headline would be.

---

## Discussion

### The architecture's contribution, stated at the correct grain

The central claim this evidence supports is **complementary threat-class
coverage**, not uniform per-layer participation in every decision, and
not a single "the architecture achieves X%" headline. Specifically:

- B3 (§R1) is necessary and largely sufficient for the semantic (STBV)
  threat class, with a real, bounded capability gap on subtle/indirect
  phrasing.
- MBD (§R3) is necessary and largely sufficient for the kinematic/
  behavioral threat class, with a real, bounded precision limitation.
- These two capabilities are confirmed non-overlapping in both
  directions (§R5): B3 contributes ~0 to kinematic-only detection; MBD
  contributes ~0 (beyond incidental side effects) to semantic-only
  detection; and both continue to function when both threat types
  co-occur in a shared scene.
- The Trust Decision Engine's fusion (§R2) does not primarily add raw
  detection rate; its measurable contribution is structural — routing
  uncertain evidence through CAUTION and escalating corroborated
  suspicion to REJECT — a small effect on aggregate F1 but a real,
  significant, and architecturally meaningful one at the decision level.
- Cooperative Perception (§R4) is verified functioning at the code level
  but has not yet been exercised on any of this paper's own constructed
  benchmarks, and should be reported as such, not folded into either the
  "working" or the "contributing" column.

### Why no single number should be reported as "the" result

§R1, §R6a, §R6b, and §R10 each produce a number that superficially looks
like "architecture accuracy," and this document's organizing rule exists
specifically to prevent them from being ranked against each other:

- §R1 (v1, F1=0.7175) and §R10 (120-scenario corpus, F1=0.990) are not
  comparable — §R10's corpus has a confirmed methodological validity
  problem (§R10's own finding), so it cannot serve as a stronger or
  weaker version of §R1's result; it answers a different, compromised
  question.
- §R1 (v1) and §R6b (v2 full-corpus, F1=0.5171) are not comparable as a
  "v2 improves/degrades on v1" ranking — they use different ground-truth
  populations (v1 has no ambient bystanders; v2's aggregate necessarily
  includes MBD's real baseline FPR on real traffic) and answer different
  questions (controlled isolated-message detection vs. aggregate
  performance under realistic ambient traffic).
- §R6a (per-family attacker recall improvement) and §R6b (full-corpus
  F1 decline) are not in tension with each other, and neither should be
  quoted without the other — they are two different, both-real
  measurements of the same experiment, decomposing what "richer context"
  does to detection (helps the specific attacker) versus what it does to
  aggregate precision (exposes MBD's real FPR to more traffic).

### What remains open

STBV-Bench v2 has not been ablated (only the full-stack configuration
has been run — §R6), so its findings cannot yet be decomposed by layer
the way v1's can (§R1/§R2). The mixed-threat benchmark's exact recall
percentages (§R5) rest on a small, non-family-stratified sample and
should be treated as directionally indicative rather than precise. CP
(§R4) requires a further, unscoped change (event-label generation in the
semantic transformation engine) before it can be evaluated on this
paper's own benchmarks at all. Two previously-referenced "full
architecture" figures (0.859, 98.8%) could not be traced to any file in
this repository and, if they appear in any external manuscript draft,
require the same correction applied here.
