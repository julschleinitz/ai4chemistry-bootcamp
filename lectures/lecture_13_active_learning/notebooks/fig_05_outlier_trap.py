# %% [markdown]
# # Figure 5 - the outlier trap
#
# Slide 16.  After Settles, TR1648, 2009, Fig. 7.  Point **A** sits exactly on the
# decision boundary but alone in empty space; point **B** is just off the boundary
# inside a dense cluster.  Uncertainty sampling picks A.  Labelling B helps far
# more, because B is representative of a hundred other molecules and A is
# representative of nothing.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style, pool
style.use(); style.versions()

# %%
X, y, is_out = pool.make_pool()
p1 = pool.logistic_posterior(X)
unc = 1.0 - np.abs(2 * p1 - 1.0)          # 1 at the boundary, 0 when confident

d = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
n_nbr = (d < 0.45).sum(1) - 1

# A = the most uncertain ISOLATED point.  pool.py plants two outliers on the
# decision boundary precisely so that this selection is not a fluke.
isolated = n_nbr <= 1
kA = int(np.argmax(np.where(isolated, unc, -np.inf)))
# B = the most uncertain point that sits in a dense region
dense = n_nbr >= np.quantile(n_nbr, 0.80)
kB = int(np.argmax(np.where(dense, unc, -np.inf)))
assert unc[kA] > 0.9 and n_nbr[kA] <= 1, "A must be uncertain AND isolated"
assert n_nbr[kB] > 20, "B must sit in a dense region"
print("A: uncertainty %.3f, %d neighbours within 0.45  (outlier=%s)"
      % (unc[kA], n_nbr[kA], bool(is_out[kA])))
print("B: uncertainty %.3f, %d neighbours within 0.45" % (unc[kB], n_nbr[kB]))

# %%
fig, ax = plt.subplots(figsize=(7.4, 5.2))
for cls, col, lab in ((0, style.TER, "class 0"), (1, style.ACCENT, "class 1")):
    m = (y == cls) & ~is_out
    ax.scatter(X[m, 0], X[m, 1], s=17, c=col, alpha=0.55, lw=0, label=lab)
ax.scatter(X[is_out, 0], X[is_out, 1], s=30, facecolors="none",
           edgecolors=style.MUTED, linewidths=1.0, label="outliers")

bx, by = pool.decision_boundary()
ax.plot(bx, by, color=style.INK, lw=1.6, ls="--", label="decision boundary")

for k, lab, col, dx, dy, txt in (
        (kA, "A", style.EMPH, -3.35, -0.55,
         "A  most uncertain point\nalone in empty space\nrepresentative of nothing"),
        (kB, "B", style.SEC, 0.55, -1.35,
         "B  slightly less uncertain\ninside a dense cluster\nrepresentative of ~100 molecules")):
    ax.scatter(*X[k], s=230, marker="*", c=col, edgecolors=style.INK,
               linewidths=1.0, zorder=8)
    ax.annotate(txt, xy=X[k], xytext=(X[k, 0] + dx, X[k, 1] + dy),
                fontsize=10, color=col, fontweight="bold", linespacing=1.35,
                arrowprops=dict(arrowstyle="->", color=col, lw=1.4),
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=col, lw=1.0))

ax.set_title("uncertainty sampling picks A", fontsize=13, fontweight="bold",
             color=style.EMPH, pad=10)
ax.set_xlim(-4.2, 4.6); ax.set_ylim(-4.0, 4.0)
ax.set_xlabel("descriptor 1"); ax.set_ylabel("descriptor 2")
ax.legend(loc="lower left", fontsize=8.5, ncol=2)
style.save(fig, "fig_05_outlier_trap")
