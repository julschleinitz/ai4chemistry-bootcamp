"""Notebook specs: what sigma_f and sigma_n actually do to the posterior.

Two companion figures for the hyperparameter section. Both hold everything
else fixed and sweep one parameter, so the effect is unambiguous.

The pedagogical split:
  sigma_f  controls what happens AWAY from the data  (the band's ceiling)
  sigma_n  controls what happens AT the data         (through the points, or near them)
"""

FIG18 = ("fig_18_sigma_f.ipynb",
         "Figure 18 — what σ_f does: how far the belief can travel from the data",
         "Same six observations, same length-scale, same noise. Only the signal "
         "standard deviation σ_f changes.\n\n"
         "σ_f is the **prior** spread of the function, so it sets the CEILING of "
         "the posterior band: far from any data, σ(x) → σ_f. At the observations "
         "it does almost nothing — all three panels fit the data equally well "
         "(mean |error| 0.017, 0.001, 0.000). The whole effect is in the GAPS, "
         "and therefore entirely on how much the campaign wants to explore.",
         [(None, r'''
style.SHOW_TEXT = True   # False -> clean panels for ungrouping into pptx shapes

xs = np.linspace(0, 10, 600)
OX = np.array([1.15, 2.90, 4.30, 6.10, 7.40, 8.90])
OY = land.f1d(OX)
LS, SN = 0.85, 0.05          # held fixed throughout

SETTINGS = [
    (0.25, "too small", style.RED,
     "claims to know the gaps\n→ BO stops exploring"),
    (1.00, "about right", style.INK,
     "confident at the data,\nhonestly ignorant between it"),
    (3.00, "too large", style.GOLD,
     "everything unmeasured looks wide open\n→ BO explores forever"),
]

fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 3.5), sharey=True,
                         gridspec_kw=dict(wspace=0.08))

for ax, (sf, tag, colour, note) in zip(axes, SETTINGS):
    g = gpmod.GP(gpmod.matern52, ls=LS, sf=sf, sn=SN).fit(OX[:, None], OY)
    mu, sd = g.predict(xs[:, None])

    # the ceiling: sigma(x) can never exceed sigma_f
    ax.axhline(2 * sf, color=colour, ls=":", lw=1.1, alpha=0.85)
    ax.axhline(-2 * sf, color=colour, ls=":", lw=1.1, alpha=0.85)
    style.text(ax, 9.85, 2 * sf + 0.15, r"$\pm 2\sigma_f$ ceiling",
               ha="right", va="bottom", fontsize=9.5, color=colour,
               bbox=dict(fc="white", alpha=0.85, ec="none", pad=1.6))

    ax.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL,
                    alpha=0.16, lw=0)
    ax.plot(xs, mu, color=style.TEAL, lw=2.0, zorder=5)
    ax.plot(xs, land.f1d(xs), "--", color=style.INK, lw=1.0, alpha=0.40, zorder=4)
    ax.plot(OX, OY, "o", ms=6.5, color=style.RED, mec="white", mew=1.1, zorder=7)

    ax.set_ylim(-6.6, 6.6)
    style.xlabel(ax, "reaction parameter  x")
    style.title(ax, fr"$\sigma_f$ = {sf:.2f}  —  {tag}", loc="left",
                fontsize=11.5, color=colour, pad=8)
    style.text(ax, 0.03, 0.03, note, transform=ax.transAxes, fontsize=8.8,
               color=style.INK, va="bottom",
               bbox=dict(fc="white", alpha=0.85, ec="none", pad=2.0))

    # how badly does the mean miss its own observations?
    mu_at, _ = g.predict(OX[:, None])
    miss = np.abs(mu_at - OY).mean()
    gap = sd[np.argmin(np.abs(xs - 5.2))]     # sd in the widest gap
    style.text(ax, 0.03, 0.965,
               f"fit error at the data   {miss:.3f}\nsd in the gap   {gap:.2f}",
               transform=ax.transAxes, ha="left", va="top", fontsize=9.2,
               color=colour, fontweight="bold",
               bbox=dict(fc="white", alpha=0.88, ec="none", pad=2.2))
    print(f"sigma_f={sf:<5} mean |fit error| at the data = {miss:.3f} "
          f"| sd in the gap at x=5.2 = {gap:.3f}  (ceiling {sf:.2f})")

style.ylabel(axes[0], "yield (arb.)")
style.text(axes[1], 0.5, 1.10, "dashed = the truth   ·   dots = experiments   ·   "
           r"$\ell$ and $\sigma_n$ identical in all three panels",
           transform=axes[1].transAxes, ha="center", fontsize=9.5,
           color=style.GRAY)
style.save(fig, "fig_18_sigma_f", OUT)
''')])

