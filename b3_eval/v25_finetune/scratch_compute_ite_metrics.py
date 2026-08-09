import csv, pathlib, json

BASE = pathlib.Path("ite_bench/results")
CONFIGS = {1: "B1 only", 2: "B1+B2(+CP)", 3: "B1+B2+CP", 4: "B3 only", 5: "Full stack"}

def metrics(rows, positive_decisions):
    tp = fp = tn = fn = 0
    for r in rows:
        is_att = r["is_attacker"] == "True"
        pred_pos = r["decision"] in positive_decisions
        if is_att and pred_pos: tp += 1
        elif is_att and not pred_pos: fn += 1
        elif not is_att and pred_pos: fp += 1
        else: tn += 1
    n = tp+fp+tn+fn
    acc = (tp+tn)/n if n else float("nan")
    prec = tp/(tp+fp) if (tp+fp) else float("nan")
    rec = tp/(tp+fn) if (tp+fn) else float("nan")
    f1 = 2*prec*rec/(prec+rec) if (prec+rec) else float("nan")
    fpr = fp/(fp+tn) if (fp+tn) else float("nan")
    return dict(n=n, tp=tp, fp=fp, tn=tn, fn=fn, acc=acc, prec=prec, rec=rec, f1=f1, fpr=fpr)

out = {}
for cfg, name in CONFIGS.items():
    rows = list(csv.DictReader(open(BASE / f"ite_config_{cfg}.csv", encoding="utf-8")))
    out[cfg] = {"name": name, "overall_flagged": metrics(rows, {"REJECT","CAUTION"}),
                "overall_reject_only": metrics(rows, {"REJECT"})}
    # per-layer breakdown
    by_layer = {}
    for layer in sorted(set(r["layer"] for r in rows if r["layer"])):
        layer_rows = [r for r in rows if r["layer"] == layer or r["attack_family"] == "benign_control"]
        # actually restrict to that layer's attack rows + all benign for fair recall/FPR per layer
        pass
    out[cfg]["layers_present"] = sorted(set(r["layer"] for r in rows))
print(json.dumps(out, indent=2))
