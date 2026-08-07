#!/usr/bin/env python3
"""
b3_eval/v25_finetune/finalize_thresholds.py
===============================================
Assembles the frozen, machine-readable recalibrated-parameter artifact
(b3_eval/v25_finetune/results/recalibrated_thresholds.json) from
recalibrate_v1_external.py's output. Does NOT modify pipeline/b3_bridge.py
or trust_engine/policy.py live defaults -- this is purely a documented
artifact, applied at evaluation time via rerun_recalibrated.py's
isce_config.yaml override mechanism (same pattern as
rerun_paper_ablation.py's checkpoint override).
"""
from __future__ import annotations
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"


def main():
    v1 = json.loads((RESULTS / "v1_recalibration_analysis.json").read_text())
    T_new = v1["calibration"]["temperature_new"]
    high = v1["thresholds"]["high_confidence"]
    medium = v1["thresholds"]["medium_confidence"]

    out = {
        "_description": "Frozen recalibration parameters for B3's LoRA fine-tuned "
                          "checkpoint (semantic_gate_v3_v25_lora_merged), fit on a "
                          "validation-only split of STBV-Bench v1 (never on test). "
                          "Applied at evaluation time ONLY, via an isce_config.yaml "
                          "override (see rerun_recalibrated.py) -- pipeline/b3_bridge.py's "
                          "live B3RiskPolicy defaults (0.85/0.60) and isce_config.yaml's "
                          "committed temperature_scaling (2.1446, fit for the ORIGINAL "
                          "checkpoint) are UNCHANGED on disk.",
        "checkpoint": "b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3_v25_lora_merged",
        "fit_on": "STBV-Bench v1, stratified-by-attack_family random val split "
                   "(20% of the first 10,000 samples, seed=42); see RECALIBRATION_RESULTS.md "
                   "for full methodology and why a template-level split (as used for v2.5) "
                   "was not available for v1.",
        "objective": "F1-maximization on validation (medium_confidence primary; "
                      "high_confidence chosen by precision-anchored search over the "
                      "REJECT band, subject to >=5% recall of validation positives), "
                      "consistent with calibration.py's existing temperature-fit approach. "
                      "No documented alternative objective was found for the original "
                      "0.85/0.60 thresholds in stbv_paper.tex, so this explicit choice is "
                      "disclosed rather than assumed.",
        "temperature_scaling": {
            "fitted_temperature_new": T_new,
            "production_temperature_old": 2.1446,
            "note": "T_old=2.1446 was fit for the ORIGINAL checkpoint (b3_eval/run_calibration.py) "
                     "and was left unchanged (mis-applied) to the fine-tuned checkpoint in the "
                     "prior task's 'old thresholds' arm -- this is the recalibration this task performs.",
        },
        "b3_risk_policy": {
            "high_confidence": high,
            "medium_confidence": medium,
            "old_high_confidence": 0.85,
            "old_medium_confidence": 0.60,
            "applies_to": "pipeline.b3_bridge.B3RiskPolicy (isce_config.yaml "
                           "b3_semantic_gate.risk_thresholds.{high,medium})",
        },
        "trust_decision_engine": {
            "note": "trust_engine.decision_engine.TrustDecisionEngine's ACCEPT/CAUTION/REJECT "
                     "fusion reads B3's risk_level (SemanticRisk.HIGH/MEDIUM/LOW/NONE) as an "
                     "OPAQUE field -- risk_level is computed entirely by B3RiskPolicy above, "
                     "using ONLY high_confidence/medium_confidence. trust_engine.policy.TrustPolicy "
                     "also carries semantic_high_confidence/semantic_medium_confidence fields, "
                     "but per that dataclass's own docstring these are 'FALLBACK ONLY' and not "
                     "read on the live SemanticResult-based decision path (verified by reading "
                     "trust_engine/decision_engine.py: it branches on semantic_risk, which "
                     "already reflects B3RiskPolicy's thresholds, never re-reading raw "
                     "confidence against TrustPolicy's own fields). There is therefore no "
                     "SEPARATE Trust-Decision-Engine-level Accept/Caution/Reject threshold to "
                     "tune beyond B3RiskPolicy's high/medium above; for robustness and to keep "
                     "the fallback path consistent, the SAME values are frozen below for "
                     "TrustPolicy.semantic_high_confidence/semantic_medium_confidence, though "
                     "they are not exercised by the current live code path.",
            "semantic_high_confidence": high,
            "semantic_medium_confidence": medium,
            "cryptographic_reject_below": 0.40,
            "cryptographic_caution_below": 0.70,
            "cryptographic_bands_note": "Unchanged -- B1/crypto path is independent of B3's "
                                          "checkpoint and out of scope for this recalibration.",
        },
        "calibration_metrics": v1["calibration"],
    }
    (RESULTS / "recalibrated_thresholds.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
