import csv, json
from collections import Counter, defaultdict

def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

c4 = {r["sample_id"]: r for r in load("results/ablation/ablation_config_4.csv")}
c5 = {r["sample_id"]: r for r in load("results/ablation/ablation_config_5.csv")}

ids = sorted(set(c4) & set(c5))
assert len(ids) == 10000

transitions = Counter()
transition_examples = defaultdict(lambda: Counter())  # (from,to) -> attack_family counter
full_dist = Counter()

for sid in ids:
    a = c4[sid]["decision"]  # config 4: B3 raw, no fusion
    b = c5[sid]["decision"]  # config 5: full stack fused
    full_dist[b] += 1
    if a != b:
        transitions[(a, b)] += 1
        transition_examples[(a, b)][c4[sid]["attack_family"]] += 1

print("=== Full-stack (config 5) decision distribution over all 10,000 ===")
for k in ("ACCEPT", "CAUTION", "REJECT"):
    print(f"  {k}: {full_dist[k]} ({full_dist[k]/10000*100:.2f}%)")

print("\n=== Config4 -> Config5 transitions (128 total flips) ===")
hard_flips = 0
into_caution = 0
out_of_caution = 0
for (a, b), n in sorted(transitions.items(), key=lambda kv: -kv[1]):
    print(f"  {a:8s} -> {b:8s} : {n}")
    if {a, b} == {"ACCEPT", "REJECT"}:
        hard_flips += n
    elif b == "CAUTION" and a != "CAUTION":
        into_caution += n
    elif a == "CAUTION" and b != "CAUTION":
        out_of_caution += n

total_flips = sum(transitions.values())
print(f"\nTotal flips: {total_flips}")
print(f"Hard flips (ACCEPT<->REJECT, bypassing CAUTION entirely): {hard_flips} ({hard_flips/total_flips*100:.1f}% of flips)")
print(f"Moved INTO CAUTION from a decisive state: {into_caution} ({into_caution/total_flips*100:.1f}% of flips)")
print(f"Moved OUT OF CAUTION to a decisive state: {out_of_caution} ({out_of_caution/total_flips*100:.1f}% of flips)")

print("\n=== Transition breakdown by attack_family (top families per transition) ===")
for (a, b), fam_counter in transition_examples.items():
    print(f"  {a} -> {b}:")
    for fam, n in fam_counter.most_common():
        print(f"      {fam}: {n}")

out = {
    "full_stack_decision_distribution": dict(full_dist),
    "config4_to_config5_transitions": {f"{a}->{b}": n for (a, b), n in transitions.items()},
    "hard_flips_accept_reject": hard_flips,
    "moved_into_caution": into_caution,
    "moved_out_of_caution": out_of_caution,
    "total_flips": total_flips,
    "transition_by_family": {f"{a}->{b}": dict(c) for (a, b), c in transition_examples.items()},
}
with open("results/ablation/ablation_3way_analysis.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\n-> results/ablation/ablation_3way_analysis.json")
