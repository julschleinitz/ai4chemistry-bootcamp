# %% [markdown]
# # Figure 7 - the same error bar, two different causes
#
# Slide 17, companion to figure 6 (use it only if there is time).  A gap in the
# data gives an epistemic band (blue); a densely sampled but noisy region gives
# an aleatoric band (red).  Same band width, different cause -- and only one of
# them shrinks if you spend money.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
from gp import GP
style.use(); style.versions()

# %%
rng = np.random.default_rng(11)
f = lambda x: 0.85 * np.sin(1.15 * x) + 0.10 * x

xs = np.linspace(0, 12, 500)[:, None]
# left half: sparse (a gap)  |  right half: dense but very noisy
XL = np.array([[0.4], [1.2], [2.0]])
XR = np.linspace(7.6, 11.6, 26)[:, None]
NOISY = 0.42
X = np.vstack([XL, XR])
y = np.concatenate([f(XL).ravel() + rng.normal(0, 0.03, len(XL)),
                    f(XR).ravel() + rng.normal(0, NOISY, len(XR))])

g = GP(ell=1.5, sigma_f=1.2, sigma_n=NOISY).fit(X, y)
mu, sd_lat = g.predict(xs, latent=True)      # epistemic only
_, sd_tot = g.predict(xs, latent=False)      # epistemic + aleatoric

kE = int(np.argmax(np.where(xs.ravel() < 6.5, sd_lat, -np.inf)))
kA = 9.6
print("epistemic band peaks at x = %.1f (the gap); the noisy region sits near x = %.1f"
      % (xs[kE, 0], kA))

# %%
fig, ax = plt.subplots(figsize=(9.6, 4.1))
ax.fill_between(xs.ravel(), mu - 2 * sd_tot, mu + 2 * sd_tot,
                color=style.ALEATORIC, alpha=0.16, lw=0,
                label="total  $\\pm2\\sigma$  (epistemic + aleatoric)")
ax.fill_between(xs.ravel(), mu - 2 * sd_lat, mu + 2 * sd_lat,
                color=style.EPISTEMIC, alpha=0.30, lw=0,
                label="epistemic  $\\pm2\\sigma$  (reducible)")
ax.plot(xs, f(xs), color=style.MUTED, lw=1.0, ls="--", label="true function")
ax.plot(xs, mu, color=style.INK, lw=1.6, label="posterior mean")
ax.scatter(X, y, s=32, c=style.INK, zorder=6, label="observations")

ax.annotate("a GAP in the data\nwide band, ALL epistemic\nan experiment fixes this",
            xy=(xs[kE, 0], mu[kE] + 2 * sd_lat[kE]), xytext=(3.15, 2.35),
            fontsize=10.5, color=style.EPISTEMIC, fontweight="bold", linespacing=1.35,
            ha="center",
            arrowprops=dict(arrowstyle="->", color=style.EPISTEMIC, lw=1.4),
            bbox=dict(boxstyle="round,pad=0.35", fc="white",
                      ec=style.EPISTEMIC, lw=1.0))
ax.annotate("DENSE but noisy\nwide band, ALL aleatoric\nmore experiments will not help",
            xy=(kA, f(np.array([[kA]]))[0] - 0.95), xytext=(8.4, -2.5),
            fontsize=10.5, color=style.ALEATORIC, fontweight="bold", linespacing=1.35,
            ha="center",
            arrowprops=dict(arrowstyle="->", color=style.ALEATORIC, lw=1.4),
            bbox=dict(boxstyle="round,pad=0.35", fc="white",
                      ec=style.ALEATORIC, lw=1.0))

ax.set_xlim(0, 12); ax.set_ylim(-3.3, 3.1)
ax.set_xlabel("descriptor"); ax.set_ylabel("measured property")
ax.legend(loc="upper right", fontsize=8.5)
style.save(fig, "fig_07_two_compounds_gp")
