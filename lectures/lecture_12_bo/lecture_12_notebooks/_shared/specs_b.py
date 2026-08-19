"""Notebook specs: the 2-D landscape, noise ablation, ARD, encoding, MOBO, batch."""

FIG02 = ("fig_02_why_obvious_fails.ipynb",
         "Figure 2 — why the obvious approaches fail",
         "Five strategies, twenty experiments each, one landscape, each as "
         "its own square panel (axes generic: x1, x2 -- this is about the "
         "shape of the search, not the specific chemistry). No panel titles "
         "or method notes on the plots themselves -- just the best result "
         "found and where it is. Each strategy also gets a GIF of its "
         "twenty points landing in the order they were actually acquired. "
         "One-factor-at-a-time, grid, a classical DOE (face-centred CCD + "
         "quadratic response surface), finite-difference gradient ascent, "
         "and random search. Random search is included because it is the "
         "honest baseline any BO result must beat; DOE is included because "
         "it is the strongest of the five, and the one BO has to beat in "
         "fig. 15.",
         [(None, r'''
from matplotlib.animation import FuncAnimation, PillowWriter

style.SHOW_TEXT = True   # False -> drop even the best-result label and the
                         # x1/x2 axis labels, for ungrouping into pptx shapes

T, C, Z = land.mesh()
xstar, zstar = land.optimum()
print("true optimum:", np.round(xstar, 2), "yield", round(zstar, 1))
BUDGET = 20
rng = np.random.default_rng(0)


def best_of(pts):
    pts = np.asarray(pts)
    yv = land.yield_surface(pts)
    i = int(np.argmax(yv))
    return pts[i], yv[i], i


def base(ax):
    """Contour + true optimum, shared by every static and animated panel."""
    cs = ax.contourf(T, C, Z, levels=18, cmap="BuGn", alpha=0.9)
    ax.contour(T, C, Z, levels=8, colors="white", linewidths=0.4, alpha=0.6)
    ax.plot(*xstar, "*", ms=15, color=style.RED, mec="white", mew=0.8, zorder=8)
    ax.set_xlim(*land.BOUNDS[0]); ax.set_ylim(*land.BOUNDS[1])
    ax.set_box_aspect(1)
    style.xlabel(ax, "x1")
    style.ylabel(ax, "x2")
    return cs


def best_label(ax, pts):
    pts = np.asarray(pts)
    _, best, i = best_of(pts)
    style.text(ax, 0.03, 0.03, f"best {best:.0f}%\nfound at run {i + 1} of {len(pts)}",
               transform=ax.transAxes, fontsize=10, color=style.INK,
               va="bottom", fontweight="bold", zorder=10,
               bbox=dict(fc="white", alpha=0.92, ec="none", pad=2.2))


def static_plot(name, pts, colour, predict=None):
    """One square panel per strategy: contour, path, points, best-result label."""
    pts = np.asarray(pts)
    fig, ax = plt.subplots(figsize=(4.3, 4.3))
    cs = base(ax)
    if predict is not None:
        ax.contour(T, C, predict(T, C), levels=7, colors=colour, linewidths=0.9,
                  linestyles="--", alpha=0.9)
    ax.plot(pts[:, 0], pts[:, 1], "-", color=colour, lw=0.9, alpha=0.55)
    ax.scatter(pts[:, 0], pts[:, 1], s=32, c=colour, edgecolor="white",
              linewidth=0.7, zorder=6)
    best_label(ax, pts)
    cb = fig.colorbar(cs, ax=ax, fraction=0.046, pad=0.04)
    style.cbar_label(cb, "true yield / %")
    cb.outline.set_visible(False)
    style.save(fig, f"fig_02_{name}", OUT)
    plt.close(fig)


def animate(name, pts, colour):
    """GIF: the strategy's own twenty points landing in acquisition order."""
    pts = np.asarray(pts)
    fig_a, ax_a = plt.subplots(figsize=(4.3, 4.3))

    def _draw(k):
        ax_a.clear()
        base(ax_a)
        if k:
            shown = pts[:k]
            if k > 1:
                ax_a.plot(shown[:, 0], shown[:, 1], "-", color=colour, lw=0.8,
                         alpha=0.45)
                ax_a.scatter(shown[:-1, 0], shown[:-1, 1], s=30, c=colour,
                            edgecolor="white", linewidth=0.7, zorder=6)
            ax_a.scatter(shown[-1:, 0], shown[-1:, 1], s=60, c=style.GOLD,
                        edgecolor="white", linewidth=1.0, zorder=7)
            best_label(ax_a, shown)

    anim = FuncAnimation(fig_a, _draw, frames=range(len(pts) + 1), interval=400)
    gif_path = f"{OUT}/fig_02_{name}_acquisition.gif"
    anim.save(gif_path, writer=PillowWriter(fps=2.5))
    plt.close(fig_a)
    print("wrote", gif_path)


# --- 1. one factor at a time -------------------------------------------------
# walks up one axis, turns once, stops -- misses the curved ridge entirely
c0 = 2.0
ts = np.linspace(*land.BOUNDS[0], 10)
leg1 = [[t, c0] for t in ts]
tbest = ts[int(np.argmax(land.yield_surface(np.array(leg1))))]
cs_ = np.linspace(*land.BOUNDS[1], 10)
leg2 = [[tbest, c] for c in cs_]
ofat = np.array(leg1 + leg2)

# --- 2. grid ------------------------------------------------------------------
# regular, and mostly in bad regions -- 6 factors x 5 levels = 15,625 runs
gt = np.linspace(land.BOUNDS[0, 0] + 8, land.BOUNDS[0, 1] - 8, 5)
gc = np.linspace(land.BOUNDS[1, 0] + 0.4, land.BOUNDS[1, 1] - 0.4, 4)
grid = np.array([[a, b] for a in gt for b in gc])

# --- 3. DOE -- central composite design + quadratic RSM ----------------------
# a face-centred design + fitted quadratic (see _shared/doe.py and fig. 15)
res_doe = doemod.run(land.BOUNDS, land.yield_surface, BUDGET, seed=0)
doe_pts = res_doe["X"]

# --- 4. finite-difference gradient ascent ------------------------------------
# starts well off the peak, on the correct side of the deceptive bump so it
# climbs onto the ridge instead of getting trapped; d+1 runs per step means
# only ~6 real moves for the budget, so it still falls short of the optimum
NOISE = 1.0
p = np.array([95.0, 0.6])
path = [p.copy()]
step = np.array([18.0, 1.1])
h = np.array([4.0, 0.25])
while len(path) < BUDGET - 2:
    fp = land.f(p) + rng.normal(0, NOISE)
    g = np.zeros(2)
    for j in range(2):
        q = p.copy(); q[j] += h[j]
        q = np.clip(q, land.BOUNDS[:, 0], land.BOUNDS[:, 1])
        path.append(q.copy())
        g[j] = (land.f(q) + rng.normal(0, NOISE) - fp) / h[j]
    n = np.linalg.norm(g)
    if n < 1e-9:
        break
    p = np.clip(p + step * g / n, land.BOUNDS[:, 0], land.BOUNDS[:, 1])
    path.append(p.copy())
gradient = np.array(path)[:BUDGET]

# --- 5. random ----------------------------------------------------------------
# the honest baseline -- always compare against it
rand = rng.uniform(land.BOUNDS[:, 0], land.BOUNDS[:, 1], size=(BUDGET, 2))

STRATEGIES = [
    ("ofat", ofat, style.RED, None),
    ("grid", grid, style.INK, None),
    ("doe", doe_pts, style.PLUM, res_doe["predict"]),
    ("gradient", gradient, style.GOLD, None),
    ("random", rand, style.TEAL, None),
]

for name, pts, colour, predict in STRATEGIES:
    static_plot(name, pts, colour, predict)
    animate(name, pts, colour)
''')])

