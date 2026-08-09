import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pubstyle as ps
import matplotlib.pyplot as plt
import numpy as np

ps.apply()
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"

rows = list(csv.DictReader(open(V25B_HM / "config_5.csv", encoding="utf-8")))
tp = fp = fn = tn = 0
for r in rows:
    y = r["is_attacker"] == "True"
    p = r["decision"] != "ACCEPT"
    if p and y: tp += 1
    elif p and not y: fp += 1
    elif not p and y: fn += 1
    else: tn += 1
total_errors = fp + fn

fig, axes = plt.subplots(1, 2, figsize=(6.0, 2.8))

# Left: error composition (FP vs FN), real counts
axes[0].bar(["False Positives\n(benign flagged)", "False Negatives\n(attack missed)"], [fp, fn],
             color=[ps.FAIL_C, ps.CAUTION_ROLE_C], edgecolor="black", linewidth=0.6, width=0.55)
for i, v in enumerate([fp, fn]):
    axes[0].text(i, v + total_errors * 0.02, f"{v:,}\n({100*v/total_errors:.1f}% of errors)",
                  ha="center", fontsize=7.5)
axes[0].set_ylabel("Count")
axes[0].set_title(f"(A) Error Composition\n($n_{{errors}}={total_errors:,}$ of $10{{,}}098$)", fontsize=8.5)

# Right: full confusion breakdown as stacked bar, correct vs incorrect
axes[1].bar(["Benign\n(n=4,734)"], [tn], color=ps.SUCCESS_C, label="Correct (TN)")
axes[1].bar(["Benign\n(n=4,734)"], [fp], bottom=[tn], color=ps.FAIL_C, label="Incorrect (FP)")
axes[1].bar(["Malicious\n(n=5,364)"], [tp], color=ps.SUCCESS_C)
axes[1].bar(["Malicious\n(n=5,364)"], [fn], bottom=[tp], color=ps.CAUTION_ROLE_C, label="Incorrect (FN)")
axes[1].set_ylabel("Count")
axes[1].legend(loc="upper center", fontsize=6.5, ncol=1)
axes[1].set_title("(B) Correct vs.\\ Incorrect\nby Ground Truth", fontsize=8.5)

fig.suptitle("Error Analysis, Full STBV Framework, STBV-Bench v2.5b", fontsize=9.5, y=1.02)
plt.tight_layout()
ps.save(fig, OUT / "fig_error_analysis")
plt.close()
print(f"[error_analysis] tp={tp} fp={fp} fn={fn} tn={tn} total_errors={total_errors}")
