"""
figures_generated/scripts/generate_attack_category_v25b.py
===============================================================
Attack-CATEGORY confidence-distribution figure (third redesign of this
figure; see ATTACK_VISUALIZATION_REDESIGN.md for why bar+error-bar was
superseded by a boxplot with real outlier points). STBV-Bench v2.5b,
Full STBV Framework, current final checkpoint, real per-message B3
confidence scores from config_5.csv, aggregated into the four semantic-
attack categories already defined in Section III (Threat Model).
"""
import csv, pathlib
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"
plt.rcParams.update({"font.size": 10.5, "figure.dpi": 150, "font.family": "DejaVu Sans"})

CATS = {
    "authority_override": "Authority Claims", "false_clearance": "Authority Claims",
    "priority_manipulation": "Authority Claims", "sensor_discreditation": "Authority Claims",
    "context_inversion": "Narrative Manipulation", "narrative_poisoning": "Narrative Manipulation",
    "role_confusion": "Narrative Manipulation", "traffic_efficiency_lure": "Narrative Manipulation",
    "cross_source_contradiction": "Multi-Source Manipulation", "fabricated_consensus": "Multi-Source Manipulation",
    "goal_manipulation": "Indirection", "indirect_prompt_injection": "Indirection", "instruction_hiding": "Indirection",
}

rows = list(csv.DictReader(open(V25B_HM / "config_5.csv", encoding="utf-8")))
cat_conf = defaultdict(list)
for r in rows:
    if r["is_attacker"] == "True":
        cat_conf[CATS[r["attack_family"]]].append(float(r["raw_score"]))

# Order by median, ascending, so the hardest category (lowest median) is at the bottom.
cats = sorted(cat_conf.keys(), key=lambda c: np.median(cat_conf[c]))
data = [cat_conf[c] for c in cats]
ns = [len(d) for d in data]
below_tau = [sum(1 for v in d if v < 0.70) for d in data]

fig, ax = plt.subplots(figsize=(6.4, 3.8))
bp = ax.boxplot(data, vert=False, labels=[f"{c}\n($n$={n})" for c, n in zip(cats, ns)],
                 patch_artist=True, widths=0.55,
                 flierprops=dict(marker="o", markersize=3, markerfacecolor="#D55E00",
                                  markeredgecolor="#D55E00", alpha=0.55))
for patch in bp["boxes"]:
    patch.set_facecolor("#0072B2")
    patch.set_alpha(0.55)
for median in bp["medians"]:
    median.set_color("black")
    median.set_linewidth(1.4)

ax.axvline(0.70, color="0.35", lw=1.1, ls="--")
ax.text(0.70, len(cats) + 0.42, "$\\tau_H$", fontsize=9, ha="center", color="0.3")
ax.set_xlim(-0.02, 1.02)
ax.set_xlabel("Per-message B3 confidence $P$(malicious)")
ax.set_title("Confidence distribution by attack category\n(outlier points = individual ambiguous messages)", fontsize=10)

for i, (c, bt, n) in enumerate(zip(cats, below_tau, ns)):
    ax.text(1.03, i + 1, f"{bt}/{n}\nbelow $\\tau_H$", fontsize=7.3, va="center", ha="left", color="0.25")

fig.tight_layout()
fig.savefig(OUT / "fig_attack_family_v25b.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_attack_family_v25b.png", bbox_inches="tight", dpi=300)
print("wrote", OUT / "fig_attack_family_v25b.pdf")
for c, bt, n in zip(cats, below_tau, ns):
    print(f"{c:28s} n={n:4d} below_tauH={bt} ({100*bt/n:.1f}%) median={np.median(cat_conf[c]):.4f}")