FIG15 = ("fig_15_grid_doe_bo.ipynb",
         "Figure 15 — the same twenty experiments, spent three ways",
         "Grid, a face-centred central composite design with a fitted quadratic "
         "response surface, and Bayesian optimization. Identical budget, "
         "identical landscape.\n\n"
         "**The honest finding:** in two dimensions with twenty runs, all three "
         "get close. A grid is hard to beat on a small, cheap, low-dimensional "
         "problem — which is exactly what the lecture says. The difference BO "
         "makes is HOW FAST it gets there, shown in panel d, and that gap widens "
         "with every factor you add. For real benchmarks see Felton et al., "
         "Chemistry-Methods 2021, 1, 116-122.",
         [(None, r'''
style.SHOW_TEXT = True   # False -> clean panels (no titles/captions/labels)
                         # for ungrouping the PDF into editable pptx shapes

T, C, Z = land.mesh()
xstar, zstar = land.optimum()
BUDGET = 20
lo, hi = land.BOUNDS[:, 0], land.BOUNDS[:, 1]
print("true optimum", np.round(xstar, 1), "=", round(zstar, 1), "%")

fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 3.6), sharey=True,
                         gridspec_kw=dict(wspace=0.15))


def base(ax):
    cs = ax.contourf(T, C, Z, levels=18, cmap="BuGn", alpha=0.9)
    ax.contour(T, C, Z, levels=8, colors="white", linewidths=0.4, alpha=0.6)
    ax.plot(*xstar, "*", ms=15, color=style.RED, mec="white", mew=0.8, zorder=8)
    style.xlabel(ax, land.LABELS[0])
    ax.set_xticks([70, 100, 130])
    return cs


def running_best(pts):
    return np.maximum.accumulate(land.yield_surface(np.asarray(pts)))


# ---- a. grid ---------------------------------------------------------------
gt = np.linspace(lo[0] + 8, hi[0] - 8, 5)
gc = np.linspace(lo[1] + 0.4, hi[1] - 0.4, 4)
grid = np.array([[a, b] for a in gt for b in gc])
cs = base(axes[0])
axes[0].scatter(grid[:, 0], grid[:, 1], s=28, c=style.INK, edgecolor="white",
                linewidth=0.7, zorder=6)
b0 = land.yield_surface(grid).max()
style.title(axes[0], f"a · grid — {b0:.0f}%", loc="left", color=style.INK,
            fontsize=10.5)
style.ylabel(axes[0], land.LABELS[1])

# ---- b. face-centred CCD + quadratic RSM (see _shared/doe.py) --------------
res_doe = doemod.run(land.BOUNDS, land.yield_surface, BUDGET, seed=0)
doe_pts, yv, ZH = res_doe["X"], res_doe["y"], res_doe["predict"](T, C)
cs = base(axes[1])
axes[1].contour(T, C, ZH, levels=7, colors=style.RED, linewidths=0.8,
                linestyles="--", alpha=0.95)
axes[1].scatter(doe_pts[:, 0], doe_pts[:, 1], s=28, c=style.INK, edgecolor="white",
                linewidth=0.7, zorder=6)
i = np.unravel_index(np.argmax(ZH), ZH.shape)
axes[1].plot(T[i], C[i], "P", ms=10, color=style.RED, mec="white", mew=0.8,
             zorder=9)
b1 = yv.max()
style.title(axes[1], f"b · CCD + quadratic — {b1:.0f}%", loc="left",
            color=style.INK, fontsize=10.5)
style.text(axes[1], 0.03, 0.04, "dashed: the fitted quadratic\ncannot bend along the "
           "ridge,\nso its predicted optimum (+)\nis in the wrong place",
           transform=axes[1].transAxes, fontsize=8.4, color=style.INK,
           va="bottom", bbox=dict(fc="white", alpha=0.85, ec="none", pad=2.0))
err = zstar - land.f([T[i], C[i]])
print(f"RSM predicted optimum is worth {land.f([T[i], C[i]]):.1f}% "
      f"— {err:.1f} points below the true optimum")

# ---- c. BO -----------------------------------------------------------------
gx = np.linspace(*land.BOUNDS[0], 60)
gy = np.linspace(*land.BOUNDS[1], 60)
cand = np.array([[a, b] for a in gx for b in gy])
BO_SEEDS = 12
runs = [gpmod.bo_loop(land.f, land.BOUNDS, n_init=6, n_iter=BUDGET - 6,
                      acq="ei", noise=0.0, seed=s, grid=cand,
                      ls=[20.0, 1.2], sf=28.0) for s in range(BO_SEEDS)]
curves = np.array([np.maximum.accumulate(r["ytrue"]) for r in runs])
res = runs[0]                      # panel c shows seed 0, stated in the caption
P = res["X"]
cs = base(axes[2])
axes[2].plot(P[6:, 0], P[6:, 1], "-", color=style.RED, lw=0.7, alpha=0.28)
axes[2].scatter(P[:6, 0], P[:6, 1], s=30, marker="s", c=style.INK,
                edgecolor="white", linewidth=0.7, zorder=6, label="6 seeds")
axes[2].scatter(P[6:, 0], P[6:, 1], s=28, c=style.RED, edgecolor="white",
                linewidth=0.7, zorder=7, label="14 by EI")
b2 = res["ytrue"].max()
style.title(axes[2], f"c · Bayesian optimization — {b2:.0f}%", loc="left",
            color=style.RED, fontsize=10.5)
style.text(axes[2], 0.03, 0.04, "one run (seed 0);\npanel d shows all 12",
           transform=axes[2].transAxes, fontsize=8.4, color=style.INK,
           va="bottom", bbox=dict(fc="white", alpha=0.85, ec="none", pad=2.0))
style.legend(axes[2], loc="upper left", fontsize=8.2, framealpha=0.9,
             facecolor="white")

cb = fig.colorbar(cs, ax=axes, fraction=0.016, pad=0.012)
style.cbar_label(cb, "true yield / %")
cb.outline.set_visible(False)
style.save(fig, "fig_15_grid_doe_bo", OUT)
plt.close(fig)

# ---- separate figure: sequential vs batch ----------------------------------
fig2, ax = plt.subplots(figsize=(6.2, 3.6))
bo_curve = np.median(curves, axis=0)
q1, q3 = np.percentile(curves, [25, 75], axis=0)
nn = np.arange(1, BUDGET + 1)
ax.fill_between(nn, q1, q3, color=style.RED, alpha=0.15, lw=0)
ax.plot(nn, bo_curve, color=style.RED, lw=2.3,
        label=f"BO — sequential (median of {BO_SEEDS} runs)")
ax.axhline(b0, color=style.INK, lw=1.4, ls="--",
           label=f"grid — batch, result at run 20 ({b0:.0f}%)")
ax.plot([BUDGET], [b0], "o", ms=8, color=style.INK)
ax.axhline(b1, color=style.GOLD, lw=1.4, ls="--",
           label=f"CCD + quadratic — batch ({b1:.0f}%)")
ax.plot([BUDGET], [b1], "o", ms=8, color=style.GOLD)
ax.axhline(zstar, color=style.INK, ls=":", lw=1.0)
style.text(ax, BUDGET, zstar + 1.2, "true optimum", ha="right", fontsize=8.6,
           color=style.INK)
cross = np.where(bo_curve >= b0)[0]
if len(cross):
    n_x = int(cross[0]) + 1
    ax.plot([n_x], [bo_curve[n_x - 1]], "o", ms=10, mfc="none", mec=style.RED,
            mew=2.0, zorder=8)
    style.annotate(ax, f"BO reaches the grid's answer\nat experiment {n_x}",
                   (n_x, bo_curve[n_x - 1]), textcoords="offset points",
                   xytext=(-10, -46), fontsize=8.8, color=style.RED, ha="right",
                   arrowprops=dict(arrowstyle="->", color=style.RED, lw=1.0))
    print(f"BO reaches the grid's best after {n_x} of 20 experiments (median)")
style.xlabel(ax, "experiment number")
style.ylabel(ax, "best true yield so far / %")
ax.set_ylim(0, 102)
ax.set_xlim(1, BUDGET + 0.5)
style.legend(ax, loc="lower right", fontsize=8.4)
style.title(ax, "a batch design tells you at the end; BO tells you as it goes",
            loc="left", fontsize=10.5)
style.save(fig2, "fig_15d_sequential_vs_batch", OUT)


''')])

