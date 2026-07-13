"""
evaluation/runner.py
=======================
Parts 5, 6, 8, 9 core: executes seeded, configurable attack scenarios
through the full trust stack (or any ablated configuration of it, or a
baseline), recording per-message decisions, per-stage latencies, and
per-stage contract-conformance -- no silent failures (any contract
violation or exception is recorded as an explicit failure row, never
swallowed).

CONFIGURATIONS (Part 8 -- ablation axis). All ablations are done by
composition/monkey-patching in THIS module only; production code is never
modified:
  full          : PKI*+B1+MBD+B2+CP+B3+TrustEngine   (*PKI runs only when
                  material is attached; scenario generator does not attach
                  it, so PKI's contribution is evaluated separately via the
                  pki_abuse scenario family)
  no_b1         : B1 neutered to always-pass
  no_mbd        : enable_mbd=False
  no_b2         : B2 neutered to passthrough (no calibration/blending)
  no_cp         : enable_cp=False
  no_b3         : B3 forced unavailable
  no_fusion     : Trust Engine replaced by naive AND of layer pass-flags
                  ("without Trust Engine" per the mandate -- something must
                  still emit a decision; naive conjunction is the honest
                  null model)

BASELINES (Part 9). Each is a deliberately simple, clearly-documented
approximation of a class of prior approach -- labeled as approximations,
not reimplementations of specific papers:
  baseline_pki_only    : accept anything with valid signature/cert; with no
                         PKI material attached, accepts everything (this IS
                         the point of the baseline: PKI alone is blind to
                         content).
  baseline_pki_mbd     : PKI + MBD anomaly threshold (no B1/B2/CP/B3).
  baseline_threshold   : single-threshold model on B1's raw validation
                         score only (the "simple threshold model" baseline).

SEEDS & SWEEPS (Part 5): every run takes an explicit seed list; scenario
regeneration is per-seed via scenario_generation.HeldOutScenarioGenerator,
so all results are reproducible bit-for-bit given (config, seed).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from b1_scsv.scsv import SCSV
from pipeline.orchestrator import ISCEPipeline
import pipeline.orchestrator as _orch_module
from adapters import LoggingAdapter, APIAdapter, DSMassAdapter
from scenario_generation.generator import HeldOutScenarioGenerator, ScenarioConfig

CONFIGURATIONS = ["full", "no_b1", "no_mbd", "no_b2", "no_cp", "no_b3", "no_fusion"]
BASELINES = ["baseline_pki_only", "baseline_pki_mbd", "baseline_threshold"]

# Part 6: per-stage output contracts, verified on EVERY message.
STAGE_CONTRACTS = {
    "b1": {"valid", "fatal", "score", "confidence", "reasons", "checks", "details"},
    "b2": {"explanation_text", "evidence", "confidence_calibration", "provenance",
            "validation_valid", "validation_score"},
    "b3": {"available", "label", "confidence", "risk_level", "status"},
    "fusion": {"trust_score", "trust_level", "semantic_risk", "cryptographic_risk",
                "attack_detected", "confidence", "reasoning", "contributors", "details"},
}
OPTIONAL_STAGE_CONTRACTS = {
    "mbd": {"passed", "kinematic_score", "temporal_consistency", "replay_score",
             "sybil_score", "collusion_score", "anomaly_score", "evidence", "boundary"},
    "cp": {"boundary", "event_label", "num_reports", "senders", "spatial_score",
            "speed_score", "heading_score", "diversity_score", "cp_confidence",
            "fusion_confidence", "cp_pass", "reports"},
}


def _build_pipeline(configuration: str) -> Tuple[ISCEPipeline, Callable[[], None]]:
    """Returns (pipeline, restore_fn). restore_fn undoes any module-level
    monkey-patching (B3 unavailability patches the orchestrator module's
    imported name, which is process-global)."""
    enable_mbd = configuration not in ("no_mbd",)
    enable_cp = configuration not in ("no_cp",)
    pipe = ISCEPipeline(
        scsv=SCSV(cert_rotation_owner="mbd"),
        enable_mbd=enable_mbd, enable_cp=enable_cp, pki_ca=None,
        adapters={"log": LoggingAdapter(), "api": APIAdapter(), "ds_mass": DSMassAdapter()},
    )
    restores: List[Callable[[], None]] = []

    if configuration == "no_b1":
        original = pipe.scsv.check_stateful
        class _FakePass:
            valid, fatal, validation_score, confidence = True, False, 1.0, 1.0
            reasons, checks, details = [], {}, {}
        pipe.scsv.check_stateful = lambda message: _FakePass()
        restores.append(lambda: setattr(pipe.scsv, "check_stateful", original))

    if configuration == "no_b2":
        from b2_explain.models import ExplainabilityReport
        orig_explain, orig_ev = pipe.b2.explain, pipe.b2.explain_evidence
        def fake_explain(va):
            return ExplainabilityReport(
                explanation_text="[B2 ABLATED]", evidence=[],
                confidence_calibration=va.get("confidence", 1.0), provenance={},
                validation_valid=va.get("valid", True), validation_score=va.get("score", 1.0))
        def fake_ev(evidence):
            ok = all(e.passed for e in evidence)
            sc = sum(e.score for e in evidence) / len(evidence) if evidence else 1.0
            cf = sum(e.confidence for e in evidence) / len(evidence) if evidence else 1.0
            return ExplainabilityReport(explanation_text="[B2 ABLATED]", evidence=[],
                                          confidence_calibration=cf, provenance={},
                                          validation_valid=ok, validation_score=sc)
        pipe.b2.explain, pipe.b2.explain_evidence = fake_explain, fake_ev
        restores.append(lambda: (setattr(pipe.b2, "explain", orig_explain),
                                  setattr(pipe.b2, "explain_evidence", orig_ev)))

    if configuration == "no_b3":
        original_ct = _orch_module.classify_text
        _orch_module.classify_text = lambda text, metadata=None: {
            "available": False, "label": None, "confidence": None,
            "risk_level": "unavailable", "status": "ABLATED (no_b3)"}
        restores.append(lambda: setattr(_orch_module, "classify_text", original_ct))

    if configuration == "no_fusion":
        # "Without Trust Engine": naive conjunction null model. Decision is
        # REJECT iff any available layer's own pass flag is False.
        original_decide = pipe.trust_engine.decide
        from trust_engine.models import FinalTrustDecision, TrustLevel, SemanticRisk
        def naive_decide(b1, b2, b3):
            passed = bool(b1.get("valid", True)) and not bool(b1.get("fatal", False))
            level = TrustLevel.ACCEPT if passed else TrustLevel.REJECT
            return FinalTrustDecision(
                trust_score=1.0 if passed else 0.0, trust_level=level,
                semantic_risk=SemanticRisk.UNAVAILABLE, cryptographic_risk="n/a",
                attack_detected=not passed, confidence=1.0,
                reasoning="[TRUST ENGINE ABLATED: naive B1-pass conjunction]",
                contributors=["naive"], details={})
        pipe.trust_engine.decide = naive_decide
        restores.append(lambda: setattr(pipe.trust_engine, "decide", original_decide))

    def restore_all() -> None:
        for r in reversed(restores):
            r()
    return pipe, restore_all


def _baseline_predict(baseline: str, pipe: ISCEPipeline,
                       window: List[Dict[str, Any]]) -> Tuple[str, Dict[str, float]]:
    """Part 9 baselines. Returns (decision, latencies)."""
    target = window[-1]
    t0 = time.perf_counter()
    if baseline == "baseline_pki_only":
        # Valid signature => accept. No material attached => cannot reject.
        sig_ok = "_pki_signature" in target  # scenario msgs carry none
        decision = "ACCEPT"  # PKI-only is content-blind; this IS the finding.
        lat = {"total_ms": (time.perf_counter() - t0) * 1000.0}
        return decision, lat
    if baseline == "baseline_pki_mbd":
        mbd = pipe._run_mbd(target)
        decision = "REJECT" if (mbd["anomaly_score"] > 0.5 or not mbd["passed"]) else "ACCEPT"
        return decision, {"total_ms": (time.perf_counter() - t0) * 1000.0}
    if baseline == "baseline_threshold":
        b1 = pipe.scsv.check_stateful(target)
        score = getattr(b1, "validation_score", getattr(b1, "score", 1.0))
        decision = "REJECT" if score < 0.7 else "ACCEPT"
        return decision, {"total_ms": (time.perf_counter() - t0) * 1000.0}
    raise ValueError(f"unknown baseline {baseline}")


def _verify_contracts(result: Dict[str, Any]) -> List[str]:
    violations = []
    for stage, keys in STAGE_CONTRACTS.items():
        obj = result.get(stage) if stage != "fusion" else result.get("fusion")
        if obj is None:
            violations.append(f"{stage}: missing (None) but mandatory")
            continue
        missing = keys - set(obj.keys())
        if missing:
            violations.append(f"{stage}: missing keys {sorted(missing)}")
    for stage, keys in OPTIONAL_STAGE_CONTRACTS.items():
        obj = result.get(stage)
        if obj is not None:
            missing = keys - set(obj.keys())
            if missing:
                violations.append(f"{stage}: missing keys {sorted(missing)}")
    return violations


def run_scenario(configuration: str, scenario_cfg: ScenarioConfig,
                  messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Runs one scenario under one configuration/baseline. Returns one row
    per message: {decision, truth, latencies, contract_violations, error}.
    Exceptions become explicit error rows -- never silently skipped."""
    rows: List[Dict[str, Any]] = []
    is_baseline = configuration in BASELINES
    pipe, restore = _build_pipeline("full" if is_baseline else configuration)
    window: List[Dict[str, Any]] = []
    try:
        for i, m in enumerate(messages):
            window.append(m)
            truth = bool(m.get("is_attacker", False))
            row: Dict[str, Any] = {
                "scenario_id": scenario_cfg.scenario_id, "family": scenario_cfg.scenario_family,
                "configuration": configuration, "seed": scenario_cfg.seed,
                "msg_index": i, "truth_attacker": truth,
            }
            try:
                if is_baseline:
                    decision, lat = _baseline_predict(configuration, pipe, window)
                    row.update({"decision": decision, "latencies": lat,
                                 "contract_violations": []})
                else:
                    r = pipe.run(list(window), context=scenario_cfg.road_context)
                    row.update({"decision": r["decision"], "latencies": r["latencies"],
                                 "contract_violations": _verify_contracts(r),
                                 "trust_score": r["fusion"]["trust_score"],
                                 "b3_available": r["b3"]["available"]})
            except Exception as e:
                row.update({"decision": "ERROR", "error": f"{type(e).__name__}: {e}",
                             "traceback": traceback.format_exc(limit=3),
                             "latencies": {}, "contract_violations": ["EXCEPTION"]})
            rows.append(row)
    finally:
        restore()
    return rows


