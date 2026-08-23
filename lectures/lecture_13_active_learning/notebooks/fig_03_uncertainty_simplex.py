# %% [markdown]
# # Figure 3 - the three uncertainty measures over the 3-class simplex
#
# Slide 12.  After Settles, *Active Learning Literature Survey*, TR1648, 2009,
# Fig. 5.  Three heat-maps on one shared colour scale.  The teaching point is
# that they agree at the centre and disagree towards the edges -- and that for
# two classes they are identical.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
style.use(); style.versions()

# %%
def simplex_grid(n=340):
    """Barycentric grid over the 3-class probability simplex."""
    xs = np.linspace(0, 1, n)
    ys = np.linspace(0, np.sqrt(3) / 2, n)
    XX, YY = np.meshgrid(xs, ys)
    # cartesian -> barycentric for the triangle (0,0), (1,0), (0.5, sqrt3/2)
    p3 = YY / (np.sqrt(3) / 2)
    p2 = XX - p3 * 0.5
    p1 = 1.0 - p2 - p3
    inside = (p1 >= 0) & (p2 >= 0) & (p3 >= 0)
    P = np.stack([p1, p2, p3], -1)
    return XX, YY, P, inside


def least_confident(P):
    return 1.0 - P.max(-1)


def margin(P):
    S = np.sort(P, -1)
    return 1.0 - (S[..., -1] - S[..., -2])       # inverted so "high = query me"


def entropy(P):
    Q = np.clip(P, 1e-12, 1)
    return -(Q * np.log(Q)).sum(-1) / np.log(3)  # normalised to [0, 1]


XX, YY, P, inside = simplex_grid()
measures = [("Least confident", least_confident(P)),
            ("Margin", margin(P)),
            ("Entropy", entropy(P))]

# %%
fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.5))
for ax, (name, Z) in zip(axes, measures):
    Zm = np.where(inside, Z, np.nan)
    Zm = (Zm - np.nanmin(Zm)) / (np.nanmax(Zm) - np.nanmin(Zm))
    im = ax.imshow(Zm, origin="lower", extent=[0, 1, 0, np.sqrt(3) / 2],
                   cmap="magma_r", vmin=0, vmax=1, interpolation="bilinear")
    tri = np.array([[0, 0], [1, 0], [0.5, np.sqrt(3) / 2], [0, 0]])
    ax.plot(tri[:, 0], tri[:, 1], color=style.INK, lw=1.1)
    for (x, y), lab, ha, va in [((0, 0), "$y_1$", "right", "top"),
                                ((1, 0), "$y_2$", "left", "top"),
                                ((0.5, np.sqrt(3) / 2), "$y_3$", "center", "bottom")]:
        ax.text(x, y, "  " + lab + " ", ha=ha, va=va, fontsize=10, color=style.INK)
    ax.set_title(name, fontsize=11, pad=6)
    ax.axis("off")

cb = fig.colorbar(im, ax=axes, fraction=0.028, pad=0.02, ticks=[0, 1])
cb.ax.set_yticklabels(["confident", "query me"], fontsize=9)
cb.outline.set_visible(False)
fig.text(0.5, -0.04,
         "Each triangle is the space of 3-class predictions. Bottom edge = class $y_3$ ruled out: "
         "there, margin and entropy disagree.",
         ha="center", fontsize=9, color=style.MUTED, style="italic")
style.save(fig, "fig_03_uncertainty_simplex")
