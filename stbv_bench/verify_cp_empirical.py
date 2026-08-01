"""
Empirical CP verification (requested check, not a re-run of anything
committed): confirms CP actually influences decisions on genuine
multi-message windows, using the existing Phase 2 scenario fixtures
(scenarios/{sybil,replay,fabrication,collusion,mixed,semantic}/*.json,
20 messages each = 120 total). These are real multi-vehicle continuous
scenarios (unlike STBV-Bench's independent single messages), so it is
correct methodology here to replay each scenario statefully through ONE
persistent pipeline per scenario, growing the message window at each
step -- this is the same approach PUBLICATION_PROGRESS.md's Phase 2 audit
used, and is the right comparison point for "does CP ever get >1 report
to work with, and if so, does it change anything."

For each scenario, replay it twice: once with CP enabled, once with CP
disabled (both otherwise identical, fresh pipeline per scenario per arm),
and diff the two decision sequences message-by-message.
"""
import sys, json, glob
sys.path.insert(0, ".")
from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

SCENARIOS = ["sybil", "replay", "fabrication", "collusion", "mixed", "semantic"]

results = {}
for scen in SCENARIOS:
    files = sorted(glob.glob(f"scenarios/{scen}/*.json"))
    msgs = [json.loads(open(f, encoding="utf-8").read()) for f in files]

    p_cp_on = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=False)
    p_cp_off = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=False, enable_b3=False)

    window = []
    rows = []
    for i, m in enumerate(msgs):
        window.append(dict(m))  # accumulate real multi-vehicle window
        res_on = p_cp_on.run(list(window), context="urban")
        res_off = p_cp_off.run(list(window), context="urban")
        cp_dict = res_on.get("cp") or {}
        rows.append({
            "i": i, "station": m["header"].get("station_id"),
            "is_attacker": m.get("is_attacker"),
            "decision_cp_on": res_on["decision"], "decision_cp_off": res_off["decision"],
            "flipped": res_on["decision"] != res_off["decision"],
            "cp_num_reports": cp_dict.get("num_reports"),
            "cp_confidence": cp_dict.get("cp_confidence"),
            "cp_event_label": cp_dict.get("event_label"),
        })
    n_flipped = sum(r["flipped"] for r in rows)
    n_multi_report = sum(1 for r in rows if (r["cp_num_reports"] or 0) > 1)
    results[scen] = {"rows": rows, "n_flipped": n_flipped, "n_multi_report": n_multi_report, "n": len(rows)}
    print(f"{scen:12s} n={len(rows):3d} multi-report-steps={n_multi_report:3d} "
          f"decision_flips(CPon vs CPoff)={n_flipped}")
    for r in rows:
        if r["flipped"] or (r["cp_num_reports"] or 0) > 1:
            print(f"    i={r['i']:2d} station={r['station']} attacker={r['is_attacker']} "
                  f"num_reports={r['cp_num_reports']} cp_conf={r['cp_confidence']} "
                  f"event={r['cp_event_label']} on={r['decision_cp_on']} off={r['decision_cp_off']} "
                  f"flip={r['flipped']}")

total_flipped = sum(v["n_flipped"] for v in results.values())
total_multi = sum(v["n_multi_report"] for v in results.values())
total_n = sum(v["n"] for v in results.values())
print(f"\nTOTAL: n={total_n}, multi-report steps={total_multi}, CP-attributable decision flips={total_flipped}")

with open("results/ablation/cp_empirical_verification.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)
print("-> results/ablation/cp_empirical_verification.json")
