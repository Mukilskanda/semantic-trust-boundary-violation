# Adversarial Pre-Submission Review — `stbv_paper.tex`

**Mandate.** Three independent reviewers, each attempting to reject.
Weaknesses are only listed where they are verifiable from the paper, its
companion documents, or the repository's own result files — nothing here
is a hypothetical objection. Every claim below was checked against the
actual artifacts.

**Reviewers.**
- **A** — IEEE T-ITS (transportation systems; deployment realism, ITS standards, real-world validity)
- **B** — IEEE TDSC (dependability & security; threat models, does-the-defense-actually-work)
- **C** — IEEE TIFS (forensics & security; ML-security rigor, data provenance, adversarial robustness, statistics)

---

## Verdict summary (read this first)

| Reviewer | Recommendation | One-line basis |
|---|---|---|
| **A (T-ITS)** | **Reject** | Fails its own real-time requirement by ~30×, and rejects 72.5% of a benign vehicle's messages in the only live test. |
| **B (TDSC)** | **Reject** | The proposed defense detects 0/240 live attacks and is evaded 83.7% of the time by a scripted attacker. The security claim is not supported. |
| **C (TIFS)** | **Reject** | No baseline comparison of any kind; training data is off-machine and unverifiable; an unaddressed shared-source leakage path between B3's training data and the evaluation benchmark. |

**Unanimous.** This paper is not currently publishable at any of the
three venues. It is, however, *salvageable* — see §7. The core problem
is not that the results are bad; it is that the paper **frames a set of
substantially negative results as a positive contribution**, and omits
the comparisons that would let a reviewer judge the contribution at all.

---

## 1. CRITICAL weaknesses (any one is sufficient for rejection)

### C1 — No baseline comparison whatsoever
- **Severity:** CRITICAL
- **Raised by:** A, B, C (unanimous)
- **Reason:** The paper proposes a semantic verification layer and never
  compares it against *any* alternative: no keyword/regex baseline, no
  classical classifier (TF-IDF + SVM/LR), no zero-shot or few-shot LLM
  judge, no published misbehavior-detection baseline. Verified: zero
  occurrences of any baseline-method comparison in the source. This
  matters most because the VeReMi and VeReMi Extension papers
  (van der Heijden et al. 2018; Kamel et al. 2020) *ship published
  baseline detectors on the exact dataset this paper evaluates on*, and
  the paper cites Kamel et al. for the data while ignoring their
  baselines. A reviewer cannot determine whether a 141.9M-parameter
  transformer beats `grep -i "ignore previous instructions"`.
- **Required fix:** Add at minimum three baselines on STBV-Bench v1:
  (i) a lexical/regex detector over known attack phrasings, (ii) a
  TF-IDF + logistic regression classifier trained on the same data,
  (iii) an off-the-shelf instruction-tuned LLM as zero-shot judge. Add
  published VeReMi baselines for the kinematic benchmark. Report all
  with the same metrics and CIs.
- **Confidence:** **High.** This is an absolute requirement at all three
  venues; no amount of rebuttal substitutes for it.

### C2 — The headline fusion contribution is, on the paper's own numbers, net-harmful
- **Severity:** CRITICAL
- **Raised by:** B, C
- **Reason:** Config 4 (no fusion) → Config 5 (full stack), from
  Table `tab:full_ablation`: F1 $0.715 \to 0.718$ (**+0.003**), Recall
  $0.557 \to 0.565$ (+0.008), **Precision $1.000 \to 0.983$ (−0.017)**,
  **FPR $0.000 \to 0.023$ (+0.023)**. Fusion buys 0.8 points of recall
  by giving up perfect precision and introducing 69 false positives
  where there were zero. The paper describes this as a "small but
  statistically significant, structurally meaningful effect"
  (McNemar $p=3.06\times10^{-29}$) — but a $p$-value on $n=10{,}000$
  detects a 0.003 F1 shift trivially; significance here is a sample-size
  artifact, not evidence of value. The paper never states the
  precision/FPR *cost* in the abstract or conclusion, only the benefit.
