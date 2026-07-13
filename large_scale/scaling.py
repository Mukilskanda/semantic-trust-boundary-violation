"""
large_scale/scaling.py
========================
Parts 1 & 3: turn the spec's scale targets and sweep axes into concrete,
seeded ScenarioConfig objects, composing the EXISTING
scenario_generation.HeldOutScenarioGenerator (kinematic attacks) and
large_scale.semantic_attacks (text-payload attacks). No generator is forked.

Part 1 targets:
  message counts : 100, 500, 1000, 5000, 10000, 50000
  vehicle counts : 5, 10, 25, 50, 100, 250, 500, 1000
Part 3 sweep axes:
  vehicle_count, attacker_percentage, traffic_density, communication_range,
  attack_intensity, semantic_attack_confidence, message_frequency

The message-count target is met by choosing, per scenario, the number of
sequential CAM updates so that vehicle_count * updates ~= target, and by
running enough scenarios per grid cell. Communication range and message
frequency are represented explicitly (range gates which peers enter a
vehicle's cooperative window; frequency maps to the generator's Hz).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scenario_generation.generator import ScenarioConfig

# Spec scale targets
MESSAGE_TARGETS = [100, 500, 1000, 5000, 10000, 50000]
VEHICLE_TARGETS = [5, 10, 25, 50, 100, 250, 500, 1000]
ATTACKER_PCTS = [0.01, 0.05, 0.10, 0.20, 0.40]

# Kinematic families handled by the existing generator
KINEMATIC_FAMILIES = ["replay", "sybil", "collusion", "fabrication"]
# generator attack_type per family (identity_cloning/cert_spoofing map to the
# generator's certificate_switching mechanism, documented as an approximation)
_ATTACK_TYPE = {"replay": "replay", "sybil": "sybil", "collusion": "collusion",
                "fabrication": "fabrication",
                "certificate_spoofing": "certificate_switching",
                "identity_cloning": "certificate_switching"}

DENSITIES = ["sparse", "moderate", "dense"]
CONTEXTS = ["urban", "highway", "rural"]
# Part 3: communication range (m) gating the cooperative window
COMM_RANGES_M = [50, 150, 300, 500]
# Part 3: message frequency (Hz)
FREQUENCIES_HZ = [2.0, 5.0, 10.0]
# Part 3: semantic attack confidence (mean p_malicious the attacker aims to
# stay *under* to evade -- lower = stealthier/adaptive)
SEMANTIC_CONFIDENCE_LEVELS = [0.5, 0.7, 0.9]


@dataclass
class ScaledScenario:
    """A ScenarioConfig plus the large-scale axes the base config doesn't carry."""
    base: ScenarioConfig
    comm_range_m: int = 300
    frequency_hz: float = 10.0
    semantic_confidence: float = 0.9
    attacker_pct: float = 0.10
    include_semantic: bool = True

    @property
    def target_updates(self) -> int:
        return max(self.base.message_count, 1)


def _updates_for(vehicle_count: int, message_target: int) -> int:
    """Sequential CAM updates per vehicle so total ~= message_target."""
    return max(1, round(message_target / max(vehicle_count, 1)))


def build_scale_grid(seed: int, message_target: int,
                      vehicle_counts: Optional[List[int]] = None,
                      attacker_pcts: Optional[List[float]] = None,
                      families: Optional[List[str]] = None) -> List[ScaledScenario]:
    """Part 1: fixed message target, swept vehicle counts x attacker pct x family."""
    vehicle_counts = vehicle_counts or VEHICLE_TARGETS
    attacker_pcts = attacker_pcts or ATTACKER_PCTS
    families = families or (["benign"] + KINEMATIC_FAMILIES)
    out: List[ScaledScenario] = []
    sid = 0
    for vc in vehicle_counts:
        updates = _updates_for(vc, message_target)
        for pct in attacker_pcts:
            for fam in families:
                attacker_count = 0 if fam == "benign" else max(1, round(vc * pct))
                for density in DENSITIES:
                    for ctx in CONTEXTS:
                        sid += 1
                        base = ScenarioConfig(
                            scenario_id=f"s{seed}_{fam}_{vc}v_{int(pct*100)}pct_{density}_{ctx}_{sid}",
                            scenario_family=fam,
                            attack_type=_ATTACK_TYPE.get(fam, "none") if fam != "benign" else "none",
                            traffic_density=density, road_context=ctx,
                            vehicle_count=vc, attacker_count=attacker_count,
                            seed=seed + sid, expected_label="BENIGN" if fam == "benign" else "MALICIOUS",
                            message_count=updates)
                        out.append(ScaledScenario(base=base, attacker_pct=pct))
    return out


def build_sweep_grid(seed: int,
                      vehicle_counts: Optional[List[int]] = None,
                      attacker_pcts: Optional[List[float]] = None,
                      densities: Optional[List[str]] = None,
                      comm_ranges: Optional[List[int]] = None,
                      frequencies: Optional[List[float]] = None,
                      semantic_confidences: Optional[List[float]] = None,
                      families: Optional[List[str]] = None,
                      message_target: int = 1000) -> List[ScaledScenario]:
    """Part 3: full Cartesian sweep over every requested axis. Callers should
    subset axes for tractable runs (the driver exposes --quick / caps)."""
    vehicle_counts = vehicle_counts or [10, 50, 250]
    attacker_pcts = attacker_pcts or ATTACKER_PCTS
    densities = densities or DENSITIES
    comm_ranges = comm_ranges or COMM_RANGES_M
    frequencies = frequencies or FREQUENCIES_HZ
    semantic_confidences = semantic_confidences or SEMANTIC_CONFIDENCE_LEVELS
    families = families or (["benign"] + KINEMATIC_FAMILIES)

    out: List[ScaledScenario] = []
    sid = 0
    for vc, pct, density, rng_m, hz, sconf, fam in itertools.product(
            vehicle_counts, attacker_pcts, densities, comm_ranges,
            frequencies, semantic_confidences, families):
        sid += 1
        attacker_count = 0 if fam == "benign" else max(1, round(vc * pct))
        updates = _updates_for(vc, message_target)
        base = ScenarioConfig(
            scenario_id=f"sweep{seed}_{fam}_{vc}v_{int(pct*100)}pct_{density}_r{rng_m}_{hz:g}hz_sc{int(sconf*100)}_{sid}",
            scenario_family=fam,
            attack_type=_ATTACK_TYPE.get(fam, "none") if fam != "benign" else "none",
            traffic_density=density, road_context="urban",
            vehicle_count=vc, attacker_count=attacker_count,
            seed=seed + sid, expected_label="BENIGN" if fam == "benign" else "MALICIOUS",
            message_count=updates)
        out.append(ScaledScenario(base=base, comm_range_m=rng_m, frequency_hz=hz,
                                    semantic_confidence=sconf, attacker_pct=pct))
    return out


def estimate_messages(scenarios: List[ScaledScenario]) -> int:
    return sum(s.base.vehicle_count * s.target_updates for s in scenarios)
