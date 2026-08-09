import csv, pathlib, json, statistics as st
from collections import defaultdict

BASE = pathlib.Path("b3_eval/v25_finetune/ablation_results/v25b_full_hardmine")
rows = list(csv.DictReader(open(BASE / "config_5.csv", encoding="utf-8")))

fam_att = defaultdict(list)  # attacker rows: list of (conf, flagged, is_fn)
for r in rows:
    if r["is_attacker"] == "True":
        conf = float(r["raw_score"])
        flagged = r["decision"] in ("REJECT", "CAUTION")
        fam_att[r["attack_family"]].append((conf, flagged))

metrics = {}
for fam, vals in fam_att.items():
    confs = [c for c, f in vals]
    fn = sum(1 for c, f in vals if not f)
    n = len(vals)
    metrics[fam] = {
        "n": n,
        "mean_conf": st.mean(confs),
        "median_conf": st.median(confs),
        "stdev_conf": st.pstdev(confs),
        "min_conf": min(confs),
        "max_conf": max(confs),
        "fn_count": fn,
        "recall": (n - fn) / n,
    }

# benign (FP) side, single pseudo-family
ben = [(float(r["raw_score"]), r["decision"] in ("REJECT", "CAUTION")) for r in rows if r["is_attacker"] == "False"]
fp = sum(1 for c, f in ben if f)
print("benign_control: n=%d FP=%d FPR=%.3f mean_conf=%.3f" % (len(ben), fp, fp/len(ben), st.mean(c for c,f in ben)))

# information-content summary across families for each metric
import numpy as np
for metric in ["mean_conf", "stdev_conf", "recall", "fn_count"]:
    vals = np.array([metrics[f][metric] for f in metrics])
    cv = vals.std() / vals.mean() if vals.mean() else float("nan")
    print(f"{metric:12s} min={vals.min():.4f} max={vals.max():.4f} std={vals.std():.4f} CV={cv:.4f} range={vals.max()-vals.min():.4f}")

print(json.dumps(metrics, indent=2, sort_keys=True))
