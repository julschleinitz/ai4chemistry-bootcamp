"""A small, dependency-free Gaussian process + Bayesian optimization toolkit.

Only numpy is used, so these notebooks run anywhere. Nothing here is clever —
it is deliberately the textbook form so that students can read it against the
equations on the slides.

Reference: Rasmussen & Williams, Gaussian Processes for Machine Learning,
MIT Press 2006, chapters 2 and 5.
"""
import numpy as np
from math import erf, sqrt, pi, log


# ---------------------------------------------------------------- normal dist
def norm_pdf(z):
    return np.exp(-0.5 * np.asarray(z) ** 2) / sqrt(2 * pi)


def norm_cdf(z):
    z = np.asarray(z, dtype=float)
    return 0.5 * (1.0 + np.vectorize(erf)(z / sqrt(2.0)))


# ---------------------------------------------------------------- kernels
def _sqdist(A, B):
    A = np.atleast_2d(A); B = np.atleast_2d(B)
    return ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)


def rbf(A, B, ls=1.0, sf=1.0):
    """Squared exponential. ls may be a scalar or one value per dimension (ARD)."""
    A = np.atleast_2d(A) / np.asarray(ls)
    B = np.atleast_2d(B) / np.asarray(ls)
    return sf ** 2 * np.exp(-0.5 * _sqdist(A, B))


def matern52(A, B, ls=1.0, sf=1.0):
    """Matern nu=5/2 — twice differentiable sample paths."""
    A = np.atleast_2d(A) / np.asarray(ls)
    B = np.atleast_2d(B) / np.asarray(ls)
    r = np.sqrt(np.maximum(_sqdist(A, B), 1e-24))
    s5 = sqrt(5.0) * r
    return sf ** 2 * (1.0 + s5 + 5.0 / 3.0 * r ** 2) * np.exp(-s5)


# ---------------------------------------------------------------- the GP
class GP:
    """Zero-mean GP regression with Gaussian noise.

    posterior mean  mu(x)     = k*^T K^-1 y
    posterior var   sigma2(x) = k** - k*^T K^-1 k*
    with K = K(X,X) + sn^2 I.  Note sigma2 does not contain y — at FIXED
    hyperparameters. Fitting ls/sf/sn to the data puts y back in indirectly.
    """

    def __init__(self, kernel=matern52, ls=1.0, sf=1.0, sn=1e-2, jitter=1e-10):
        self.kernel, self.ls, self.sf, self.sn, self.jitter = kernel, ls, sf, sn, jitter
        self.X = self.y = None

    def _K(self, X):
        n = len(X)
        return (self.kernel(X, X, self.ls, self.sf)
                + (self.sn ** 2 + self.jitter) * np.eye(n))

    def fit(self, X, y):
        self.X = np.atleast_2d(np.asarray(X, float))
        self.y = np.asarray(y, float).ravel()
        self.ymean = self.y.mean() if len(self.y) else 0.0
        self.L = np.linalg.cholesky(self._K(self.X))
        self.alpha = np.linalg.solve(self.L.T,
                                     np.linalg.solve(self.L, self.y - self.ymean))
        return self

    def predict(self, Xs, full_cov=False):
        Xs = np.atleast_2d(np.asarray(Xs, float))
        if self.X is None:                       # prior
            mu = np.zeros(len(Xs))
            Kss = self.kernel(Xs, Xs, self.ls, self.sf)
            return (mu, Kss) if full_cov else (mu, np.sqrt(np.diag(Kss)))
        Ks = self.kernel(Xs, self.X, self.ls, self.sf)
        mu = Ks @ self.alpha + self.ymean
        v = np.linalg.solve(self.L, Ks.T)
        Kss = self.kernel(Xs, Xs, self.ls, self.sf) - v.T @ v
        if full_cov:
            return mu, Kss
        return mu, np.sqrt(np.clip(np.diag(Kss), 0.0, None))

    def sample(self, Xs, n=10, seed=0):
        mu, K = self.predict(Xs, full_cov=True)
        L = np.linalg.cholesky(K + 1e-9 * np.eye(len(Xs)))
        r = np.random.default_rng(seed)
        return mu[None, :] + (L @ r.standard_normal((len(Xs), n))).T

    def log_marginal_likelihood(self):
        n = len(self.X)
        fit = -0.5 * (self.y - self.ymean) @ np.linalg.solve(
            self.L.T, np.linalg.solve(self.L, self.y - self.ymean))
        complexity = -np.log(np.diag(self.L)).sum()
        return fit + complexity - 0.5 * n * log(2 * pi)