FIG11 = ("fig_11_noise_ablation.ipynb",
         "Figure 11 — get the noise wrong and the outcome becomes a lottery",
         "Two BO campaigns, same landscape, same seeds, same true measurement "
         "noise (sd = 6 percentage points). One is told the noise is ~0, the "
         "other is told the truth.\n\n"
         "**Two honest findings.** First, under noise the best *observed* yield "
         "overstates what those conditions really give — for both settings, "
         "because the maximum of noisy readings is biased upwards. Second, and "
         "this is the one that matters: telling the GP sigma_n ~ 0 does not just "
         "cost a couple of points on average, it makes the result *wildly "
         "variable*. The same consistency argument as the human benchmark.",
         [("## Setup\n\n"
           "28 random seeds each, 6 seed experiments, 14 BO iterations. Per run "
           "we record what a chemist would report (highest observed yield), what "
           "those conditions are actually worth, and what the *model* would "
           "recommend (argmax of the posterior mean).",
           r'''
style.SHOW_TEXT = True   # False -> clean panels (no titles/captions/labels)
                         # for ungrouping the PDF into editable pptx shapes

NOISE = 6.0
N_SEEDS = 28
N_ITER = 14
gx = np.linspace(*land.BOUNDS[0], 36)
gy = np.linspace(*land.BOUNDS[1], 36)
cand = np.array([[a, b] for a in gx for b in gy])
_, zstar = land.optimum()
LS, SF = [20.0, 1.2], 28.0

res = {}
for tag, assumed in [(r"told $\sigma_n \approx 0$", 0.05),
                     (r"told the measured $\sigma_n$", NOISE)]:
    rep, true_at_rep, pick = [], [], []
    for s in range(N_SEEDS):
        r = gpmod.bo_loop(land.f, land.BOUNDS, n_init=6, n_iter=N_ITER, acq="ei",
                          noise=NOISE, assumed_sn=assumed, seed=s, grid=cand,
                          ls=LS, sf=SF)
        i = int(np.argmax(r["y"]))
        rep.append(r["y"][i]); true_at_rep.append(r["ytrue"][i])
        g = gpmod.GP(gpmod.matern52, ls=LS, sf=SF,
                     sn=max(assumed, 1e-4)).fit(r["X"], r["y"])
        mu, _ = g.predict(cand)
        pick.append(land.f(cand[int(np.argmax(mu))]))
    res[tag] = {k: np.array(v) for k, v in
                dict(rep=rep, true=true_at_rep, pick=pick).items()}
    d = res[tag]
    print(f"{tag:32s} reported {np.median(d['rep']):5.1f} | actually worth "
          f"{np.median(d['true']):5.1f} | optimism gap {np.median(d['rep']-d['true']):4.1f}")
    print(f"{'':32s} model's pick: median {np.median(d['pick']):5.1f}  "
          f"mean {d['pick'].mean():5.1f}  sd {d['pick'].std():4.1f}  "
          f"worst {d['pick'].min():5.1f}")
print("true optimum:", round(zstar, 1))
'''),
          (None, r'''
fig, axes = plt.subplots(1, 2, figsize=(style.FIG_W_FULL, 3.6),
                         gridspec_kw=dict(wspace=0.26, width_ratios=[1.1, 1]))
cols = [style.RED, style.TEAL]
rng = np.random.default_rng(0)

# ---- left: distribution of what the model actually recommends -----------------
ax = axes[0]
for gi, ((tag, d), c) in enumerate(zip(res.items(), cols)):
    v = d["pick"]
    ax.scatter(gi + rng.uniform(-0.11, 0.11, v.size), v, s=26, color=c,
               alpha=0.55, edgecolor="none", zorder=4)
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    ax.add_patch(plt.Rectangle((gi - 0.22, q1), 0.44, q3 - q1, fc="none",
                              ec=c, lw=1.4, zorder=5))
    ax.plot([gi - 0.22, gi + 0.22], [med, med], color=c, lw=2.6, zorder=6)
    style.text(ax, gi + 0.30, med, f"median {med:.0f}%", fontsize=9, color=c,
               va="center", fontweight="bold")
    style.text(ax, gi, 36.0, f"sd {v.std():.1f}   worst {v.min():.0f}%", ha="center",
               fontsize=10.0, color=c, fontweight="bold",
               bbox=dict(fc="white", alpha=0.85, ec="none", pad=2.0))
ax.axhline(zstar, color=style.INK, ls=":", lw=1.0)
style.text(ax, 1.45, zstar + 1.2, "true optimum", ha="right", fontsize=9,
           color=style.INK)
ax.set_xticks([0, 1]); ax.set_xticklabels(list(res), fontsize=11)
ax.set_xlim(-0.45, 1.55)
ax.set_ylim(33, 100)
style.ylabel(ax, "true yield at the model's recommended conditions / %",
             fontsize=9.5)
style.title(ax, "what the model ends up recommending", loc="left",
            fontsize=11.0, pad=18)
style.text(ax, 0.5, 1.005, "one dot = one campaign", transform=ax.transAxes,
           ha="center", fontsize=9.0, color=style.GRAY, va="bottom")

# ---- right: the optimism gap, which is there either way -----------------------
ax = axes[1]
W = 0.30
for gi, ((tag, d), c) in enumerate(zip(res.items(), cols)):
    for ki, (k, al, lab) in enumerate([("rep", 0.85, "reported"),
                                       ("true", 0.35, "actually worth")]):
        x = gi + (ki - 0.5) * W
        med = np.median(d[k])
        q1, q3 = np.percentile(d[k], [25, 75])
        ax.bar(x, med, width=W * 0.86, color=c, alpha=al, edgecolor=c, lw=1.0)
        ax.errorbar(x, med, yerr=[[med - q1], [q3 - med]], fmt="none",
                    ecolor=style.INK, elinewidth=1.0, capsize=3, alpha=0.65)
        style.text(ax, x, med + 0.8, f"{med:.0f}", ha="center", fontsize=9,
                   color=style.INK)
    gap = np.median(d["rep"] - d["true"])
    style.annotate(ax, f"overstated by {gap:.1f}", (gi, 99.5), ha="center",
                   fontsize=9.5, color=c, fontweight="bold")
ax.axhline(zstar, color=style.INK, ls=":", lw=1.0)
ax.set_xticks([0, 1]); ax.set_xticklabels(list(res), fontsize=11)
ax.set_ylim(70, 104)
style.ylabel(ax, "yield / %")
style.title(ax, "your reported best overstates reality — either way", loc="left",
            fontsize=10.5)
hand = [plt.Rectangle((0, 0), 1, 1, fc=style.GRAY, alpha=a_, ec=style.GRAY)
        for a_ in (0.85, 0.35)]
style.legend(ax, hand, ["highest observed yield", "what it is actually worth"],
             fontsize=8.6, loc="upper center", bbox_to_anchor=(0.5, -0.10),
             ncol=2, handlelength=1.1)
style.save(fig, "fig_11_noise_ablation", OUT)
''')])

