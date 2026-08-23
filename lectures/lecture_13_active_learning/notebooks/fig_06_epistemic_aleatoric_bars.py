# %% [markdown]
# # Figure 6 - THE KEY FIGURE
#
# Slide 17.  Two stacked bars of identical total height.  Compound A is almost all
# epistemic (blue, reducible).  Compound B is almost all aleatoric (red,
# irreducible).  Entropy sampling sees only the total, so it cannot tell them
# apart -- and it will keep buying compound B forever.
#
# Must be readable in two seconds from the back of the room.  Resist adding
# anything to it.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
style.use(); style.versions()

# %%
TOTAL = 1.00
BARS = [(0.00, "Compound A\nunseen scaffold", 0.88),
        (1.35, "Compound B\nfilthy assay", 0.12)]
W = 0.92

fig, ax = plt.subplots(figsize=(9.6, 3.2))

for x, lab, epi in BARS:
    ale = TOTAL - epi
    ax.bar(x, epi, width=W, color=style.EPISTEMIC, edgecolor="white", lw=1.8, zorder=3)
    ax.bar(x, ale, width=W, bottom=epi, color=style.ALEATORIC, edgecolor="white",
           lw=1.8, zorder=3)
    ax.text(x, -0.04, lab, ha="center", va="top", fontsize=14, fontweight="bold",
            color=style.INK, linespacing=1.4)
    for frac, base, name in ((epi, 0.0, "epistemic"), (ale, epi, "aleatoric")):
        big = frac > 0.25
        ax.text(x, base + frac / 2,
                ("%s\n%.0f%%" % (name, 100 * frac)) if big else name,
                ha="center", va="center", color="white",
                fontsize=15 if big else 10.5, fontweight="bold", linespacing=1.3)

# the identical totals -- the whole point of the figure
ax.plot([-0.62, 1.98], [TOTAL, TOTAL], color=style.INK, lw=1.4, ls=":", zorder=4)
ax.annotate("identical\ntotal entropy", xy=(1.98, TOTAL), xytext=(2.16, TOTAL),
            va="center", ha="left", fontsize=13, fontweight="bold", color=style.INK,
            linespacing=1.35)

ax.text(-0.62, 1.205, "Entropy sampling sees only the total height.",
        fontsize=15.5, fontweight="bold", color=style.INK)
ax.text(-0.62, 1.100, "BALD sees only the blue.",
        fontsize=15.5, fontweight="bold", color=style.EPISTEMIC)

ax.set_ylim(0, 1.30); ax.set_xlim(-0.70, 2.98)
ax.set_ylabel("predictive uncertainty  H[$y\\,|\\,x$]", fontsize=11)
ax.set_yticks([0, TOTAL]); ax.set_yticklabels(["0", "H"], fontsize=12)
ax.set_xticks([]); ax.spines["bottom"].set_visible(False)
style.save(fig, "fig_06_epistemic_aleatoric_bars")
