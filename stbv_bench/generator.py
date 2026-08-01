"""
stbv_bench/generator.py
========================
Steps 3-5 of the STBV-Bench pipeline: applies the Semantic Transformation
Engine (transformations.py) to a canonical message (canonical.py), performs
Semantic Validation (structural sanity -- the message must still parse and
carry plausible kinematics), and packages the result with the FULL metadata
schema required by the STBV-Bench specification.

Reuses, rather than duplicates:
  - bridges/message_adapter.py's schema conventions (via canonical.py)
  - the peer_reports/rsu_messages injection convention already established
    by semantic_evaluation/semantic_attack_generator.py
  - pipeline/orchestrator.py's ISCEPipeline for benchmark validation (Step 6)
    -- see stbv_bench/build_stbv_bench.py, which runs every generated
    message through the REAL, frozen architecture to record what it
    actually decided (not what the transformation rule predicted).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

from stbv_bench.canonical import veremi_report_to_canonical
from stbv_bench.transformations import TransformationRule


@dataclass(frozen=True)
class STBVBenchSample:
    """One fully-provenanced STBV-Bench record, per the required schema:
    source dataset, original message, transformed message, attack family,
    transformation rule, semantic objective, expected trust layer, expected
    decision, severity, reproducible random seed."""

    sample_id: str
    source_dataset: str                 # e.g. "VeReMi Extension / ConstPos_1416"
    original_message: Dict[str, Any]     # the real VeReMi flat report, unmodified
    transformed_message: Dict[str, Any]  # canonical CAM message + injected payload
    attack_family: str
    transformation_rule: str
    semantic_objective: str
    expected_trust_layer: str
    expected_decision: str
    severity: str
    seed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "source_dataset": self.source_dataset,
            "original_message": self.original_message,
            "transformed_message": self.transformed_message,
            "attack_family": self.attack_family,
            "transformation_rule": self.transformation_rule,
            "semantic_objective": self.semantic_objective,
            "expected_trust_layer": self.expected_trust_layer,
            "expected_decision": self.expected_decision,
            "severity": self.severity,
            "seed": self.seed,
        }


def generate_sample(
    veremi_report: Dict[str, Any],
    rule: TransformationRule,
    *,
    sample_id: str,
    source_dataset: str,
    seed: int,
    station_id: int,
    station_type: int = 5,
) -> STBVBenchSample:
    """Applies one transformation rule to one real VeReMi report, producing
    one fully-provenanced STBV-Bench sample. Deterministic given `seed`."""
    rng = random.Random(seed)

    canonical_msg = veremi_report_to_canonical(
        veremi_report, station_id=station_id, station_type=station_type
    )
    payload_text = rule.render(rng)

    if rule.inject_as in ("peer", "both"):
        canonical_msg["scene_context"]["peer_reports"].append(payload_text)
    if rule.inject_as in ("rsu", "both"):
        canonical_msg["scene_context"]["rsu_messages"].append(payload_text)

    # --- Semantic Validation (Step 4): structural sanity, not a trust
    # judgement -- confirms the transformation didn't break the schema
    # required by pipeline/synthesizer.py and bridges/message_adapter.py.
    assert "header" in canonical_msg and "cam" in canonical_msg
    assert isinstance(canonical_msg["scene_context"]["peer_reports"], list)
    assert isinstance(canonical_msg["scene_context"]["rsu_messages"], list)
    if rule.inject_as in ("peer", "both"):
        assert payload_text in canonical_msg["scene_context"]["peer_reports"]
    if rule.inject_as in ("rsu", "both"):
        assert payload_text in canonical_msg["scene_context"]["rsu_messages"]

    canonical_msg["attack_family"] = rule.family
    canonical_msg["is_attacker"] = rule.family != "benign_control"
    canonical_msg["expected_label"] = "MALICIOUS" if rule.family != "benign_control" else "BENIGN"

    return STBVBenchSample(
        sample_id=sample_id,
        source_dataset=source_dataset,
        original_message=dict(veremi_report),
        transformed_message=canonical_msg,
        attack_family=rule.family,
        transformation_rule=rule.transformation_rule,
        semantic_objective=rule.semantic_objective,
        expected_trust_layer=rule.expected_trust_layer,
        expected_decision=rule.expected_decision,
        severity=rule.severity,
        seed=seed,
    )
