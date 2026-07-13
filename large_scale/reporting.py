"""
large_scale/reporting.py
==========================
Parts 6 & 7: consolidate large-scale results into publication outputs (CSV,
JSON, LaTeX, figures) and auto-generate FINAL_REPORT.md (best config, largest
weakness/bottleneck/FP source/FN source, publication recommendations).

Reuses evaluation.metrics_and_outputs for the shared metric + plot code.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from evaluation import metrics_and_outputs as mo


def _by(rows, key):
    groups: Dict[Any, List[Dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r.get(key), []).append(r)
    return groups


def _scored(rows):
    return [r for r in rows if r.get("decision") in ("ACCEPT", "CAUTION", "REJECT")]


def write_all_outputs(rows: List[Dict[str, Any]], resource: Dict[str, Any],
                       out_dir: pathlib.Path, b3_available: bool,
                       scenario_rows: List[Dict[str, Any]] = None) -> None:
    plots = out_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    per_msg = _scored(rows)                       # per-message: latency, mass, diagnostics
    scored = scenario_rows if scenario_rows is not None else per_msg  # PRIMARY metric unit

    mo.write_rows_csv(rows, out_dir / "per_message.csv")
    if scenario_rows is not None:
        import csv as _csv
        keys = sorted({k for r in scenario_rows for k in r})
        with (out_dir / "per_scenario.csv").open("w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(scenario_rows)

    # metrics by family
    fam_table = {"full": {}}
    for fam, frows in _by(scored, "family").items():
        if fam is not None:
            fam_table["full"][fam] = mo.confusion(frows)
    mo.write_metrics_csv(fam_table, out_dir / "metrics_by_family.csv")
    mo.write_latex_table(fam_table, out_dir / "metrics_by_family.tex",
                          caption="Detection metrics per attack family, full stack.",
                          label="tab:largescale")

    # sweep results: metrics per (vehicle_count, attacker_pct)
    sweep_rows = []
    for vc, vrows in _by(scored, "vehicle_count").items():
        for pct, prows in _by(vrows, "attacker_pct").items():
            m = mo.confusion(prows)
            sweep_rows.append({"vehicle_count": vc, "attacker_pct": pct, **m})
    import csv as _csv
    if sweep_rows:
        with (out_dir / "sweep_results.csv").open("w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(sweep_rows[0].keys()))
            w.writeheader(); w.writerows(sweep_rows)

    # confusion + ROC/PR aggregate
    agg = mo.confusion(scored)
    mo.plot_confusion_matrix(agg, "full stack (all families)", plots / "confusion_full.png")
    auc = mo.plot_roc_pr(scored, "full stack", plots / "curves_full")

    # latency histogram + throughput (per-message: needs latencies)
    _latency_hist(per_msg, plots / "latency_hist.png")
    _throughput_by_scale(per_msg, plots / "throughput_by_vehicle_count.png")

    # trust-score + belief-mass distributions (Part 4)
    _trust_score_dist(per_msg, plots / "trust_score_distribution.png")
    _belief_mass_dist(per_msg, plots / "belief_mass_distribution.png")

    # attacker-pct detection curve
    _detection_vs_attacker_pct(scored, plots / "detection_vs_attacker_pct.png")

    summary = {"n_rows": len(rows), "n_scored": len(scored), "aggregate": agg,
               "by_family": fam_table["full"], "sweep": sweep_rows,
               "auc": auc, "resource": resource, "b3_available": b3_available}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

    _final_report(rows, per_msg, scored, fam_table["full"], sweep_rows, agg, resource,
                  out_dir, b3_available, auc)


# ----------------------------------------------------------------- plots ---
def _latency_hist(rows, path):
    tot = [r["latencies"].get("total_ms") for r in rows
           if r.get("latencies") and r["latencies"].get("total_ms") is not None]
    if not tot:
        return
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.hist(tot, bins=40)
    ax.set_xlabel("per-message total latency (ms)"); ax.set_ylabel("count")
    ax.set_title("Pipeline latency distribution", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def _throughput_by_scale(rows, path):
    groups = _by(rows, "vehicle_count")
    xs = sorted(k for k in groups if k is not None)
    if not xs:
        return
    ys = []
    for vc in xs:
        lat = [r["latencies"]["total_ms"] for r in groups[vc]
               if r.get("latencies") and r["latencies"].get("total_ms")]
        ys.append(1000.0 / (sum(lat) / len(lat)) if lat else 0)
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot(xs, ys, "o-")
    ax.set_xlabel("vehicle count"); ax.set_ylabel("throughput (msg/s, 1 core)")
    ax.set_title("Throughput vs scale", fontsize=9); ax.set_xscale("log")
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def _trust_score_dist(rows, path):
    benign = [r["trust_score"] for r in rows if "trust_score" in r and not r["truth_attacker"]]
    attack = [r["trust_score"] for r in rows if "trust_score" in r and r["truth_attacker"]]
    if not benign and not attack:
        return
    fig, ax = plt.subplots(figsize=(4.2, 3))
    if benign:
        ax.hist(benign, bins=30, alpha=.6, label="benign", density=True)
    if attack:
        ax.hist(attack, bins=30, alpha=.6, label="attacker", density=True)
    ax.set_xlabel("final trust score"); ax.set_ylabel("density")
    ax.set_title("Trust-score distribution", fontsize=9); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def _belief_mass_dist(rows, path):
    m_a = [r["m_A"] for r in rows if r.get("m_A") is not None]
    m_n = [r["m_notA"] for r in rows if r.get("m_notA") is not None]
    m_t = [r["m_theta"] for r in rows if r.get("m_theta") is not None]
    if not m_a:
        return
    fig, ax = plt.subplots(figsize=(4.2, 3))
    for data, lbl in ((m_a, "m(A) belief"), (m_n, "m(¬A) disbelief"), (m_t, "m(Θ) ignorance")):
        ax.hist(data, bins=30, alpha=.5, label=lbl, density=True)
    ax.set_xlabel("mass"); ax.set_ylabel("density")
    ax.set_title("Belief-mass distribution (crypto frame)", fontsize=9); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def _detection_vs_attacker_pct(rows, path):
    groups = _by([r for r in rows if r["truth_attacker"]], "attacker_pct")
    xs = sorted(k for k in groups if k is not None)
    if not xs:
        return
    ys = []
    for pct in xs:
        det = sum(1 for r in groups[pct] if r["decision"] == "REJECT") / len(groups[pct])
        ys.append(det)
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([x * 100 for x in xs], ys, "o-")
    ax.set_xlabel("attacker %"); ax.set_ylabel("REJECT rate on attackers")
    ax.set_title("Detection vs attacker density", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


# --------------------------------------------------------------- report ----
def _final_report(rows, per_msg, scored, by_family, sweep_rows, agg, resource, out_dir,
                  b3_available, auc):
    n_err = sum(1 for r in rows if r.get("decision") in ("ERROR", "GEN_ERROR"))
    n_contract = sum(len(r.get("contract_violations") or []) for r in rows)

    # best config = highest F1 among family groups with a defined F1
    best_fam = max(((f, m) for f, m in by_family.items() if m["f1"] == m["f1"]),
                   key=lambda kv: kv[1]["f1"], default=(None, None))
    # largest FP source (family with most false positives)
    fp_src = max(by_family.items(), key=lambda kv: kv[1]["fp"], default=(None, None))
    fn_src = max(by_family.items(), key=lambda kv: kv[1]["fn"], default=(None, None))

    lat = mo.latency_summary(per_msg)
    bottleneck = None
    if lat:
        per_stage = {k: v["mean"] for k, v in lat.items() if k != "total_ms"}
        if per_stage:
            bottleneck = max(per_stage, key=per_stage.get)

    lines = [
        "# Large-Scale Evaluation — Final Report",
        "",
        "*Auto-generated by large_scale/reporting.py. Numbers are computed from this run's",
        "per_message.csv; nothing here is hand-entered.*",
        "",
        "## Provenance",
        f"- Messages scored: **{len(scored)}**  (rows total {len(rows)}, errors {n_err})",
        f"- Throughput: **{resource['throughput_msgs_per_s']:.0f} msg/s** (single core), "
        f"wall {resource['wall_seconds']:.1f}s, peak RSS {resource['peak_host_rss_mb']:.0f} MB",
        f"- B3 real model available: **{b3_available}**",
    ]
    if not b3_available:
        lines += ["", "> **HONESTY NOTE.** The B3 semantic verdicts in this run are **labelled",
                  "> synthetic** (seeded profiles from `large_scale/semantic_attacks.py`), not real",
                  "> inference — the checkpoint/GPU were absent. The kinematic layers",
                  "> (PKI/B1/MBD/B2/CP) and the entire fusion/decision path are real. Re-run on GPU",
                  "> with the materialized checkpoint to replace the semantic column with measured",
                  "> values before citing any semantic-attack number."]
    lines += [
        "",
        "## Aggregate (full stack, all families)",
        f"- Accuracy **{agg['accuracy']:.3f}**, Precision **{fmt(agg['precision'])}**, "
        f"Recall **{fmt(agg['recall'])}**, F1 **{fmt(agg['f1'])}**",
        f"- FPR **{fmt(agg['fpr'])}**, FNR **{fmt(agg['fnr'])}**, "
        f"CAUTION rate **{agg['caution_rate']:.3f}**",
        f"- ROC-AUC: **{fmt(auc['auc_roc']) if auc else 'n/a (no continuous score / single class)'}**",
        "",
        "## Best-performing configuration",
        (f"- Highest-F1 family: **{best_fam[0]}** (F1 {fmt(best_fam[1]['f1'])}, "
         f"recall {fmt(best_fam[1]['recall'])}, FPR {fmt(best_fam[1]['fpr'])})"
         if best_fam[0] else "- Not determinable (no family had a defined F1)."),
        "",
        "## Largest weakness",
        _weakness(by_family, agg),
        "",
        "## Largest bottleneck",
        (f"- Slowest stage by mean latency: **{bottleneck}** "
         f"({lat[bottleneck]['mean']:.3f} ms mean, {lat[bottleneck]['p95']:.3f} ms p95)."
         if bottleneck else "- Latency not captured."),
        (f"- Note: the ~150s one-time B3 model load is excluded via preload; per-message B3 "
         "latency needs a GPU run." if not b3_available else ""),
        "",
        "## Largest source of false positives",
        (f"- Family **{fp_src[0]}** with {fp_src[1]['fp']} FPs (FPR {fmt(fp_src[1]['fpr'])}). "
         if fp_src[0] else "- No false positives recorded."),
        _fp_diagnosis(scored),
        "",
        "## Largest source of false negatives",
        (f"- Family **{fn_src[0]}** with {fn_src[1]['fn']} FNs (FNR {fmt(fn_src[1]['fnr'])})."
         if fn_src[0] else "- No false negatives recorded."),
        _fn_diagnosis(scored, b3_available),
        "",
        "## Full-stack integrity (Part 5)",
        f"- Per-layer contract violations across all messages: **{n_contract}** "
        f"({'clean' if n_contract == 0 else 'INVESTIGATE'}).",
        f"- Pipeline exceptions: **{sum(1 for r in rows if r.get('decision') == 'ERROR')}**.",
        "",
        "## Publication recommendations",
        _pub_recs(agg, by_family, b3_available, n_contract),
        "",
        "## Figures (plots/)",
        "- confusion_full.png, curves_full/roc.png, curves_full/pr.png",
        "- latency_hist.png, throughput_by_vehicle_count.png",
        "- trust_score_distribution.png, belief_mass_distribution.png",
        "- detection_vs_attacker_pct.png",
    ]
    (out_dir / "FINAL_REPORT.md").write_text("\n".join(l for l in lines if l is not None))


def fmt(v):
    return "n/a" if v is None or (isinstance(v, float) and v != v) else f"{v:.3f}"


def _weakness(by_family, agg):
    benign = by_family.get("benign")
    if benign and benign.get("caution_rate", 0) > 0.5:
        return (f"- **Benign CAUTION rate {benign['caution_rate']:.3f}**: while the REJECT-based "
                "false-positive rate is low, most benign scenarios are flagged CAUTION at least "
                "once (by design: fresh/unverified senders are cautioned until corroborated — see "
                "CHANGELOG.md). This is the main operational cost and a reviewer will ask for its "
                "downstream impact; quantify how often CAUTION would gate a real application action.")
    if agg["fpr"] == agg["fpr"] and agg["fpr"] > 0.10:
        return (f"- **False-positive rate {agg['fpr']:.3f}** (REJECT on benign) is the dominant "
                "weakness; see FP diagnosis below.")
    low_recall = [(f, m) for f, m in by_family.items() if m["recall"] == m["recall"] and m["recall"] < 0.5]
    if low_recall:
        worst = min(low_recall, key=lambda kv: kv[1]["recall"])
        return (f"- **Low recall on {worst[0]}** ({worst[1]['recall']:.3f}): a substantial share of "
                "these attacks reach ACCEPT/CAUTION rather than REJECT.")
    return "- No single dominant weakness at this scale; benign CAUTION rate is the main cost."


def _fp_diagnosis(scored):
    fps = [r for r in scored if r["decision"] == "REJECT" and not r["truth_attacker"]]
    if not fps:
        return "- No false positives to diagnose."
    from collections import Counter
    by_den = Counter(r.get("density") for r in fps)
    return (f"- Diagnosis: {len(fps)} benign REJECTs concentrated in density "
            f"{dict(by_den)}; inspect CP corroboration / MBD fresh-sender confidence in those cells.")


def _fn_diagnosis(scored, b3_available):
    fns = [r for r in scored if r["decision"] != "REJECT" and r["truth_attacker"]]
    if not fns:
        return "- No false negatives to diagnose."
    caution = sum(1 for r in fns if r["decision"] == "CAUTION")
    base = (f"- Diagnosis: {len(fns)} missed attacks, of which {caution} landed in CAUTION "
            "(flagged-but-not-rejected) rather than ACCEPT.")
    if not b3_available:
        base += (" Because B3 verdicts are synthetic here, the semantic-attack FN rate is not a "
                 "real measurement — confirm on GPU.")
    return base


def _pub_recs(agg, by_family, b3_available, n_contract):
    recs = []
    if not b3_available:
        recs.append("1. **Blocking for submission:** re-run with the real B3 checkpoint on GPU; "
                    "the semantic-attack columns must be measured, not synthetic.")
    if agg["fpr"] == agg["fpr"] and agg["fpr"] > 0.05:
        recs.append(f"2. Reduce benign FPR ({agg['fpr']:.3f}) via a cost-sensitive risk-band "
                    "threshold study (report an ROC/operating-point analysis).")
    recs.append(f"{len(recs)+1}. Report multi-seed CIs (evaluation/stats.py) on the headline "
                "metrics; single-seed points are not sufficient for a top venue.")
    recs.append(f"{len(recs)+1}. Include the ablation + baseline tables (evaluation/run_experiments.py) "
                "alongside these scale curves.")
    if n_contract == 0:
        recs.append(f"{len(recs)+1}. The clean per-layer contract record supports a strong "
                    "'full-stack validation' subsection (Part 5).")
    return "\n".join(recs)
