"""
evaluation/oracle.py
=====================
Encodes the FROZEN Phase 1 ground-truth detection matrix (approved,
v2) as structured data, so oracle_eval.py can score the real pipeline
against it without re-deriving expectations from the implementation.

Only kinematic families are encoded here (replay, sybil, collusion,
fabrication, position/speed manipulation, cert switching) -- these are
the families scenario_generation/generator.py can produce end-to-end
through the REAL pipeline in this environment. Semantic (B3) families
require the real DeBERTa checkpoint (currently a git-lfs pointer, not
real weights, in this artifact -- see B3_ASSESSMENT.md) and must be run
on the GPU machine; see oracle_semantic.py stub at the bottom for that
follow-up, deliberately left unimplemented rather than faked here.

Each entry is the ORACLE -- i.e. what SHOULD happen, per Phase 1 v2,
independent of what the code currently does.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class OracleEntry:
    family: str
    earliest_layer: str                 # layer expected to fire first
    may_detect: List[str]               # plausible secondary detectors
    should_not_detect: List[str]        # structurally blind layers
    expected_decision: str              # REJECT | CAUTION | ACCEPT
    expected_confidence: str            # High | Medium | Low
    notes: str = ""


# scenario_family values as produced by scenario_generation/generator.py
KINEMATIC_ORACLE: List[OracleEntry] = [
    OracleEntry(
        family="replay",
        earliest_layer="b1",
        may_detect=["mbd"],
        should_not_detect=["pki", "cp", "b3"],
        expected_decision="REJECT",
        expected_confidence="High",
        notes="Phase1 v2 #1. PKI validates signature bytes, not freshness; "
              "B1 explicitly owns replay/freshness per its own contract.",
    ),
    OracleEntry(
        family="sybil",
        earliest_layer="mbd",
        may_detect=["cp", "b1"],
        should_not_detect=["pki", "b3"],
        expected_decision="REJECT",
        expected_confidence="Medium",
        notes="Phase1 v2 #2. Individually-valid certs; only cross-message/"
              "cross-sender correlation reveals it.",
    ),
    OracleEntry(
        family="collusion",
        earliest_layer="cp",
        may_detect=["b3"],
        should_not_detect=["pki", "b1", "mbd"],
        expected_decision="REJECT",
        expected_confidence="Medium",
        notes="Phase1 v2 #3. High-conflict fusion case by design "
              "(minority dissent vs colluding majority).",
    ),
    OracleEntry(
        family="fabrication",
        earliest_layer="mbd",   # behavioral subcase; generator.py doesn't
        may_detect=["cp"],       # distinguish behavioral/cooperative/semantic
        should_not_detect=["pki", "b1", "b3"],
        expected_decision="REJECT",
        expected_confidence="Medium",
        notes="Phase1 v2 #4a (behavioral subcase only -- generator.py has "
              "one 'fabrication' family; cooperative/semantic subcases "
              "(#4b/#4c) require dedicated scenario construction, not yet "
              "generated here).",
    ),
    OracleEntry(
        family="manipulation",  # covers position/speed/cert attack_type
        earliest_layer="b1",
        may_detect=["mbd", "cp"],
        should_not_detect=["pki", "b3"],
        expected_decision="REJECT",   # except cert-switching -> CAUTION
        expected_confidence="High",
        notes="Phase1 v2 #5/#6/#7 collapsed under generator.py's single "
              "'manipulation' scenario_family; attack_type sub-field "
              "distinguishes position_manipulation / speed_manipulation / "
              "certificate_switching -- cert-switching alone should be "
              "CAUTION not REJECT per your explicit instruction.",
    ),
]

CERT_SWITCHING_OVERRIDE = {
    "expected_decision": "CAUTION",
    "expected_confidence": "Low",
}


def oracle_for(scenario_family: str, attack_type: Optional[str] = None) -> Optional[OracleEntry]:
    for e in KINEMATIC_ORACLE:
        if e.family == scenario_family:
            if attack_type == "certificate_switching":
                return OracleEntry(
                    family=e.family, earliest_layer="mbd",
                    may_detect=["pki"], should_not_detect=["b1", "cp", "b3"],
                    expected_decision=CERT_SWITCHING_OVERRIDE["expected_decision"],
                    expected_confidence=CERT_SWITCHING_OVERRIDE["expected_confidence"],
                    notes="Phase1 v2 #7. CAUTION unless corroborated, per "
                          "explicit instruction.",
                )
            return e
    if scenario_family == "benign":
        return OracleEntry(
            family="benign", earliest_layer="none", may_detect=[],
            should_not_detect=["pki", "b1", "mbd", "cp", "b3"],
            expected_decision="ACCEPT", expected_confidence="High",
        )
    return None