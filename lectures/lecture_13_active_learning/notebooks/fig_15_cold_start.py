# %% [markdown]
# # Figure 15 - for the first few rounds, active learning loses
#
# Slide 42.  A model trained on almost nothing produces biased, outlier-seeking
# queries: it does not yet know enough to know what it does not know.
#
# Same simulation as figure 14, but with a **small seed set and small batches**
# (3 and 3), which is where the cold start actually shows up.  The shaded region
# is where uncertainty sampling is *worse* than random.  Both curves are means
# over 40 runs, so the dip is not noise.

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

N_REP = 40
kw = dict(rounds=16, batch=3, n_seed=3)
rnd = alsim.replicate("random", X, y, test_idx, n_rep=N_REP, **kw)
unc = alsim.replicate("uncertainty", X, y, test_idx, n_rep=N_REP, **kw)

worse = unc["mean"] > rnd["mean"]
# Only the INITIAL contiguous run of "worse" is the cold start.  Later isolated
# crossings are noise and must not be shaded as if they were part of it.
i = 1
while i < len(worse) and worse[i]:
    i += 1
cold = rnd["n"][1:i]
print("uncertainty sampling is worse than random at n =", rnd["n"][worse].tolist())
print("initial contiguous cold-start run: n =", cold.tolist())
print("crosses over at n =", int(rnd["n"][i]))

# %%
fig, ax = plt.subplots(figsize=(8.4, 4.8))
lo, hi = cold.min(), cold.max()
ax.axvspan(lo - 1.5, hi + 1.5, color=style.EMPH, alpha=0.10, lw=0)
ax.text((lo + hi) / 2, 0.372, "active learning\nLOSES here", ha="center", va="top",
        fontsize=11, color=style.EMPH, fontweight="bold", linespacing=1.35)

for r, lab, col, lw in ((rnd, "Random", style.AF_RAND, 2.6),
                        (unc, "Uncertainty sampling", style.EMPH, 2.2)):
    ax.fill_between(r["n"], r["mean"] - r["sd"] / np.sqrt(N_REP),
                    r["mean"] + r["sd"] / np.sqrt(N_REP), color=col, alpha=0.16, lw=0)
    ax.plot(r["n"], r["mean"], color=col, lw=lw, label=lab, marker="o", ms=3.4)

ax.set_xlabel("number of labels acquired")
ax.set_ylabel("test error  (held-out random test set)")
ax.set_xlim(rnd["n"][0], rnd["n"][-1]); ax.set_ylim(0.16, 0.39)
ax.legend(loc="upper right", fontsize=10)
ax.text(0.985, 0.055,
        "the fix is not clever:\nstart with a large, diverse seed set,\nthen switch to AL",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=10.5,
        color=style.SEC, fontweight="bold", linespacing=1.4,
        bbox=dict(boxstyle="round,pad=0.4", fc="#EFF5FC", ec=style.SEC, lw=1.0))
fig.text(0.5, -0.055,
         "illustrative simulation, %d runs each; seed set of 3, batches of 3" % N_REP,
         ha="center", fontsize=8.5, color=style.MUTED, style="italic")
style.save(fig, "fig_15_cold_start")
