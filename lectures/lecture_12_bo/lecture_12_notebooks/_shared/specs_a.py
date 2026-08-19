"""Notebook specs: the 1-D GP and acquisition-function figures."""

FIG04 = ("fig_04_posterior_collapse.ipynb",
         "Figure 4 — the posterior is not a fit, it is what survives",
         "Prior, then 2, 4 and 6 observations. Sample paths thin out, the credible "
         "band collapses, the mean sharpens. The mean posterior sd is printed on "
         "each panel so the collapse is a number, not just a picture.",
         [(None, r'''
xs = np.linspace(0, 10, 500)
OX = np.array([1.15, 2.90, 4.30, 6.10, 7.40, 8.90])
OY = land.f1d(OX)

fig, axes = plt.subplots(4, 1, figsize=(style.FIG_W_FULL, 5.6), sharex=True,
                         gridspec_kw=dict(hspace=0.22))
labels = ["prior — before any experiment", "n = 2", "n = 4", "n = 6"]

for ax, k, lab in zip(axes, [0, 2, 4, 6], labels):
    g = gpmod.GP(gpmod.matern52, ls=0.85, sf=1.0, sn=0.03)
    if k:
        g.fit(OX[:k, None], OY[:k])
    mu, sd = g.predict(xs[:, None])
    for s in g.sample(xs[:, None], n=60, seed=100 + k):
        ax.plot(xs, s, color=style.TEAL, lw=0.35, alpha=0.22, zorder=2)
    ax.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL,
                    alpha=0.13, lw=0, zorder=3)
    ax.plot(xs, mu, color=style.INK, lw=1.6, zorder=5,
            alpha=0.55 if k == 0 else 1.0)
    if k:
        ax.plot(OX[:k], OY[:k], "o", ms=6, color=style.RED,
                mec="white", mew=1.0, zorder=7)
    ax.set_ylim(-2.6, 2.6)
    ax.set_yticks([-2, 0, 2])
    ax.text(0.008, 0.90, lab, transform=ax.transAxes, va="top",
            fontsize=10, fontweight="bold",
            color=style.RED if k else style.INK)
    ax.text(0.992, 0.90, f"mean sd = {sd.mean():.3f}", transform=ax.transAxes,
            va="top", ha="right", fontsize=9.5, color=style.GRAY)

axes[-1].set_xlabel("reaction parameter  x")
axes[0].set_title("Each observation deletes functions from the ensemble — "
                  "nothing is fitted", loc="left", color=style.INK)
style.save(fig, "fig_04_posterior_collapse", OUT)
''')])