FIG09 = ("fig_09_ard_relevance.ipynb",
         "Figure 9 — ARD as a free sensitivity analysis",
         "One length-scale per input dimension. A large fitted length-scale "
         "means the model barely uses that factor. Here the landscape is "
         "synthetic so the answer is known in advance and ARD can be checked. "
         "The last cell shows the three-line change needed to run the same "
         "analysis on the real EDBO direct-arylation dataset.",
         [("## A 5-factor surface where we decide in advance which factors matter\n\n"
           "Factors 1 and 2 drive the response strongly, factor 3 weakly, and "
           "factors 4 and 5 not at all. If ARD works, the fitted inverse "
           "length-scales should recover that ordering.\n\n"
           "**Inputs are scaled to [0,1] before fitting.** Length-scales carry the "
           "units of their input, so comparing a length-scale in °C against one in "
           "mol% is meaningless unless you normalise first.",
           r'''
rng = np.random.default_rng(0)
D = 5
NAMES = ["temperature", "catalyst loading", "residence time", "stir rate", "vial lot"]
TRUE_W = np.array([1.0, 0.85, 0.30, 0.0, 0.0])


def f5(U):
    """U in [0,1]^5. Only the first three columns do anything."""
    U = np.atleast_2d(U)
    z = (0.95 * np.exp(-((U[:, 0] - 0.65) ** 2) / 0.06)
         + 0.80 * np.exp(-((U[:, 1] - 0.40) ** 2) / 0.08)
         + 0.55 * U[:, 0] * U[:, 1]
         + 0.22 * np.sin(3.0 * U[:, 2]))
    return 100.0 * z / 2.2


N = 160
U = rng.random((N, D))
y = f5(U) + rng.normal(0, 1.5, N)
print("n =", N, " yield range", round(y.min(), 1), "-", round(y.max(), 1))
'''),
          ("## Fit hyperparameters by maximising the log marginal likelihood\n\n"
           "Random restarts on a log grid — crude, transparent, and fast enough "
           "at this size. A real package uses gradients.",
           r'''
(ls, sf, sn), lml = gpmod.fit_hypers_ard(U, y, D, kernel=gpmod.matern52,
                                         seed=1, n_restarts=250)
print("fitted length-scales :", np.round(ls, 3))
print("fitted output scale  :", round(sf, 3))
print("fitted noise sd      :", round(sn, 3))
print("log marginal lik.    :", round(lml, 2))
relevance = 1.0 / ls
relevance = relevance / relevance.max()
for n_, r_, t_ in zip(NAMES, relevance, TRUE_W):
    print(f"  {n_:18s} ARD relevance {r_:5.2f}   (built in: {t_:.2f})")
'''),
          (None, r'''
order = np.argsort(relevance)
fig, ax = plt.subplots(figsize=(6.0, 3.2))
cols = [style.RED if relevance[i] > 0.5 else
        (style.GOLD if relevance[i] > 0.2 else style.GRAY) for i in order]
ax.barh(np.arange(D), relevance[order], color=cols, height=0.62)
ax.plot(TRUE_W[order] / TRUE_W.max(), np.arange(D), "o", ms=6,
        color=style.INK, mfc="white", mew=1.4, label="built into the surface")
ax.set_yticks(np.arange(D))
ax.set_yticklabels([NAMES[i] for i in order])
ax.set_xlabel(r"ARD relevance,  $(1/\ell)$ normalised   —   inputs scaled to [0,1]")
ax.set_xlim(0, 1.12)
ax.legend(loc="lower right", fontsize=8.8)
ax.set_title("the campaign tells you which factors mattered", loc="left",
             fontsize=10.5)
for i, k in enumerate(order):
    ax.text(relevance[k] + 0.02, i, f"{relevance[k]:.2f}", va="center",
            fontsize=9, color=style.GRAY)
style.save(fig, "fig_09_ard_relevance", OUT)
'''),
          ("## The same analysis on the real dataset\n\n"
           "`_shared/edbo_data.py` downloads the 1,728-experiment direct-arylation "
           "dataset (reaction 3 of Shields et al. 2021). One-hot the three "
           "categorical columns, scale the two continuous ones to [0,1], and call "
           "the same fitter. Runs only if there is network access.",
           r'''
import edbo_data
if edbo_data.available():
    df = edbo_data.load()
    print(df.shape, "rows loaded")
    cats = ["Base_SMILES", "Ligand_SMILES", "Solvent_SMILES"]
    Xr = [df[c].astype("category").cat.codes.to_numpy()[:, None] for c in cats]
    Xr = np.hstack(Xr).astype(float)
    Xr = Xr / np.maximum(Xr.max(0), 1)
    con = df[["Concentration", "Temp_C"]].to_numpy(float)
    con = (con - con.min(0)) / (con.max(0) - con.min(0))
    Ur = np.hstack([Xr, con])
    yr = df["yield"].to_numpy(float)
    sub = np.random.default_rng(0).choice(len(Ur), 400, replace=False)
    (lsr, sfr, snr), lmlr = gpmod.fit_hypers_ard(Ur[sub], yr[sub], Ur.shape[1],
                                                 seed=2, n_restarts=250)
    rel = (1 / lsr) / (1 / lsr).max()
    for n_, r_ in zip(["base", "ligand", "solvent", "concentration",
                       "temperature"], rel):
        print(f"  {n_:14s} ARD relevance {r_:5.2f}")
else:
    print("No network — skipping the real-data fit.")
    print("Run this cell on a connected machine to reproduce it.")
''')])

