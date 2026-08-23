"""Deck palette + matplotlib rcParams for Lecture 13.

Palette lifted from lecture_01-chemical-representations_v2.pptx so figures do not
look pasted in from elsewhere.  Shared with Lecture 12 -- do not fork.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

INK       = "#123830"   # primary text / lines
EMPH      = "#C00000"   # emphasis
SEC       = "#2E6FBA"   # secondary  -> EPISTEMIC (reducible; buy this)
TER       = "#1B8A98"   # tertiary
ACCENT    = "#E0A526"
MUTED     = "#777777"   # captions
TINT      = "#EAF6F1"   # block tint

# semantic colours for this lecture -- used consistently from section 4 onwards
EPISTEMIC = SEC
ALEATORIC = EMPH

# acquisition-function colours, matching Schleinitz et al. JACS 2025 Fig. 3
AF_AL   = "#4BA3DC"   # active learning        (blue)
AF_SC   = "#3E9B4F"   # scaffold similarity   (green)
AF_CH   = "#C77FBF"   # C-H site similarity   (pink)
AF_RAND = "#6E6E6E"   # random baseline       (grey)

CYCLE = [INK, EMPH, SEC, TER, ACCENT, MUTED]


def use():
    """Apply the deck style.  Call once at the top of every notebook."""
    mpl.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "font.family": "sans-serif",
        "font.sans-serif": ["Calibri", "Carlito", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": mpl.cycler(color=CYCLE),
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "text.color": INK,
        "figure.facecolor": "white",
    })


def save(fig, name, outdir="../figures"):
    """Write <name>.pdf (vector) and <name>.png (300 dpi) side by side."""
    import os
    os.makedirs(outdir, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(outdir, f"{name}.{ext}"))
    print(f"wrote {outdir}/{name}.pdf and .png")


def versions():
    import sys, numpy
    print("python     ", sys.version.split()[0])
    print("numpy      ", numpy.__version__)
    print("matplotlib ", mpl.__version__)
