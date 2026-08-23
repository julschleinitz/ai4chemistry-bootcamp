# %% [markdown]
# # Figure 13 - length and direction
#
# Slide 28.  The BADGE gradient embedding, drawn as arrows from the origin:
# **direction** is the penultimate-layer fingerprint (diversity), **length** is
# how far the model would move if it were wrong (uncertainty).  Then k-means++
# seeding on those vectors picks long, well-separated arrows.
#
# Small batch -> length dominates -> behaves like uncertainty sampling.
# Large batch -> separation dominates -> behaves like core-set.  No hyperparameter.
#
# Ash et al., BADGE, ICLR 2020, arXiv:1906.03671.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
style.use(); style.versions()

# %%
rng = np.random.default_rng(9)
N = 150
theta = rng.uniform(0, 2 * np.pi, N)
# three loose "scaffold families" in direction, with varying uncertainty in length
theta = np.concatenate([rng.normal(0.7, 0.42, 60), rng.normal(2.9, 0.35, 50),
                        rng.normal(4.9, 0.40, 40)])
mag = np.abs(rng.normal(0, 1, len(theta))) ** 1.3 * 0.9 + 0.06
G = np.column_stack([mag * np.cos(theta), mag * np.sin(theta)])


def kmeanspp(G, k, rng):
    picked = [int(np.argmax(np.sum(G ** 2, 1)))]         # deterministic start
    d2 = np.sum((G - G[picked[0]]) ** 2, 1)
    for _ in range(k - 1):
        pr = d2 / max(d2.sum(), 1e-12)
        j = int(rng.choice(len(G), p=pr))
        picked.append(j)
        d2 = np.minimum(d2, np.sum((G - G[j]) ** 2, 1))
    return np.array(picked)


sel = kmeanspp(G, 8, np.random.default_rng(2))
print("selected %d of %d" % (len(sel), len(G)))
print("mean |g| selected %.2f  vs  pool %.2f   (uncertainty is respected)"
      % (np.linalg.norm(G[sel], axis=1).mean(), np.linalg.norm(G, axis=1).mean()))
ang = np.sort(np.arctan2(G[sel, 1], G[sel, 0]))
print("selected directions span %.0f deg of arc  (diversity is respected)"
      % np.degrees(np.ptp(ang)))

# %%
fig, ax = plt.subplots(figsize=(7.2, 5.5))
for g in G:
    ax.annotate("", xy=g, xytext=(0, 0),
                arrowprops=dict(arrowstyle="-", color=style.MUTED, lw=0.7, alpha=0.45))
for g in G[sel]:
    ax.annotate("", xy=g, xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", color=style.SEC, lw=2.1,
                                shrinkA=0, shrinkB=0))
ax.scatter(*G[sel].T, s=52, c=style.SEC, edgecolors="white", lw=1.0, zorder=6,
           label="selected by $k$-means++")
ax.scatter([0], [0], s=40, c=style.INK, zorder=7)

lim = np.abs(G).max() * 1.18
ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
ax.axhline(0, color=style.MUTED, lw=0.6, alpha=0.4)
ax.axvline(0, color=style.MUTED, lw=0.6, alpha=0.4)
ax.set_xlabel("gradient embedding  $g_x = (p - e_{\\hat y}) \\otimes z(x)$")
ax.set_ylabel("")
ax.set_xticks([]); ax.set_yticks([])
for sp in ax.spines.values():
    sp.set_visible(False)
ax.legend(loc="lower left", fontsize=9.5)

ax.set_xlim(-lim * 1.05, lim * 1.30); ax.set_ylim(-lim * 1.18, lim * 1.12)
longest = G[sel][int(np.argmax(np.linalg.norm(G[sel], axis=1)))]
ax.annotate("LENGTH = uncertainty",
            xy=longest * 0.62, xytext=(lim * 0.16, -lim * 1.06), fontsize=11,
            color=style.EMPH, fontweight="bold", ha="left",
            arrowprops=dict(arrowstyle="->", color=style.EMPH, lw=1.3),
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=style.EMPH, lw=0.9))
ax.text(lim * 0.30, lim * 0.98, "DIRECTION = fingerprint\nthree scaffold families;\n"
        "the sampler takes from each", fontsize=11, color=style.SEC,
        fontweight="bold", linespacing=1.35, ha="left", va="top",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=style.SEC, lw=0.9))
fig.text(0.5, 0.015,
         "small batch $\\rightarrow$ length wins $\\rightarrow$ uncertainty sampling      |      "
         "large batch $\\rightarrow$ separation wins $\\rightarrow$ core-set",
         ha="center", fontsize=10.5, color=style.INK, fontweight="bold")
style.save(fig, "fig_13_badge_embedding")
