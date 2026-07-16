#!/usr/bin/env python3
"""
generate_decision_traces.py  (v2 — matched to real result schema)
=================================================================
Emits one END-TO-END DECISION TRACE per semantic attack family through:
  PKI -> B1 -> MBD -> B2 -> CP -> B3 -> Trust Engine -> DS Fusion -> Decision

Every value is read from the ACTUAL pipeline result. Layers that are not
enabled in the current pipeline configuration (e.g. PKI/MBD/CP when the
default ISCEPipeline runs them as None) are reported honestly as
"not enabled in this run" — NOT faked as a pass. This matters: a trace must
show what actually executed.

To exercise PKI/MBD/CP, construct the pipeline with them enabled and pass a CA
(see --full-stack, which sets enable_mbd/enable_cp=True; PKI still requires a
CA object the evaluation harness supplies — if absent, PKI is reported as
not-enabled rather than invented).

Usage:
    python3 generate_decision_traces.py --format json --out decision_traces.json
    python3 generate_decision_traces.py --out decision_traces.md
    python3 generate_decision_traces.py --full-stack --out decision_traces.md
"""
from __future__ import annotations
import argparse, json, pathlib, sys
from typing import Any, Dict, List, Optional

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _d(x) -> Dict[str, Any]:
    """Coerce possibly-None layer output to a dict."""
    return x if isinstance(x, dict) else {}


def _first_per_family(corpus):
    picked = {}
    for r in corpus:
        if str(r.get("expected_label")).upper() == "BENIGN" and "benign" not in picked:
            picked["benign"] = r
    for r in corpus:
        if str(r.get("expected_label")).upper() == "MALICIOUS":
            cat = str(r.get("attack_category", "unknown"))
            picked.setdefault(cat, r)
    return picked


def _layer(name, enabled, passed, score, latency_ms, evidence, note, checks=None, inputs=None):
    return {"layer": name, "enabled": enabled, "passed": passed, "score": score,
            "latency_ms": round(latency_ms, 3) if isinstance(latency_ms, (int, float)) else None,
            "evidence": evidence or [], "note": note,
            "checks": checks or [], "inputs": inputs or []}


def build_trace(pipe, rec):
    r = pipe.run([rec], context=(_d(rec.get("scene_context")).get("context")) or "urban")
    lat = _d(r.get("latencies"))
    pki, b1, mbd = r.get("pki"), _d(r.get("b1")), r.get("mbd")
    b2, cp, b3 = _d(r.get("b2")), r.get("cp"), _d(r.get("b3"))
    fusion, synth = _d(r.get("fusion")), _d(r.get("synthesized_message"))

    layers = []
    # PKI — may be disabled (None)
    if pki is None:
        layers.append(_layer("PKI", False, None, None, lat.get("pki_ms"),
                             ["not enabled in this pipeline configuration"],
                             "certificate / signature validation"))
    else:
        p = _d(pki)
        layers.append(_layer("PKI", True, p.get("valid", p.get("passed")),
                             p.get("confidence"), lat.get("pki_ms"),
                             p.get("reasons", p.get("evidence", [])),
                             "certificate / signature validation",
                             ["certificate chain", "signature", "revocation"],
                             ["certificate_id", "header.station_id"]))
    # B1 — always present
    layers.append(_layer("B1 (SCSV)", True, b1.get("valid", b1.get("passed")),
                         b1.get("score"), lat.get("b1_ms"),
                         b1.get("reasons", b1.get("evidence", [])),
                         "structural / protocol / replay / plausibility",
                         list(_d(b1.get("checks")).keys()) or ["ETSI structure", "replay", "timestamp"],
                         ["cam.*", "generation_delta_time"]))
    # MBD — may be disabled
    if mbd is None:
        layers.append(_layer("MBD", False, None, None, lat.get("mbd_ms"),
                             ["not enabled in this pipeline configuration"],
                             "behavioral / kinematic misbehavior"))
    else:
        m = _d(mbd)
        layers.append(_layer("MBD", True, m.get("passed"), m.get("anomaly_score"),
                             lat.get("mbd_ms"), m.get("evidence", []),
                             "behavioral / kinematic misbehavior",
                             ["plausibility", "sybil", "replay"], ["pos", "spd", "hed"]))
    # B2 — real keys: validation_valid / validation_score
    layers.append(_layer("B2", True, b2.get("validation_valid", True),
                         b2.get("validation_score", b2.get("confidence_calibration")),
                         lat.get("b2_ms"), b2.get("evidence", []),
                         "explainability / trust propagation",
                         ["cross-message consistency", "trust propagation"], ["mbd result"]))
    # CP — may be disabled
    if cp is None:
        layers.append(_layer("CP", False, None, None, lat.get("cp_ms"),
                             ["not enabled in this pipeline configuration"],
                             "cooperative-perception corroboration"))
    else:
        c = _d(cp)
        layers.append(_layer("CP", True, c.get("passed", True),
                             c.get("confidence", c.get("score")), lat.get("cp_ms"),
                             c.get("evidence", c.get("reasons", [])),
                             "cooperative-perception corroboration",
                             ["peer agreement", "event contradiction"], ["scene_context.peer_reports"]))
    # B3 — real keys present
    b3_avail = b3.get("available")
    layers.append(_layer("B3 (semantic)", bool(b3_avail),
                         (None if not b3_avail else (b3.get("label") == "BENIGN")),
                         b3.get("confidence"),
                         lat.get("bridge_ms", lat.get("synthesizer_ms")),
                         [f"label={b3.get('label')}", f"risk={b3.get('risk_level')}",
                          f"p_malicious={b3.get('p_malicious')}", f"available={b3_avail}"],
                         "semantic trust gate (DeBERTa-v2)",
                         ["semantic classification (binary)", "risk-band mapping"],
                         ["synthesized scene text"]))

    payload = (_d(rec.get("scene_context")).get("peer_reports")
               or _d(rec.get("scene_context")).get("rsu_messages") or [None])
    return {
        "attack_id": rec.get("attack_id"), "family": rec.get("attack_category", "benign"),
        "subcategory": rec.get("attack_subcategory"), "expected_label": rec.get("expected_label"),
        "injected_payload": payload[0] if payload else None,
        "synthesized_text_b3_saw": synth.get("text", "")[:400],
        "layers": layers,
        "fusion": {"trust_score": fusion.get("trust_score"),
                   "trust_level": fusion.get("trust_level"),
                   "semantic_risk": fusion.get("semantic_risk"),
                   "cryptographic_risk": fusion.get("cryptographic_risk"),
                   "attack_detected": fusion.get("attack_detected"),
                   "fuse_ms": lat.get("fuse_ms", lat.get("fusion_ms")),
                   "masses": {"note": "Yager combination; conflict→Θ; B3 risk band drives policy floor"}},
        "final_decision": r.get("decision", fusion.get("trust_level")),
        "reason": r.get("reason", _d(r.get("fusion")).get("reasoning", "")),
        "total_ms": lat.get("total_ms"),
        "correct": ((r.get("decision", fusion.get("trust_level")) == "REJECT") ==
                    (str(rec.get("expected_label")).upper() == "MALICIOUS")),
    }