FIG12 = ("fig_12_categorical_encoding.ipynb",
         "Figure 12 — your encoding matters more than your acquisition function",
         "One-hot encoding makes every ligand exactly as far from every other. "
         "A descriptor encoding puts chemically similar ligands close together, "
         "so information transfers between them. Ligand SMILES are verbatim from "
         "the EDBO direct-arylation dataset.",
         [("## The ligands\n\n"
           "Six of the twelve phosphines in the dataset, with SMILES taken "
           "verbatim from `experiment_index.csv`. If the notebook can reach the "
           "network it uses all twelve.\n\n"
           "> The descriptors below are simple countable features parsed straight "
           "from the SMILES string — heavy-atom count, ring-bond count, aromatic "
           "fraction and so on. **Shields et al. use DFT-derived steric and "
           "electronic descriptors, which are better.** The point of this figure "
           "is the contrast with one-hot, and better descriptors only strengthen "
           "it.",
           r'''
import edbo_data as ed

lig = dict(ed.CACHED_LIGANDS)
if ed.available():
    df = ed.load()
    uniq = list(dict.fromkeys(df["Ligand_SMILES"]))
    known = {v: k for k, v in ed.CACHED_LIGANDS.items()}
    lig = {known.get(s, f"ligand {i+1}"): s for i, s in enumerate(uniq)}
    print(f"loaded {len(lig)} ligands from the full dataset")
else:
    print(f"offline — using the {len(lig)} cached ligands")

names, Dmat, keys = ed.descriptor_matrix(lig)
print("descriptors:", keys)
for n_, row in zip(names, Dmat):
    print(f"  {n_:14s}", {k: int(v) for k, v in zip(keys, row)})
'''),
          (None, r'''
OH = ed.onehot_matrix(names)
d_oh = ed.pairwise(OH)
d_de = ed.pairwise(ed.zscore(Dmat))
scores, var, _ = ed.pca_2d(Dmat)

fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.15),
                         gridspec_kw=dict(wspace=0.42, width_ratios=[1, 1.15]))

im = axes[0].imshow(d_oh, cmap="BuGn", vmin=0, vmax=max(d_oh.max(), d_de.max()))
axes[0].set_xticks(range(len(names))); axes[0].set_yticks(range(len(names)))
axes[0].set_xticklabels(names, rotation=90, fontsize=8.5)
axes[0].set_yticklabels(names, fontsize=8.5)
axes[0].set_title("one-hot: every pair\nexactly as far apart", loc="left",
                  fontsize=10.5, color=style.RED)
for sp in axes[0].spines.values():
    sp.set_visible(False)
off = d_oh[~np.eye(len(names), dtype=bool)]

ax = axes[1]
ax.scatter(scores[:, 0], scores[:, 1], s=85, c=style.TEAL, edgecolor="white",
           linewidth=1.1, zorder=5)
for (x, y), n_ in zip(scores, names):
    ax.annotate(n_, (x, y), textcoords="offset points", xytext=(8, 5),
                fontsize=9.0, color=style.INK)
ax.set_xlabel(f"PC1 ({100*var[0]:.0f}% of variance)")
ax.set_ylabel(f"PC2 ({100*var[1]:.0f}%)")
ax.set_title("descriptors: chemical\nfamilies separate", loc="left",
             fontsize=10.5, color=style.TEAL)
ax.margins(0.30)
style.save(fig, "fig_12_categorical_encoding", OUT)
print("one-hot: every off-diagonal distance =", round(off.mean(), 4),
      "  sd =", round(off.std(), 6), " (identical by construction)")
print("descriptor distances range", round(d_de[d_de > 0].min(), 2), "-",
      round(d_de.max(), 2))
''')])

