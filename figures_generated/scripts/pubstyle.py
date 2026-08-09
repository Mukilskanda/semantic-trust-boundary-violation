"""
figures_generated/scripts/pubstyle.py
========================================
Shared publication style module for every regenerated figure in this pass.
Colorblind-safe (Okabe-Ito derived), consistent typography, vector-first.
Import and call `apply()` once at the top of each figure script.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Okabe-Ito colorblind-safe palette
BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
RED = "#D55E00"
PURPLE = "#CC79A7"
GREY = "#666666"
LIGHT_GREY = "#BBBBBB"
YELLOW = "#F0E442"

SEQ_BLUE = "Blues"  # sequential palette for heatmaps/confusion matrices

BENIGN_C = GREY
MALICIOUS_C = BLUE
ACCEPT_C = GREEN
CAUTION_C = ORANGE
REJECT_C = RED

# Semantic role mapping (Task 9): every figure in this pass follows this,
# not ad hoc per-figure color choices.
ARCH_C = BLUE          # architecture / pipeline stages
SUCCESS_C = GREEN      # successful detections
CAUTION_ROLE_C = ORANGE  # caution / moderate performance
FAIL_C = RED           # failures / bottlenecks / threshold lines
SEMANTIC_C = PURPLE    # semantic validation (B3, v2.5b)
HIST_C = GREY          # historical / supplementary results


def apply():
    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 600,
        "font.family": "serif",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.linewidth": 1.0,
        "xtick.major.width": 1.0,
        "ytick.major.width": 1.0,
        "lines.linewidth": 2.0,
        "lines.markersize": 5,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "savefig.bbox": "tight",
        "svg.fonttype": "none",
    })


def save(fig, out_base):
    """Save PDF (vector, used by LaTeX), SVG (vector), and PNG @600dpi."""
    fig.savefig(str(out_base) + ".pdf")
    fig.savefig(str(out_base) + ".svg")
    fig.savefig(str(out_base) + ".png", dpi=600)