def _polish(X, y, kernel, ls, sf, sn, sweeps=6, span=0.6, pts=13):
    """Coordinate-wise refinement of (ls, sf, sn) on a shrinking log grid.

    Random restarts alone get WORSE as n grows, because the likelihood peak
    sharpens and a fixed number of random draws is less and less likely to
    land near it. This local pass fixes that. Crude, deterministic, and
    plenty accurate for teaching-scale problems.
    """
    def lml(ls_, sf_, sn_):
        try:
            return GP(kernel, ls=ls_, sf=sf_, sn=sn_).fit(X, y).log_marginal_likelihood()
        except np.linalg.LinAlgError:
            return -np.inf

    ls = np.atleast_1d(np.array(ls, float)).copy()
    best = lml(ls, sf, sn)
    for k in range(sweeps):
        r = span * (0.5 ** k)
        for j in range(len(ls)):
            for v in ls[j] * 10 ** np.linspace(-r, r, pts):
                cand = ls.copy(); cand[j] = v
                val = lml(cand, sf, sn)
                if val > best:
                    best, ls = val, cand
        for v in sf * 10 ** np.linspace(-r, r, pts):
            val = lml(ls, v, sn)
            if val > best:
                best, sf = val, v
        for v in sn * 10 ** np.linspace(-r, r, pts):
            val = lml(ls, sf, v)
            if val > best:
                best, sn = val, v
    return (ls, sf, sn), best


def fit_hypers_ard(X, y, d, kernel=matern52, ls_grid=None, sf_grid=None,
                   sn_grid=None, seed=0, n_restarts=40, polish=True):
    """Crude but honest hyperparameter search: random restarts on a log grid,
    maximising the log marginal likelihood. One length-scale per dimension (ARD).

    A real package uses gradients; this is transparent and fast enough at n<2000.
    """
    rng = np.random.default_rng(seed)
    ls_grid = ls_grid if ls_grid is not None else (-1.2, 1.2)     # log10 bounds
    sf_grid = sf_grid if sf_grid is not None else (-0.5, 1.0)
    sn_grid = sn_grid if sn_grid is not None else (-2.5, -0.3)
    best = (-np.inf, None)
    for _ in range(n_restarts):
        ls = 10 ** rng.uniform(*ls_grid, size=d)
        sf = 10 ** rng.uniform(*sf_grid)
        sn = 10 ** rng.uniform(*sn_grid)
        try:
            gp = GP(kernel, ls=ls, sf=sf, sn=sn).fit(X, y)
            lml = gp.log_marginal_likelihood()
        except np.linalg.LinAlgError:
            continue
        if lml > best[0]:
            best = (lml, (ls, sf, sn))
    if polish and best[1] is not None:
        return _polish(X, y, kernel, *best[1])
    return best[1], best[0]


# ---------------------------------------------------------------- acquisitions
def ei(mu, sd, fbest, xi=0.0):
    """Expected improvement (maximisation)."""
    sd = np.maximum(sd, 1e-12)
    z = (mu - fbest - xi) / sd
    return (mu - fbest - xi) * norm_cdf(z) + sd * norm_pdf(z)


