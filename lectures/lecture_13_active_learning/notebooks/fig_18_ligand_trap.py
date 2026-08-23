# %% [markdown]
# # Figure 18 - the uncertainty-sampling trap on a ligand library
#
# Section 3.1.  You have an enumerated ligand set, you want a model that predicts
# well *across the whole library*, and you reach for uncertainty sampling.  It
# spends your budget on the strangest ligands in the catalogue - the ones no
# nearest neighbour resembles - and your model does not improve where it matters.
#
# **This is a simulation, and the figure says so.**  The descriptor axes are the
# two a phosphine chemist would reach for (Tolman cone angle vs. electronic
# parameter), the bulk of the library sits where real catalogues sit, and I have
# planted a handful of deliberate exotics.  It is an illustration of a mechanism,
# not a result on a real catalogue.
#
# The right-hand panel is the fix: multiply the uncertainty by a density term so
# the score rewards points that are *representative as well as* uncertain
# (Settles & Craven's information density), and the budget lands in the populated
# regions instead.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
style.use(); style.versions()

# %%
rng = np.random.default_rng(12)

# --- the library: three populated families a chemist would recognise ---
FAMILIES = [
    ("trialkyl", 165.0, 2062.5, 14.0, 1.1, 150),
    ("triaryl",  148.0, 2068.5, 11.0, 1.3, 170),
    ("biaryl / bulky", 195.0, 2059.5, 13.0, 1.0, 110),
]
pts, fam = [], []
for i, (_, cx, cy, sx, sy, n) in enumerate(FAMILIES):
    pts.append(np.column_stack([rng.normal(cx, sx, n), rng.normal(cy, sy, n)]))
    fam += [i] * n
X = np.vstack(pts)
fam = np.array(fam)

# --- the exotics: real ligands exist out here, but very few of them ---
EXOTIC = np.array([[228.0, 2085.0], [104.0, 2048.0], [236.0, 2044.0],
                   [ 98.0, 2082.0], [215.0, 2079.5], [118.0, 2043.5]])
X = np.vstack([X, EXOTIC])
is_exotic = np.zeros(len(X), bool); is_exotic[-len(EXOTIC):] = True
print("library: %d ligands, of which %d exotics" % (len(X), is_exotic.sum()))

# %%
# --- a stand-in model uncertainty: distance to the k nearest labelled neighbours ---
# (this is what any sensible epistemic estimate looks like on a fixed library)
Z = (X - X.mean(0)) / X.std(0)
lab = rng.choice(np.where(~is_exotic)[0], size=25, replace=False)   # small seed set
d_lab = np.linalg.norm(Z[:, None, :] - Z[None, lab, :], axis=2)
unc = np.sort(d_lab, axis=1)[:, :3].mean(1)          # mean distance to 3 nearest labelled
unc = unc / unc.max()

# --- density of the library itself, for the corrected score ---
d_all = np.linalg.norm(Z[:, None, :] - Z[None, ::3, :], axis=2)
dens = np.exp(-(np.sort(d_all, axis=1)[:, 1:11] ** 2) / 0.5).mean(1)
dens = dens / dens.max()

BUDGET = 12
BETA = 1.0
pick_unc = np.argsort(-unc)[:BUDGET]
pick_dens = np.argsort(-(unc * dens ** BETA))[:BUDGET]

print("uncertainty sampling      : %d of %d picks are exotics"
      % (is_exotic[pick_unc].sum(), BUDGET))
print("uncertainty x density^%.0f : %d of %d picks are exotics"
      % (BETA, is_exotic[pick_dens].sum(), BUDGET))
assert is_exotic[pick_unc].sum() >= 5, "the trap must actually fire"
assert is_exotic[pick_dens].sum() <= 1, "the fix must actually work"

# %%
FCOL = [style.TER, style.ACCENT, style.SEC]
fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.7), sharex=True, sharey=True)

panels = [(axes[0], pick_unc, "Uncertainty sampling", "$a(x) = \\sigma(x)$", style.EMPH),
          (axes[1], pick_dens, "Uncertainty $\\times$ density",
           "$a(x) = \\sigma(x)\\;\\cdot\\;\\mathrm{density}(x)^{\\beta}$", style.SEC)]

for ax, pick, title, formula, col in panels:
    for i, (name, *_ ) in enumerate(FAMILIES):
        m = (fam == i)
        ax.scatter(X[:len(fam)][m, 0], X[:len(fam)][m, 1], s=15, c=FCOL[i],
                   alpha=0.45, lw=0, label=name if ax is axes[0] else None)
    ax.scatter(X[is_exotic, 0], X[is_exotic, 1], s=52, marker="D",
               facecolors="none", edgecolors=style.INK, linewidths=1.2,
               label="exotics (rare)" if ax is axes[0] else None)
    ax.scatter(X[lab, 0], X[lab, 1], s=26, marker="x", c=style.MUTED, lw=1.0,
               label="already labelled" if ax is axes[0] else None)
    ax.scatter(X[pick, 0], X[pick, 1], s=140, marker="o", facecolors="none",
               edgecolors=col, linewidths=2.0, zorder=8)
    ax.set_title(title, fontsize=12.5, color=col, fontweight="bold", pad=8)
    ax.set_xlabel("Tolman cone angle  $\\theta$  /  $^\\circ$")
    n_ex = is_exotic[pick].sum()
    ax.text(0.5, -0.235, "%d of %d picks are exotics" % (n_ex, BUDGET),
            transform=ax.transAxes, ha="center", fontsize=13, fontweight="bold",
            color=col)
    ax.text(0.03, 0.955, formula, transform=ax.transAxes, fontsize=12,
            va="top", color=col,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=col, lw=0.9))

axes[0].set_ylabel("electronic parameter  $\\nu_{CO}$  /  cm$^{-1}$")
axes[0].legend(loc="lower left", fontsize=8.5, ncol=2)
axes[0].invert_yaxis()
fig.text(0.5, 1.03,
         "budget of %d ligands, spent two ways on the same library" % BUDGET,
         ha="center", fontsize=11, color=style.INK)
fig.text(0.5, -0.125,
         "illustrative simulation - synthetic library on real descriptor axes; "
         "the mechanism is real, the catalogue is not",
         ha="center", fontsize=9, color=style.EMPH, style="italic", fontweight="bold")
style.save(fig, "fig_18_ligand_trap")
