# %% [markdown]
# # Figure 9 - query by committee, and the MLIP loop
#
# Slide 23.  Five ensemble members over a 1-D reaction coordinate, with the
# disagreement envelope shaded and a DFT-trigger threshold drawn on.  Where the
# committee disagrees more than the model's own noise level, you call DFT.
#
# This is what Smith et al. (*J. Chem. Phys.* **2018**, *148*, 241733) and
# Vandermause et al. (*npj Comput. Mater.* **2020**, *6*, 20) actually do.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
from gp import GP
style.use(); style.versions()

# %%
rng = np.random.default_rng(17)
truth = lambda x: 2.4 * np.exp(-((x - 2.2) ** 2) / 1.1) - 1.5 * np.exp(-((x - 6.6) ** 2) / 0.8) \
                  + 0.35 * np.sin(1.5 * x)

xs = np.linspace(0, 10, 500)[:, None]
X = np.array([[0.5], [1.4], [2.3], [3.1], [8.8], [9.5]])   # a gap over 4 -> 8.5
y = truth(X).ravel()

# a committee: each member sees a bootstrap resample, as an ensemble would
members = []
for m in range(5):
    idx = rng.choice(len(X), size=len(X), replace=True)
    members.append(GP(ell=1.25 + 0.1 * m, sigma_f=1.7, sigma_n=0.05)
                   .fit(X[idx], y[idx]).predict(xs)[0])
M = np.stack(members)
spread = M.std(0)

THRESH = 0.35            # the model's own noise level
trigger = xs.ravel()[spread > THRESH]
print("committee spread exceeds the %.2f eV/A threshold over x in [%.1f, %.1f]"
      % (THRESH, trigger.min(), trigger.max()))
print("that is %.0f%% of the trajectory" % (100 * len(trigger) / len(xs)))

# %%
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9.6, 5.3), sharex=True,
                              gridspec_kw=dict(height_ratios=[2.4, 1], hspace=0.12))

ax.fill_between(xs.ravel(), M.min(0), M.max(0), color=style.EPISTEMIC, alpha=0.20,
                lw=0, label="committee envelope")
for i, m in enumerate(M):
    ax.plot(xs, m, lw=1.15, color=style.EPISTEMIC, alpha=0.75,
            label="committee members" if i == 0 else None)
ax.plot(xs, truth(xs), color=style.MUTED, lw=1.1, ls="--", label="true potential")
ax.scatter(X, y, s=40, c=style.INK, zorder=6, label="DFT reference points")
ax.set_ylabel("energy  /  arb.")
ax.legend(loc="upper right", fontsize=8.5, ncol=2)
ax.set_title("an ensemble of neural-network potentials, along one reaction coordinate",
             fontsize=11, pad=8)

ax2.fill_between(xs.ravel(), 0, spread, color=style.EPISTEMIC, alpha=0.35, lw=0)
ax2.plot(xs, spread, color=style.EPISTEMIC, lw=1.6)
ax2.axhline(THRESH, color=style.EMPH, lw=1.5, ls=":")
ax2.text(0.12, THRESH, " DFT trigger threshold", va="bottom", fontsize=9.5,
         color=style.EMPH, fontweight="bold")
ax2.fill_between(xs.ravel(), 0, spread.max() * 1.15,
                 where=(spread > THRESH), color=style.EMPH, alpha=0.10, lw=0)
ax2.set_ylabel("committee\ndisagreement")
ax2.set_xlabel("reaction coordinate")
ax2.set_ylim(0, spread.max() * 1.15)
ax2.annotate("the model has left\nfamiliar chemistry:\ncall DFT here",
             xy=(6.0, spread.max() * 0.72), xytext=(6.0, spread.max() * 0.30),
             ha="center", fontsize=10, color=style.EMPH, fontweight="bold",
             linespacing=1.3)
style.save(fig, "fig_09_qbc_ensemble")
