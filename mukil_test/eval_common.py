#!/usr/bin/env python3
# =====================================================================
# eval_common.py  --  shared house style, metrics, bootstrap, IO
# Used by: run_lolo.py, analyze_fusion_divergence.py,
#          evaluate_decision_trust.py, plot_trust_evolution.py
#
# House palette matches the paper's figures (teal / brick / slate).
# All figures export vector PDF + PNG preview.
# =====================================================================
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- shared palette (identical to the TikZ / fig5 assets) ----
ACC     = "#1F6F8B"   # proposed / accent (teal)
ACC_DK  = "#124456"
NEUTRAL = "#9AA6B2"   # existing / zero (gray)
BENIGN  = "#5E8B7E"   # benign class (muted green)
THREAT  = "#B4472F"   # attack / brick
AMBER   = "#C08A2E"   # caution band
INK     = "#14213D"


def set_style():
    """One shared look for every figure (IEEE-friendly, serif, no chartjunk)."""
    plt.rcParams.update({
        "font.family": "serif",          # swap to Times for camera-ready
        "font.size": 8.5,
        "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK,
        "axes.linewidth": 0.7,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 150,
    })


def demo_watermark(fig):
    """Stamp 'DEMO DATA' across a figure so scaffold is never mistaken for results."""
    fig.text(0.5, 0.5, "DEMO DATA", rotation=28, ha="center", va="center",
             fontsize=58, color=THREAT, alpha=0.08, zorder=100, fontweight="bold")


# ---------------------------------------------------------------- metrics
def binary_metrics(y_true, y_pred):
    """y_true, y_pred: arrays of {0,1}. Positive (1) = malicious/detected."""
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec  = tp / (tp + fn) if (tp + fn) else float("nan")
    f1   = (2 * prec * rec / (prec + rec)
            if (prec == prec and rec == rec and (prec + rec) > 0) else float("nan"))
    fpr  = fp / (fp + tn) if (fp + tn) else float("nan")
    fnr  = fn / (fn + tp) if (fn + tp) else float("nan")
    acc  = (tp + tn) / len(y_true) if len(y_true) else float("nan")
    return dict(acc=acc, prec=prec, rec=rec, f1=f1, fpr=fpr, fnr=fnr,
                tp=tp, fp=fp, tn=tn, fn=fn)


def bootstrap_ci(y_true, y_pred, key="f1", n=10000, seed=0, alpha=0.05):
    """Percentile bootstrap CI for one metric key from binary_metrics."""
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    rng = np.random.default_rng(seed)
    m = len(y_true)
    if m == 0:
        return (float("nan"), float("nan"))
    vals = []
    for _ in range(n):
        idx = rng.integers(0, m, m)
        v = binary_metrics(y_true[idx], y_pred[idx])[key]
        if v == v:  # skip nan
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    lo = float(np.percentile(vals, 100 * alpha / 2))
    hi = float(np.percentile(vals, 100 * (1 - alpha / 2)))
    return (lo, hi)


# ---------------------------------------------------------------- IO
def load_json_or_demo(path, demo_fn, name):
    """Load results/<file>.json if it exists; otherwise build demo data loudly."""
    if path and os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        print(f"[{name}] loaded real data from {path}")
        return data, False
    print("=" * 68)
    print(f"[{name}] NO INPUT FILE FOUND -> generating DEMO data (NOT REAL).")
    print(f"[{name}] Replace with your results file via --input to get real numbers.")
    print("=" * 68)
    return demo_fn(), True


def save_json(obj, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"  wrote {path}")


def save_latex_table(header, rows, caption, label, path, align=None):
    """Emit a booktabs LaTeX table. rows: list of lists (already stringified)."""
    ncol = len(header)
    align = align or ("l" + "c" * (ncol - 1))
    lines = [r"\begin{table}[t]", r"\centering",
             r"\caption{" + caption + "}", r"\label{" + label + "}",
             r"\begin{tabular}{" + align + "}", r"\toprule",
             " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(str(c) for c in row) + r" \\" for row in rows]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  wrote {path}")


