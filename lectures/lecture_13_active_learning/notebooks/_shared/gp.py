"""A minimal Gaussian process, pure numpy.

Only what the lecture-13 figures need: an ARD squared-exponential kernel, the
posterior mean/variance, and exact posterior function draws.  No scipy.
"""
import numpy as np


def se_kernel(A, B, ell=1.0, sigma_f=1.0):
    """Squared-exponential (RBF) kernel.  ell may be a scalar or per-dimension (ARD)."""
    A = np.atleast_2d(A); B = np.atleast_2d(B)
    ell = np.asarray(ell, dtype=float)
    As, Bs = A / ell, B / ell
    d2 = (As**2).sum(1)[:, None] + (Bs**2).sum(1)[None, :] - 2 * As @ Bs.T
    return sigma_f**2 * np.exp(-0.5 * np.maximum(d2, 0.0))


class GP:
    """Exact GP regression with a Gaussian likelihood."""

    def __init__(self, ell=1.0, sigma_f=1.0, sigma_n=1e-3):
        self.ell, self.sigma_f, self.sigma_n = ell, sigma_f, sigma_n
        self.X = np.zeros((0, 1)); self.y = np.zeros(0)

    def fit(self, X, y):
        self.X = np.atleast_2d(np.asarray(X, dtype=float))
        if self.X.shape[0] == 1 and len(np.ravel(X)) > 1:
            self.X = self.X.T
        self.y = np.ravel(np.asarray(y, dtype=float))
        n = self.X.shape[0]
        K = se_kernel(self.X, self.X, self.ell, self.sigma_f) + \
            (self.sigma_n**2 + 1e-10) * np.eye(n)
        self.L = np.linalg.cholesky(K)
        self.alpha = np.linalg.solve(self.L.T, np.linalg.solve(self.L, self.y))
        return self

    def predict(self, Xs, latent=True):
        """Return (mean, std).  latent=True excludes the observation noise."""
        Xs = np.atleast_2d(np.asarray(Xs, dtype=float))
        if Xs.shape[0] == 1 and len(np.ravel(Xs)) > 1:
            Xs = Xs.T
        if self.X.shape[0] == 0:
            mu = np.zeros(Xs.shape[0])
            var = np.full(Xs.shape[0], self.sigma_f**2)
        else:
            Ks = se_kernel(self.X, Xs, self.ell, self.sigma_f)
            mu = Ks.T @ self.alpha
            v = np.linalg.solve(self.L, Ks)
            var = self.sigma_f**2 - (v**2).sum(0)
        if not latent:
            var = var + self.sigma_n**2
        return mu, np.sqrt(np.maximum(var, 1e-12))

    def sample(self, Xs, n_samples=8, rng=None, jitter=1e-8):
        """Exact draws from the posterior over functions."""
        rng = np.random.default_rng(0) if rng is None else rng
        Xs = np.atleast_2d(np.asarray(Xs, dtype=float))
        if Xs.shape[0] == 1 and len(np.ravel(Xs)) > 1:
            Xs = Xs.T
        mu, _ = self.predict(Xs)
        Kss = se_kernel(Xs, Xs, self.ell, self.sigma_f)
        if self.X.shape[0] > 0:
            Ks = se_kernel(self.X, Xs, self.ell, self.sigma_f)
            v = np.linalg.solve(self.L, Ks)
            cov = Kss - v.T @ v
        else:
            cov = Kss
        cov = cov + jitter * np.eye(cov.shape[0])
        Lc = np.linalg.cholesky(cov + 1e-9 * np.eye(cov.shape[0]))
        return mu[None, :] + rng.standard_normal((n_samples, Xs.shape[0])) @ Lc.T
