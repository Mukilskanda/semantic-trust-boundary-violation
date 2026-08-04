# Theoretical Analysis of the Trust Decision Engine

**Scope.** This document formalizes and proves (or, where a clean proof
is not available, sketches) six properties of the fusion mathematics
actually implemented in `trust_engine/decision_engine.py` and
`trust_engine/dempster_shafer.py`. Every symbol, formula, and threshold
below is read directly from that code — nothing here is a proposed
redesign or an idealized model of what the system "should" do. Where the
real implementation deviates from a clean mathematical property (and it
does, in two disclosed places), that deviation is stated as part of the
proposition, not hidden.

This is not a rewrite of `ARCHITECTURE_DECISIONS.md` or the paper's own
"Trust Decision Engine" subsection — it is the first complete, symbolic
derivation of the fusion algebra's formal properties, checked against
the code line-by-line rather than asserted from the docstrings alone.

---

## 1. The formal object being analyzed

**Frame of discernment.** $\Theta = \{A, \lnot A\}$, where $A$ =
"trustworthy/benign" and $\lnot A$ = "suspicious/malicious"
(`trust_engine/dempster_shafer.py`, module docstring).

**Mass function.** A triple $m = (m_A, m_{\lnot A}, m_\Theta) \in
[0,1]^3$ with $m_A + m_{\lnot A} + m_\Theta = 1$
(`MassFunction.__post_init__`, which raises if this invariant is
violated by more than $10^{-6}$ — an enforced, not merely documented,
invariant).

**Score-confidence encoding.** Every evidence source is mapped to a mass
function via (`MassFunction.from_score_confidence`):

$$m_A = s \cdot c, \qquad m_{\lnot A} = (1-s)\cdot c, \qquad m_\Theta = 1-c$$

