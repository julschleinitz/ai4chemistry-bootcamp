# %% [markdown]
# # Figure 10 - you have a 96-well plate, not one flask
#
# Slide 25.  Score the pool by uncertainty, take the top 96, and look at where
# they land: one blob.  One informative region, sampled 96 times.  You have burned
# a plate to learn one thing.
#
# The diagnosis in one line: every acquisition function up to this point scores
# points INDEPENDENTLY.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style, pool
style.use(); style.versions()

# %%
# A larger pool, so 96 is a plausible batch -- PLUS one dense family of close
# analogues straddling the decision boundary.  That family is the point: a real
# virtual library is not uniformly dense, and the region where the model is
# unsure is usually the region where somebody already made 500 close analogues.
# Without it, a linear boundary spreads the top-k along a line and the figure
# teaches nothing.
rng = np.random.default_rng(21)
X, y, is_out = pool.make_pool(seed=21)
extra = np.vstack([X + rng.normal(0, 0.12, X.shape) for _ in range(4)])

ANALOGUE_CENTRE = np.array([0.60, 0.92])        # sits on the boundary
analogues = ANALOGUE_CENTRE + rng.normal(0, 0.18, size=(900, 2))
X = np.vstack([X, extra, analogues])
p1 = pool.logistic_posterior(X)
unc = 1.0 - np.abs(2 * p1 - 1.0)

K = 96
top = np.argsort(-unc)[:K]
in_family = np.linalg.norm(X[top] - ANALOGUE_CENTRE, axis=1) < 0.85
d_batch = np.linalg.norm(X[top][:, None] - X[top][None], axis=2).mean()
d_pool = np.linalg.norm(X[::9][:, None] - X[::9][None], axis=2).mean()
print("pool size %d, batch %d" % (len(X), K))
print("%d of the %d selected (%.0f%%) come from the single analogue family"
      % (in_family.sum(), K, 100 * in_family.mean()))
print("mean pairwise distance  batch %.2f  vs  whole pool %.2f  (%.1fx tighter)"
      % (d_batch, d_pool, d_pool / d_batch))
assert in_family.mean() > 0.8, "the batch must actually be redundant"

# %%
fig, (ax, axp) = plt.subplots(1, 2, figsize=(10.8, 4.7),
                              gridspec_kw=dict(width_ratios=[1.55, 1]))

sc = ax.scatter(X[:, 0], X[:, 1], c=unc, s=13, cmap="magma_r", lw=0, alpha=0.75)
ax.scatter(X[top, 0], X[top, 1], s=46, facecolors="none", edgecolors=style.EMPH,
           linewidths=1.25, zorder=6, label="the top-96 batch")
bx, by = pool.decision_boundary()
ax.plot(bx, by, color=style.INK, lw=1.4, ls="--", label="decision boundary")
ax.set_xlim(-4.2, 4.6); ax.set_ylim(-4.0, 4.0)
ax.set_xlabel("descriptor 1"); ax.set_ylabel("descriptor 2")
ax.legend(loc="lower left", fontsize=9)
cb = fig.colorbar(sc, ax=ax, fraction=0.043, pad=0.02, ticks=[unc.min(), unc.max()])
cb.ax.set_yticklabels(["confident", "uncertain"], fontsize=8.5)
cb.outline.set_visible(False)
ax.set_title("acquisition score over the pool", fontsize=11, pad=8)

# the plate: 96 wells, all the same scaffold
axp.set_title("what arrives in the plate", fontsize=11, pad=8)
for r in range(8):
    for c in range(12):
        axp.add_patch(plt.Circle((c, -r), 0.40, facecolor=style.EMPH, alpha=0.72,
                                 edgecolor="white", lw=1.0))
axp.set_xlim(-1.0, 12.0); axp.set_ylim(-7.9, 1.5)
axp.set_aspect("equal"); axp.axis("off")
axp.text(5.5, 1.0, "96 analogues of the same scaffold", ha="center", fontsize=11.5,
         fontweight="bold", color=style.EMPH)
axp.text(5.5, -8.4, "one informative region, sampled 96 times", ha="center",
         fontsize=10.5, color=style.INK, style="italic")
style.save(fig, "fig_10_topk_redundancy")
