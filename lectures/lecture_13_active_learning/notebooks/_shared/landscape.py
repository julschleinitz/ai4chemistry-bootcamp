"""The 2-D reaction-yield surface shared with Lecture 12.

Temperature (60-140 C) x catalyst loading (0.5-5 mol%).  A curved ridge, one
broad optimum, one deceptive local bump, additive Gaussian noise with a
settable sigma.  Building this once is what makes the BO-vs-AL comparison an
honest one: same surface, same budget, same seed.

If the Lecture 12 version of this module already exists, USE THAT ONE instead --
the two lectures must run on an identical landscape.
"""
import numpy as np

T_LO, T_HI = 60.0, 140.0        # temperature, degrees C
L_LO, L_HI = 0.5, 5.0           # catalyst loading, mol%
BOUNDS = np.array([[T_LO, T_HI], [L_LO, L_HI]])
SIGMA_NOISE = 3.0               # absolute % yield; 2-5% is normal in HTE


def to_unit(X):
    X = np.atleast_2d(np.asarray(X, dtype=float))
    return (X - BOUNDS[:, 0]) / (BOUNDS[:, 1] - BOUNDS[:, 0])


def from_unit(U):
    U = np.atleast_2d(np.asarray(U, dtype=float))
    return BOUNDS[:, 0] + U * (BOUNDS[:, 1] - BOUNDS[:, 0])


def yield_surface(X):
    """True (noiseless) yield in %, for X = [[temperature, loading], ...].

    Design note -- this matters, and it is why the surface is not mostly zero.
    The background frequencies are set so that a 20-point design does NOT fully
    resolve the surface -- if it did, both campaigns would score the same globally
    and the figure would teach nothing.
    An earlier version was a narrow ridge on a flat zero background.  On such a
    surface, domain-wide RMSE is dominated by the peak, so a campaign that
    samples only the peak (Bayesian optimization) scores as well globally as one
    that spreads out -- which is an artefact of the test surface, not a fact
    about the methods.  A real yield surface varies smoothly everywhere, so the
    background here carries broad structure of its own.  Figure 1 is only an
    honest comparison because of this.
    """
    u = to_unit(X)
    t, l = u[:, 0], u[:, 1]

    # broad smooth background: yield varies across the WHOLE domain
    bg = (34.0
          + 17.0 * np.sin(3.28 * np.pi * (t - 0.08))
          + 13.0 * np.cos(2.80 * np.pi * (l + 0.16))
          - 15.0 * (t - 0.5) * (l - 0.5)
          + 8.0 * np.sin(4.16 * np.pi * t * l))

    # curved ridge: the optimal loading rises with temperature
    ridge_l = 0.22 + 0.62 * t - 0.20 * t**2
    ridge = 44.0 * np.exp(-((l - ridge_l) ** 2) / (2 * 0.140**2))
    ridge *= np.exp(-((t - 0.66) ** 2) / (2 * 0.26**2))

    # deceptive secondary bump, low temperature / low loading
    bump = 22.0 * np.exp(-(((t - 0.14) ** 2) / (2 * 0.11**2) +
                           ((l - 0.13) ** 2) / (2 * 0.10**2)))

    # thermal decomposition penalty at the hot end
    decomp = 16.0 * np.clip(t - 0.82, 0, None) ** 2 / 0.032

    return np.clip(bg + ridge + bump - decomp, 0.0, 100.0)


def observe(X, sigma=SIGMA_NOISE, rng=None):
    """A noisy experiment."""
    rng = np.random.default_rng(0) if rng is None else rng
    f = yield_surface(X)
    return f + rng.normal(0.0, sigma, size=f.shape)


def grid(n=140):
    """Return (TT, LL, F) for contour plotting."""
    t = np.linspace(T_LO, T_HI, n)
    l = np.linspace(L_LO, L_HI, n)
    TT, LL = np.meshgrid(t, l)
    pts = np.column_stack([TT.ravel(), LL.ravel()])
    return TT, LL, yield_surface(pts).reshape(TT.shape)


def optimum(n=400):
    TT, LL, F = grid(n)
    k = np.argmax(F)
    return np.array([TT.ravel()[k], LL.ravel()[k]]), F.ravel()[k]
