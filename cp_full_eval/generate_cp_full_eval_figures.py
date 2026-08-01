#!/usr/bin/env python3
"""Figures for the CP full evaluation: attacker-detection recovery,
false-positive cost, per-category decision changes, and the cold-start
diversity mechanism."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
raw = json.loads((HERE / "results" / "cp_full_eval_results.json").read_text())
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=150)
    plt.close(fig)


# 1. Attacker detection: CP off vs on
n_att = caught_off = caught_on = 0
for sc in raw["scenes"]:
    for a, b in zip(sc["cp_off_b3_on"], sc["cp_on_b3_on"]):
        if a["is_attacker"]:
            n_att += 1
            caught_off += int(a["attack_detected"])
            caught_on += int(b["attack_detected"])

fig, ax = plt.subplots(figsize=(3.4, 3.2))
bars = ax.bar(["CP off", "CP on"], [caught_off / n_att, caught_on / n_att],
              color=["#7f7f7f", "#2ca02c"])
for bar, v, n in zip(bars, [caught_off, caught_on], [n_att, n_att]):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
            f"{v}/{n}", ha="center", fontsize=8)
ax.set_ylim(0, 1.1)
ax.set_ylabel("Fraction of attacker messages reaching REJECT")
ax.set_title("Attacker Detection Recovery\n(event-labeled multi-vehicle corpus)")
save(fig, "cp_fig_attacker_detection")

# 2. Per-category decision changes (full stack)
analysis = json.loads((HERE / "results" / "cp_full_eval_analysis.json").read_text())
cats = list(analysis["per_category_full_stack"].keys())
changes = [analysis["per_category_full_stack"][c]["decision_changes"] for c in cats]
ns = [analysis["per_category_full_stack"][c]["n"] for c in cats]
fig, ax = plt.subplots(figsize=(4.8, 3.6))
labels = [c.replace("_", "\n") for c in cats]
ax.bar(labels, [ch / n for ch, n in zip(changes, ns)], color="#1f77b4")
for i, (ch, n) in enumerate(zip(changes, ns)):
    ax.text(i, ch / n + 0.01, f"{ch}/{n}", ha="center", fontsize=7)
ax.set_ylabel("Fraction of steps with a CP-attributable decision change")
ax.set_title("Decision Changes by Scenario Category (full stack)")
plt.setp(ax.get_xticklabels(), fontsize=6.5)
save(fig, "cp_fig_decision_changes_by_category")

# 3. False positives vs true positives (net CP effect)
fig, ax = plt.subplots(figsize=(3.6, 3.2))
labels2 = ["Attacker msgs\nnewly caught\n(CAUTION→REJECT)", "Benign msgs\nspuriously escalated\n(ACCEPT→CAUTION)"]
vals = [11, 22]
colors = ["#2ca02c", "#d62728"]
ax.bar(labels2, vals, color=colors)
for i, v in enumerate(vals):
    ax.text(i, v + 0.3, str(v), ha="center", fontsize=9)
ax.set_ylabel("Number of messages")
ax.set_title("Net Effect of Enabling CP\n(142 messages, 24 scenes)")
save(fig, "cp_fig_net_effect")

# 4. Cold-start mechanism: diversity score vs window position (one example scene)
example_scene = raw["scenes"][0]
on_rows = example_scene["cp_on_b3_on"]
xs = list(range(len(on_rows)))
divs = [r["cp_diversity"] for r in on_rows]
decs = [r["decision"] for r in on_rows]
fig, ax = plt.subplots(figsize=(4.0, 3.2))
ax.plot(xs, divs, marker="o", color="#9467bd")
ax.set_xlabel("Message index within window (accumulating)")
ax.set_ylabel("CP diversity score")
ax.set_title("Cold-Start Mechanism: Diversity Climbs\nas the Window Accumulates Reports")
for x, d, dec in zip(xs, divs, decs):
    ax.annotate(dec, (x, d), textcoords="offset points", xytext=(0, 6), fontsize=6, ha="center")
save(fig, "cp_fig_cold_start_mechanism")

print(f"Wrote 4 figures to {OUT}")
