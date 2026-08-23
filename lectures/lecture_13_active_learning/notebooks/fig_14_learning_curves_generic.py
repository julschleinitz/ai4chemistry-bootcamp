# %% [markdown]
# # Figure 14 - there is no single winner
#
# Slide 29.  Random, uncertainty, core-set and BADGE on one axis set.
#
# **This is a simulation, and the figure says so on its face.**  It is an
# L2-regularised logistic regression on a synthetic 2-D task with a curved
# boundary and a band of irreducible label noise (`_shared/alsim.py`).  Do not
# present it as a chemistry benchmark and do not let anyone read a general
# ranking of the four methods off it.
#
# What it *does* honestly show, and what happened when I ran it:
#
# * uncertainty sampling wins **early**, while there is real epistemic
#   uncertainty to buy;
# * random **catches up and matches it** by the end;
# * core-set and BADGE never beat random on this task -- core-set ignores the
#   labels, and with 5 quadratic features the gradient embedding carries little
#   information.
#
# That is the section-9 message arriving three slides early, which is fine.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style, alsim
style.use(); style.versions()

# %%
X, y = alsim.make_task()
rng = np.random.default_rng(0)
test_idx = rng.choice(len(X), size=400, replace=False)   # random, held out at round 0

STRATS = [("random", "Random", style.AF_RAND, 2.6),
          ("uncertainty", "Uncertainty", style.EMPH, 2.0),
          ("coreset", "Core-set", style.SEC, 2.0),
          ("badge", "BADGE", style.ACCENT, 2.0)]
N_REP = 24

res = {}
for key, _, _, _ in STRATS:
    res[key] = alsim.replicate(key, X, y, test_idx, n_rep=N_REP,
                               rounds=18, batch=8, n_seed=8)
    e = res[key]["mean"]
    print("%-12s  err %.3f -> %.3f   best %.3f" % (key, e[0], e[-1], e.min()))

# %%
fig, ax = plt.subplots(figsize=(8.4, 4.9))
for key, lab, col, lw in STRATS:
    r = res[key]
    ax.fill_between(r["n"], r["mean"] - r["sd"] / np.sqrt(N_REP),
                    r["mean"] + r["sd"] / np.sqrt(N_REP), color=col, alpha=0.15, lw=0)
    ax.plot(r["n"], r["mean"], color=col, lw=lw, label=lab,
            zorder=6 if key == "random" else 5)

ax.set_xlabel("number of labels acquired")
ax.set_ylabel("test error  (held-out random test set)")
ax.legend(loc="upper right", fontsize=10, ncol=2)
ax.set_xlim(res["random"]["n"][0], res["random"]["n"][-1])

# annotate the two honest observations -- placed in clear space above the curves
nu = res["uncertainty"]["n"]; eu = res["uncertainty"]["mean"]
k = int(np.argmin(np.abs(nu - 40)))
ax.annotate("uncertainty wins early", xy=(nu[k], eu[k] - 0.004),
            xytext=(nu[k] + 14, 0.300), fontsize=11, color=style.EMPH,
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=style.EMPH, lw=1.3))
nr = res["random"]["n"]; er = res["random"]["mean"]
ax.annotate("random catches up", xy=(nr[-3], er[-3] - 0.004),
            xytext=(nr[-3] - 46, 0.262), fontsize=11, color=style.INK,
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=style.INK, lw=1.3))

ax.set_ylim(0.135, 0.345)
ax.text(0.50, 0.035, "illustrative simulation - one synthetic task;  "
                     "the ranking does NOT transfer to your data set",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=9.5,
        color=style.EMPH, style="italic", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.35", fc="#FFF3F3", ec=style.EMPH, lw=1.0))
fig.text(0.5, -0.06,
         "logistic regression, quadratic features, %d independent runs; bands are the "
         "standard error of the mean" % N_REP,
         ha="center", fontsize=8.5, color=style.MUTED, style="italic")
style.save(fig, "fig_14_learning_curves_generic")
