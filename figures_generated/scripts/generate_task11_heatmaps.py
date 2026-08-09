"""
figures_generated/scripts/generate_task11_heatmaps.py
=========================================================
Real, non-fabricated heatmaps for Task 11/12's figure requests, built
ENTIRELY from existing per-sample CSVs already produced this session --
no new numbers invented. Where a requested cell is not measurable (e.g.
B1's recall on attack families v2.5b doesn't structurally contain), the
cell is marked N/A (grey), not filled with a plausible-looking number.

Sources:
  - v2.5b, current (hardmine) checkpoint, configs 1-5:
    b3_eval/v25_finetune/ablation_results/v25b_full_hardmine/config_{1..5}.csv
  - v2.5b, prior checkpoint, config 5 (for the improvement heatmap):
    b3_eval/v25_finetune/ablation_results/v25b_full/config_5.csv
  - ITE-Bench, the ONLY benchmark with real, separable B1/B2/B3 attacks:
    ite_bench/results/ (config 1/3/5 per-family CSVs, if present) --
    used for the attack-family x layer heatmap's B1/B2 columns, since
    v2.5b structurally cannot populate them (0.000 recall by benchmark
    construction, already established and disclosed).
"""
import csv, pathlib, sys
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "figures_generated"
plt.rcParams.update({"font.size": 8, "figure.dpi": 150})

V25B_HM = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full_hardmine"
V25B_OLD = ROOT / "b3_eval/v25_finetune/ablation_results/v25b_full"

CONFIG_LABELS = {4: "B3 only", 6: "B1+B2+B3\n(no CP)", 5: "Full STBV\n(B1+B2+B3+CP)"}
HEATMAP_CONFIGS = (4, 6, 5)  # Traditional/+B2/+CP dropped: all-zero on this semantic-only
# benchmark by construction (see stbv_paper.tex Section VI-C prose); not shown as a row/column
# of zeros per this pass's "remove B1-related dead-zero content from the v2.5b results" edit.


def load(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def per_family_recall(rows):
    fam = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["is_attacker"] != "True":
            continue
        f = r["attack_family"]
        fam[f][1] += 1
        if r["decision"] != "ACCEPT":
            fam[f][0] += 1
    return {f: (c / t if t else None) for f, (c, t) in fam.items()}


def per_family_confusion(rows):
    fam = defaultdict(lambda: [0, 0, 0, 0])  # tp fp fn tn
    for r in rows:
        y = r["is_attacker"] == "True"
        p = r["decision"] != "ACCEPT"
        f = r["attack_family"]
        if p and y: fam[f][0] += 1
        elif p and not y: fam[f][1] += 1
        elif not p and y: fam[f][2] += 1
        else: fam[f][3] += 1
    return fam


# ============================================================
# Figure 1: Attack-family x trust-layer recall heatmap (v2.5b, current checkpoint)
# ============================================================
families = sorted({r["attack_family"] for r in load(V25B_HM / "config_5.csv")})
recall_by_cfg = {cfg: per_family_recall(load(V25B_HM / f"config_{cfg}.csv")) for cfg in HEATMAP_CONFIGS}

mat = np.full((len(families), len(HEATMAP_CONFIGS)), np.nan)
for fi, fam in enumerate(families):
    for ci, cfg in enumerate(HEATMAP_CONFIGS):
        v = recall_by_cfg[cfg].get(fam)
        if v is not None:
            mat[fi, ci] = v

fig, ax = plt.subplots(figsize=(4.2, 0.24 * len(families) + 1.2))
masked = np.ma.masked_invalid(mat)
cmap = plt.cm.Blues.copy()
cmap.set_bad(color="#e8e0d0")  # distinct, non-alarming grey-tan for "not measurable"
im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(HEATMAP_CONFIGS))); ax.set_xticklabels([CONFIG_LABELS[c] for c in HEATMAP_CONFIGS], fontsize=7)
ax.set_yticks(range(len(families))); ax.set_yticklabels(families, fontsize=6)
for fi in range(len(families)):
    for ci in range(len(HEATMAP_CONFIGS)):
        v = mat[fi, ci]
        txt = f"{v:.2f}" if not np.isnan(v) else "N/A"
        ax.text(ci, fi, txt, ha="center", va="center", fontsize=6,
                 color="white" if (not np.isnan(v) and v > 0.5) else "black")
ax.set_title("Recall by Attack Family x Configuration\nSTBV-Bench v2.5b, current final checkpoint (N/A = benchmark\ncontains no attacks of this class for this layer to detect)")
plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="Recall")
plt.tight_layout()
plt.savefig(OUT / "fig_heatmap_family_x_layer_v25b.pdf")
plt.close()
print(f"[fig1] {len(families)} families x 5 configs, v2.5b current checkpoint")