def render_markdown(traces):
    out = ["# End-to-End Decision Traces (one per family)", "",
           "*Real pipeline output. Layers marked 'not enabled' were disabled in this run's "
           "pipeline configuration and are reported honestly rather than assumed to pass. "
           "Each trace is one representative message; detection RATES come from the full "
           "multi-seed evaluation, not from single traces.*", ""]
    for t in traces:
        out.append(f"## {t['family']} (`{t['attack_id']}`, expected {t['expected_label']})")
        if t.get("injected_payload"):
            out.append(f"**Injected payload:** {t['injected_payload']}")
        out.append(f"**Text B3 saw:** {t['synthesized_text_b3_saw']!r}\n")
        out.append("| Layer | Enabled | Result | Score | Latency ms | Evidence |")
        out.append("|---|---|---|---|---|---|")
        for L in t["layers"]:
            res = "N/A" if L["passed"] is None else ("PASS" if L["passed"] else "FLAG/DETECT")
            ev = "; ".join(str(e) for e in L["evidence"])[:80]
            out.append(f"| {L['layer']} | {L['enabled']} | {res} | {L['score']} | {L['latency_ms']} | {ev} |")
        f = t["fusion"]
        out.append(f"| **DS Fusion** | True | detected={f['attack_detected']} | trust={f['trust_score']} | {f['fuse_ms']} | risk band → policy floor |")
        out.append(f"\n**FINAL: {t['final_decision']}** ({'correct' if t['correct'] else 'INCORRECT'}), total {t['total_ms']} ms")
        out.append(f"> {t['reason']}\n\n---\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=20260713)
    ap.add_argument("--full-stack", action="store_true",
                    help="enable MBD and CP (PKI still requires a CA; reported honestly if absent)")
    args = ap.parse_args()

    try:
        from semantic_evaluation.semantic_attack_generator import generate_corpus
        from pipeline.orchestrator import ISCEPipeline
    except Exception as e:
        print(f"[FATAL] import failed: {e}"); return 2

    corpus = generate_corpus(seed=args.seed)
    picked = _first_per_family(corpus)
    print(f"[info] {len(picked)} families: {sorted(picked)}", file=sys.stderr)

    pipe = ISCEPipeline(enable_mbd=args.full_stack, enable_cp=args.full_stack)
    traces = []
    for fam, rec in picked.items():
        try:
            traces.append(build_trace(pipe, rec))
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[warn] {fam}: {type(e).__name__}: {e}", file=sys.stderr)

    text = json.dumps(traces, indent=2, default=str) if args.format == "json" else render_markdown(traces)
    if args.out:
        pathlib.Path(args.out).write_text(text); print(f"[written] {args.out} ({len(traces)} traces)", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())