FIG19 = ("fig_19_sigma_n.ipynb",
         "Figure 19 — what σ_n does: through the points, or near them",
         "Same observations, same length-scale, same signal variance. Only the "
         "noise standard deviation σ_n changes.\n\n"
         "**Two of the runs are replicates** — nominally identical conditions, "
         "disagreeing by 0.5 because of measurement error. That pair is the whole "
         "story. With σ_n ≈ 0 the model is asked to pass through two different "
         "values at the same x — impossible — so it splits the difference while "
         "still claiming a band of 0.02 at every point. With a truthful σ_n it "
         "passes between them and keeps an honest floor of uncertainty. Too "
         "large and it stops listening to the data at all.\n\n"
         "The log marginal likelihood printed on each panel is the decisive "
         "number: the interpolating model scores −628 against −7. The fitting "
         "procedure rejects it overwhelmingly — *if* you let it choose.",
         [(None, r'''
style.SHOW_TEXT = True   # False -> clean panels for ungrouping into pptx shapes

xs = np.linspace(0, 10, 900)
# two runs at IDENTICAL conditions, 0.5 apart in measured yield -- a real
# replicate. With sigma_n ~ 0 the model is asked to pass through two different
# values at the same x, which is impossible; the marginal likelihood says so.
OX = np.array([1.15, 2.90, 4.30, 4.30, 6.10, 7.40, 8.90])
OY = land.f1d(OX).copy()
mid = 0.5 * (OY[2] + OY[3])
OY[2], OY[3] = mid + 0.25, mid - 0.25
LS, SF = 0.85, 1.0           # held fixed throughout

SETTINGS = [
    (0.01, r"$\sigma_n \approx 0$ — interpolation", style.RED,
     "asked to pass through two different values\nat the SAME x — which is impossible"),
    (0.25, r"$\sigma_n$ = 0.25 — the measured value", style.INK,
     "passes between them, and keeps a floor\nof uncertainty even at the data"),
    (1.00, r"$\sigma_n$ = 1.0 — too large", style.GOLD,
     "treats the data as mostly noise and\nreverts towards the prior mean"),
]

fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 3.7), sharey=True,
                         gridspec_kw=dict(wspace=0.08))

for ax, (sn, tag, colour, note) in zip(axes, SETTINGS):
    g = gpmod.GP(gpmod.matern52, ls=LS, sf=SF, sn=sn).fit(OX[:, None], OY)
    mu, sd = g.predict(xs[:, None])

    ax.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL,
                    alpha=0.16, lw=0)
    ax.plot(xs, mu, color=style.TEAL, lw=2.0, zorder=5)
    ax.plot(OX, OY, "o", ms=6.5, color=style.RED, mec="white", mew=1.1, zorder=7)

    # ring the replicate pair
    ax.annotate("two runs, same\nnominal conditions", (4.30, min(OY[2], OY[3])),
                textcoords="offset points", xytext=(0, -46), ha="center",
                fontsize=8.8, color=style.RED, zorder=9,
                arrowprops=dict(arrowstyle="->", color=style.RED, lw=1.1),
                bbox=dict(fc="white", alpha=0.88, ec="none", pad=1.8))

    # band width exactly AT an isolated observation
    i0 = int(np.argmin(np.abs(xs - 8.90)))
    ax.annotate("", xy=(8.90, mu[i0] + 2 * sd[i0]), xytext=(8.90, mu[i0] - 2 * sd[i0]),
                arrowprops=dict(arrowstyle="<->", color=style.BLUE, lw=1.4),
                zorder=9)
    style.text(ax, 0.97, 0.965, f"band at a data point = {2 * sd[i0]:.2f}",
               transform=ax.transAxes, ha="right", va="top", fontsize=9.0,
               color=style.BLUE, fontweight="bold",
               bbox=dict(fc="white", alpha=0.88, ec="none", pad=1.8))

    lml = g.log_marginal_likelihood()
    style.text(ax, 0.97, 0.865, f"log marginal lik. = {lml:,.0f}",
               transform=ax.transAxes, ha="right", va="top", fontsize=9.0,
               color=colour, fontweight="bold",
               bbox=dict(fc="white", alpha=0.88, ec="none", pad=1.8))

    ax.set_ylim(-3.1, 3.3)
    style.xlabel(ax, "reaction parameter  x")
    style.title(ax, tag, loc="left", fontsize=11.5, color=colour, pad=8)
    style.text(ax, 0.03, 0.03, note, transform=ax.transAxes, fontsize=8.8,
               color=style.INK, va="bottom",
               bbox=dict(fc="white", alpha=0.85, ec="none", pad=2.0))

    resid = np.abs(g.predict(OX[:, None])[0] - OY).mean()
    print(f"sigma_n={sn:<5} mean |residual| at the data = {resid:.3f} "
          f"| band at a data point = {2 * sd[i0]:.3f} "
          f"| log marginal lik. = {lml:8.2f}")

style.ylabel(axes[0], "yield (arb.)")
style.text(axes[1], 0.5, 1.10, r"$\ell$ and $\sigma_f$ identical in all three "
           "panels — only the assumed measurement error changes",
           transform=axes[1].transAxes, ha="center", fontsize=9.5,
           color=style.GRAY)
style.save(fig, "fig_19_sigma_n", OUT)
''')])

ALL = [FIG18, FIG19]
