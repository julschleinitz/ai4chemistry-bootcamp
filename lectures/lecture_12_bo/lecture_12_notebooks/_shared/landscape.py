"""2-D reaction-yield surfaces reused across lecture 12 figures.

Temperature 60-140 C  x  catalyst loading 0.5-5 mol%.
Building this once is what makes the grid / DOE / BO comparison an honest
comparison: same surface, same budget, same random seed.

Several surface *shapes* are registered in SURFACES (see list_surfaces()),
all sharing the same bounds and axis labels above -- so any figure can be
re-run against a harder or differently-shaped landscape without touching its
plotting code. The default, "ridge", is what every existing figure uses
unless it passes `kind=` explicitly:

- "ridge"        curved ridge (defeats a fitted quadratic), one broad global
                 optimum, one deceptive local bump, a decomposition penalty.
- "twin_peaks"   two comparable optima of nearly equal height -- grid, DOE
                 and BO can each legitimately land on either one.
- "narrow_ridge" the same curved-ridge idea but much narrower, so a coarse
                 grid or CCD is more likely to straddle it and miss entirely.

Nothing here is fitted to real data — these are teaching surfaces. The
real-data figures in this lecture come from the EDBO dataset and from
Shields et al. 2021.
"""
import numpy as np

BOUNDS = np.array([[60.0, 140.0],      # temperature / C
                   [0.5, 5.0]])        # catalyst loading / mol%
LABELS = ["temperature / °C", "catalyst loading / mol%"]


def _u(X):
    """Map the box to the unit square."""
    X = np.atleast_2d(np.asarray(X, float))
    return (X - BOUNDS[:, 0]) / (BOUNDS[:, 1] - BOUNDS[:, 0])


def _ridge(t, c):
    # curved ridge: optimum loading rises with temperature
    ridge_c = 0.30 + 0.45 * t
    ridge = np.exp(-((c - ridge_c) ** 2) / (2 * 0.095 ** 2))

    # along-ridge profile: broad global optimum near t = 0.68
    along = np.exp(-((t - 0.68) ** 2) / (2 * 0.30 ** 2))

    # deceptive secondary bump, low temperature / low loading
    bump = 0.62 * np.exp(-(((t - 0.16) ** 2) / (2 * 0.075 ** 2)
                           + ((c - 0.18) ** 2) / (2 * 0.075 ** 2)))

    # decomposition penalty at high temperature and high loading
    decomp = 0.35 * np.clip(t - 0.80, 0, None) / 0.20 * np.clip(c - 0.55, 0, None) / 0.45

    return 92.0 * ridge * along + 58.0 * bump - 100.0 * decomp


def _twin_peaks(t, c):
    peak_a = np.exp(-(((t - 0.28) ** 2) / (2 * 0.11 ** 2)
                      + ((c - 0.28) ** 2) / (2 * 0.11 ** 2)))
    peak_b = np.exp(-(((t - 0.74) ** 2) / (2 * 0.13 ** 2)
                      + ((c - 0.68) ** 2) / (2 * 0.13 ** 2)))
    decomp = 0.30 * np.clip(t - 0.80, 0, None) / 0.20 * np.clip(c - 0.55, 0, None) / 0.45
    return 91.0 * peak_a + 89.0 * peak_b - 100.0 * decomp


def _narrow_ridge(t, c):
    ridge_c = 0.25 + 0.50 * t
    ridge = np.exp(-((c - ridge_c) ** 2) / (2 * 0.045 ** 2))
    along = np.exp(-((t - 0.60) ** 2) / (2 * 0.35 ** 2))
    decomp = 0.30 * np.clip(t - 0.82, 0, None) / 0.18 * np.clip(c - 0.60, 0, None) / 0.40
    return 96.0 * ridge * along - 100.0 * decomp


SURFACES = {
    "ridge": _ridge,
    "twin_peaks": _twin_peaks,
    "narrow_ridge": _narrow_ridge,
}


def list_surfaces():
    """Names accepted as `kind=` by yield_surface / f / optimum / mesh."""
    return list(SURFACES)


def yield_surface(X, kind="ridge"):
    """True yield in %, in [0, 100]. Vectorised over rows of X."""
    u = _u(X)
    t, c = u[:, 0], u[:, 1]
    z = SURFACES[kind](t, c)
    return np.clip(z, 0.0, 100.0)


def f(x, kind="ridge"):
    """Scalar interface for the BO loop."""
    return float(yield_surface(np.atleast_2d(x), kind=kind)[0])


def optimum(n=400, kind="ridge"):
    """Grid-search the true optimum, for reference lines on plots."""
    t = np.linspace(*BOUNDS[0], n)
    c = np.linspace(*BOUNDS[1], n)
    T, C = np.meshgrid(t, c)
    Z = yield_surface(np.column_stack([T.ravel(), C.ravel()]), kind=kind).reshape(T.shape)
    i = np.unravel_index(np.argmax(Z), Z.shape)
    return np.array([T[i], C[i]]), Z[i]


def mesh(n=220, kind="ridge"):
    t = np.linspace(*BOUNDS[0], n)
    c = np.linspace(*BOUNDS[1], n)
    T, C = np.meshgrid(t, c)
    Z = yield_surface(np.column_stack([T.ravel(), C.ravel()]), kind=kind).reshape(T.shape)
    return T, C, Z


# ---------------------------------------------------------------- 1-D slice
X1_LO, X1_HI = 0.0, 10.0


def f1d(x):
    """A 1-D objective for the GP / acquisition-function figures.

    Deliberately multi-modal with unequal peaks, so EI, PI and UCB disagree.
    """
    x = np.asarray(x, float)
    return (1.35 * np.exp(-((x - 2.4) ** 2) / 1.1)
            + 1.00 * np.exp(-((x - 5.1) ** 2) / 0.7)
            + 1.55 * np.exp(-((x - 7.9) ** 2) / 1.5)
            - 0.28 * np.sin(1.15 * x) - 0.35)