FIG00 = ("fig_00_title_gp_collapse.ipynb",
         "Figure 0 — title figure",
         "A compact two-panel version of the posterior collapse for the title "
         "slide: everything you believe before any experiment, and what six "
         "experiments leave standing.",
         [(None, r'''
xs = np.linspace(0, 10, 500)
# acquisition order, not left-to-right: a real campaign jumps around the
# domain (space-filling, then homing in) rather than sweeping monotonically
OX = np.array([4.30, 8.90, 1.15, 6.10, 2.90, 7.40])
OY = land.f1d(OX)
LS, SF, SN = 0.85, 1.0, 0.03   # Matern-5/2 length-scale, signal sd, noise sd

fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.5), sharey=True,
                         gridspec_kw=dict(wspace=0.08))
for ax, k, lab in zip(axes, [0, 6],
                      ["before any experiment", "after six experiments"]):
    g = gpmod.GP(gpmod.matern52, ls=LS, sf=SF, sn=SN)
    if k:
        g.fit(OX[:k, None], OY[:k])
    mu, sd = g.predict(xs[:, None])
    for s in g.sample(xs[:, None], n=90, seed=7 + k):
        ax.plot(xs, s, color=style.TEAL, lw=0.35, alpha=0.20)
    ax.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL,
                    alpha=0.13, lw=0)
    ax.plot(xs, mu, color=style.INK, lw=1.8, alpha=0.55 if k == 0 else 1.0)
    if k:
        ax.plot(OX[:k], OY[:k], "o", ms=7, color=style.RED, mec="white", mew=1.1)
        i = int(np.argmax(OY[:k]))
        ax.annotate("best so far", (OX[i], OY[i]), textcoords="offset points",
                    xytext=(6, 12), fontsize=9, color=style.RED)
    ax.set_ylim(-2.6, 2.6)
    ax.set_xlabel("reaction parameter  x")
    ax.set_title(lab, loc="left", fontsize=11)
    ax.text(0.98, 0.04, fr"$\ell$={LS}   $\sigma_f$={SF}   $\sigma_n$={SN}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, color=style.GRAY)
axes[0].set_ylabel("objective")
pdf_path, png_path = style.save(fig, "fig_00_title_gp_collapse", OUT)

from IPython.display import Image, display
display(Image(filename=png_path))
'''),
          ("## Animation — watching the acquisition happen\n\nThe two static "
           "panels only show the endpoints. This animation steps through the "
           "six experiments one at a time: each new observation (gold) is "
           "folded into the fit, the credible band tightens locally around "
           "it, and the sample paths that disagree with it are deleted. Same "
           "kernel and hyperparameters as above.\n", r'''
from matplotlib.animation import FuncAnimation, PillowWriter
from IPython.display import Image, display

fig_a, ax_a = plt.subplots(figsize=(5.4, 3.7))

def _draw(k):
    ax_a.clear()
    g = gpmod.GP(gpmod.matern52, ls=LS, sf=SF, sn=SN)
    if k:
        g.fit(OX[:k, None], OY[:k])
    mu, sd = g.predict(xs[:, None])
    for s in g.sample(xs[:, None], n=60, seed=7 + k):
        ax_a.plot(xs, s, color=style.TEAL, lw=0.35, alpha=0.18)
    ax_a.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL,
                      alpha=0.13, lw=0)
    ax_a.plot(xs, mu, color=style.INK, lw=1.8, alpha=0.55 if k == 0 else 1.0)
    if k:
        ax_a.plot(OX[:k - 1], OY[:k - 1], "o", ms=7, color=style.RED,
                  mec="white", mew=1.1, zorder=6)
        ax_a.plot(OX[k - 1:k], OY[k - 1:k], "o", ms=10, color=style.GOLD,
                  mec="white", mew=1.3, zorder=7)
    ax_a.set_xlim(0, 10)
    ax_a.set_ylim(-2.6, 2.6)
    ax_a.set_xlabel("reaction parameter  x")
    ax_a.set_ylabel("objective")
    title = "before any experiment" if k == 0 else f"after experiment {k}"
    ax_a.set_title(title, loc="left", fontsize=11)
    ax_a.text(0.98, 0.04, fr"$\ell$={LS}   $\sigma_f$={SF}   $\sigma_n$={SN}",
              transform=ax_a.transAxes, ha="right", va="bottom",
              fontsize=8.5, color=style.GRAY)

anim = FuncAnimation(fig_a, _draw, frames=range(7), interval=900)
gif_path = f"{OUT}/fig_00_title_gp_acquisition.gif"
anim.save(gif_path, writer=PillowWriter(fps=1))
plt.close(fig_a)
print("wrote", gif_path)
display(Image(filename=gif_path))
''')])

