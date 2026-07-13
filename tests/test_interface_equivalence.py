"""
tests/test_interface_equivalence.py
======================================
Locks the interface A/B result (see INTERFACE_COMPARISON.md).

Claims pinned:
  I1. DEFAULT-OFF SAFETY: with the default TrustPolicy, adding `p_malicious`
      to a SemanticResult changes NOTHING. The legacy interface is the
      default and is byte-for-byte unaffected by the new optional field.
  I2. STBV EQUIVALENCE: when the other layers are clean (the STBV premise),
      the two interfaces produce IDENTICAL decisions for every p_malicious in
      [0,1]. The continuous interface buys nothing precisely where it was
      hypothesised to help.
  I3. DIRECTION OF DIVERGENCE: where they DO differ (only when B1 is already
      degraded), the LEGACY interface is more often the more conservative
      (safer) one. Enabling the continuous interface makes the system less
      cautious -- which is why it stays off.
  I4. CONTRACT ADDITIVITY: `p_malicious` is optional; SemanticResults without
      it still work under both policies.

Run with:  python3 tests/test_interface_equivalence.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from b2_explain.explainability import ExplainabilityEngine
from pipeline.b3_bridge import B3RiskPolicy, SemanticResult
from trust_engine.decision_engine import TrustDecisionEngine
from trust_engine.policy import TrustPolicy

_FAILURES = []


def check(name, cond, evidence=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  -- {evidence}" if evidence else ""))
    if not cond:
        _FAILURES.append(name)


POL = B3RiskPolicy()
ENG_DEFAULT = TrustDecisionEngine()                                   # default policy
ENG_LEGACY = TrustDecisionEngine(policy=TrustPolicy(use_continuous_semantic_belief=False))
ENG_CONT = TrustDecisionEngine(policy=TrustPolicy(use_continuous_semantic_belief=True))
EXPLAIN = ExplainabilityEngine()
RANK = {"ACCEPT": 0, "CAUTION": 1, "REJECT": 2}


def b3(p, with_p=True):
    label = "MALICIOUS" if p >= 0.5 else "BENIGN"
    conf = max(p, 1.0 - p)
    d = {"available": True, "label": label, "confidence": conf,
         "risk_level": POL.classify(label, conf), "status": "ok"}
    if with_p:
        d["p_malicious"] = p
    return d


def b1b2(score):
    b1 = {"valid": score >= 0.7, "fatal": False, "score": score, "confidence": 1.0,
          "reasons": [], "checks": {}, "details": {}}
    return b1, EXPLAIN.explain(b1).to_dict()


print("=" * 78)
print("INTERFACE EQUIVALENCE (legacy argmax+max-prob  vs  continuous p_malicious)")
print("=" * 78)

# --- I1: default policy is unaffected by the new field --------------------
print("\n--- I1: default policy ignores p_malicious (no behaviour change) ---")
mismatch = 0
for i in range(0, 101, 5):
    p = i / 100
    for s in (0.3, 0.6, 1.0):
        b1, b2 = b1b2(s)
        with_field = ENG_DEFAULT.decide(b1, b2, b3(p, with_p=True))
        without = ENG_DEFAULT.decide(b1, b2, b3(p, with_p=False))
        if with_field.trust_level != without.trust_level or \
           abs(with_field.trust_score - without.trust_score) > 1e-12:
            mismatch += 1
check("Adding p_malicious changes nothing under the default policy",
      mismatch == 0, f"{mismatch} mismatches over 63 grid points")
check("Default policy has the continuous interface OFF",
      TrustPolicy().use_continuous_semantic_belief is False)

# --- I2: STBV premise (clean crypto) -> decision-equivalent ---------------
print("\n--- I2: under the STBV premise (clean crypto), the interfaces are equivalent ---")
b1c, b2c = b1b2(1.0)
diffs = []
for i in range(0, 101):
    p = i / 100
    a = ENG_LEGACY.decide(b1c, b2c, b3(p))
    c = ENG_CONT.decide(b1c, b2c, b3(p))
    if a.trust_level != c.trust_level:
        diffs.append(p)
check("ZERO decision differences across all p in [0,1] with clean crypto",
      len(diffs) == 0, f"{len(diffs)} differing p values")
check("=> the continuous interface adds no detection capability for STBV attacks",
      len(diffs) == 0)

# --- I3: where they differ, legacy is the safer one ----------------------
print("\n--- I3: under degraded crypto they diverge, and LEGACY is safer ---")
legacy_safer = cont_safer = 0
for si in range(1, 21):
    s = si / 20
    b1, b2 = b1b2(s)
    for i in range(0, 101, 2):
        p = i / 100
        a = ENG_LEGACY.decide(b1, b2, b3(p))
        c = ENG_CONT.decide(b1, b2, b3(p))
        if a.trust_level != c.trust_level:
            if RANK[a.trust_level.value] > RANK[c.trust_level.value]:
                legacy_safer += 1
            else:
                cont_safer += 1
total_diff = legacy_safer + cont_safer
check("The interfaces DO diverge once crypto is degraded",
      total_diff > 0, f"{total_diff} differing grid points")
check("LEGACY is more often the more conservative (safer) interface",
      legacy_safer > cont_safer,
      f"legacy safer at {legacy_safer} points vs continuous at {cont_safer}")
check("=> enabling the continuous interface would make the system LESS cautious",
      legacy_safer > cont_safer)

# --- I4: contract additivity ---------------------------------------------
print("\n--- I4: p_malicious is optional; absent is handled by both policies ---")
sr = SemanticResult.unavailable("x").to_dict()
check("SemanticResult.unavailable() carries p_malicious=None",
      "p_malicious" in sr and sr["p_malicious"] is None)
no_p = {"available": True, "label": "MALICIOUS", "confidence": 0.9,
        "risk_level": "high", "status": "ok"}      # legacy caller, no p_malicious
b1c, b2c = b1b2(1.0)
d_legacy = ENG_LEGACY.decide(b1c, b2c, dict(no_p))
d_cont = ENG_CONT.decide(b1c, b2c, dict(no_p))
check("Continuous policy falls back to the legacy mapping when p_malicious is absent",
      d_legacy.trust_level == d_cont.trust_level
      and abs(d_legacy.trust_score - d_cont.trust_score) < 1e-12,
      f"{d_legacy.trust_level.value} == {d_cont.trust_level.value}")

print()
print("=" * 78)
if _FAILURES:
    print(f"{len(_FAILURES)} FAILURE(S): {_FAILURES}")
    sys.exit(1)
print("Interface equivalence locked. Verdict: RETAIN the existing interface.")
sys.exit(0)
