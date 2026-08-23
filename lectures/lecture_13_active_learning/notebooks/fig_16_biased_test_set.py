# %% [markdown]
# # Figure 16 - your data is now a biased sample
#
# Slide 43.  Two error estimates over the same campaign: one measured on the
# actively-acquired labels, one on a random held-out test set that was fixed at
# round zero and never touched.  The gap between them is the sampling bias.
#
# Uncertainty sampling deliberately buys hard points, so the error measured on
# its own acquisitions *over-states* the difficulty of the problem.  The lesson is
# not "AL is bad"; it is that you cannot evaluate on the pool you acquired.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style, alsim
style.use(); style.versions()

# %%
X, y = alsim.make_task()
rng = np.random.default_rng(0)
test_idx = rng.choice(len(X), size=400, replace=False)

N_REP = 30
r = alsim.replicate("uncertainty", X, y, test_idx, n_rep=N_REP,
                    rounds=18, batch=8, n_seed=8)
gap = r["pool_mean"] - r["mean"]
print("error on the acquired labels  -  error on the held-out test set:")
for i in range(0, len(r["n"]), 3):
    print("   n=%3d   acquired %.3f   held-out %.3f   gap %+.3f"
          % (r["n"][i], r["pool_mean"][i], r["mean"][i], gap[i]))
print("mean gap over the campaign: %+.3f" % gap[1:].mean())

# %%
fig, ax = plt.subplots(figsize=(8.6, 4.8))
ax.fill_between(r["n"], r["mean"], r["pool_mean"], color=style.EMPH, alpha=0.13,
                lw=0, label="the bias")
for series, lab, col, ls in ((r["pool_mean"], "measured on the ACQUIRED labels", style.EMPH, "-"),
                            (r["mean"], "measured on a random HELD-OUT test set", style.SEC, "-")):
    ax.plot(r["n"], series, color=col, lw=2.3, ls=ls, label=lab, marker="o", ms=3.4)

ax.set_xlabel("number of labels acquired")
ax.set_ylabel("classification error")
ax.set_xlim(r["n"][0], r["n"][-1])
ax.legend(loc="upper right", fontsize=10)

k = int(len(r["n"]) * 0.62)
ax.annotate("", xy=(r["n"][k], r["pool_mean"][k]), xytext=(r["n"][k], r["mean"][k]),
            arrowprops=dict(arrowstyle="<->", color=style.INK, lw=1.4))
ax.text(r["n"][k] + 4, (r["pool_mean"][k] + r["mean"][k]) / 2,
        "this gap is the\nsampling bias", fontsize=10.5, color=style.INK,
        fontweight="bold", va="center", linespacing=1.35)

ax.text(0.02, 0.05,
        "hold out a random test set at round zero -- and never touch it",
        transform=ax.transAxes, ha="left", va="bottom", fontsize=10.5,
        color=style.SEC, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", fc="#EFF5FC", ec=style.SEC, lw=1.0))
fig.text(0.5, -0.055,
         "uncertainty sampling, illustrative simulation, %d runs" % N_REP,
         ha="center", fontsize=8.5, color=style.MUTED, style="italic")
style.save(fig, "fig_16_biased_test_set")
