"""Classical design of experiments: face-centred CCD + quadratic response
surface. Shared by fig_02 (one panel among several naive strategies) and
fig_15 (grid vs. DOE vs. BO), so both build the identical design from the
same bounds, budget, and seed.
"""
import numpy as np


def ccd_points(bounds, budget, seed=0):
    """4 corners + 4 face centres + 4 centre replicates (12 fixed runs),
    padded with uniform random fill up to `budget`."""
    lo, hi = bounds[:, 0], bounds[:, 1]
    ctr = (lo + hi) / 2
    pts = [[lo[0], lo[1]], [lo[0], hi[1]], [hi[0], lo[1]], [hi[0], hi[1]],
           [lo[0], ctr[1]], [hi[0], ctr[1]], [ctr[0], lo[1]], [ctr[0], hi[1]]]
    pts += [list(ctr)] * 4
    pts = np.array(pts)
    if budget > len(pts):
        rng = np.random.default_rng(seed)
        pts = np.vstack([pts, rng.uniform(lo, hi, size=(budget - len(pts), 2))])
    else:
        pts = pts[:budget]
    return pts


def fit_quadratic(bounds, X, y):
    """Least-squares quadratic response surface in coded units. Returns the
    coefficients and a predict(T, C) closure over natural-units grids."""
    lo, hi = bounds[:, 0], bounds[:, 1]
    ctr, half = (lo + hi) / 2, (hi - lo) / 2
    u = (X - ctr) / half
    Xd = np.column_stack([np.ones(len(u)), u[:, 0], u[:, 1], u[:, 0] ** 2,
                          u[:, 1] ** 2, u[:, 0] * u[:, 1]])
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)

    def predict(T, C):
        UT, UC = (T - ctr[0]) / half[0], (C - ctr[1]) / half[1]
        return (beta[0] + beta[1] * UT + beta[2] * UC + beta[3] * UT ** 2
                + beta[4] * UC ** 2 + beta[5] * UT * UC)
    return beta, predict


def run(bounds, surface_fn, budget, seed=0):
    """Build the CCD, evaluate `surface_fn` (vectorised, like
    landscape.yield_surface) on it, and fit the quadratic. Returns a dict
    with points X, observed y, fitted beta, and predict(T, C)."""
    X = ccd_points(bounds, budget, seed)
    y = surface_fn(X)
    beta, predict = fit_quadratic(bounds, X, y)
    return {"X": X, "y": y, "beta": beta, "predict": predict}