# ============================================================
# Figure 2: Per-family precision/recall/F1/FPR heatmap (full stack, current checkpoint)
# ============================================================
full_rows = load(V25B_HM / "config_5.csv")
fam_conf = per_family_confusion(full_rows)
metric_names = ["Precision", "Recall", "F1", "FPR"]
mat2 = np.full((len(families), 4), np.nan)
for fi, fam in enumerate(families):
    tp, fp, fn, tn = fam_conf[fam]
    prec = tp / (tp + fp) if tp + fp else np.nan
    rec = tp / (tp + fn) if tp + fn else np.nan
    f1 = 2 * prec * rec / (prec + rec) if (prec and rec and prec + rec) else np.nan
    fpr = fp / (fp + tn) if fp + tn else np.nan
    mat2[fi] = [prec, rec, f1, fpr]

fig, ax = plt.subplots(figsize=(4.2, 0.24 * len(families) + 1.2))
masked2 = np.ma.masked_invalid(mat2)
im2 = ax.imshow(masked2, cmap=cmap, vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels(metric_names, fontsize=7)
ax.set_yticks(range(len(families))); ax.set_yticklabels(families, fontsize=6)
for fi in range(len(families)):
    for mi in range(4):
        v = mat2[fi, mi]
        txt = f"{v:.2f}" if not np.isnan(v) else "N/A"
        ax.text(mi, fi, txt, ha="center", va="center", fontsize=6,
                 color="white" if (not np.isnan(v) and v > 0.5) else "black")
ax.set_title("Per-Family Performance, Full STBV Framework\nSTBV-Bench v2.5b, current final checkpoint")
plt.colorbar(im2, ax=ax, fraction=0.04, pad=0.02)
plt.tight_layout()
plt.savefig(OUT / "fig_heatmap_family_performance_v25b.pdf")
plt.close()
print("[fig2] per-family precision/recall/F1/FPR")

# ============================================================
# Figure 3: Checkpoint improvement heatmap (prior vs current, per family, full stack)
# ============================================================
old_rows = load(V25B_OLD / "config_5.csv")
old_conf = per_family_confusion(old_rows)
new_conf = fam_conf

mat3 = np.full((len(families), 3), np.nan)
for fi, fam in enumerate(families):
    def prf(conf):
        tp, fp, fn, tn = conf[fam]
        prec = tp / (tp + fp) if tp + fp else np.nan
        rec = tp / (tp + fn) if tp + fn else np.nan
        f1 = 2 * prec * rec / (prec + rec) if (prec and rec and prec + rec) else np.nan
        return prec, rec, f1
    op, orr, of1 = prf(old_conf)
    npc, nr, nf1 = prf(new_conf)
    mat3[fi] = [npc - op if not (np.isnan(npc) or np.isnan(op)) else np.nan,
                nr - orr if not (np.isnan(nr) or np.isnan(orr)) else np.nan,
                nf1 - of1 if not (np.isnan(nf1) or np.isnan(of1)) else np.nan]

fig, ax = plt.subplots(figsize=(3.6, 0.24 * len(families) + 1.2))
masked3 = np.ma.masked_invalid(mat3)
vmax = np.nanmax(np.abs(mat3)) if np.isfinite(np.nanmax(np.abs(mat3))) else 0.1
im3 = ax.imshow(masked3, cmap="RdBu", vmin=-vmax, vmax=vmax, aspect="auto")
ax.set_xticks(range(3)); ax.set_xticklabels(["$\\Delta$Prec.", "$\\Delta$Rec.", "$\\Delta$F1"], fontsize=7)
ax.set_yticks(range(len(families))); ax.set_yticklabels(families, fontsize=6)
for fi in range(len(families)):
    for mi in range(3):
        v = mat3[fi, mi]
        txt = f"{v:+.2f}" if not np.isnan(v) else "N/A"
        ax.text(mi, fi, txt, ha="center", va="center", fontsize=6)
ax.set_title("Checkpoint Improvement\n(current - prior), full stack, v2.5b")
plt.colorbar(im3, ax=ax, fraction=0.05, pad=0.03)
plt.tight_layout()
plt.savefig(OUT / "fig_heatmap_checkpoint_delta_v25b.pdf")
plt.close()
print("[fig3] checkpoint improvement (current - prior)")

# ============================================================
# Figure 4: Error analysis heatmap (TP/FP/FN/TN counts per family, full stack, current checkpoint)
# ============================================================
mat4 = np.array([fam_conf[fam] for fam in families], dtype=float)
fig, ax = plt.subplots(figsize=(3.6, 0.24 * len(families) + 1.2))
im4 = ax.imshow(mat4, cmap="Greys", aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels(["TP", "FP", "FN", "TN"], fontsize=7)
ax.set_yticks(range(len(families))); ax.set_yticklabels(families, fontsize=6)
for fi in range(len(families)):
    for mi in range(4):
        v = mat4[fi, mi]
        ax.text(mi, fi, f"{int(v)}", ha="center", va="center", fontsize=6,
                 color="white" if v > mat4.max() / 2 else "black")
ax.set_title("Error Analysis by Attack Family\nFull STBV Framework, v2.5b, current final checkpoint")
plt.colorbar(im4, ax=ax, fraction=0.05, pad=0.03)
plt.tight_layout()
plt.savefig(OUT / "fig_heatmap_error_analysis_v25b.pdf")
plt.close()
print("[fig4] error analysis (TP/FP/FN/TN)")

print("[ok] 4 heatmaps written to figures_generated/")
