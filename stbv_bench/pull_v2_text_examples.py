import sys, json, csv
sys.path.insert(0, ".")
from pipeline.synthesizer import synthesize_message
from stbv_bench.transformations import ALL_RULES

TARGET_FAMILIES = ["goal_manipulation", "indirect_prompt_injection"]
N_PER_FAMILY = 4

windows = [json.loads(l) for l in open("results/stbv_bench_v2/stbv_bench_v2_windows.jsonl", encoding="utf-8")]
decisions = list(csv.DictReader(open("results/stbv_bench_v2/stbv_bench_v2_per_message.csv", encoding="utf-8")))

# Build a lookup: for each window_id, ordered list of (sender, decision) for attacker-sender rows,
# in the same order they were produced (i.e., in window message order for that sender's own messages)
dec_by_window = {}
for r in decisions:
    dec_by_window.setdefault(r["window_id"], []).append(r)

for fam in TARGET_FAMILIES:
    print(f"\n{'='*100}\nFAMILY: {fam}\n{'='*100}")
    fam_windows = [w for w in windows if w["attack_family"] == fam]
    shown = 0
    for w in fam_windows:
        if shown >= N_PER_FAMILY:
            break
        attacker_senders = set(w["attacker_senders"])
        window_msgs = []
        dec_rows = iter([r for r in dec_by_window.get(w["window_id"], [])])
        for m in w["messages"]:
            clean = {k: v for k, v in m.items() if not k.startswith("_")}
            window_msgs.append(clean)
            sender = m.get("_window_sender")
            if sender in attacker_senders and shown < N_PER_FAMILY:
                synth = synthesize_message(list(window_msgs), {}, context="urban")
                try:
                    row = next(dec_rows)
                    decision = row["decision"]
                except StopIteration:
                    decision = "?"
                print(f"\n--- window={w['window_id']} sender={sender} n_in_window={len(window_msgs)} decision={decision} ---")
                print(synth["text"])
                shown += 1
