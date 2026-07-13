# Interface Comparison: argmax + confidence  vs  full calibrated probability

**Verdict: RETAIN the existing interface.** The continuous-probability
interface produces **zero** decision changes under this system's core threat
model, and where it *does* change decisions it makes the system **less
cautious**. It is implemented but **disabled**, kept only so the comparison
stays reproducible.

---

## 1. What was compared

Both interfaces are deterministic functions of the same 2-class softmax, so
the comparison is exact — no sampling, no model needed. Writing
`p = p(malicious)` and `c = MAX_SOURCE_CONFIDENCE = 0.98`:

| | mass mapping `(m_A, m_¬A, m_Θ)` |
|---|---|
| **Legacy** (argmax + max-prob) | `p < 0.5` → `(1−p, 0, p)`  ·  `p ≥ 0.5` → `(0, p, 1−p)` |
| **Continuous** (`p_malicious`) | `((1−p)·c, p·c, 1−c)` |

Everything downstream — Yager combination, pignistic transform, banding,
policy floors — is **shared**, and both were run through the **real,
unmodified `TrustDecisionEngine`**.

## 2. Evidence: exhaustive domain sweep (not a sample)

`evaluation/run_interface_comparison.py` sweeps a dense grid over the *entire*
input domain — the only two variables that can produce a difference (B1
validation score × `p_malicious`), **1020 grid points**. Because it covers the
whole domain, the result holds for **any dataset and any B3 output
distribution**; no GPU run can overturn it.

| Result | Value |
|---|---|
| Decisions differing, **crypto clean (STBV premise)** | **0 / 101** |
| Decisions differing overall | 74 / 1020 (7.3%) — *all* with B1 already degraded |
| …of those, **legacy** more conservative | **50** |
| …of those, continuous more conservative | 24 |
| Latency overhead | none measurable (both are the same arithmetic; `_semantic_mass` is one branch) |
| F1 / FP / FN across 14 swept score-distributions | **identical in every regime** (zero discordant pairs; McNemar not applicable — there is nothing to test) |

The decision rule stated up front (adopt iff McNemar p < 0.05 **and** F1
improves **and** FP does not worsen **and** latency overhead < 5%) is **not
met on its first clause**: there are no discordant pairs to be significant.

## 3. Why — and the finding that matters more than the interface

**Under the STBV premise the two interfaces are decision-equivalent**, and the
reason is structural, not incidental:

With crypto clean, the fused pignistic trust under the continuous interface is
(derived, and verified numerically):

```
trust(p) = 0.9998 − 0.4998·p
```

so it reaches CAUTION (`< 0.70`) only at `p > 0.60`, and REJECT (`< 0.40`)
would require `p > 1.20` — **unreachable**. Yager's rule sends conflict to Θ,
and the pignistic transform gives Θ *half credit* toward trust, so semantic
disbelief is heavily damped against a confident, clean crypto source.

**Consequence: the fused DS score is essentially decision-inert on the STBV
path. The decisions are made by the policy floors on B3's `risk_level` band
(≥0.5 → LOW → CAUTION floor; ≥0.85 → HIGH → REJECT floor) — and those floors
are identical in both interfaces.** Changing how the semantic *mass* is built
therefore cannot change the outcome.

This is worth stating plainly in the paper as a property (and a limitation) of
the architecture: **on the STBV path, the Dempster–Shafer machinery supplies
calibrated evidence and an auditable belief state, while the actual
ACCEPT/CAUTION/REJECT boundary is set by the risk-band policy.** That is a
defensible design, but it should be claimed honestly rather than implying the
DS score itself is doing the discriminating.

## 4. Correction to an earlier claim

I previously described the sub-0.5 region as a "dead zone" where suspicion is
**discarded**. That was imprecise, and the sweep corrected it: sub-0.5
suspicion is **not discarded — it is routed into Θ (ignorance)**. The legacy
interface's semantics are therefore *"49% chance of attack" ≡ "I don't know"* —
a **miscategorisation** (suspicion as ignorance rather than disbelief), not a
dropped signal.

And crucially, **the continuous interface does not fix it**: at `p = 0.49` it
yields `trust = 0.755` → still ACCEPT. The proposed cure does not cure the
disease. If sub-0.5 suspicion should be actionable, the correct lever is the
**risk-band thresholds** in `B3RiskPolicy` (a cost-sensitive threshold choice,
requiring an ROC/cost analysis on real B3 outputs) — **not** the mass
interface. That is the honest follow-up.

## 5. Coupling assessment (the second half of the adoption bar)

Even had the numbers been favourable, adoption would need to not increase
coupling. It does increase it, mildly: `p_malicious` gives the Trust Engine a
*probabilistic* reading of B3's output, whereas today the engine consumes
`risk_level` as an **opaque band** and is genuinely agnostic to B3's label
space (b3_bridge's stated contract: *"the Trust Decision Engine consumes
risk_level as an opaque field… it does not know or care what label strings B3's
underlying model uses"*). Interpreting a probability means the engine now
assumes a 2-class softmax semantics. Small, but real — and unjustifiable for
zero measured gain.

## 6. What is in the repository

Implemented but **OFF by default**, purely so a reviewer can reproduce the A/B:

- `TrustPolicy.use_continuous_semantic_belief` (default `False`; docstring
  states the evidence and says do not enable)
- `TrustDecisionEngine._semantic_mass` — both mappings side by side, documented
- `SemanticResult.p_malicious` — **additive, optional** (`None` by default);
  every existing consumer is unaffected. Useful for logging/forensics
  regardless of the fusion decision.
- `evaluation/run_interface_comparison.py` — the A/B (exhaustive map + a
  real-data mode if you ever want to score B3 into
  `b3_eval/data/interface_eval.jsonl`)
- `tests/test_interface_equivalence.py` — locks all four claims (9 checks)

**Nothing about the default behaviour of the stack changed.** Verified:
`test_interface_equivalence.py` claim I1 — adding `p_malicious` to a
SemanticResult changes neither the trust level nor the trust score, to 1e-12,
across 63 grid points, under the default policy.

## 7. Bottom line for the paper

> We evaluated replacing B3's argmax+confidence interface with the full
> calibrated probability, fused via the same Yager/pignistic machinery. Across
> an exhaustive sweep of the input domain (1020 points), the two interfaces are
> decision-equivalent whenever the cryptographic and behavioural layers agree —
> i.e. throughout the STBV threat class — and diverge only under already-degraded
> cryptographic evidence, where the simpler interface is the more conservative
> of the two in 50 of 74 cases. We therefore retain the existing interface, and
> note that on the STBV path the ACCEPT/CAUTION/REJECT boundary is determined by
> the semantic risk-band policy rather than by the fused belief score.