- **Required fix:** Report the fusion delta as a signed trade-off
  (recall gain vs. precision/FPR loss) everywhere it appears, including
  the abstract. Justify with a cost model why +0.008 recall is worth
  −0.017 precision in a V2X setting, or withdraw the claim that fusion
  contributes positively. Replace the bare $p$-value with an effect size
  and its CI.
- **Confidence:** **High.** The numbers are the paper's own.

### C3 — Undisclosed shared-source path between B3's training data and the evaluation benchmark
- **Severity:** CRITICAL
- **Raised by:** C (B concurs)
- **Reason:** Appendix `app:provenance` (added from the model author's
  account) states B3's Dataset B was built **from VeReMi Extension
  kinematic values formatted as ETSI CAM/DENM/CPM messages**, and
  Dataset C used **"3 VeReMi kinematic variants" with "real VeReMi
  grounding"**. STBV-Bench v1 is **"built from real VeReMi Extension
  trajectories"** and rendered to scene text by this repository's
  synthesizer. Both sides of the evaluation therefore derive from the
  *same source dataset* and both render it into *ETSI-convention message
  text*. The paper's only defense is a **taxonomy-level** claim ("zero
  family-name overlap"), which does not address distributional or
  formatting overlap at all. Verified: the paper never discusses this
  shared source as a leakage vector. This directly undercuts the
  headline claim that STBV-Bench is a held-out evaluation.
- **Required fix:** (i) Quantify overlap between B3's training text and
  STBV-Bench text with embedding-similarity and n-gram overlap
  distributions, reported explicitly. (ii) Report B3 performance on a
  benchmark built from a *non-VeReMi* trajectory source. (iii) Until
  done, downgrade all STBV-Bench numbers from "held-out evaluation" to
  "in-domain evaluation with a shared trajectory source."
- **Confidence:** **High** that a reviewer raises it; **Medium** on the
  magnitude of actual contamination (it may be small — but the paper
  currently provides zero evidence either way, which is the problem).

### C4 — The paper's principal contribution detects nothing in the only live deployment test
- **Severity:** CRITICAL
- **Raised by:** A, B
- **Reason:** Section `sec:deployment` / Table `tab:carla_scenarios`:
  B3 returned `BENIGN` on **all 400** live-CARLA messages, including
  **all 240 attack-scenario messages across six attack types**. Every
  Reject in that table comes from B1/MBD/CP. The two scenarios with no
  kinematic signature — precisely B3's stated threat class —
  scored **0/40 Reject**. The paper calls B3 "this architecture's
  principal contribution" (Section III). A defense with 0% recall in its
  own live evaluation, against its own designed threat class, is not a
  validated defense. The paper discloses this honestly (creditably) but
  then does not revise its contribution claims accordingly.
- **Required fix:** Either (i) diagnose and fix the distribution shift
  and re-run, or (ii) restate the paper's contribution as
  "STBV-Bench + a negative result on live transfer," which is a
  publishable but very different paper. The current framing —
  strong headline numbers with the live failure in a later subsection —
  will read to reviewers as burying the lede.
- **Confidence:** **High.**

### C5 — Adaptive attacker defeats the defense 83.7% of the time
- **Severity:** CRITICAL
- **Raised by:** B, C
- **Reason:** Section `sec:adaptive`: 41/49 seeds evade within a
  10-round budget, median ~3 rounds, using *deterministic scripted text
  transforms* — not gradient attacks, not an LLM adversary. Detection
  probability collapses 1.000 → 0.163. The dominant strategy is padding
  with benign filler. For TDSC/TIFS, a security mechanism broken by a
  9-strategy greedy search is not a security mechanism. The paper's
  threat model excludes adaptive attackers *by scope*, yet the paper
  itself demonstrates the attack succeeds — an internal contradiction
  between the scope claim and the reported evidence.