def savefig(fig, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    fig.savefig(path.replace(".pdf", ".png"), bbox_inches="tight", dpi=220)
    print(f"  wrote {path} (+ .png preview)")


# ---------------------------------------------------------------- curves
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))


def roc_curve(y_true, score):
    """Return (fpr, tpr) with a leading (0,0). score = P(positive)."""
    y = np.asarray(y_true).astype(int)
    s = np.asarray(score, float)
    order = np.argsort(-s)
    y = y[order]
    P = int(y.sum()); N = len(y) - P
    tps = np.cumsum(y); fps = np.cumsum(1 - y)
    tpr = tps / (P if P else 1)
    fpr = fps / (N if N else 1)
    return np.concatenate([[0], fpr]), np.concatenate([[0], tpr])


def auc_trapz(x, y):
    return float(_trapz(y, x))


def pr_curve(y_true, score):
    """Return (recall, precision)."""
    y = np.asarray(y_true).astype(int)
    s = np.asarray(score, float)
    order = np.argsort(-s)
    y = y[order]
    P = int(y.sum())
    tps = np.cumsum(y); fps = np.cumsum(1 - y)
    recall = tps / (P if P else 1)
    precision = tps / np.maximum(tps + fps, 1)
    return recall, precision


def average_precision(y_true, score):
    recall, precision = pr_curve(y_true, score)
    ap, r_prev = 0.0, 0.0
    for r, p in zip(recall, precision):
        ap += (r - r_prev) * p
        r_prev = r
    return float(ap)


def bootstrap_scalar(y_true, score, fn, n=2000, seed=0, alpha=0.05):
    """Percentile CI for a scalar metric fn(y_true, score)."""
    y = np.asarray(y_true).astype(int); s = np.asarray(score, float)
    rng = np.random.default_rng(seed); m = len(y); vals = []
    for _ in range(n):
        idx = rng.integers(0, m, m)
        if len(np.unique(y[idx])) < 2:
            continue
        vals.append(fn(y[idx], s[idx]))
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 100 * alpha / 2)),
            float(np.percentile(vals, 100 * (1 - alpha / 2))))


# ---------------------------------------------------------------- calibration
def ece_mce_brier(y_true, prob, bins=10):
    y = np.asarray(y_true, float); p = np.asarray(prob, float)
    edges = np.linspace(0, 1, bins + 1)
    ece = mce = 0.0; N = len(y); per_bin = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        m = (p >= lo) & (p < hi) if i < bins - 1 else (p >= lo) & (p <= hi)
        if m.sum() == 0:
            per_bin.append({"conf": None, "acc": None, "n": 0}); continue
        conf = float(p[m].mean()); acc = float(y[m].mean()); w = m.sum() / N
        ece += w * abs(acc - conf); mce = max(mce, abs(acc - conf))
        per_bin.append({"conf": conf, "acc": acc, "n": int(m.sum())})
    brier = float(np.mean((p - y) ** 2))
    return {"ece": float(ece), "mce": float(mce), "brier": brier,
            "bins": per_bin, "edges": edges.tolist()}


def fit_temperature(y_true, prob, grid=None):
    """1-D temperature search minimizing NLL on probabilities."""
    y = np.asarray(y_true, float)
    p = np.clip(np.asarray(prob, float), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p))
    grid = np.linspace(0.5, 5.0, 181) if grid is None else grid
    best_T, best_nll = 1.0, 1e18
    for T in grid:
        q = np.clip(1 / (1 + np.exp(-logit / T)), 1e-6, 1 - 1e-6)
        nll = -np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))
        if nll < best_nll:
            best_T, best_nll = float(T), float(nll)
    return best_T


def apply_temperature(prob, T):
    p = np.clip(np.asarray(prob, float), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p))
    return 1 / (1 + np.exp(-logit / T))


def demo_scores(n=300, seed=0, auc_target="high"):
    """Demo y_true + P(malicious) with realistic overlap. NOT REAL DATA."""
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.6).astype(int)
    # malicious scores skew high, benign low, with overlap
    s = np.where(y == 1, rng.beta(6, 2.2, n), rng.beta(2.2, 6, n))
    s = np.clip(s + rng.normal(0, 0.05, n), 0, 1)
    return y, s