def pi_acq(mu, sd, fbest, xi=0.0):
    """Probability of improvement."""
    sd = np.maximum(sd, 1e-12)
    return norm_cdf((mu - fbest - xi) / sd)


def ucb(mu, sd, beta=2.0):
    return mu + beta * sd


def noisy_ei(gp, Xs, Xobs, n_fantasy=64, seed=0):
    """Noisy EI: marginalise over uncertainty in the incumbent.

    Standard EI conditions on f+ = max(observed y) as if it were the truth.
    Under noise that value is probably lucky. Here we instead draw posterior
    samples of f at the OBSERVED points, take the max of each draw as a
    plausible incumbent, and average EI over those.

    This is the idea behind Letham et al., Bayesian Analysis 2019, 14, 495-519,
    which is the ancestor of qNEI / qNEHVI in BoTorch.
    """
    mu, sd = gp.predict(Xs)
    fdraws = gp.sample(Xobs, n=n_fantasy, seed=seed)   # (n_fantasy, n_obs)
    incumbents = fdraws.max(axis=1)
    return np.mean([ei(mu, sd, f) for f in incumbents], axis=0)


# ---------------------------------------------------------------- BO loop
def bo_loop(f, bounds, n_init=5, n_iter=25, acq="ei", beta=2.0, noise=0.0,
            assumed_sn=None, seed=0, kernel=matern52, ls=None, sf=1.0,
            grid=None, noisy_incumbent=False):
    """Run BO on a callable f over a box, or over a fixed candidate grid.

    noise      : sd of the noise ACTUALLY added to observations
    assumed_sn : sd the GP is TOLD about (defaults to `noise`).
                 Setting assumed_sn ~ 0 while noise > 0 reproduces the classic
                 failure mode: the GP interpolates a lucky point and the
                 campaign chases it.
    """
    rng = np.random.default_rng(seed)
    bounds = np.asarray(bounds, float)
    d = len(bounds)
    if assumed_sn is None:
        assumed_sn = noise
    if ls is None:
        ls = 0.2 * (bounds[:, 1] - bounds[:, 0])

    cand = grid if grid is not None else None
    if cand is None:
        cand = rng.uniform(bounds[:, 0], bounds[:, 1], size=(4000, d))

    # space-filling seed via a coarse Latin hypercube
    seeds = np.empty((n_init, d))
    for j in range(d):
        cut = (np.arange(n_init) + rng.random(n_init)) / n_init
        seeds[:, j] = bounds[j, 0] + cut * (bounds[j, 1] - bounds[j, 0])
        rng.shuffle(seeds[:, j])

    X = seeds.copy()
    ytrue = np.array([f(x) for x in X])
    y = ytrue + rng.normal(0, noise, size=len(X)) if noise else ytrue.copy()

    traj = [y.max()]
    for _ in range(n_iter):
        gp = GP(kernel, ls=ls, sf=sf, sn=max(assumed_sn, 1e-4)).fit(X, y)
        mu, sd = gp.predict(cand)
        if acq == "ei":
            a = (noisy_ei(gp, cand, X, seed=int(rng.integers(1e6)))
                 if noisy_incumbent else ei(mu, sd, y.max()))
        elif acq == "ucb":
            a = ucb(mu, sd, beta)
        elif acq == "pi":
            a = pi_acq(mu, sd, y.max())
        elif acq == "random":
            a = rng.random(len(cand))
        elif acq == "exploit":
            a = mu
        elif acq == "explore":
            a = sd
        else:
            raise ValueError(acq)
        xn = cand[int(np.argmax(a))]
        yt = f(xn)
        X = np.vstack([X, xn])
        ytrue = np.append(ytrue, yt)
        y = np.append(y, yt + (rng.normal(0, noise) if noise else 0.0))
        traj.append(ytrue.max())          # report TRUE best found, not lucky reading
    return dict(X=X, y=y, ytrue=ytrue, traj=np.array(traj))
