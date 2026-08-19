"""Deck palette and matplotlib defaults for lecture 12 figures.

Colours are lifted from lecture_01-chemical-representations_v2.pptx so that
generated figures sit alongside the Nature panels without clashing.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

INK    = "#123830"   # primary text and lines (dark green)
RED    = "#C00000"   # emphasis
BLUE   = "#2E6FBA"   # secondary
TEAL   = "#1B8A98"   # tertiary
GOLD   = "#E0A526"   # accent
PLUM   = "#7B5EA7"
GRAY   = "#777777"   # captions, muted
RULE   = "#C3BBAB"
TINT   = "#EAF6F1"   # pale block fill
TINT2  = "#DCE9E4"
PAPER  = "#FFFFFF"

CYCLE = [INK, RED, BLUE, GOLD, TEAL, PLUM]

# Slide geometry: the widest figure box in the deck is about 10.8 x 3.9 inches.
# Keep text >= 9 pt at final scale.
FIG_W_FULL = 10.8
FIG_W_HALF = 5.2
FIG_W_THIRD = 3.7

# Set False before building a figure to get clean panels (no titles, captions,
# annotations, legends, or axis/colorbar labels) so the PDF ungroups into pptx
# shapes without baked-in text -- the wording then lives only in the code
# comments, ready to be retyped as an editable pptx text box. Numeric tick
# labels are left alone since they're part of reading the axes, not commentary.
SHOW_TEXT = True

# Set False to skip the inline preview in save() (e.g. for a headless batch
# build via build_and_run.py, where there's no notebook cell to render into).
PREVIEW = True


def title(ax, s, **kw):
    if SHOW_TEXT:
        ax.set_title(s, **kw)


def xlabel(ax, s, **kw):
    if SHOW_TEXT:
        ax.set_xlabel(s, **kw)


def ylabel(ax, s, **kw):
    if SHOW_TEXT:
        ax.set_ylabel(s, **kw)


def text(ax, *a, **kw):
    if SHOW_TEXT:
        ax.text(*a, **kw)


def annotate(ax, *a, **kw):
    if SHOW_TEXT:
        ax.annotate(*a, **kw)


def legend(ax, *a, **kw):
    if SHOW_TEXT:
        ax.legend(*a, **kw)


def cbar_label(cb, s):
    if SHOW_TEXT:
        cb.set_label(s)


def use_deck_style():
    mpl.rcParams.update({
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "font.family": "sans-serif",
        "font.sans-serif": ["Calibri", "Carlito", "DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": mpl.cycler(color=CYCLE),
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 1.6,
        "text.color": INK,
        "figure.dpi": 110,
    })


def preview(fig):
    """Render fig into the notebook cell's output, same pixels as the PNG
    save() writes below it. Renders via savefig-to-buffer, so it works even
    though HEADER forces the non-interactive Agg backend (plt.show() would
    just no-op there). Silently does nothing outside a notebook kernel, so
    it's harmless from build_and_run.py's headless exec."""
    if not PREVIEW:
        return
    try:
        from IPython import get_ipython
        if get_ipython() is None:
            return                       # headless exec (build_and_run.py)
        import io
        from IPython.display import display, Image
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        display(Image(data=buf.getvalue()))
    except ImportError:
        pass


def save(fig, name, outdir="../../lecture_12_figures/generated"):
    """Preview fig inline, then write both a vector PDF (archival) and a
    300-dpi PNG (for the deck)."""
    import os
    preview(fig)
    os.makedirs(outdir, exist_ok=True)
    pdf = os.path.join(outdir, name + ".pdf")
    png = os.path.join(outdir, name + ".png")
    fig.savefig(pdf)
    fig.savefig(png, dpi=300)
    print("wrote", pdf)
    print("wrote", png)
    return pdf, png