def generate_scenarios_for_seed(seed: int, out_dir: pathlib.Path,
                                 families: Optional[List[str]] = None,
                                 message_count: int = 20) -> List[Tuple[ScenarioConfig, List[Dict[str, Any]]]]:
    """Deterministically (re)generate the held-out scenario suite for one
    seed. Returns (config, messages) pairs, also persisted to out_dir for
    the manifest's dataset fingerprint."""
    from scenario_generation.generator import generate_held_out_suite
    seed_dir = out_dir / f"seed_{seed}"
    generate_held_out_suite(str(seed_dir), seed=seed, message_count_override=message_count)
    pairs = []
    meta = json.loads((seed_dir / "metadata.json").read_text())
    entries = meta["scenarios"] if isinstance(meta, dict) and "scenarios" in meta else meta
    for entry in entries:
        cfg = ScenarioConfig(**{k: entry[k] for k in (
            "scenario_id", "scenario_family", "attack_type", "traffic_density",
            "road_context", "vehicle_count", "attacker_count", "seed",
            "expected_label", "message_count") if k in entry})
        if families and cfg.scenario_family not in families:
            continue
        sdir = seed_dir / cfg.scenario_id
        msgs = [json.loads(f.read_text()) for f in sorted(sdir.glob("*.json"))
                if f.name != "metadata.json"]
        pairs.append((cfg, msgs))
    return pairs
