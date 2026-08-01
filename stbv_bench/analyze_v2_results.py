import csv, json
from collections import defaultdict, Counter

rows = list(csv.DictReader(open("results/stbv_bench_v2/stbv_bench_v2_per_message.csv", encoding="utf-8")))
att = [r for r in rows if r["is_attacker_sender"] == "True"]

by_fam = defaultdict(lambda: Counter())
for r in att:
    by_fam[r["attack_family"]][r["decision"]] += 1

out = {
    "n_messages_total": len(rows),
    "decision_distribution": dict(Counter(r["decision"] for r in rows)),
    "cp_num_reports_range": [min(int(r["cp_num_reports"]) for r in rows),
                               max(int(r["cp_num_reports"]) for r in rows)],
    "cp_confidence_distinct_values": sorted(set(r["cp_confidence"] for r in rows)),
    "n_attacker_sender_rows": len(att),
    "per_family_recall": {},
}
for fam, c in sorted(by_fam.items()):
    n = sum(c.values())
    detected = c.get("CAUTION", 0) + c.get("REJECT", 0)
    out["per_family_recall"][fam] = {"n": n, "detected": detected,
                                       "recall": detected / n if n else float("nan"),
                                       "decision_counts": dict(c)}

with open("results/stbv_bench_v2/analysis_summary.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
