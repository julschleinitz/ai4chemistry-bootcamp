"""Run a 20-experiment campaign on the L12 landscape, two ways.

BO with expected improvement wants the argmax.  AL with variance sampling wants a
globally good model.  Same landscape, same budget, same seed -- which is the whole
point of figure 1.
"""
import math

import numpy as np
import landscape as L
from gp import GP


def _seed_points(n=5, seed=0):
    """A small space-filling seed design (scrambled Latin hypercube)."""
    rng = np.random.default_rng(seed)
    u = (np.arange(n)[:, None] + rng.random((n, 2))) / n
    for d in range(2):
        u[:, d] = u[rng.permutation(n), d]
    return L.from_unit(u)


class _CenteredGP:
    """GP with a constant prior mean fixed to the data mean -- standard practice.

    This matters for figure 1 and it is not a trick: a GP with a zero prior mean
    would predict 0% yield everywhere it has no data, which happens to be roughly
    correct in the low-yield regions, and would flatter a clustered BO design for
    the wrong reason.  Centring on the data mean is what any library does.
    """

    def __init__(self, **kw):
        self.g = GP(**kw)

    def fit(self, X, y):
        self.mean = float(np.mean(y))
        self.g.fit(X, y - self.mean)
        return self

    def predict(self, Xs, **kw):
        mu, sd = self.g.predict(Xs, **kw)
        return mu + self.mean, sd


def _fit(X, y):
    # unit-cube inputs so a single length-scale is meaningful across both axes
    return _CenteredGP(ell=0.26, sigma_f=32.0, sigma_n=L.SIGMA_NOISE).fit(L.to_unit(X), y)


def _ei(mu, sd, best):
    """Expected improvement, closed form, with a numpy-only normal CDF/PDF."""
    sd = np.maximum(sd, 1e-9)
    z = (mu - best) / sd
    Phi = 0.5 * (1.0 + np.vectorize(math.erf)(z / np.sqrt(2.0)))
    phi = np.exp(-0.5 * z**2) / np.sqrt(2.0 * np.pi)
    return (mu - best) * Phi + sd * phi


def run(strategy, budget=20, n_seed=5, seed=0, n_cand=60):
    """strategy in {'bo', 'al'}.  Returns dict with the campaign and its fitted model."""
    rng = np.random.default_rng(seed)
    X = _seed_points(n_seed, seed=seed)
    y = L.observe(X, rng=rng)

    t = np.linspace(L.T_LO, L.T_HI, n_cand)
    l = np.linspace(L.L_LO, L.L_HI, n_cand)
    TT, LL = np.meshgrid(t, l)
    cand = np.column_stack([TT.ravel(), LL.ravel()])

    for _ in range(budget - n_seed):
        g = _fit(X, y)
        mu, sd = g.predict(L.to_unit(cand))
        if strategy == "bo":
            score = _ei(mu, sd, y.max())
        elif strategy == "al":
            score = sd                      # pure variance / uncertainty sampling
        else:
            raise ValueError(strategy)
        # never re-query a point we already have
        d = np.linalg.norm(L.to_unit(cand)[:, None, :] - L.to_unit(X)[None, :, :],
                           axis=2).min(1)
        score = np.where(d < 0.02, -np.inf, score)
        x_new = cand[int(np.argmax(score))][None, :]
        X = np.vstack([X, x_new])
        y = np.append(y, L.observe(x_new, rng=rng))

    g = _fit(X, y)
    TTg, LLg, F = L.grid(90)
    pts = np.column_stack([TTg.ravel(), LLg.ravel()])
    mu, _ = g.predict(L.to_unit(pts))
    err2 = (mu - F.ravel()) ** 2
    rmse = float(np.sqrt(err2.mean()))
    # RMSE away from the optimum -- the bottom 75% of the true surface.  This is
    # the quantity the lecture actually claims differs: how well do you know the
    # parts of the space you are NOT optimising?
    cut = np.quantile(F.ravel(), 0.75)
    rmse_away = float(np.sqrt(err2[F.ravel() <= cut].mean()))
    return dict(X=X, y=y, gp=g, fitted=mu.reshape(F.shape), truth=F,
                TT=TTg, LL=LLg, rmse=rmse, rmse_away=rmse_away,
                best_found=float(L.yield_surface(X[[int(np.argmax(y))]])[0]))