- **Required fix:** Either demonstrate a mitigation (adversarial
  training, the structural filler-padding detector the paper itself
  identifies, ensembling) with re-measured ASR, or reposition the
  paper's claim from "defense" to "measurement study of a defense's
  brittleness." A security venue will not accept "adaptive attackers are
  out of scope" alongside an in-paper 83.7% ASR.
- **Confidence:** **High.**

---

## 2. MAJOR weaknesses

### M1 — No ablation isolating Dempster–Shafer fusion from the policy floors
- **Severity:** MAJOR
- **Raised by:** B, C
- **Reason:** The paper states plainly (Section `sec:tde`,
  `dempster_shafer.py`) that Yager's rule *alone will not* drive a
  decision to Reject, and that two explicit policy floors do that work.
  The five ablation configs vary *layers*, never the fusion mechanism.
  So there is no evidence that the DS/Yager machinery contributes
  anything beyond what the two floors (`B3 HIGH → Reject`,
  `B3 MED/LOW → ≥Caution`) plus threshold banding would achieve alone.
  Given C2 (fusion's net effect is +0.003 F1 at a precision cost), the
  natural reviewer hypothesis is that **the DS formalism is decorative**
  and a 6-line rule table would reproduce the results. The paper's own
  "low parameter sensitivity" finding actively supports this reading:
  it reports that sensitivity is low *because the floors dominate*.
- **Required fix:** Add configs: (a) floors only, no DS combination;
  (b) DS combination only, floors disabled; (c) full. If (a) $\approx$
  (c), the DS contribution must be withdrawn or re-scoped to the
  uncertainty-propagation property alone.
- **Confidence:** **High.**

### M2 — Three mutually inconsistent latency figures for the same system
- **Severity:** MAJOR
- **Raised by:** A, C
- **Reason:** (i) Section `sec:results`: end-to-end mean **110 ms**
  ($p_{99}=254$ ms) on STBV-Bench. (ii) Table `tab:deployment`: mean
  **66.8 ms** (SUMO) / **80.0 ms** (CARLA), with the B3 bridge alone at
  65.9 ms. (iii) Appendix `app:provenance` (model author's account):
  B3 inference **"~3–6 ms/message, mean 20–28 ms, P99 < 50 ms"**. Figure
  (iii) is 10–20× faster than the paper's own measurement of the same
  component in (ii), on the same GPU class. None of these are
  reconciled, and (i) vs (ii) differ by 1.6× on the same pipeline. A
  reviewer will conclude the latency methodology is unreliable, which
  contaminates the real-time feasibility argument that is T-ITS's core
  interest.
- **Required fix:** One measurement protocol, one hardware spec, one
  table; explicitly reconcile or retract the provenance-report latency
  figures; state what differs between the STBV-Bench harness and the
  deployment harness that produces a 1.6× gap.
- **Confidence:** **High.**

### M3 — Fails the real-time requirement it sets for itself, by ~30×
- **Severity:** MAJOR
- **Raised by:** A
- **Reason:** The paper's own analysis: sustained throughput 11.2–15.0
  msg/s against a stated requirement of 20–460 msg/s at realistic
  concurrency (mean 19.8 / max 46 vehicles at 1–10 Hz CAM). It fails
  even the *least* demanding case. Additionally $p_{99}=254$ ms on
  STBV-Bench exceeds the 100 ms CAM interval by 2.5×. For T-ITS,
  "does not meet real-time constraints" is close to dispositive for a
  V2X in-loop trust gate.
- **Required fix:** Implement the batching the paper itself identifies
  and re-measure, or restrict the claimed deployment target to a
  scope where 11–15 msg/s suffices (e.g. a single ego-vehicle
  processing only DENMs) and justify that scope quantitatively.
- **Confidence:** **High.**

### M4 — 72.5% of a benign vehicle's messages are Rejected in the live test
- **Severity:** MAJOR
- **Raised by:** A, B
- **Reason:** Table `tab:carla_scenarios`, `normal_driving` (ground
  truth: benign): 29/40 Reject, 10 Caution, 1 Accept. A trust gate that
  discards ~3 of every 4 messages from an ordinary, correctly-behaving
  vehicle decelerating at an intersection is unusable. This compounds
  MBD's independently measured 52.4% per-message FPR and 99.4%
  per-vehicle "ever-flagged" FPR on real VeReMi data. The paper
  describes the mechanism honestly but does not confront the
  operational implication: cooperative perception would be effectively
  disabled in urban driving.
- **Required fix:** Re-tune MBD's deceleration sensitivity and re-run;
  report benign-traffic FPR as a headline metric alongside recall, not
  only inside a failure appendix. Add a per-scenario CI (currently
  $n=40$, one run).
- **Confidence:** **High.**

### M5 — Training data is off-machine, unverifiable, and not reproducible
- **Severity:** MAJOR
- **Raised by:** C (B concurs)
- **Reason:** The training corpus and all construction/training scripts
  are absent from the repository (verified: `train_b3_v3.py`,
  `build_dataset_C_v3.py`, `corpus/` etc. do not exist here). Their
  description comes from a narrative account of a different machine,
  which cannot be re-executed or byte-verified. That account itself
  discloses: LLM-generated training data at temperature 0.8–0.9 **with
  no fixed seed** (not reproducible), a **0.7% junk-row data-quality
  bug whose cleanup was written but not confirmed applied**, and a 9th
  attack family **not integrated into the evaluated checkpoint**. The
  paper therefore evaluates a model whose exact training set is not
  reconstructable, not reproducible, and not identical to the one
  described.
- **Required fix:** Deposit the corpus, the construction scripts, and
  the training script in an archival repository with a DOI; re-run the
  cleanup and re-train, or state precisely which checkpoint corresponds
  to which corpus state. Absent that, all training-side claims must be
  marked as third-party-reported.
- **Confidence:** **High.** Reproducibility policies at all three
  venues make this a formal compliance issue, not a matter of taste.

### M6 — Cooperative Perception's showcase benchmark has an 85% false-positive rate
- **Severity:** MAJOR
- **Raised by:** A, B
- **Reason:** `CP_FULL_EVALUATION.md` / Section `sec:cp_full`: on the
  142-message benchmark purpose-built to show CP working, the full stack
  produces **121 false positives** (benign at Caution/Reject) —
  85% of the corpus — of which CP itself adds 22 on top of a 99-FP
  baseline. The paper isolates CP's marginal +11 attacker detections and
  foregrounds that, while the absolute operating point (85% FPR) is
  disclosed but not confronted. A system at that FPR has no operational
  meaning regardless of marginal attribution.
- **Required fix:** Report the absolute operating point in the same
  table as the marginal effect; state explicitly that this benchmark
  cannot be used to claim deployment readiness for CP; fix the MBD
  collusion-score confound driving the 99-FP baseline before claiming
  CP's contribution is interpretable.
- **Confidence:** **High.**

### M7 — Evidence is cited to internal Markdown files, not to the paper or archival material
- **Severity:** MAJOR
- **Raised by:** C
- **Reason:** ~20 `\texttt{*.md}` citations carry substantive evidential
  load (`FAILURE_ANALYSIS.md` ×7, `SAFETY_ANALYSIS.md` ×6,
  `THEORETICAL_ANALYSIS.md` ×2, plus deployment/CP/adaptive documents).
  These are not archival, not peer-reviewed, not versioned, and not
  accessible to a reader. Several load-bearing claims (all six
  proofs; the entire failure taxonomy; every safety risk rating) exist
  *only* there. A paper cannot outsource its proofs to an unpublished
  file.
- **Required fix:** Move the proofs into the paper or a formal
  supplementary PDF submitted with it; convert the analysis documents
  into properly archived supplementary material with a DOI; ensure every
  claim in the main text is supported *in* the main text or its official
  supplement.
- **Confidence:** **High.**

### M8 — The formal propositions are near-trivial and oversold
- **Severity:** MAJOR (at TIFS/TDSC), MODERATE (at T-ITS)
- **Raised by:** C, B
- **Reason:** Section `sec:theory` presents six "propositions." On
  inspection: P1/P3 are the observation that a composition of
  $\max$ operations over a 3-element ordinal set is monotone
  non-decreasing; P4 is the standard, textbook property of Yager's rule
  (published 1987) restated; P6 is the identity-element property of a
  vacuous mass function, also textbook DS theory; P5 is "the function
  has no missing `else` branch." Only P2's closed-form derivative
  ($dT/ds = \tfrac12 c(1+m_\Theta^{(2)})$) is a non-obvious
  contribution, and it is one line of algebra. Presenting these as a
  "theoretical contribution" invites the response that the paper
  restates known DS properties and calls code inspection a proof.
  Compounding this: the propositions are proved about the *implementation's
  control flow*, which is a software-verification exercise, not a
  security-theoretic one.
- **Required fix:** Retitle to "Correctness properties of the
  implementation" and drop the framing of theoretical novelty; or
  strengthen into a real contribution — e.g. prove a bound on the
  worst-case decision degradation under a bounded-adversarial input
  perturbation to one source, which would connect the formalism to the
  paper's actual (adaptive-attack) problem.
- **Confidence:** **High** at TIFS; **Medium** at T-ITS.

### M9 — Paper does not compile: missing figure
- **Severity:** MAJOR (submission blocker, trivially fixable)
- **Raised by:** A, B, C
- **Reason:** `\includegraphics[width=\linewidth]{fig1.png}` (line 68)
  references a file not present in the repository. The document will
  fail to build from the submitted source. Editorial desk-check at all
  three venues will flag this before review.
- **Required fix:** Supply `fig1.png` or remove the reference.
- **Confidence:** **High** (verified directly).

---

## 3. MODERATE weaknesses

### D1 — Benchmark prevalence (70/30 malicious) is unrealistic and inflates precision/F1
- **Severity:** MODERATE
- **Raised by:** C
- **Reason:** Real V2X attack prevalence is orders of magnitude lower.
  The paper acknowledges this in Limitations and correctly directs
  readers to FPR — but still reports precision/F1 at 70/30 as headline
  numbers, including in the abstract. At a realistic 0.1–1% prevalence,
  the same FPR (0.023) yields precision far below the reported 0.983.
- **Required fix:** Report precision at several realistic prevalences
  (0.1%, 1%, 5%) alongside the corpus figure, or lead with FPR/recall.
- **Confidence:** High.

### D2 — Deployment evaluation has no repetitions, seeds, or confidence intervals
- **Severity:** MODERATE
- **Raised by:** A, C
- **Reason:** $n=400$ live messages, 40 per scenario, one CARLA run, one
  town, one seed, one GPU. All deployment conclusions (including the
  CRITICAL C4 finding and the M4 FPR finding) rest on a single
  unreplicated run with no variance estimate. The paper acknowledges
  this but still draws strong conclusions from it.
- **Required fix:** ≥5 runs with different seeds and ≥2 towns; report
  mean ± CI per scenario.
- **Confidence:** High.

### D3 — Evaluation scenarios were modified after observing system behavior
- **Severity:** MODERATE
- **Raised by:** B, C
- **Reason:** The CARLA CP-window construction was revised mid-session
  after the initial configuration produced Rejects on benign DENM
  scenarios. The revision is documented and defensible (the original
  window was not a coherent CP query), but it is nonetheless *tuning the
  evaluation after seeing results*, which requires pre-registration-style
  disclosure to avoid the appearance of favorable selection.
- **Required fix:** Report both configurations' results side by side, so
  the reader sees what the un-tuned construction produced.
- **Confidence:** Medium-High.

### D4 — Six of twenty attack families at ≤9% recall; ten more between 42–65%
- **Severity:** MODERATE
- **Raised by:** A, B
- **Reason:** The "100% precision / 55.7% recall" headline masks that
  only 8/20 families work well, 6/20 are near-total failures (1–9%), and
  the remaining 6 sit at 42–65%. Aggregate recall on a benchmark whose
  family mix is chosen by the authors is not a meaningful capability
  estimate — changing the family proportions changes the headline
  number arbitrarily.
- **Required fix:** Lead with the per-family distribution rather than
  the aggregate; justify the family mix or report macro-averaged recall.
- **Confidence:** High.

### D5 — Timing data taken from a harness the paper itself calls leakage-compromised
- **Severity:** MODERATE
- **Raised by:** C
- **Reason:** Fig. `fig_latency_per_stage` uses the 120-scenario
  diagnostic harness. The paper flags that harness's *accuracy* results
  as leakage-compromised and excludes them, then uses its *timing* data,
  arguing timing is unaffected by label leakage. The argument is
  reasonable but invites the question of why a discredited harness is
  used at all when the deployment evaluation (Section `sec:deployment`)
  now produces per-stage timings from a clean run.
- **Required fix:** Replace with per-stage timings from the SUMO/CARLA
  deployment runs, which are uncontaminated and already measured.
- **Confidence:** High. (Low-cost fix — the data already exists.)

### D6 — Model identity ambiguity (DeBERTa-v2 vs. deberta-v3-small)
- **Severity:** MODERATE
- **Raised by:** C
- **Reason:** The paper says "DeBERTa-v2 sequence classifier"; the
  provenance appendix says `microsoft/deberta-v3-small`. Both can be
  true (`config.json` reports `model_type: deberta-v2` because v3
  checkpoints use the DebertaV2 architecture classes), but as written
  the paper misidentifies the pretrained model. Readers cannot
  reproduce without knowing which checkpoint was fine-tuned.
- **Required fix:** State "DeBERTa-v3-small, fine-tuned; DebertaV2
  architecture classes" once, explicitly.
- **Confidence:** High.

### D7 — No human validation of generated benchmark labels
- **Severity:** MODERATE
- **Raised by:** C
- **Reason:** STBV-Bench's ground truth is assigned by the generator
  that produced the text. No human annotation, no inter-rater
  reliability, no verification that "malicious" samples are actually
  semantically malicious to a competent reader. If the generator emits a
  benign-reading sentence labeled malicious, B3's "misses" may be
  correct behavior mislabeled as failure.
- **Required fix:** Human-annotate a stratified sample (≥300, ≥2
  annotators, report Cohen's $\kappa$) and report label accuracy.
- **Confidence:** High.

### D8 — Threat model's stated scope contradicts the paper's own results
- **Severity:** MODERATE
- **Raised by:** B
- **Reason:** Section III excludes adaptive attackers by scope; Section
  `sec:adaptive` then demonstrates an adaptive attack succeeding 83.7%
  of the time. A threat model cannot exclude the attack the paper
  proves works.
- **Required fix:** Bring adaptive attackers *into* the threat model and
  report the architecture's performance under it honestly, or remove the
  adaptive evaluation (not recommended — it is the paper's most valuable
  result).
- **Confidence:** High.

---

## 4. MINOR weaknesses

| ID | Weakness | Severity | Fix | Conf. |
|---|---|---|---|---|
| N1 | AF9 family described but not integrated into the evaluated checkpoint — the model evaluated is not the model described. | Minor | State the evaluated checkpoint's exact family set. | High |
| N2 | Case 1–4 external verification (70.4%, "complete failure on Case 3") is disclosed in an appendix but absent from Results/abstract, where the other external number (89.9% recall) appears. | Minor–Mod | Report both external results together. | High |
| N3 | `\texttt{}` used for document filenames throughout, creating the impression of code artifacts rather than references. | Minor | Use proper citations/supplement refs. | High |
| N4 | Related-work table is checkmarks-only; no quantitative comparison to any cited system. | Minor–Mod | Add numeric columns where prior work reports metrics. | High |
| N5 | Checkpoint SHA-256 truncated to `9ee7475e...` with "full hash in project documentation" — not verifiable from the paper. | Minor | Print the full hash. | High |
| N6 | Calibration temperature $T{=}2.145$ fit on $n=85$; the paper shows it *fails to transfer* (ECE 0.054→0.169 externally). A parameter fit on 85 samples that degrades out-of-distribution should not be presented as a calibration result. | Minor–Mod | Refit on a larger split or drop the calibration claim. | High |
| N7 | **Abstract is 844 words** (measured) against IEEE T-ITS's ~150–250 word guidance — >3× over, containing ~25 distinct numeric results. This is a formal submission-compliance violation, not a style preference, and will be flagged at desk-check alongside M9. It also reads as a results dump rather than a contribution statement. | **Moderate** | Cut to ≤250 words, 3–4 headline claims. | High |
| N8 | "Semantic Trust Boundary" is asserted as a novel concept without differentiating it from existing semantic-communication-security and content-trust literature. | Minor–Mod | Sharpen the novelty delta in Related Work. | Medium |

---

## 5. Scores (1–10; 10 = best. Calibrated to venue standards, not generously.)

| Criterion | A (T-ITS) | B (TDSC) | C (TIFS) | Mean | Justification |
|---|---|---|---|---|---|
| **Novelty** | 5 | 4 | 4 | **4.3** | The layered semantic-trust framing is a reasonable idea; the execution's novel component (B3) is a fine-tuned off-the-shelf DeBERTa, and the "theory" is textbook DS restated (M8). No baseline exists to establish that the idea beats simpler alternatives (C1). |
| **Technical depth** | 5 | 4 | 4 | **4.3** | Architecture is thoughtfully layered and the DS/Yager choice is well-motivated. Undercut by: no fusion-vs-floors ablation (M1), trivial propositions (M8), and a fusion contribution that is net-negative on precision (C2). |
| **Experiments** | 3 | 3 | 2 | **2.7** | Extensive in *volume* — six evaluations, ~24k messages — but no baselines (C1), a leakage path unaddressed (C3), single-run deployment (D2), post-hoc scenario tuning (D3), and no human label validation (D7). Volume is not rigor. |
| **Writing** | 7 | 6 | 6 | **6.3** | Unusually candid and well-organized; limitations are genuinely disclosed rather than hidden — a real strength. Penalized for a 700-word abstract (N7), burying the live-failure result (C4), and .md-file citations (M7). |
| **Figures** | 6 | 6 | 5 | **5.7** | 21 figures, mostly clear and appropriate. Penalized for the missing `fig1.png` (M9), one figure sourced from a discredited harness (D5), and no figure showing the fusion trade-off that C2 identifies. |
| **Statistics** | 4 | 3 | 3 | **3.3** | Bootstrap CIs, McNemar, Cohen's $h$, ECE/Brier all present — genuinely more than most submissions. Fatally undercut by using $p=3\times10^{-29}$ to defend a +0.003 F1 (C2), no CIs on deployment results (D2), no power analysis, and unreported prevalence sensitivity (D1). |
| **Reproducibility** | 3 | 2 | 2 | **2.3** | Pipeline code and evaluation artifacts are present and traceable — commendable. But the *model* cannot be reproduced: training data and scripts are off-machine (M5), LLM-generated without seeds, with a known-unapplied data fix and a family mismatch. The central artifact is not reproducible. |
| **Overall** | **3** | **2** | **2** | **2.3** | Below the bar at all three venues in current form. |

---

## 6. Acceptance probability (as submitted, no revisions)

| Venue | Accept | Major revision | Reject | Basis |
|---|---|---|---|---|
| **IEEE T-ITS** | **2%** | 18% | **80%** | Most sympathetic of the three — values the CARLA/SUMO deployment work and the ITS framing. Still fails on no-baselines (C1) and real-time infeasibility (M3). |
| **IEEE TDSC** | **1%** | 9% | **90%** | A defense with 0/240 live detection (C4) and 83.7% adaptive ASR (C5) will not pass a dependability venue regardless of presentation quality. |
| **IEEE TIFS** | **1%** | 7% | **92%** | Strictest on provenance and adversarial rigor. C3 (leakage path), M5 (unreproducible model), and C1 (no baselines) are each individually near-fatal here. |
| **Aggregate (best venue, as-is)** | **~2%** | — | — | — |

### After a serious revision addressing C1–C5 and M1–M9

| Venue | Accept probability | Conditions |
|---|---|---|
| **IEEE T-ITS** | **35–45%** | Requires: baselines added; latency reconciled and batching implemented; MBD FPR fixed; deployment re-run with repetitions. The deployment/CARLA contribution is genuinely publishable if the system meets its own real-time claim. |
| **IEEE TDSC** | **20–30%** | Requires additionally: an adaptive-attack mitigation with re-measured ASR, and a reframed threat model. |
| **IEEE TIFS** | **15–25%** | Requires additionally: leakage quantification against the shared VeReMi source, and full archival release of training data/scripts. |

**Most promising alternative framing.** If C1–C5 cannot be resolved on a
reasonable timeline, the highest-probability path is to **reframe as a
negative-results / measurement paper**: *"Semantic trust verification in
V2X: a layered architecture, a benchmark, and an honest account of where
it fails."* Lead with the live-transfer failure (C4), the adaptive
brittleness (C5), and the fusion trade-off (C2) as the *findings* rather
than the caveats. This paper's genuine and unusual strength is the
quality and candor of its failure analysis — which is currently buried
under contribution claims the evidence does not support. As a
measurement paper with baselines added, acceptance probability at T-ITS
rises to roughly **50–60%**, because the deployment integration, the
failure taxonomy, and the safety analysis are all real, novel, and
useful contributions in that framing.

---

## 7. Prioritized fix list (highest expected value first)

1. **Add baselines** (C1) — single highest-value action; without it, no venue.
2. **Restate the fusion result as a trade-off** (C2) — costs nothing, removes a fatal credibility hit.
3. **Quantify the VeReMi shared-source overlap** (C3) — one embedding-similarity experiment; either clears the paper or must be disclosed.
4. **Add the floors-vs-DS ablation** (M1) — cheap, and either validates or retires the central formalism.
5. **Reconcile the three latency figures** (M2) and re-measure once, cleanly.
6. **Fix `fig1.png` (M9) and cut the 844-word abstract to ≤250 (N7)** — both trivial, both currently desk-reject triggers before a reviewer ever reads the paper.
7. **Re-run deployment with ≥5 seeds and CIs** (D2), reporting both scenario constructions (D3).
8. **Move proofs and analyses into the paper/official supplement** (M7).
9. **Retitle the theory section** (M8) to claim implementation correctness rather than theoretical novelty.
10. **Decide the framing** (§6) — contribution paper with fixes, or measurement paper with candor. The current hybrid satisfies neither reviewer type.

---

## 8. What the paper does genuinely well (for balance; unsolicited but relevant to revision strategy)

These are not scored above because the mandate was adversarial, but they
are real and should be *preserved and foregrounded* in revision:

- **Candor is exceptional.** The paper discloses its own adaptive-attack
  failure, its weak families, CP's non-contribution, MBD's FPR, and the
  live-CARLA B3 failure. Most submissions hide far less serious problems.
  Reviewers do notice this, and it earns real goodwill — but only if the
  contribution claims are scaled to match the evidence.
- **The failure analysis is publication-grade on its own.** Eight
  root-caused clusters traced to real per-message data is better failure
  analysis than most accepted papers contain.
- **Traceability.** Every number maps to a result file. This is rare and
  should be advertised (via a proper artifact DOI, per M5/M7).
- **The live-CARLA integration is a genuine engineering contribution**
  and the negative transfer result is scientifically valuable — it is
  currently the paper's most interesting finding and is framed as its
  most embarrassing one.
