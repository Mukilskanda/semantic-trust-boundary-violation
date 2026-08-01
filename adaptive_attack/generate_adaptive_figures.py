#!/usr/bin/env python3
"""Figures for the adaptive attack evaluation, from adaptive_attack_analysis.json."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
d = json.loads((HERE / "results" / "adaptive_attack_analysis.json").read_text())
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=150)
    plt.close(fig)


# Confidence / detection-probability evolution
its = list(range(len(d["mean_p_malicious_by_iteration"])))
fig, ax1 = plt.subplots(figsize=(4.2, 3.2))
ax1.plot(its, d["mean_p_malicious_by_iteration"], marker="o", ms=3, color="#d62728",
         label="Mean P(malicious)")
ax1.plot(its, d["detection_probability_by_iteration"], marker="s", ms=3, color="#1f77b4",
         label="Detection probability")
ax1.set_xlabel("Adaptive mutation round")
ax1.set_ylabel("Probability")
ax1.set_ylim(0, 1.05)
ax1.set_title("Confidence & Detection Evolution\nUnder Adaptive Mutation")
ax1.legend(fontsize=7)
save(fig, "adaptive_fig_confidence_evolution")

# Per-family ASR
fam = d["family_breakdown"]
fams = sorted(fam.keys(), key=lambda f: fam[f]["asr"])
fig, ax = plt.subplots(figsize=(4.4, 3.4))
ax.barh(fams, [fam[f]["asr"] for f in fams], color="#9467bd")
for i, f in enumerate(fams):
    ax.text(fam[f]["asr"] + 0.01, i, f"n={fam[f]['n']}", va="center", fontsize=7)
ax.set_xlabel("Attack Success Rate (evasion within budget)")
ax.set_xlim(0, 1.15)
ax.set_title("Adaptive Attack Success Rate by Family")
save(fig, "adaptive_fig_asr_by_family")

# Per-strategy evasion rate when chosen
strat = d["strategy_breakdown"]
strat_names = [s for s in strat if strat[s]["times_chosen_as_best_candidate"] > 0]
strat_names.sort(key=lambda s: strat[s]["evasion_rate_when_chosen"] or 0)
fig, ax = plt.subplots(figsize=(4.6, 3.4))
ax.barh(strat_names, [strat[s]["evasion_rate_when_chosen"] or 0 for s in strat_names], color="#2ca02c")
for i, s in enumerate(strat_names):
    ax.text((strat[s]["evasion_rate_when_chosen"] or 0) + 0.01, i,
            f"n={strat[s]['times_chosen_as_best_candidate']}", va="center", fontsize=7)
ax.set_xlabel("Evasion rate when chosen as best candidate")
ax.set_title("Per-Strategy Effectiveness\n(share of winning rounds that achieved evasion)")
save(fig, "adaptive_fig_strategy_effectiveness")

print(f"Wrote 3 figures to {OUT}")