FIG05 = ("fig_05_acquisition_panel.ipynb",
         "Figure 5 — three ways to turn a posterior into a decision",
         "The anchor figure of the lecture. One posterior on top; PI, EI and UCB "
         "below on a shared x-axis, each with its argmax dropped as a line. "
         "Also exports three cumulative versions for a click-build in the deck.",
         [(None, r'''
xs = np.linspace(0, 10, 700)
OX = np.array([1.15, 2.90, 4.30, 6.10, 9.30])
OY = land.f1d(OX)
g = gpmod.GP(gpmod.matern52, ls=0.85, sf=1.0, sn=0.03).fit(OX[:, None], OY)
mu, sd = g.predict(xs[:, None])
fbest = OY.max()

A = {"PI":  gpmod.pi_acq(mu, sd, fbest),
     "EI":  gpmod.ei(mu, sd, fbest),
     "UCB": gpmod.ucb(mu, sd, 2.0)}
COL = {"PI": style.GRAY, "EI": style.RED, "UCB": style.BLUE}
NOTE = {"PI": "chance of beating the best — ignores by how much",
        "EI": "expected size of the improvement",
        "UCB": r"$\mu + 2\sigma$ — the plausible best case"}


def draw(which, fname):
    n = 1 + len(which)
    fig, axes = plt.subplots(n, 1, figsize=(style.FIG_W_FULL, 1.35 + 1.15 * n),
                             sharex=True, gridspec_kw=dict(hspace=0.20,
                             height_ratios=[2.1] + [1.0] * len(which)))
    ax = axes[0]
    ax.plot(xs, land.f1d(xs), "--", color=style.INK, lw=1.1, alpha=0.55,
            label="true objective (never observed)")
    ax.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL, alpha=0.16,
                    lw=0, label=r"posterior $\pm 2\sigma$")
    ax.plot(xs, mu, color=style.TEAL, lw=2.0, label="posterior mean")
    ax.plot(OX, OY, "o", ms=7, color=style.RED, mec="white", mew=1.1,
            label="experiments so far", zorder=6)
    ax.axhline(fbest, color=style.RED, lw=0.8, ls=":", alpha=0.8)
    ax.text(9.95, fbest + 0.05, r"$f^+$", color=style.RED, ha="right", fontsize=11)
    ax.set_ylabel("yield (arb.)")
    ax.legend(loc="lower center", ncol=4, fontsize=9.6, framealpha=0.92,
              facecolor="white")
    ax.set_ylim(-1.9, 2.5)

    for ax, name in zip(axes[1:], which):
        a = A[name]
        ax.plot(xs, a, color=COL[name], lw=1.8)
        ax.fill_between(xs, 0 if name != "UCB" else a.min(), a,
                        color=COL[name], alpha=0.13, lw=0)
        xstar = xs[int(np.argmax(a))]
        ax.axvline(xstar, color=COL[name], lw=1.0, ls="--")
        axes[0].axvline(xstar, color=COL[name], lw=1.0, ls="--", alpha=0.75)
        ax.plot([xstar], [a.max()], "v", ms=8, color=COL[name])
        ax.set_ylabel(name, color=COL[name], fontweight="bold")
        ax.set_yticks([])
        ax.text(0.988, 0.90, NOTE[name], transform=ax.transAxes, va="top",
                ha="right", fontsize=10.6, color=style.GRAY, bbox=dict(fc="white", alpha=0.85, ec="none", pad=2.0))
    axes[-1].set_xlabel("reaction parameter  x")
    style.save(fig, fname, OUT)
    plt.close(fig)


draw(["PI"], "fig_05a_acquisition_pi")
draw(["PI", "EI"], "fig_05b_acquisition_pi_ei")
draw(["PI", "EI", "UCB"], "fig_05_acquisition_panel")

for name, a in A.items():
    print(f"{name:4s} argmax at x = {xs[int(np.argmax(a))]:.2f}")
print("argmax of the posterior mean at x =", round(float(xs[int(np.argmax(mu))]), 2))
''')])

