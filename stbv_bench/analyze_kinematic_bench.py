import csv, json
from collections import defaultdict

def load(i):
    return list(csv.DictReader(open(f"results/veremi_kinematic/veremi_kinematic_config_{i}.csv", encoding="utf-8")))

out = {}
for i in (1, 2, 3, 4):
    rows = load(i)
    tp = fp = fn = tn = 0
    for r in rows:
        truth = r["is_attacker"] == "True"
        pred = r["decision"] in ("REJECT", "CAUTION")
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
        elif not pred and truth:
            fn += 1
        else:
            tn += 1
    n = len(rows)
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    out[f"config_{i}"] = {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                            "precision": prec, "recall": rec, "f1": f1, "fpr": fpr}

rows2 = load(2)
by_sender = defaultdict(list)
for r in rows2:
    by_sender[r["sender"]].append(r)
veh_tp = veh_fp = veh_fn = veh_tn = 0
for sender, rs in by_sender.items():
    truth = rs[0]["is_attacker"] == "True"
    ever_flagged = any(r["decision"] in ("REJECT", "CAUTION") for r in rs)
    if ever_flagged and truth:
        veh_tp += 1
    elif ever_flagged and not truth:
        veh_fp += 1
    elif not ever_flagged and truth:
        veh_fn += 1
    else:
        veh_tn += 1
n_veh = len(by_sender)
prec_v = veh_tp / (veh_tp + veh_fp)
rec_v = veh_tp / (veh_tp + veh_fn)
f1_v = 2 * prec_v * rec_v / (prec_v + rec_v)
fpr_v = veh_fp / (veh_fp + veh_tn)
out["per_vehicle_ever_flagged_config_2"] = {
    "n_vehicles": n_veh, "tp": veh_tp, "fp": veh_fp, "fn": veh_fn, "tn": veh_tn,
    "precision": prec_v, "recall": rec_v, "f1": f1_v, "fpr": fpr_v,
}

by_source = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
for r in rows2:
    truth = r["is_attacker"] == "True"
    pred = r["decision"] in ("REJECT", "CAUTION")
    d = by_source[r["source_dataset"]]
    if pred and truth:
        d["tp"] += 1
    elif pred and not truth:
        d["fp"] += 1
    elif not pred and truth:
        d["fn"] += 1
    else:
        d["tn"] += 1
out["by_attack_type_config_2"] = {}
for src, d in by_source.items():
    tp, fp, fn, tn = d["tp"], d["fp"], d["fn"], d["tn"]
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    out["by_attack_type_config_2"][src] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                                             "precision": prec, "recall": rec, "fpr": fpr}

with open("results/veremi_kinematic/analysis_summary.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
