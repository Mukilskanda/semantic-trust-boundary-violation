# Determination: Should B3 Support an Explicit UNKNOWN / ABSTAIN Decision?

**Short answer: NO — do not add a discrete UNKNOWN class. It is provably a
no-op in this architecture (or actively harmful, depending on how it is
mapped).** Binary classification + calibrated confidence is *nearly*
sufficient — the existing Dempster–Shafer Θ-mass path already implements
graded soft-abstention. But the investigation surfaced a **real, measurable
gap that is not an UNKNOWN class**: the `argmax → max-prob → band` contract
discards all semantic suspicion below `p_malicious = 0.5`. The minimal
justified fix, *if and only if* the GPU experiment confirms it matters, is to
expose continuous `p_malicious` — not a new label.

Everything below is evidence, not opinion. The analytical results are
reproducible right now with `python3 tests/test_abstain_semantics.py`
(no GPU, no checkpoint needed). The one remaining empirical number requires
your GPU box: `python3 b3_eval/run_open_set_analysis.py`.

---

## 1. The stack already abstains — CAUTION *is* the abstain state

Measured by sweeping B3 confidence through the **real fusion path**
(`TrustDecisionEngine.decide`, unmodified):

| B3 conf (MALICIOUS) | risk_level | m_¬A | **m_Θ (ignorance)** | decision |
|---|---|---|---|---|
| 0.50 | low | 0.50 | **0.50** | CAUTION |
| 0.60 | medium | 0.60 | **0.40** | CAUTION |
| 0.80 | medium | 0.80 | **0.20** | CAUTION |
| 0.85 | high | 0.85 | **0.15** | REJECT |
| 0.95 | high | 0.95 | **0.05** | REJECT |

B3's uncertainty flows into Θ (ignorance) mass, which is *exactly* the
Dempster–Shafer representation of "I don't know" (Shafer 1976, ch. 1–2), and
the Trust Decision Engine converts it into CAUTION. This is textbook
**selective classification with a reject option** — it is already
implemented, and it is implemented in the correct layer (B3 owns the
semantic-risk taxonomy; the Trust Engine owns decisions, including the
decision to abstain). Adding an UNKNOWN *label* to B3 to obtain abstention
would duplicate a capability the architecture already has, and would move
decision authority into B3 — a layer-boundary violation.

## 2. A discrete UNKNOWN class is provably useless here (the decisive result)

There are only three ways to map an UNKNOWN verdict into DS mass. All three
fail:

**(a) UNKNOWN → vacuous (Θ) mass — a provable no-op.**
The STBV premise is that PKI/B1/MBD/CP are *all clean* — that is what makes
an attack an STBV. So the verdict hinges entirely on B3. Measured, through
the real engine:

| B3 output on an OOD attack | decision |
|---|---|
| confidently WRONG: BENIGN @ 0.97 (the open-set failure) | **ACCEPT** |
| hypothetical UNKNOWN → vacuous mass | **ACCEPT** |

Identical. Ignorance mass, by construction, cannot move a verdict away from
what the other layers concluded — and the other layers concluded "clean."
**An UNKNOWN class mapped to ignorance rescues exactly zero attacks.**
(Locked as claim C2 in `tests/test_abstain_semantics.py`.)

**(b) UNKNOWN → disbelief (¬A) mass — repeats a bug we just fixed.**
This would make "I don't know" mean "I think it's an attack." That is
precisely the CP-semantics error corrected in `CHANGELOG.md` (absence of
evidence ≠ evidence of guilt), which was producing FPR up to 0.93. Doing it
again in B3 would be a regression of a fix, not an improvement.

**(c) UNKNOWN → a TrustPolicy floor at CAUTION.** This *would* change
decisions — but note it is a **Trust Engine policy change, not a B3 class**.
And it is not free: B3-unavailable currently degrades gracefully
(`validation/run_b4_fallback_degradation.py`), so a blanket "abstain ⇒
CAUTION" floor would push the entire degraded mode to CAUTION, with a real
FPR cost. Justifiable only if the silent-failure rate (§4) is high.

## 3. The gap that *is* real: the sub-0.5 dead zone

`inference.py` returns `argmax` + `max(prob)`. `B3RiskPolicy.classify()`
returns `"none"` for **any** non-malicious label, regardless of confidence.
Consequence, measured through the real fusion path:

| p(malicious) | label / conf emitted | risk_level | m_¬A | decision |
|---|---|---|---|---|
| 0.05 | BENIGN / 0.95 | none | 0.00 | ACCEPT |
| 0.35 | BENIGN / 0.65 | none | 0.00 | ACCEPT |
| **0.49** | BENIGN / 0.51 | none | **0.00** | **ACCEPT** |
| **0.51** | MALICIOUS / 0.51 | low | **0.51** | **CAUTION** |