FIG06 = ("fig_06_ucb_beta_sweep.ipynb",
         "Figure 6 — UCB: optimism with a dial",
         "The same posterior scored with beta = 0.5, 2 and 5, built up one "
         "beta at a time for a click-build (same figsize/xlim/ylim recipe as "
         "fig. 5's PI/EI/UCB build). The argmax walks from exploitation to "
         "exploration as beta grows. beta = 2 is a one-sided ~98% bound, not "
         "95%. No title -- each row's own label is beta's value.",
         [(None, r'''
xs = np.linspace(0, 10, 700)
OX = np.array([1.15, 2.90, 4.30, 6.10, 9.30])
OY = land.f1d(OX)
g = gpmod.GP(gpmod.matern52, ls=0.85, sf=1.0, sn=0.03).fit(OX[:, None], OY)
mu, sd = g.predict(xs[:, None])

COLB = {0.5: style.INK, 2.0: style.BLUE, 5.0: style.GOLD}
A_UCB = {b: gpmod.ucb(mu, sd, b) for b in COLB}


def draw(betas, fname):
    # same figsize/xlim/ylim recipe as fig_05's draw(): n rows -> taller figure,
    # top panel pinned to fig_05's own (0, 10) x (-1.9, 2.5) box
    n = 1 + len(betas)
    fig, axes = plt.subplots(n, 1, figsize=(style.FIG_W_FULL, 1.35 + 1.15 * n),
                             sharex=True, gridspec_kw=dict(hspace=0.20,
                             height_ratios=[2.1] + [1.0] * len(betas)))
    ax = axes[0]
    ax.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL, alpha=0.16, lw=0)
    ax.plot(xs, mu, color=style.TEAL, lw=2.0)
    ax.plot(OX, OY, "o", ms=6.5, color=style.RED, mec="white", mew=1.0, zorder=6)
    style.ylabel(ax, "yield (arb.)")
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.9, 2.5)

    for axb, b in zip(axes[1:], betas):
        c = COLB[b]
        a = A_UCB[b]
        axb.plot(xs, a, color=c, lw=1.8)
        xstar = xs[int(np.argmax(a))]
        axb.axvline(xstar, color=c, lw=1.0, ls="--")
        ax.axvline(xstar, color=c, lw=1.0, ls="--", alpha=0.75)
        axb.plot([xstar], [a.max()], "v", ms=8, color=c)
        style.ylabel(axb, fr"$\beta$={b}", color=c, fontweight="bold")
        axb.set_yticks([])
        axb.set_xlim(0, 10)
    style.xlabel(axes[-1], "reaction parameter  x")
    style.save(fig, fname, OUT)
    plt.close(fig)


draw([0.5], "fig_06a_ucb_beta_0p5")
draw([0.5, 2.0], "fig_06b_ucb_beta_0p5_2p0")
draw([0.5, 2.0, 5.0], "fig_06_ucb_beta_sweep")
''')])

FIG08 = ("fig_08_hyperparameters.ipynb",
         "Figure 8 — the length-scale is a chemical claim",
         "Same six observations, three length-scales. Too short and the posterior "
         "reverts to the mean between points, so BO degenerates towards random "
         "search; too long and it oversmooths and misses the narrow optimum.",
         [(None, r'''
xs = np.linspace(0, 10, 600)
OX = np.array([1.15, 2.90, 4.30, 6.10, 7.40, 8.90])
OY = land.f1d(OX)

settings = [(0.18, "too short", "reverts to the mean between points"),
            (0.85, "about right", "interpolates, and extrapolates honestly"),
            (4.00, "too long", "oversmooths — the optimum disappears")]

fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 2.9), sharey=True,
                         gridspec_kw=dict(wspace=0.07))
for ax, (ls, tag, note) in zip(axes, settings):
    g = gpmod.GP(gpmod.matern52, ls=ls, sf=1.0, sn=0.03).fit(OX[:, None], OY)
    mu, sd = g.predict(xs[:, None])
    ax.plot(xs, land.f1d(xs), "--", color=style.INK, lw=1.0, alpha=0.45)
    ax.fill_between(xs, mu - 2 * sd, mu + 2 * sd, color=style.TEAL,
                    alpha=0.16, lw=0)
    ax.plot(xs, mu, color=style.TEAL, lw=1.9)
    ax.plot(OX, OY, "o", ms=6, color=style.RED, mec="white", mew=1.0, zorder=6)
    ax.set_ylim(-2.4, 2.6)
    ax.set_xlabel("reaction parameter  x")
    ax.set_title(fr"$\ell$ = {ls}  —  {tag}", loc="left", fontsize=10.5,
                 color=style.RED if tag != "about right" else style.INK)
    ax.text(0.03, 0.04, note, transform=ax.transAxes, fontsize=9,
            color=style.GRAY)
    print(f"ls={ls:<5} log marginal likelihood = {g.log_marginal_likelihood():8.2f}")
axes[0].set_ylabel("yield (arb.)")
axes[0].plot([], [], "--", color=style.INK, alpha=0.45, label="truth")
axes[0].legend(loc="upper left", fontsize=8.5)
style.save(fig, "fig_08_hyperparameters", OUT)
''')])

