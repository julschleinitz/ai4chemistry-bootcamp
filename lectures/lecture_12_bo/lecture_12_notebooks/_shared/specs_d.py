"""Notebook spec: how the log marginal likelihood finds l, sigma_f and sigma_n.

This is the companion to figures 18 and 19. Those show what each knob DOES;
this one shows how the machine CHOOSES them, and produces figure 20.
"""

FIG20 = ("fig_20_marginal_likelihood.ipynb",
         "Figure 20 — how the marginal likelihood finds ℓ, σ_f and σₙ",
         "Figures 18 and 19 showed what the two variance knobs do to the "
         "posterior. Neither told you where the numbers come from. They come "
         "from one expression:\n\n"
         "$$\\log p(y \\mid X, \\theta) \\;=\\; "
         "\\underbrace{-\\tfrac12\\, y^{\\mathsf T} K^{-1} y}_{\\text{data fit}} "
         "\\;\\underbrace{-\\tfrac12 \\log|K|}_{\\text{complexity penalty}} "
         "\\;\\underbrace{-\\tfrac{n}{2}\\log 2\\pi}_{\\text{constant}}$$\n\n"
         "with $K = K(X,X;\\ \\ell, \\sigma_f) + \\sigma_n^2 I$. Every "
         "hyperparameter enters only through $K$. Maximise this over "
         "$\\theta = (\\ell, \\sigma_f, \\sigma_n)$ and you have fitted the "
         "model — no cross-validation, no held-out set.\n\n"
         "This notebook re-displays figures 18 and 19, then takes the "
         "expression apart term by term and watches it locate the truth.",
         [
             # ---------------------------------------------------------------
             ("## 1 · Recap — what the two knobs do\n\n"
              "Run `build_and_run.py fig_18` and `fig_19` first if these are "
              "missing. **σ_f** governs the band in the *gaps*; **σₙ** governs "
              "the band *at the data*.",
              r'''
import os
try:                                   # rich display when run in Jupyter
    from IPython.display import Image, display, Markdown
    HAVE_IPY = True
except ImportError:                    # headless (build_and_run.py)
    HAVE_IPY = False

for f, cap in [("fig_18_sigma_f.png",
                "σ_f — sets the ceiling of the band away from the data"),
               ("fig_19_sigma_n.png",
                "σₙ — decides whether the curve goes through the points or near them")]:
    path = f"{OUT}/{f}"
    if not os.path.exists(path):
        print(f"missing {path} — run:  python3 build_and_run.py {f[:6]}")
    elif HAVE_IPY:
        display(Markdown(f"**{cap}**"))
        display(Image(filename=path))
    else:
        print(f"[{f}]  {cap}")
'''),
             # ---------------------------------------------------------------
             ("## 2 · A dataset whose answer we know\n\n"
              "Draw data from a GP with hyperparameters we choose. Then the "
              "fitted values have something to be compared against — which is "
              "the whole reason to do this synthetically rather than on the "
              "EDBO data.",
              r'''
TRUE_LS, TRUE_SF, TRUE_SN = 1.20, 1.50, 0.30
rng = np.random.default_rng(0)


def draw_dataset(n, seed=0):
    """Sample X, then f ~ GP(0, k), then y = f + noise."""
    r = np.random.default_rng(seed)
    X = np.sort(r.uniform(0, 10, n))[:, None]
    K = gpmod.matern52(X, X, ls=TRUE_LS, sf=TRUE_SF) + 1e-9 * np.eye(n)
    f = np.linalg.cholesky(K) @ r.standard_normal(n)
    y = f + r.normal(0, TRUE_SN, n)
    return X, y, f


X, y, f_true = draw_dataset(40, seed=1)
print(f"truth:  l = {TRUE_LS},  sigma_f = {TRUE_SF},  sigma_n = {TRUE_SN}")
print(f"n = {len(y)},  y range {y.min():.2f} to {y.max():.2f}")


def lml_terms(ls, sf, sn, X=X, y=y):
    """The three terms of the log marginal likelihood, separately."""
    n = len(y)
    K = gpmod.matern52(X, X, ls=ls, sf=sf) + (sn ** 2 + 1e-10) * np.eye(n)
    L = np.linalg.cholesky(K)
    a = np.linalg.solve(L.T, np.linalg.solve(L, y))
    fit = -0.5 * y @ a                      # data fit
    comp = -np.log(np.diag(L)).sum()        # -0.5 log|K|
    const = -0.5 * n * np.log(2 * np.pi)
    return fit, comp, const


fit, comp, const = lml_terms(TRUE_LS, TRUE_SF, TRUE_SN)
print(f"\nat the true theta:  data fit {fit:8.2f}   complexity {comp:8.2f}"
      f"   constant {const:8.2f}   total {fit + comp + const:8.2f}")
'''),
             # ---------------------------------------------------------------
             ("## 3 · Why there is a maximum at all\n\n"
              "The two non-constant terms want opposite things.\n\n"
              "- **Data fit** `−½ yᵀK⁻¹y` rewards any θ that lets K explain y. "
              "Shorter ℓ, larger σ_f, smaller σₙ all make K more flexible, so "
              "this term always improves as the model gets more permissive.\n"
              "- **Complexity** `−½ log|K|` is the price. `|K|` is the product "
              "of K's eigenvalues, so a flexible K is a large-determinant K, and "
              "this term punishes it.\n\n"
              "A model that can explain anything explains your data no better "
              "than chance *once normalised* — that is Occam's razor, and it is "
              "not a term someone added by hand. It falls out of `p(D)` being a "
              "probability distribution over datasets that must sum to one.",
              r'''
fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 3.2))
SWEEPS = [("$\\ell$", "ls", np.geomspace(0.15, 40, 180), TRUE_LS),
          ("$\\sigma_f$", "sf", np.geomspace(0.2, 12, 160), TRUE_SF),
          ("$\\sigma_n$", "sn", np.geomspace(0.02, 3.0, 160), TRUE_SN)]

for ax, (label, which, grid, truth) in zip(axes, SWEEPS):
    F, C, T = [], [], []
    for v in grid:
        kw = dict(ls=TRUE_LS, sf=TRUE_SF, sn=TRUE_SN)
        kw[which] = v
        a, b, c = lml_terms(**kw)
        F.append(a); C.append(b); T.append(a + b + c)
    F, C, T = map(np.asarray, (F, C, T))

    ax.plot(grid, F, color=style.BLUE, lw=1.6, label="data fit")
    ax.plot(grid, C, color=style.GOLD, lw=1.6, label="complexity")
    ax.plot(grid, T, color=style.RED, lw=2.4, label="total")
    best = grid[int(np.argmax(T))]
    ax.axvline(best, color=style.RED, ls="--", lw=1.1)
    ax.axvline(truth, color=style.INK, ls=":", lw=1.4)
    ax.set_xscale("log")
    ax.set_ylim(T.max() - 90, max(F.max(), C.max()) + 10)
    style.xlabel(ax, label + "   (log scale)")
    style.title(ax, f"argmax {best:.2f}   ·   truth {truth:.2f}", loc="left",
                fontsize=10.5, color=style.RED if abs(best - truth) / truth > .35
                else style.INK)
    print(f"{label:12s} argmax {best:6.3f}   truth {truth:5.2f}")

style.ylabel(axes[0], "log marginal likelihood")
style.legend(axes[0], loc="lower left", fontsize=8.5, ncol=3,
             bbox_to_anchor=(0.0, -0.42))
style.text(axes[1], 0.5, 1.16, "dotted = truth   ·   dashed = the maximum   ·   "
           "the other two hyperparameters held at their true values",
           transform=axes[1].transAxes, ha="center", fontsize=9.5,
           color=style.GRAY)
style.save(fig, "fig_20a_lml_terms", OUT)
'''),
             # ---------------------------------------------------------------
             ("## 4 · The ℓ / σₙ ridge — why small n is dangerous\n\n"
              "Sweeping one parameter at a time hides the real difficulty. "
              "**ℓ and σₙ are confounded**: rough-looking data is explained "
              "either by a short length-scale (the function really wiggles) or "
              "by a large noise level (it doesn't, you just measured badly). "
              "The likelihood surface has a diagonal ridge connecting the two "
              "stories, and with few points the ridge is nearly flat — so the "
              "optimiser can land anywhere along it.\n\n"
              "This is the mechanism behind the warning on the slide, and it is "
              "why Shields et al. found the length-scale prior to be the single "
              "most critical component of their model.",
              r'''
LSG = np.geomspace(0.15, 40, 95)
SNG = np.geomspace(0.02, 3.0, 90)

fig, axes = plt.subplots(1, 2, figsize=(style.FIG_W_FULL, 3.6),
                         gridspec_kw=dict(wspace=0.22))

for ax, n_pts in zip(axes, [8, 40]):
    Xn, yn, _ = draw_dataset(n_pts, seed=1)
    Z = np.empty((len(SNG), len(LSG)))
    for i, sn in enumerate(SNG):
        for j, ls in enumerate(LSG):
            a, b, c = lml_terms(ls, TRUE_SF, sn, Xn, yn)
            Z[i, j] = a + b + c
    Z -= Z.max()                                   # relative to the best
    cs = ax.contourf(LSG, SNG, np.clip(Z, -25, 0), levels=25, cmap="BuGn")
    ax.contour(LSG, SNG, np.clip(Z, -25, 0), levels=[-6, -3, -1],
               colors="white", linewidths=0.7, alpha=0.8)
    i, j = np.unravel_index(np.argmax(Z), Z.shape)
    ax.plot(LSG[j], SNG[i], "o", ms=11, mfc="none", mec=style.RED, mew=2.2,
            zorder=6)
    ax.plot(TRUE_LS, TRUE_SN, "*", ms=17, color=style.GOLD, mec="white",
            mew=0.9, zorder=7)
    ax.set_xscale("log"); ax.set_yscale("log")
    style.xlabel(ax, r"length-scale  $\ell$")
    style.ylabel(ax, r"noise  $\sigma_n$")
    style.title(ax, f"n = {n_pts}   —   argmax at "
                    fr"$\ell$={LSG[j]:.2f}, $\sigma_n$={SNG[i]:.2f}",
                loc="left", fontsize=11)
    print(f"n={n_pts:3d}  argmax  l={LSG[j]:6.2f}  sn={SNG[i]:5.2f}   "
          f"(truth l={TRUE_LS}, sn={TRUE_SN})")

cb = fig.colorbar(cs, ax=axes, fraction=0.022, pad=0.015)
style.cbar_label(cb, "log marginal likelihood, relative to its maximum")
cb.outline.set_visible(False)
style.text(axes[0], 0.5, 1.16, "star = truth   ·   circle = the maximum   ·   "
           r"the diagonal ridge is the $\ell$ / $\sigma_n$ trade-off",
           transform=axes[0].transAxes, ha="center", fontsize=9.5,
           color=style.GRAY)
style.save(fig, "fig_20b_lml_ridge", OUT)
'''),
             # ---------------------------------------------------------------
             ("## 5 · Does it actually recover the truth?\n\n"
              "Fit all three hyperparameters jointly, at a range of dataset "
              "sizes, over several independent datasets. The answer is the "
              "honest one: **yes, but only once you have enough data**, and "
              "*σₙ* is recovered far more reliably than *ℓ* or *σ_f*.",
              r'''
NS = [5, 8, 12, 20, 40, 80]
SEEDS = range(6)
rec = {k: {n: [] for n in NS} for k in ("ls", "sf", "sn")}

for n_pts in NS:
    for s in SEEDS:
        Xn, yn, _ = draw_dataset(n_pts, seed=100 + s)
        (lsh, sfh, snh), _ = gpmod.fit_hypers_ard(
            Xn, yn, 1, kernel=gpmod.matern52, seed=s, n_restarts=140,
            ls_grid=(-0.9, 1.1), sf_grid=(-0.7, 1.1), sn_grid=(-2.0, 0.5))
        rec["ls"][n_pts].append(float(lsh[0]))
        rec["sf"][n_pts].append(float(sfh))
        rec["sn"][n_pts].append(float(snh))

fig, axes = plt.subplots(1, 3, figsize=(style.FIG_W_FULL, 3.2), sharex=True)
INFO = [("ls", r"$\ell$", TRUE_LS), ("sf", r"$\sigma_f$", TRUE_SF),
        ("sn", r"$\sigma_n$", TRUE_SN)]

for ax, (key, label, truth) in zip(axes, INFO):
    med = [np.median(rec[key][n]) for n in NS]
    q1 = [np.percentile(rec[key][n], 25) for n in NS]
    q3 = [np.percentile(rec[key][n], 75) for n in NS]
    ax.fill_between(NS, q1, q3, color=style.TEAL, alpha=0.20, lw=0)
    ax.plot(NS, med, "o-", color=style.TEAL, lw=2.0, ms=6)
    for n in NS:
        ax.plot([n] * len(rec[key][n]), rec[key][n], ".", color=style.GRAY,
                ms=4, alpha=0.6)
    ax.axhline(truth, color=style.RED, ls="--", lw=1.4)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_ylim(truth / 12, truth * 12)
    ax.set_xticks(NS); ax.set_xticklabels([str(n) for n in NS])
    style.xlabel(ax, "number of experiments")
    style.title(ax, f"{label}   truth {truth}", loc="left", fontsize=11)
    print(f"{label:10s} " + "  ".join(
        f"n={n}: {np.median(rec[key][n]):5.2f}" for n in NS))

style.ylabel(axes[0], "fitted value")
style.text(axes[1], 0.5, 1.16, "dashed = truth   ·   band = interquartile range "
           "over 6 independent datasets", transform=axes[1].transAxes,
           ha="center", fontsize=9.5, color=style.GRAY)
style.save(fig, "fig_20c_recovery", OUT)
'''),
             # ---------------------------------------------------------------
             ("## 6 · What to take to the bench\n\n"
              "1. **One expression fits the whole model.** No validation split, "
              "no cross-validation. That is unusual and it is why GPs are "
              "practical at n = 20.\n"
              "2. **The maximum is a compromise**, not a best fit. Data fit and "
              "complexity pull in opposite directions; Occam is built in.\n"
              "3. **ℓ and σₙ are confounded.** With few points the likelihood "
              "cannot tell a rough function from a noisy measurement. Two fixes, "
              "both of which you already have on the slides: put a prior on ℓ "
              "(what Shields et al. did) or *measure* σₙ from replicates and fix "
              "it (what your figure 19 argues for). Fixing σₙ collapses the "
              "ridge to a line and the remaining problem is well posed.\n"
              "4. **σ_f is the easiest of the three** — it is set by the overall "
              "scale of y, which even a handful of points pins down.",
              None),
         ])

ALL = [FIG20]
