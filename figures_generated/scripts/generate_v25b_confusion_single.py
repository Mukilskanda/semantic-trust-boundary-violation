"""
figures_generated/scripts/generate_v25b_confusion_single.py
===============================================================
Single confusion matrix (Full STBV Framework only), STBV-Bench v2.5b,
current final checkpoint. Replaces the 6-panel grid per the publication
pass's "too many confusion matrices, keep only the most useful one"
instruction -- the other 5 configurations' exact Acc/Prec/Rec/F1/FPR
remain fully available in Table V; the 3 "Traditional/+B2/+CP" panels
were visually identical (all-zero-recall) and added nothing a single
sentence doesn't already say, and B3-only/B1+B2+B3(no CP) differ from
the full stack only in FP count by <70 out of ~10,000, indistinguishable
by eye at grid scale.
"""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

rows = list(csv.DictReader(open(V25B_HM / "config_5.csv", encoding="utf-8")))
tp = fp = fn = tn = 0
for r in rows:
    y = r["is_attacker"] == "True"
    p = r["decision"] != "ACCEPT"
    if p and y: tp += 1
    elif p and not y: fp += 1
    elif not p and y: fn += 1
    else: tn += 1
mat = np.array([[tn, fp], [fn, tp]])

fig, ax = plt.subplots(figsize=(3.0, 2.9))
im = ax.imshow(mat, cmap="Greys", vmin=0)
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{mat[i, j]:,}", ha="center", va="center", fontsize=11,
                 color="white" if mat[i, j] > mat.max() / 2 else "black")
ax.set_xticks([0, 1]); ax.set_xticklabels(["Accept", "Caution/Reject"], fontsize=8)
ax.set_yticks([0, 1]); ax.set_yticklabels(["Benign", "Malicious"], fontsize=8)
ax.set_title("Full STBV Framework, STBV-Bench v2.5b\ncurrent final checkpoint ($n{=}10{,}098$)", fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "fig_v25b_confusion_single.pdf")
plt.close()
print(f"[ok] tp={tp} fp={fp} fn={fn} tn={tn}")