FIG10 = ("fig_10_noise_taxonomy.ipynb",
         "Figure 10 — three different things get called noise",
         "Homoscedastic output noise, heteroscedastic output noise, and input "
         "noise. Chemists conflate these constantly; they need different fixes.",
         [(None, r'''
rng = np.random.default_rng(3)
x = np.linspace(0, 10, 13)
ytrue = land.f1d(x)
xs = np.linspace(0, 10, 400)

fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 3.1), sharey=True,
                         gridspec_kw=dict(wspace=0.07))

# 1. homoscedastic
ax = axes[0]
s = 0.18
ax.plot(xs, land.f1d(xs), color=style.INK, lw=1.2, alpha=0.5)
ax.errorbar(x, ytrue + rng.normal(0, s, x.size), yerr=s, fmt="o", ms=5,
            color=style.TEAL, ecolor=style.TEAL, elinewidth=1.1, capsize=2.5)
ax.set_title("homoscedastic", loc="left", color=style.TEAL, pad=26)
ax.text(0.0, 1.02, "constant sd everywhere → a standard GP handles it,\n"
        "just do not set $\\sigma_n\\approx 0$", transform=ax.transAxes,
        fontsize=9.2, color=style.GRAY, va="bottom")

# 2. heteroscedastic
ax = axes[1]
s2 = 0.05 + 0.30 * (x / 10) ** 2
ax.plot(xs, land.f1d(xs), color=style.INK, lw=1.2, alpha=0.5)
ax.errorbar(x, ytrue + rng.normal(0, s2), yerr=s2, fmt="o", ms=5,
            color=style.GOLD, ecolor=style.GOLD, elinewidth=1.1, capsize=2.5)
ax.set_title("heteroscedastic", loc="left", color=style.GOLD, pad=26)
ax.text(0.0, 1.02, "sd grows with x — decomposition at high T\n"
        "→ needs a heteroscedastic GP", transform=ax.transAxes,
        fontsize=9.2, color=style.GRAY, va="bottom")

# 3. input noise
ax = axes[2]
ax.plot(xs, land.f1d(xs), color=style.INK, lw=1.2, alpha=0.5)
xj = x + rng.normal(0, 0.45, x.size)
ax.errorbar(x, land.f1d(xj), xerr=0.45, fmt="o", ms=5, color=style.RED,
            ecolor=style.RED, elinewidth=1.1, capsize=2.5)
ax.set_title("input noise", loc="left", color=style.RED, pad=26)
ax.text(0.03, 0.05, "you cannot SET x exactly\n→ pump gives 1.05 not 1.00 equiv\n"
        "→ a different problem (Golem)", transform=ax.transAxes,
        fontsize=8.8, color=style.GRAY, va="bottom")

for ax in axes:
    ax.set_xlabel("reaction parameter  x")
axes[0].set_ylabel("measured yield")
style.save(fig, "fig_10_noise_taxonomy", OUT)
''')])

ALL = [FIG00, FIG04, FIG05, FIG06, FIG08, FIG10]
