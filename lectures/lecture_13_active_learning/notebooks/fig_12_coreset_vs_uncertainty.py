# %% [markdown]
# # Figure 12 - geometry instead of uncertainty
#
# Slide 27.  Two panels on the *same* pool: the uncertainty-selected batch clumps;
# the k-centre-greedy batch tiles the space.  The delta-cover circles on the right
# panel are the core-set objective made visible -- every molecule in the library is
# within delta of something you labelled.
#
# k-centre greedy is MaxMin diversity picking, which half the room already runs in
# RDKit.  Say that out loud.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style, pool
style.use(); style.versions()

# %%
X, y, is_out = pool.make_pool(seed=21)
p1 = pool.logistic_posterior(X)
unc = 1.0 - np.abs(2 * p1 - 1.0)
B = 24

top = np.argsort(-unc)[:B]


def kcenter_greedy(X, b, start=None, rng=None):
    rng = np.random.default_rng(0) if rng is None else rng
    picked = [int(rng.integers(len(X))) if start is None else start]
    d = np.linalg.norm(X - X[picked[0]], axis=1)
    for _ in range(b - 1):
        j = int(np.argmax(d))
        picked.append(j)
        d = np.minimum(d, np.linalg.norm(X - X[j], axis=1))
    return np.array(picked)


cs = kcenter_greedy(X, B)


def cover_radius(X, sel):
    return float(np.linalg.norm(X[:, None, :] - X[None, sel, :], axis=2).min(1).max())


dU, dC = cover_radius(X, top), cover_radius(X, cs)
print("batch size %d" % B)
print("covering radius delta   uncertainty batch: %.2f   core-set batch: %.2f" % (dU, dC))
print("core-set reduces the worst-case distance to a labelled point by %.0f%%"
      % (100 * (1 - dC / dU)))

# %%
fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.7), sharex=True, sharey=True)
for ax, sel, name, col, show_cover in (
        (axes[0], top, "top-%d by uncertainty" % B, style.EMPH, False),
        (axes[1], cs, "%d by $k$-centre greedy  (core-set)" % B, style.SEC, True)):
    ax.scatter(X[:, 0], X[:, 1], s=11, c=style.MUTED, alpha=0.35, lw=0)
    if show_cover:
        for j in sel:
            ax.add_patch(plt.Circle(X[j], dC, facecolor=style.SEC, alpha=0.075,
                                    edgecolor=style.SEC, lw=0.5, ls=":"))
    ax.scatter(X[sel, 0], X[sel, 1], s=62, c=col, edgecolors="white", lw=1.1, zorder=6)
    bx, by = pool.decision_boundary()
    ax.plot(bx, by, color=style.INK, lw=1.3, ls="--", alpha=0.7)
    ax.set_title(name, fontsize=11.5, pad=8, color=col, fontweight="bold")
    ax.set_xlabel("descriptor 1")
    ax.text(0.5, -0.185, "covering radius  $\\delta$ = %.2f"
            % (dU if not show_cover else dC), transform=ax.transAxes,
            ha="center", fontsize=11.5, fontweight="bold", color=col)

axes[0].set_ylabel("descriptor 2")
axes[0].set_xlim(-4.2, 4.6); axes[0].set_ylim(-4.0, 4.0)
fig.text(0.5, -0.075,
         "shaded circles on the right: the $\\delta$-cover. Core-set ignores the labels and the "
         "uncertainty entirely -- this is pure coverage.",
         ha="center", fontsize=9, color=style.MUTED, style="italic")
style.save(fig, "fig_12_coreset_vs_uncertainty")
