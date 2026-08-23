# %% [markdown]
# # Figure 17 - the BO loop in one picture: UCB
#
# Section 1, the recap.  A 1-D GP with a handful of observations, the posterior
# band, and the UCB acquisition drawn underneath:
#
# $$a_{UCB}(x) = \mu(x) + \beta\,\sigma(x)$$
#
# Two panels for two values of $\beta$, because the whole point of UCB is that
# it has one dial and you can *see* what the dial does.  Small $\beta$ exploits
# the incumbent; large $\beta$ walks off to the unexplored region.
#
# This is deliberately the simplest acquisition function in the L12 deck - no
# expectation, no integral, just "predicted mean plus a bit of error bar".

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
from gp import GP
style.use(); style.versions()

# %%
# A well-sampled region containing the incumbent, and a large unexplored gap
# elsewhere. Without that separation the two betas pick almost the same point and
# the figure teaches nothing -- the whole purpose is to SEE the dial move.
truth = lambda x: (3.0 * np.exp(-((x - 3.0) ** 2) / 2.5)
                   + 0.55 * np.sin(1.6 * x) - 0.25)

XLO, XHI = 0.0, 10.0
xs = np.linspace(XLO, XHI, 500)[:, None]
X = np.array([[0.6], [1.5], [2.2], [3.0], [3.7], [4.4], [9.6]])
y = truth(X).ravel()

g = GP(ell=1.15, sigma_f=1.2, sigma_n=0.05).fit(X, y)
mu, sd = g.predict(xs)

BETAS = (1.0, 3.0)
x_best = X[int(np.argmax(y)), 0]
for b in BETAS:
    ucb = mu + b * sd
    xq = xs[int(np.argmax(ucb)), 0]
    where = "near the incumbent (exploit)" if abs(xq - x_best) < 1.5 else "in the gap (explore)"
    print("beta = %.1f  ->  next query at x = %.2f   %s" % (b, xq, where))
print("current best observation at x = %.2f" % x_best)
assert abs(xs[int(np.argmax(mu + BETAS[0] * sd)), 0] - x_best) < 1.5, \
    "small beta must exploit"
assert abs(xs[int(np.argmax(mu + BETAS[1] * sd)), 0] - x_best) > 2.5, \
    "large beta must explore"

# %%
fig, axes = plt.subplots(2, 2, figsize=(10.8, 5.0), sharex=True,
                         gridspec_kw=dict(height_ratios=[2.1, 1], hspace=0.10,
                                          wspace=0.13))

for col, beta in enumerate(BETAS):
    ax, ax2 = axes[0, col], axes[1, col]
    ucb = mu + beta * sd
    k = int(np.argmax(ucb))

    ax.plot(xs, truth(xs), color=style.MUTED, lw=1.0, ls="--", label="true function")
    ax.fill_between(xs.ravel(), mu - beta * sd, mu + beta * sd, color=style.SEC,
                    alpha=0.18, lw=0, label="$\\mu \\pm \\beta\\sigma$")
    ax.plot(xs, mu, color=style.SEC, lw=1.7, label="posterior mean $\\mu$")
    ax.scatter(X, y, s=46, c=style.INK, zorder=6, label="observations")
    ax.axvline(xs[k, 0], color=style.EMPH, lw=1.5, ls=":", zorder=4)
    ax.set_title("$\\beta$ = %.0f     %s" % (beta,
                 "exploit" if beta < 2 else "explore"),
                 fontsize=12, pad=8, color=style.INK, fontweight="bold")
    ax.set_ylim(-2.6, 4.6)

    ax2.fill_between(xs.ravel(), ucb.min(), ucb, color=style.ACCENT, alpha=0.30, lw=0)
    ax2.plot(xs, ucb, color=style.ACCENT, lw=1.8)
    ax2.axvline(xs[k, 0], color=style.EMPH, lw=1.5, ls=":")
    ax2.scatter([xs[k, 0]], [ucb[k]], s=90, marker="v", c=style.EMPH,
                edgecolors="white", lw=1.0, zorder=7)
    ax2.set_xlabel("design variable  $x$")
    ax2.set_ylabel("$a_{UCB}$" if col == 0 else "")
    ax2.set_xlim(XLO, XHI)
    ax2.text(xs[k, 0], ucb.min(), "  next\n  experiment", fontsize=10,
             color=style.EMPH, fontweight="bold", va="bottom", linespacing=1.3)

axes[0, 0].set_ylabel("response")
axes[0, 0].legend(loc="lower left", fontsize=8.5, ncol=2)
fig.text(0.5, 1.02, "$a_{UCB}(x)\\;=\\;\\mu(x)\\;+\\;\\beta\\,\\sigma(x)$",
         ha="center", fontsize=17, fontweight="bold", color=style.INK)
fig.text(0.5, -0.055,
         "one dial. Small $\\beta$ trusts the mean and stays near the incumbent; "
         "large $\\beta$ buys the error bar and leaves.",
         ha="center", fontsize=10, color=style.MUTED, style="italic")
style.save(fig, "fig_17_ucb_recap")