A message the model considers **49% likely to be an attack** is treated
**identically to one it considers 5% likely** — zero disbelief mass, ACCEPT —
and the decision is **discontinuous** across an infinitesimal change in
`p_malicious`. The information exists in the softmax; the interface throws it
away. For a security gate this is a more serious finding than any missing
UNKNOWN class, and it is the correct thing to report in the paper.

## 4. The one question only your GPU can answer

Whether the dead zone and the open-set failure *matter in practice* depends
on a number I cannot compute (weights are an LFS stub, no torch):

> **Among unseen-family attacks that B3 gets wrong, what fraction does it
> call BENIGN with high confidence (≥0.85)?** — the *silent-failure rate*.

This matters because **temperature scaling cannot fix it.** Calibration
adjusts confidence on in-distribution data; softmax conflates aleatoric and
epistemic uncertainty and remains overconfident far from the training
distribution (Hendrycks & Gimpel, ICLR 2017 — MSP baseline; Liang et al.,
ODIN, ICLR 2018; and see the explicit statement in arXiv:2510.08631 §2.2).
So a confidently-wrong OOD prediction survives calibration untouched and the
fusion layer ACCEPTs it.

Your repo already contains the exact evidence needed: `error_analysis.py`
analyses **68 missed AF7/AF8 samples from Test-1 (unseen families)**. The
decisive question is what *confidence* those 68 carried. If low → B3 fails
loudly, the Θ path already catches them, and **binary + calibration is
sufficient, implement nothing**. If high → it fails silently, and a fix is
justified.

`b3_eval/run_open_set_analysis.py` computes this, plus MSP/energy OOD AUROC,
risk-coverage/AURC, coverage@risk, and dead-zone occupancy — and prints one
of three encoded decisions:

| Condition | Verdict |
|---|---|
| silent-failure ≥ 0.20 | Abstain/OOD mechanism justified — **but as continuous `p_malicious` + an energy-score OOD gate feeding Θ mass, never a discrete UNKNOWN class** |
| dead-zone occupancy ≥ 0.15 | Expose continuous `p_malicious` only |
| otherwise | **Binary + calibrated confidence is sufficient. Implement nothing.** Report the numbers as the evidence. |

The **energy score** (Liu et al., NeurIPS 2020; `−T·logsumexp(logits/T)`) is
recommended over MSP because it needs **no retraining, no new head, and no
architecture change** — it is a pure post-hoc function of logits you already
compute. (Its sign convention is unit-tested in `tests/test_open_set_math.py`
— an inverted sign would have flipped the AUROC and the recommendation; the
test caught exactly that bug during development.)

## 5. Why this is the better paper contribution

A discrete UNKNOWN class would be a generic, expected move that a reviewer
would call incremental. What the analysis above yields instead is a
*architecture-specific, formally-grounded* result:

> In a Dempster–Shafer trust stack, an abstention label is **information-
> theoretically inert** when the abstaining layer is the only layer with
> evidence — because ignorance mass cannot overturn the other layers'
> agreement. Abstention must therefore be expressed as *graded Θ mass*
> (which this architecture already does), and the actionable failure mode is
> not "the model cannot say UNKNOWN" but "the interface discards sub-argmax
> suspicion."

That is a defensible, novel, and *tested* claim about fusion architectures —
strictly stronger than adding a third class.

## 6. What was changed in the repository

**No production code was changed.** Per the mandate ("implement UNKNOWN only
if experiments justify it"), and since the analysis shows it is *not*
justified, nothing was implemented. Added (evaluation only):

- `tests/test_abstain_semantics.py` — regression-locks claims C1/C2/C3 above
  (12 checks, all passing, no GPU needed)
- `tests/test_open_set_math.py` — validates AUROC / risk-coverage / AURC /
  energy-sign (16 checks, all passing, no GPU needed)
- `b3_eval/run_open_set_analysis.py` — the GPU experiment that settles §4,
  with the decision rule encoded rather than left to judgement

## 7. References (verified)

- Shafer, *A Mathematical Theory of Evidence*, Princeton UP, 1976.
- Yager, "On the Dempster–Shafer framework and new combination rules,"
  *Information Sciences* 41(2), 1987.
- Hendrycks & Gimpel, "A baseline for detecting misclassified and
  out-of-distribution examples in neural networks," ICLR 2017.
- Liang, Li, Srikant, "Enhancing the reliability of out-of-distribution image
  detection in neural networks" (ODIN), ICLR 2018.
- Liu, Wang, Owens, Li, "Energy-based out-of-distribution detection,"
  NeurIPS 2020.
- Guo, Pleiss, Sun, Weinberger, "On calibration of modern neural networks,"
  ICML 2017.
- Geifman & El-Yaniv, "Selective classification for deep neural networks,"
  NeurIPS 2017; El-Yaniv & Wiener, JMLR 2010 (risk–coverage, AURC).
- Varshney et al., "Investigating selective prediction approaches across
  several tasks in IID, OOD, and adversarial settings," ACL Findings 2022.
