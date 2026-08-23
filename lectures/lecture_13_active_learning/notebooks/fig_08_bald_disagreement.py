# %% [markdown]
# # Figure 8 - confident, and confidently disagreeing
#
# Slide 22.  Three regimes of the posterior over a binary prediction, with the
# entropy and the mutual information COMPUTED, not asserted.
#
# * **(a)** every posterior draw agrees and is confident -> low H, low BALD.
# * **(b)** every draw sits at 0.5 -> **high H, ~zero BALD**.  This is the noisy
#   assay.  It is the panel that teaches.
# * **(c)** every draw is sharp and they disagree -> high H, **high BALD**.
#
# Slow down on the middle panel: entropy sampling puts it at the top of its list.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
style.use(); style.versions()

# %%
def H(p):
    """Binary entropy in bits, elementwise."""
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))


def bald(draws):
    """I[y; w] = H[mean p] - mean H[p], in bits."""
    draws = np.asarray(draws, dtype=float)
    return float(H(draws.mean()) - H(draws).mean())


rng = np.random.default_rng(5)
cases = [
    ("(a)  draws agree, and are confident",
     np.clip(rng.normal(0.94, 0.015, 12), 0.01, 0.99),
     "nothing to learn"),
    ("(b)  draws all sit at the coin flip",
     np.clip(rng.normal(0.50, 0.020, 12), 0.01, 0.99),
     "HIGH entropy, ~ZERO BALD\nthis is the noisy assay"),
    ("(c)  draws are sharp, and disagree",
     np.concatenate([rng.normal(0.03, 0.015, 6), rng.normal(0.97, 0.015, 6)]).clip(0.01, 0.99),
     "HIGH entropy, HIGH BALD\nrun this one"),
]
for name, d, _ in cases:
    print("%-40s  H = %.2f bits   BALD = %.2f bits" % (name, H(d.mean()), bald(d)))

# %%
fig, axes = plt.subplots(1, 3, figsize=(11.0, 4.0), sharey=True)
for ax, (title, draws, note) in zip(axes, cases):
    mi, h = bald(draws), float(H(draws.mean()))
    hot = mi > 0.4
    col = style.EPISTEMIC if hot else style.ALEATORIC
    for i, p in enumerate(draws):
        ax.plot([i - 0.34, i + 0.34], [p, p], color=col, lw=2.4, alpha=0.85,
                solid_capstyle="round")
    ax.axhline(draws.mean(), color=style.INK, lw=1.5, ls="--")
    ax.text(len(draws) - 0.4, draws.mean(), "  mean", va="center", fontsize=9,
            color=style.INK)
    ax.set_title(title, fontsize=10.5, pad=8, color=style.INK)
    ax.set_xlim(-0.9, len(draws) + 1.6); ax.set_ylim(-0.06, 1.06)
    ax.set_xticks([]); ax.spines["bottom"].set_visible(False)
    ax.text(0.5, -0.055,
            "H = %.2f bits        BALD = %.2f bits" % (h, mi),
            transform=ax.transAxes, ha="center", va="top", fontsize=11.5,
            fontweight="bold", color=col)
    ax.text(0.5, -0.175, note, transform=ax.transAxes, ha="center", va="top",
            fontsize=10, color=col, style="italic", linespacing=1.35)

axes[0].set_ylabel("posterior draw of  $p(y=1\\,|\\,x,\\omega)$")
axes[0].set_yticks([0, 0.5, 1])
fig.text(0.5, 1.045,
         "each short bar is one posterior sample $\\omega$ of the model, at a single candidate $x$",
         ha="center", fontsize=9, color=style.MUTED, style="italic")
style.save(fig, "fig_08_bald_disagreement")