FIG16 = ("fig_16_pareto_front.ipynb",
         "Figure 16 — nobody in chemistry wants one number",
         "Yield against selectivity over a simulated condition set. Dominance, "
         "the Pareto front, and the hypervolume that EHVI tries to grow.",
         [(None, r'''
rng = np.random.default_rng(4)
n = 30
u = rng.random((n, 2))
yield_ = 100 * (0.35 + 0.6 * np.exp(-((u[:, 0] - 0.7) ** 2) / 0.10)
                * (0.5 + 0.5 * u[:, 1])) + rng.normal(0, 2.0, n)
selec = 100 * (0.95 - 0.55 * np.exp(-((u[:, 0] - 0.75) ** 2) / 0.16)
               * (0.4 + 0.6 * u[:, 1])) + rng.normal(0, 2.0, n)
Y = np.column_stack([np.clip(yield_, 0, 100), np.clip(selec, 0, 100)])


def pareto(Y):
    keep = np.ones(len(Y), bool)
    for i in range(len(Y)):
        if keep[i]:
            dom = np.all(Y >= Y[i], axis=1) & np.any(Y > Y[i], axis=1)
            if dom.any():
                keep[i] = False
    return keep


def front_of(Y):
    keep = pareto(Y)
    order = np.argsort(Y[keep, 0])
    return Y[keep][order]


def hypervolume(F, ref):
    hv, prev_y = 0.0, ref[1]
    for px, py in F[::-1]:
        hv += max(px - ref[0], 0) * max(py - prev_y, 0)
        prev_y = max(prev_y, py)
    return hv


front = pareto(Y)
F = front_of(Y)
REF = np.array([40.0, 40.0])
hv = hypervolume(F, REF)

# a hypothetical new experiment, better than the current front -- this is
# exactly what EHVI scores: how much would running THIS condition grow the
# shaded area? Add it to the set and rebuild the front to find out.
NEW = np.array([62.0, 85.0])
F2 = front_of(np.vstack([Y, NEW]))
hv2 = hypervolume(F2, REF)
gain = hv2 - hv

fig, ax = plt.subplots(figsize=(5.7, 4.1))
# draw the extended (with-NEW) hypervolume first, in gold, then the current
# hypervolume on top, in red -- since the extended region always contains the
# current one, only the genuinely NEW area is left showing gold: that sliver
# *is* the hypervolume improvement
ax.fill_between(F2[:, 0], REF[1], F2[:, 1], step="pre", color=style.GOLD,
                alpha=0.30, lw=0, label=f"hypervolume gain (+{gain:,.0f})")
ax.step(F2[:, 0], F2[:, 1], where="pre", color=style.GOLD, lw=1.2, ls="--",
        alpha=0.9)
ax.fill_between(F[:, 0], REF[1], F[:, 1], step="pre", color=style.RED,
                alpha=0.10, lw=0)
# a Pareto point dominates everything down-and-left of it, so the boundary
# between two consecutive front points has to drop to the NEXT point's y
# right at the LEFT point's x (where="pre") -- not carry the left point's y
# rightward first (where="post", the earlier bug: that overstates the
# dominated region and bulges the wrong way, i.e. convex instead of concave)
ax.step(F[:, 0], F[:, 1], where="pre", color=style.RED, lw=1.3, alpha=0.8)

ax.scatter(Y[~front, 0], Y[~front, 1], s=22, c=style.GRAY, alpha=0.45,
           edgecolor="none", label="dominated")
ax.scatter(Y[front, 0], Y[front, 1], s=50, c=style.RED, edgecolor="white",
           linewidth=0.8, zorder=5, label="Pareto front")
ax.plot(*NEW, "*", ms=18, color=style.GOLD, mec="white", mew=1.0, zorder=6,
        label="candidate (not yet run)")
ax.plot(*REF, "s", ms=8, color=style.INK, label="reference point")

ax.set_xlabel("yield / %")
ax.set_ylabel("selectivity / %")
ax.set_title(f"hypervolume above the reference point = {hv:,.0f}", loc="left",
             fontsize=10.5)
ax.legend(loc="upper right", fontsize=8.8, framealpha=0.92,
          facecolor="white")
print("front size:", front.sum(), " hypervolume:", round(hv, 1),
      " with candidate:", round(hv2, 1), " gain:", round(gain, 1))
style.save(fig, "fig_16_pareto_front", OUT)
''')])