for a score $s \in [0,1]$ (1.0 = fully trustworthy) and confidence $c \in
[0,1]$ (1.0 = fully committed). This is the *only* place a raw
score/confidence pair becomes a mass triple anywhere in the pipeline
(the same convention is reused by `adapters/ds_mass_adapter.py` and
`b2_csia.uncertainty.MassFunction`, per that module's own docstring).

**Combination rule.** Yager's modified rule (Yager 1987), not raw
Dempster normalization (`combine()` in `dempster_shafer.py`):

$$K = m_A^{(1)} m_{\lnot A}^{(2)} + m_{\lnot A}^{(1)} m_A^{(2)}$$
$$m_A^{(12)} = m_A^{(1)} m_A^{(2)} + m_A^{(1)} m_\Theta^{(2)} + m_\Theta^{(1)} m_A^{(2)}$$
$$m_{\lnot A}^{(12)} = m_{\lnot A}^{(1)} m_{\lnot A}^{(2)} + m_{\lnot A}^{(1)} m_\Theta^{(2)} + m_\Theta^{(1)} m_{\lnot A}^{(2)}$$
$$m_\Theta^{(12)} = m_\Theta^{(1)} m_\Theta^{(2)} + K$$

(conflict mass $K$ is *reassigned to ignorance*, not divided out — the
deliberate departure from raw Dempster's rule documented at length in
`dempster_shafer.py`'s module docstring, citing Zadeh's 1984
counterexample as the reason).

**Pignistic transform** (Smets & Kennes 1994), used to reduce a mass
function to one scalar for threshold banding:

$$\mathrm{trust}(m) = m_A + \tfrac{1}{2} m_\Theta$$

**Thresholds** (`trust_engine/policy.py`, defaults):
$\tau_{\text{reject}} = 0.40$, $\tau_{\text{caution}} = 0.70$. A score
$< \tau_{\text{reject}}$ bands to REJECT; $[\tau_{\text{reject}},
\tau_{\text{caution}})$ to CAUTION; $\ge \tau_{\text{caution}}$ to
ACCEPT.

**Two evidence sources feed `combine()`:**
- $m^{(1)}$ = "crypto mass", from `(b1_score, crypto_confidence)`,
  where `b1_score` is B1's own score OR, when MBD/CP are enabled, B2's
  already-folded `validation_score` (see `pipeline/orchestrator.py`'s
  "CP EVIDENCE FOLD" block) — so $m^{(1)}$ in practice represents
  B1+MBD+CP combined, not B1 alone.
- $m^{(2)}$ = "semantic mass", from B3's output via `_semantic_mass()`
  (two interfaces, LEGACY and CONTINUOUS — see §5).

---

## 2. Proposition 1 — Semantic evidence never overrides cryptographic rejection

**Statement.** Let $\ell_1$ = the trust level B1(+MBD+CP) evidence alone
would produce (`crypto_level_alone` in code), and let $\ell$ = the
engine's final `trust_level`. Then for every input the code can
produce, $\mathrm{rank}(\ell) \ge \mathrm{rank}(\ell_1)$, where
$\mathrm{rank}(\text{ACCEPT})=0 < \mathrm{rank}(\text{CAUTION})=1 <
\mathrm{rank}(\text{REJECT})=2$. Equivalently: no amount of favorable
semantic (B3) evidence can move the final decision to a *less* severe
level than crypto/structural evidence alone already earned.

**Proof.**

*Case A — B1 fatal.* `decide()`'s first branch: `if b1_fatal: return
FinalTrustDecision(trust_level=REJECT, ...)`, unconditionally, before
`semantic_result` is read at all past the null-check
(`decision_engine.py:117–139`). $\ell = \text{REJECT}$ is already
maximal rank, so $\mathrm{rank}(\ell) \ge \mathrm{rank}(\ell_1)$ holds
trivially for any $\ell_1$. B3 is never consulted in this branch by
construction — this is not merely a floor, it is a hard short-circuit
in the control flow. $\blacksquare$ (this case)

*Case B — B1 non-fatal.* The engine computes `crypto_level_alone`
($\ell_1$) by banding `crypto_trust_score` = $\mathrm{trust}(m^{(1)})$
against the same two thresholds, independent of B3. It separately
computes `fused_level` by banding $\mathrm{trust}(\mathrm{combine}(m^{(1)},
m^{(2)}))$. The **conservative-bias ceiling**
(`decision_engine.py:207–208`) then sets:

$$\ell_{\text{ceil}} = \begin{cases}\ell_1 & \mathrm{rank}(\ell_1)\ge\mathrm{rank}(\ell_{\text{fused}})\\ \ell_{\text{fused}} & \text{otherwise}\end{cases} = \max_{\mathrm{rank}}(\ell_1, \ell_{\text{fused}})$$

— i.e. $\ell_{\text{ceil}}$ is *by construction* the rank-maximum of the
two candidates, so $\mathrm{rank}(\ell_{\text{ceil}}) \ge
\mathrm{rank}(\ell_1)$ always. The two subsequent **policy floors**
(`decision_engine.py:227–231`, HIGH → force REJECT; MEDIUM/LOW → raise
to at least CAUTION if below it) are each themselves rank-maximum
operations against $\ell_{\text{ceil}}$: forcing REJECT is
$\max_{\mathrm{rank}}(\ell_{\text{ceil}}, \text{REJECT})$; raising to
CAUTION-or-above is $\max_{\mathrm{rank}}(\ell_{\text{ceil}},
\text{CAUTION})$. A composition of rank-maximum operations against a
value that is already $\ge \ell_1$ in rank remains $\ge \ell_1$ in rank.
Hence $\mathrm{rank}(\ell) \ge \mathrm{rank}(\ell_{\text{ceil}}) \ge
\mathrm{rank}(\ell_1)$. $\blacksquare$

**Corollary (what B3 *can* do).** The only direction B3 can move the
decision is toward more severity: from ACCEPT toward CAUTION/REJECT, or
CAUTION toward REJECT — never the reverse. This is exactly the paper's
"semantic evidence can only add caution, never override a cryptographic
rejection" claim (Conclusion, `stbv_paper.tex`), now proved rather than
asserted.

**Scope of the proof.** This is a property of `decide()`'s control flow
and arithmetic, not of Yager's rule in the abstract — a symmetric DS
combination alone does not guarantee this; it is the explicit
`max_rank` ceiling/floor code (`decision_engine.py:200–231`) that
guarantees it. The docstring calls these "policy decisions layered on
top of the fusion math," which the proof above confirms precisely: the
guarantee comes from three `max`-shaped code operations, not from any
property Yager 1987 proves about his rule.

---

## 3. Proposition 2 — Trust monotonicity

**Statement.** Fix one evidence source's mass function and vary the
other source's evidence *quality* along its own natural ordering
(crypto: `b1_score` $s\in[0,1]$ at fixed confidence; semantic: source
confidence $t\in[0,1]$ at fixed which-way-it-points). Then the pignistic
trust score $\mathrm{trust}(\mathrm{combine}(m^{(1)}, m^{(2)}))$ is
monotone (non-decreasing or non-increasing, matching intuition) in that
parameter — **before** the discrete floors/ceiling of §2 are applied.

**Proof (crypto side).** Fix $m^{(2)} = (m_A^{(2)}, m_{\lnot A}^{(2)},
m_\Theta^{(2)})$ and let $m^{(1)}(s) = (sc,\ (1-s)c,\ 1-c)$ for fixed
confidence $c$. Substituting into the combine formulas and
differentiating the pignistic score $T(s) = m_A^{(12)}(s) + \tfrac12
m_\Theta^{(12)}(s)$ with respect to $s$ (full algebra in the appendix
below) gives the closed form:

$$\frac{dT}{ds} = \tfrac{1}{2}c\,(1 + m_\Theta^{(2)}) \;\ge\; 0$$

for **every** fixed $m^{(2)}$ (the $m_A^{(2)}, m_{\lnot A}^{(2)}$ terms
cancel exactly; only $m_\Theta^{(2)}$ survives). Since $c \ge 0$ and
$m_\Theta^{(2)} \ge 0$, $dT/ds \ge 0$ identically: **better crypto
evidence never decreases the fused trust score, regardless of what B3
currently believes.** $\blacksquare$

**Proof (semantic side, legacy interface, malicious branch).** Fix
$m^{(1)} = (m_A^{(1)}, m_{\lnot A}^{(1)}, m_\Theta^{(1)})$. When B3's
label is malicious, `_semantic_mass()` sets $m^{(2)}(t) = (0,\ t,\
1-t)$ where $t$ is B3's own reported confidence (clamped to $\le
0.98$). The same substitution gives:

$$T(t) = \big[m_A^{(1)} + \tfrac12 m_\Theta^{(1)}\big] \;-\; \tfrac12\, t\,\big(m_A^{(1)} + m_\Theta^{(1)}\big)$$
$$\frac{dT}{dt} = -\tfrac12\big(m_A^{(1)} + m_\Theta^{(1)}\big) \;\le\; 0$$

for every fixed $m^{(1)}$: **higher B3 confidence in "malicious" never
increases the fused trust score.** $\blacksquare$ (Symmetric algebra for
the NONE/benign branch, $m^{(2)}(t)=(t,0,1-t)$, gives $dT/dt =
\tfrac12(m_{\lnot A}^{(1)}+m_\Theta^{(1)}) \ge 0$ — higher confidence in
"clean" never decreases trust.)

**Scope and honest limits.**
1. This proves monotonicity of the *continuous, pre-floor* pignistic
   score. It does **not**, by itself, prove monotonicity of the final,
   discrete `TrustLevel` — but combined with Proposition 1's rank-max
   floors (each individually monotone: raising a floor never lowers a
   rank-max, regardless of the input that triggered it), the *ordinal*
   monotonicity survives into the final decision: strictly better crypto
   evidence, or strictly weaker semantic suspicion, never makes the
   final `trust_level` more severe, when everything else is held fixed.
2. **Known, code-documented discontinuity (not a violation, a
   different property):** the LEGACY interface's `score_for_mass` is a
   *step function* of B3's underlying $p_{\text{malicious}}$ — it is
   $1.0$ for $p<0.5$ and $0.0$ for $p\ge0.5$ regardless of how close $p$
   is to $0.5$ (`decision_engine.py`'s own docstring: "$m_{\lnot A}$ is
   discontinuous at $p=0.5$"). Monotonicity in $t$ (confidence *within*
   one side of that boundary) is proved above and holds; continuity in
   the underlying $p_{\text{malicious}}$ across the boundary does not,
   and is not claimed to.
3. **B1-fatal is a genuine discontinuity by design**, not a violation:
   crossing the fatal boundary snaps $\ell$ straight to REJECT (rank 2)
   regardless of how close the message was to being non-fatal — this is
   ordinally consistent (REJECT is the correct extreme) but not a smooth
   function of any underlying continuous parameter.

---

## 4. Proposition 3 — Conservative fusion

**Statement.** For every input, $\mathrm{rank}(\ell) \ge
\max\big(\mathrm{rank}(\ell_1),\ \mathrm{rank}(\ell_{\text{fused}})\big)$
— the final decision is never less cautious than either the
crypto-alone verdict or the raw DS-fused verdict.

**Proof.** This is Proposition 1's ceiling step restated with the
`fused_level` side made explicit: $\ell_{\text{ceil}} =
\max_{\mathrm{rank}}(\ell_1, \ell_{\text{fused}})$ is proved directly by
the code's own `if/else` (§2, Case B), and the subsequent floors are
themselves rank-max operations against $\ell_{\text{ceil}}$, hence
against both original operands too, by transitivity of $\max$.
$\blacksquare$

**What this rules out, concretely.** It is architecturally impossible
for this implementation to produce a scenario where clean-looking
crypto evidence combined with ambiguous-but-not-clean B3 evidence yields
a *less* cautious final decision than either input alone would justify.
The paper's "semantic evidence can only add caution" framing
(Conclusion) is this proposition, not merely Proposition 1's narrower
"never overrides REJECT" claim — Proposition 3 covers ACCEPT→CAUTION
softening too, not only outright rejection-overriding.

---

## 5. Proposition 4 — Conflict handling

**Statement.** For *every* pair of valid mass functions $m^{(1)},
m^{(2)}$ (in particular including the maximal-conflict case $K=1$),
$\mathrm{combine}(m^{(1)}, m^{(2)})$ returns a valid mass function
($\ge 0$, summing to 1) without division, and conflict strictly
increases the returned $m_\Theta$ relative to what
$m_\Theta^{(1)}m_\Theta^{(2)}$ alone would give.

**Proof.** By construction, $m_\Theta^{(12)} = m_\Theta^{(1)}
m_\Theta^{(2)} + K$ with $K \ge 0$ always (it is a sum of two products of
non-negative masses), so $m_\Theta^{(12)} \ge m_\Theta^{(1)}
m_\Theta^{(2)}$, with equality iff $K=0$ (no conflict). No term in any
of the three combined-mass formulas contains a division by $(1-K)$ or by
anything else — `combine()`'s only normalization step
(`dempster_shafer.py:172–177`) divides by `total`, which is proved
$=1$ by construction (Yager's rule sums to 1 exactly, unlike raw
Dempster's rule) and only guards against floating-point drift, not a
genuine $K=1$ singularity. Hence the function is total and well-defined
on the entire valid input domain, including $K=1$.

**Worked extreme case, directly from the code's own algebra.** Let
$m^{(1)}=(1,0,0)$ (dogmatic "definitely A") and $m^{(2)}=(0,1,0)$
(dogmatic "definitely $\lnot A$") — maximal, total disagreement.
$K = 1\cdot1 + 0\cdot0 = 1$. $m_A^{(12)} = 1\cdot0+1\cdot0+0\cdot0=0$.
$m_{\lnot A}^{(12)} = 0\cdot1+0\cdot0+0\cdot1=0$.
$m_\Theta^{(12)} = 0\cdot0+1 = 1$. Result: $(0,0,1)$ — **total,
well-defined ignorance**, not an arithmetic singularity (raw Dempster
normalization divides by $1-K=0$ here and is undefined). $\blacksquare$

**Why $K=1$ cannot actually occur in this codebase in practice.**
`MAX_SOURCE_CONFIDENCE = 0.98` clamps every source's confidence strictly
below 1.0 before a mass function is ever built
(`decision_engine.py:39`, `165`, `93`), so $m_\Theta \ge 0.02$ for both
sources always, making $K \le (1-0.02)(1-0.02) < 1$ strictly. The
worked case above is a mathematical boundary-condition proof of
`combine()`'s general correctness, not a claim that this exact input
occurs at runtime — the clamp is a *separate*, deliberate design
decision (documented at `decision_engine.py:31–38`, with its own
regression test in `tests/test_dempster_shafer_fusion.py`) that keeps
the system strictly inside the region where Proposition 4's guarantee is
not just well-defined but numerically well-behaved (no source can become
so dogmatic it single-handedly vetoes the other, however extreme).

---

## 6. Proposition 5 — Decision consistency

**Statement.** `TrustDecisionEngine.decide()` is a **total, deterministic
function**: for every input satisfying its stated precondition (non-null
`validation_assessment`, `explainability_report`, `semantic_result`
dicts), it terminates and returns exactly one
`FinalTrustDecision` with `trust_level` $\in \{$ACCEPT, CAUTION,
REJECT$\}$ — never none, never more than one, never an exception outside
the documented precondition failure.

**Proof sketch (by exhaustive case analysis of the control flow).**
1. **Precondition.** The three `if ... is None: raise
   MissingLayerInputError` checks (`decision_engine.py:110–115`) make
   the precondition explicit and enforced — violating it raises a
   specific, documented exception rather than proceeding with an
   undefined state.
2. **`b1_fatal` branch.** A `bool()` coercion of a dict field, so exactly
   one of `{True, False}` — no third state. `True` returns immediately
   with `trust_level=REJECT` (one value, `TrustLevel` is a Python
   `@unique Enum`, so no other value is constructible for this field).
3. **Non-fatal branch.** `semantic_risk =
   self.policy.classify_semantic_risk(semantic_result)` — inspecting
   `classify_semantic_risk` (`policy.py:106–135`): returns
   `SemanticRisk.UNAVAILABLE` if `available` is falsy; otherwise reads
   `risk_level` and either parses it into one of the 5
   `SemanticRisk` enum values or falls through to a label/confidence
   computation that itself returns exactly one of
   `{UNAVAILABLE, NONE, HIGH, MEDIUM, LOW}` via a deterministic
   if/elif/else chain with no fall-through gap. `classify_semantic_risk`
   is therefore itself a total function into a 5-element enum.
4. **Banding.** `cryptographic_risk`, `crypto_level_alone`, and
   `fused_level` are each computed via if/elif/else chains over
   $[0,\tau_{\text{reject}}), [\tau_{\text{reject}},
   \tau_{\text{caution}}), [\tau_{\text{caution}}, \infty)$ — three
   half-open intervals that partition $\mathbb{R}$ (in practice
   $[0,1]$, since both operands are pignistic scores, themselves
   provably in $[0,1]$ as a convex combination of masses each in
   $[0,1]$) with no gap and no overlap. Exactly one branch fires.
5. **Ceiling and floors.** Each is a single deterministic comparison
   (`>=` on integer ranks, or an enum membership test) with an `if/elif`
   structure — no branch is skipped or duplicated for any input.
6. **Construction.** `FinalTrustDecision` is a `@dataclass(frozen=True)`
   with all required fields populated on every return path (verified by
   reading all four `return FinalTrustDecision(...)` sites — the
   B1-fatal early return and the final non-fatal return, each fully
   populated; there is no third return path and no implicit `None`
   return, since every branch above provably reaches one of these two
   `return` statements).

Since every step is a total function of its inputs (case 3), composed
through a finite, non-overlapping partition of branches (cases 2, 4, 5)
ending in one of exactly two `return` statements (case 6), `decide()` is
a total function: same inputs (down to floating-point bit-identical
dict contents) always produce the same `FinalTrustDecision`. $\blacksquare$

**What this does *not* claim.** Determinism of `decide()` does not by
itself imply determinism of the full pipeline's *decision on a given
real-world message* — upstream stochasticity (if any) in B1/MBD/CP/B3
themselves (e.g. B3's model could, in principle, run in a non-greedy
sampling mode, though it does not in this codebase — `pipeline/b3_bridge.py`
calls `self.predictor.predict([message])` with no sampling parameters)
would still produce input-dependent, not `decide()`-dependent,
non-determinism. This proposition is scoped to the fusion function
itself, which is the paper's actual claim ("the sole fusion point").

---

## 7. Proposition 6 — Trust preservation

**Statement.** The vacuous mass function $m_\Theta = (0,0,1)$ (total
ignorance — used exactly when B3 is unavailable,
`decision_engine.py:169`) is a **two-sided identity element** for
`combine()`: $\mathrm{combine}(m, \text{vacuous}) =
\mathrm{combine}(\text{vacuous}, m) = m$ for every valid mass function
$m$. Consequently, **the absence of semantic evidence provably has zero
effect on the fused trust score** — an honest sender whose message B3
cannot evaluate is judged purely on crypto/behavioral evidence, exactly
as if B3 did not exist, never as if unavailability itself were
suspicious.

**Proof.** Let $m^{(2)} = (0, 0, 1)$ (vacuous). Substituting into the
combine formulas:

$$K = m_A^{(1)}\cdot 0 + m_{\lnot A}^{(1)}\cdot 0 = 0$$
$$m_A^{(12)} = m_A^{(1)}\cdot 0 + m_A^{(1)}\cdot 1 + m_\Theta^{(1)}\cdot 0 = m_A^{(1)}$$
$$m_{\lnot A}^{(12)} = m_{\lnot A}^{(1)}\cdot 0 + m_{\lnot A}^{(1)}\cdot 1 + m_\Theta^{(1)}\cdot 0 = m_{\lnot A}^{(1)}$$
$$m_\Theta^{(12)} = m_\Theta^{(1)}\cdot 1 + 0 = m_\Theta^{(1)}$$

so $\mathrm{combine}(m^{(1)}, \text{vacuous}) = m^{(1)}$ exactly, for
every $m^{(1)}$ — not approximately, not in the limit, an exact
algebraic identity. Since $K=0$ always in this case, there is also never
any spurious ignorance inflation from combining with an unavailable
source. Commutativity of `combine()` (every term in $K$, $m_A^{(12)}$,
$m_{\lnot A}^{(12)}$, $m_\Theta^{(12)}$ is symmetric under swapping the
$(1)$/$(2)$ superscripts) gives the other side for free. $\blacksquare$

**Corollary — this is exactly what `pipeline/b3_bridge.py`'s own
comment already asserts, now proved rather than asserted:** "B3
unavailable (vacuous mass, does not affect fusion)"
(`decision_engine.py:241`) is not a design intention description; it is
a provable consequence of `combine()`'s algebra given the specific mass
triple `MassFunction.vacuous()` produces.

**Scope — what this does *not* protect against.** Proposition 6 protects
against the fusion math itself penalizing B3-unavailability. It does
**not** protect against B1/MBD flagging an honest, well-evidenced sender
for unrelated reasons (e.g. the MBD urban-deceleration over-sensitivity
documented in `CARLA_DEPLOYMENT_EVALUATION.md` §8 and analyzed further
in `FAILURE_ANALYSIS.md`) — trust preservation is proved here strictly
with respect to the *semantic* evidence channel, which is the scope this
codebase's own architecture assigns to B3/fusion; it is not a claim
about MBD's own scoring function, which is a separate component this
document does not re-derive.

---

## 8. Summary table

| # | Property | Status | Basis |
|---|---|---|---|
| 1 | Semantic evidence never overrides cryptographic rejection | **Proved** | Rank-max ceiling/floor composition, §2 |
| 2 | Trust monotonicity | **Proved** (pignistic score, both directions), ordinal monotonicity of final level follows via §2 | Closed-form derivative, §3 |
| 3 | Conservative fusion | **Proved** | Direct restatement of §2's ceiling as a $\max_{\mathrm{rank}}$ identity, §4 |
| 4 | Conflict handling | **Proved**, including the $K=1$ boundary case | Algebraic worked example + general identity, §5 |
| 5 | Decision consistency | **Proved** (totality/determinism), by exhaustive branch case analysis | §6 |
| 6 | Trust preservation (under missing B3 evidence) | **Proved** (vacuous mass is the identity element) | Algebraic identity, §7 |

**Two disclosed, honest limitations, not glossed over:**
- The LEGACY semantic interface (the default; `use_continuous_semantic_belief=False`)
  introduces a genuine discontinuity at $p_{\text{malicious}}=0.5$ in the
  underlying probability-to-mass mapping (§3, point 2) — monotonicity is
  proved *within* each side of that boundary, not *across* it.
- Proposition 6 is scoped to the DS fusion math specifically; it does
  not extend to MBD's independent behavioral-anomaly scoring, which
  `FAILURE_ANALYSIS.md` shows can still produce false positives on
  honest senders through a channel this document's propositions do not
  cover (MBD's score enters $m^{(1)}$ as an input, upstream of
  everything proved here — these propositions describe what fusion does
  *given* $m^{(1)}$, not whether $m^{(1)}$ itself is always correct).

---

## Appendix — full derivative derivation (Proposition 2, crypto side)

Let $s = $ `b1_score` $\in[0,1]$, $c=$ `crypto_confidence` (fixed),
$m^{(2)}=(a_2, n_2, t_2)$ fixed with $a_2+n_2+t_2=1$.

$$m^{(1)}(s) = (sc,\ (1-s)c,\ 1-c)$$

$$m_A^{(12)}(s) = sc\cdot a_2 + sc\cdot t_2 + (1-c)\cdot a_2 = sc(a_2+t_2) + (1-c)a_2$$

$$K(s) = sc\cdot n_2 + (1-s)c\cdot a_2 = c\,a_2 + sc(n_2-a_2)$$

$$m_\Theta^{(12)}(s) = (1-c)t_2 + K(s) = (1-c)t_2 + c\,a_2 + sc(n_2-a_2)$$

$$T(s) = m_A^{(12)}(s) + \tfrac12 m_\Theta^{(12)}(s)$$
$$= sc(a_2+t_2) + (1-c)a_2 + \tfrac12(1-c)t_2 + \tfrac12 c\,a_2 + \tfrac12 sc(n_2-a_2)$$

Collecting the $s$-linear coefficient:

$$\frac{dT}{ds} = c(a_2+t_2) + \tfrac12 c(n_2-a_2) = c\Big[a_2+t_2+\tfrac12 n_2-\tfrac12 a_2\Big] = c\Big[\tfrac12 a_2 + t_2 + \tfrac12 n_2\Big]$$
$$= c\Big[\tfrac12(a_2+n_2) + t_2\Big] = c\Big[\tfrac12(1-t_2) + t_2\Big] = c\Big[\tfrac12 + \tfrac12 t_2\Big] = \tfrac12 c(1+t_2)$$

matching $\tfrac12 c(1+m_\Theta^{(2)})$ as claimed in §3 — non-negative
for all $c, t_2 \in [0,1]$, and notably independent of $a_2, n_2$
individually (only their sum, via $t_2=1-a_2-n_2$, matters). This exact
cancellation is *why* the monotonicity proof does not need to case-split
on what B3 currently believes — it holds unconditionally.
