# %% [markdown]
# # Figure 1 - the same 20 experiments, two different questions
#
# Slide 4.  The money figure of section 1.  Two panels, shared colour scale, the
# *fitted* surface underneath each point set, the true optimum marked.
#
# Same landscape, same budget, same seed -- say all three out loud in the room.
#
# **Two metrics are reported, and the distinction matters.**  "Best yield found"
# is what BO optimises.  "RMSE away from the optimum" (the bottom 75% of the true
# surface) is what AL optimises, and it is the quantity the lecture actually
# claims differs: how well do you know the parts of the space you are *not*
# optimising?  Global RMSE also separates the two, but less sharply, because
# expected improvement does explore.
#
# The panel numbers are one representative seed; the annotation reports the mean
# over 30 seeds so nobody has to take the single run on trust.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style, landscape as L, campaign
style.use(); style.versions()

# %%
SEED, BUDGET, N_REP = 2, 20, 30
bo = campaign.run("bo", budget=BUDGET, seed=SEED)
al = campaign.run("al", budget=BUDGET, seed=SEED)
xopt, fopt = L.optimum()
print("true optimum: %.0f C, %.2f mol%%  ->  %.1f%% yield" % (xopt[0], xopt[1], fopt))

# %%
# replicate over seeds -- reported on the figure, so the claim is not one lucky run
agg = {k: {m: [] for m in ("rmse", "rmse_away", "best_found")} for k in ("bo", "al")}
for sd in range(N_REP):
    for k in ("bo", "al"):
        r = campaign.run(k, budget=BUDGET, seed=sd)
        for m in agg[k]:
            agg[k][m].append(r[m])
for k in ("bo", "al"):
    d = agg[k]
    print("%s  global RMSE %.1f+-%.1f | away-from-opt %.1f+-%.1f | best found %.0f+-%.0f"
          % (k.upper(), np.mean(d["rmse"]), np.std(d["rmse"]),
             np.mean(d["rmse_away"]), np.std(d["rmse_away"]),
             np.mean(d["best_found"]), np.std(d["best_found"])))
n_al = sum(x < y for x, y in zip(agg["al"]["rmse_away"], agg["bo"]["rmse_away"]))
n_bo = sum(x > y for x, y in zip(agg["bo"]["best_found"], agg["al"]["best_found"]))
print("AL better away-from-optimum model: %d/%d | BO better optimum: %d/%d"
      % (n_al, N_REP, n_bo, N_REP))

# %%
TT, LL, F = bo["TT"], bo["LL"], bo["truth"]
vmin, vmax = 0.0, float(F.max())
fig, axes = plt.subplots(1, 2, figsize=(10.7, 4.35), sharey=True)

panels = [(axes[0], bo, "bo", "Bayesian optimization\nexpected improvement", style.EMPH),
          (axes[1], al, "al", "Active learning\nvariance sampling", style.SEC)]

for ax, run, key, title, col in panels:
    cf = ax.contourf(TT, LL, run["fitted"], levels=np.linspace(vmin, vmax, 24),
                     cmap="BuGn", extend="both")
    ax.contour(TT, LL, F, levels=6, colors=style.INK, linewidths=0.75,
               linestyles="--", alpha=0.5)
    ax.scatter(run["X"][:5, 0], run["X"][:5, 1], s=44, facecolors="none",
               edgecolors=style.INK, linewidths=1.3, zorder=5, label="5 seed points")
    ax.scatter(run["X"][5:, 0], run["X"][5:, 1], s=54, c=col, edgecolors="white",
               linewidths=1.1, zorder=6, label="15 acquired")
    ax.plot(*xopt, marker="*", ms=18, color=style.ACCENT, mec=style.INK, mew=0.8,
            zorder=7, label="true optimum")
    ax.set_title(title, color=col, fontsize=12, pad=8, fontweight="bold")
    ax.set_xlabel("temperature  /  $^\\circ$C")
    d = agg[key]
    wins = n_bo if key == "bo" else n_al
    what = "better optimum" if key == "bo" else "better model away from it"
    # The replicate count lives here, per panel. A single figure-level caption
    # underneath collides with these two lines once savefig's tight bbox
    # recomputes the layout -- do not put it back.
    ax.text(0.5, -0.285,
            "best yield found   %.0f%%\nRMSE away from optimum   %.1f%%\n%s in %d/%d runs"
            % (np.mean(d["best_found"]), np.mean(d["rmse_away"]), what, wins, N_REP),
            transform=ax.transAxes, ha="center", va="top", fontsize=10.5,
            color=style.INK, fontweight="bold", linespacing=1.6)

axes[0].set_ylabel("catalyst loading  /  mol%")
axes[0].legend(loc="upper left", fontsize=8.5)
fig.text(0.5, 1.015,
         "dashed contours: the TRUE surface      filled colour: what the model believes",
         ha="center", fontsize=9, color=style.MUTED, style="italic")
cb = fig.colorbar(cf, ax=axes, fraction=0.031, pad=0.02, ticks=[0, 25, 50, 75, 100])
cb.set_label("predicted yield  /  %", fontsize=9)
cb.outline.set_visible(False)
style.save(fig, "fig_01_two_campaigns")
