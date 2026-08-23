# %% [markdown]
# # Figure 4 - variance sampling walks to the edge, then tiles the space
#
# Slide 14.  Panel (a): a 1-D GP on 6 observations; the argmax of the posterior
# variance sits at the *edge* of the domain.  Panel (b): five more
# variance-selected points, and the design is space-filling.
#
# The point to make in the room: sigma^2(x) never sees the y values.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
from gp import GP
style.use(); style.versions()

# %%
rng = np.random.default_rng(4)
truth = lambda x: np.sin(1.7 * x) + 0.32 * np.cos(4.1 * x) - 0.05 * x

XLO, XHI = 0.0, 10.0
xs = np.linspace(XLO, XHI, 400)[:, None]
X = np.array([[1.1], [1.9], [2.6], [4.4], [5.1], [6.0]])   # deliberately left-clustered
y = truth(X).ravel() + rng.normal(0, 0.06, len(X))

KW = dict(ell=1.05, sigma_f=1.05, sigma_n=0.08)
g = GP(**KW).fit(X, y)
mu, sd = g.predict(xs)
k_next = int(np.argmax(sd))
print("argmax sigma^2 at x = %.2f  (domain is [%.0f, %.0f])" % (xs[k_next, 0], XLO, XHI))

# %%
# five further points, each chosen by pure variance sampling
Xb, yb = X.copy(), y.copy()
picked = []
for _ in range(5):
    gb = GP(**KW).fit(Xb, yb)
    _, sdb = gb.predict(xs)
    k = int(np.argmax(sdb))
    picked.append(xs[k, 0])
    Xb = np.vstack([Xb, xs[k]])
    yb = np.append(yb, truth(xs[k]) + rng.normal(0, 0.06))
gb = GP(**KW).fit(Xb, yb)
mub, sdb = gb.predict(xs)
print("then chose x =", np.round(picked, 2))

# %%
fig, axes = plt.subplots(1, 2, figsize=(10.6, 3.7), sharey=True)

def panel(ax, Xp, yp, m, s, title, mark=None, show_new=0):
    ax.plot(xs, truth(xs), color=style.MUTED, lw=1.0, ls="--", label="true function")
    ax.fill_between(xs.ravel(), m - 2 * s, m + 2 * s, color=style.SEC, alpha=0.18,
                    lw=0, label="posterior $\\pm 2\\sigma$")
    ax.plot(xs, m, color=style.SEC, lw=1.7, label="posterior mean")
    n0 = len(Xp) - show_new
    ax.scatter(Xp[:n0], yp[:n0], s=44, c=style.INK, zorder=6, label="observations")
    if show_new:
        ax.scatter(Xp[n0:], yp[n0:], s=54, marker="D", c=style.ACCENT,
                   edgecolors=style.INK, linewidths=0.8, zorder=7,
                   label="variance-selected")
    if mark is not None:
        ax.axvline(mark, color=style.EMPH, lw=1.6, ls=":", zorder=4)
        ax.annotate("argmax $\\sigma^2$\nis at the EDGE",
                    xy=(mark, -1.55), xytext=(mark - 3.1, -1.9),
                    fontsize=10, color=style.EMPH, fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=style.EMPH, lw=1.3))
    ax.set_title(title, fontsize=11, pad=7)
    ax.set_xlabel("reaction coordinate  (arbitrary 1-D design variable)")
    ax.set_xlim(XLO, XHI); ax.set_ylim(-2.3, 2.0)

panel(axes[0], X, y, mu, sd, "(a)  6 observations, clustered on the left",
      mark=xs[k_next, 0])
panel(axes[1], Xb, yb, mub, sdb, "(b)  after 5 more variance-selected points",
      show_new=5)
axes[0].set_ylabel("response")
axes[0].legend(loc="upper right", fontsize=8.5, ncol=1)
axes[1].legend(loc="upper right", fontsize=8.5)
axes[1].text(0.5, -0.30, "variance sampling is a space-filling design",
             transform=axes[1].transAxes, ha="center", fontsize=11,
             fontweight="bold", color=style.INK)
style.save(fig, "fig_04_gp_variance_sampling")
