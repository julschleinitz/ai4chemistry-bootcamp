# %% [markdown]
# # Figure 0 - title figure: one landscape, two campaigns
#
# Slide 1.  Decoration that happens to be the thesis of the lecture: the same
# 20-experiment budget spent by Bayesian optimization (clustered on the ridge)
# and by active learning (spread across the domain).  No axis labels, no legend.
#
# Landscape: `_shared/landscape.py`, shared with Lecture 12.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style, landscape as L, campaign
style.use(); style.versions()

# %%
bo = campaign.run("bo", seed=2)
al = campaign.run("al", seed=2)
for n, r in (("BO", bo), ("AL", al)):
    print("%s  RMSE away from optimum %.1f  best yield found %.1f%%"
          % (n, r["rmse_away"], r["best_found"]))

# %%
TT, LL, F = L.grid(200)
fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.9))
for ax, run, col in zip(axes, (bo, al), (style.EMPH, style.SEC)):
    ax.contourf(TT, LL, F, levels=22, cmap="BuGn", alpha=0.95)
    ax.contour(TT, LL, F, levels=8, colors="white", linewidths=0.5, alpha=0.6)
    ax.scatter(run["X"][:, 0], run["X"][:, 1], s=52, c=col,
               edgecolors="white", linewidths=1.2, zorder=5)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color(style.MUTED); sp.set_linewidth(0.8)
fig.subplots_adjust(wspace=0.06)
style.save(fig, "fig_00_title_al_vs_bo")
