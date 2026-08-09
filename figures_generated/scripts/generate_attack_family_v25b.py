"""
figures_generated/scripts/generate_attack_family_v25b.py
===============================================================
Per-attack-family breakdown, STBV-Bench v2.5b, Full STBV Framework,
current final (hardmine) checkpoint -- real per-sample decisions from
b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_5.csv.

Redesigned per ATTACK_FIGURE_AUDIT.md / ATTACK_METRIC_ANALYSIS.md /
ATTACK_FIGURE_SELECTION.md: recall was rejected as a visualization
metric (CV=0.0027 across families -- near-ceiling for every family, the
exact "visually flat" failure mode this redesign exists to avoid).

Panel A: mean B3 confidence (raw_score = calibrated P(malicious)) per
family, sorted low-to-high, with error bars showing each family's own
real within-family standard deviation -- the most discriminative metric
found in the Step 2 sweep (CV=1.05), not recall.
Panel B: false-negative counts per family (real, unchanged in content
from the prior version of this figure; only 3/13 families have any).
Both panels computed directly from the same real per-sample CSV; no
interpolation, smoothing, or fabricated value.
"""
import csv, pathlib, statistics as st
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"
plt.rcParams.update({"font.size": 9, "figure.dpi": 150, "font.family": "DejaVu Sans"})

rows = list(csv.DictReader(open(V25B_HM / "config_5.csv", encoding="utf-8")))
fam_conf = defaultdict(list)   # attacker rows: calibrated P(malicious)
fam_flag = defaultdict(list)   # attacker rows: was this message flagged (Caution/Reject)?
for r in rows:
    if r["is_attacker"] == "True":
        fam = r["attack_family"]
        fam_conf[fam].append(float(r["raw_score"]))
        fam_flag[fam].append(r["decision"] in ("REJECT", "CAUTION"))

families = sorted(fam_conf.keys(), key=lambda f: st.mean(fam_conf[f]))
means = [st.mean(fam_conf[f]) for f in families]
stdevs = [st.pstdev(fam_conf[f]) for f in families]
fns = [sum(1 for flagged in fam_flag[f] if not flagged) for f in families]
ns = [len(fam_conf[f]) for f in families]
labels = [f.replace("_", " ") for f in families]

# colorblind-safe: dark teal for bars, orange for the "any FN" highlight
BAR_C = "#0072B2"
FN_C = "#D55E00"
NOFN_C = "#BBBBBB"

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 4.0), sharey=True)

ax1.barh(labels, means, xerr=stdevs, color=BAR_C, height=0.62,
          error_kw=dict(ecolor="0.25", elinewidth=1.1, capsize=2.5))
ax1.set_xlim(0.0, 1.05)
ax1.set_xlabel("Mean B3 confidence $P$(malicious), $\\pm$1 std. dev.", fontsize=9)
ax1.set_title("(A) Confidence: level and consistency\n(std. dev. -- not recall -- separates families)", fontsize=9.2)
ax1.axvline(0.70, color="0.5", lw=1.0, ls="--")
ax1.text(0.70, len(labels) - 0.3, "$\\tau_H$", fontsize=8, ha="left", color="0.4")

colors = [FN_C if fn > 0 else NOFN_C for fn in fns]
ax2.barh(labels, fns, color=colors, height=0.62)
ax2.set_xlabel("False-negative count (of $n$ attacks)", fontsize=9)
ax2.set_title("(B) Where errors occur\n(only 3/13 families have any)", fontsize=9.2)
ax2.set_xlim(0, max(fns) + 1.6)
for i, (fn, n) in enumerate(zip(fns, ns)):
    ax2.text(fn + 0.08, i, f"{fn}/{n}", va="center", fontsize=7.8)

for ax in (ax1, ax2):
    ax.tick_params(axis="y", labelsize=8.6)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

fig.tight_layout()
fig.savefig(OUT / "fig_attack_family_v25b.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_attack_family_v25b.png", bbox_inches="tight", dpi=300)
print("wrote", OUT / "fig_attack_family_v25b.pdf")