FIG17 = ("fig_17_batch_selection.ipynb",
         "Figure 17 — you have a 96-well plate, not one flask",
         "Taking the top q points of the acquisition function gives q nearly "
         "identical experiments. Thompson sampling gives q diverse ones for "
         "free, because each draw has its own maximum.",
         [(None, r'''
xs = np.linspace(0, 10, 700)
OX = np.array([1.15, 2.90, 4.30, 6.10])
OY = land.f1d(OX)
g = gpmod.GP(gpmod.matern52, ls=0.85, sf=1.0, sn=0.03).fit(OX[:, None], OY)
mu, sd = g.predict(xs[:, None])
a = gpmod.ei(mu, sd, OY.max())
Q = 6

# naive: the q highest values of the acquisition function
naive = xs[np.argsort(a)[-Q:]]

# Thompson: q posterior draws, each maximised
draws = g.sample(xs[:, None], n=Q, seed=11)
thom = xs[draws.argmax(axis=1)]

fig, axes = plt.subplots(2, 1, figsize=(5.3, 4.5), sharex=True,
                         gridspec_kw=dict(hspace=0.18))

ax = axes[0]
ax.plot(xs, a, color=style.RED, lw=1.7)
ax.fill_between(xs, 0, a, color=style.RED, alpha=0.12, lw=0)
for x in naive:
    ax.axvline(x, color=style.RED, lw=1.0, alpha=0.85)
ax.set_ylabel("EI")
ax.set_title(f"naive: the top {Q} points of EI — spread {np.ptp(naive):.2f} in x",
             loc="left", fontsize=10.5, color=style.RED)
ax.text(0.985, 0.52, "six wells answering\nthe same question",
        transform=ax.transAxes, ha="right", fontsize=9.6, color=style.RED, bbox=dict(fc="white", alpha=0.85, ec="none", pad=2.0))

ax = axes[1]
for d, x in zip(draws, thom):
    ax.plot(xs, d, color=style.BLUE, lw=0.9, alpha=0.55)
    ax.axvline(x, color=style.BLUE, lw=1.0, alpha=0.85)
    ax.plot([x], [d.max()], "v", ms=7, color=style.BLUE)
ax.plot(OX, OY, "o", ms=6, color=style.INK, mec="white", mew=1.0, zorder=6)
ax.set_ylabel("posterior draws")
ax.set_xlabel("reaction parameter  x")
ax.set_title(f"Thompson sampling: {Q} draws, {Q} maxima — spread "
             f"{np.ptp(thom):.2f} in x", loc="left", fontsize=10.5,
             color=style.BLUE)
print("naive spread  :", round(float(np.ptp(naive)), 3))
print("Thompson spread:", round(float(np.ptp(thom)), 3))
style.save(fig, "fig_17_batch_selection", OUT)
''')])

ALL = [FIG02, FIG15, FIG11, FIG09, FIG12, FIG16, FIG17]
