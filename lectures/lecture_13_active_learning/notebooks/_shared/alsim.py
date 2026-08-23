"""A small, honest active-learning simulation used by figures 14, 15 and 16.

Everything is numpy: L2-regularised logistic regression trained by gradient
descent, on a 2-D pool with a curved true boundary.  Four query strategies:
random, uncertainty (margin to the boundary), core-set (k-centre greedy) and a
BADGE-style gradient-embedding + k-means++ sampler.

This is a SIMULATION, not a chemistry benchmark.  Any figure built from it must
say so on the axes.
"""
import numpy as np


# ----------------------------------------------------------------- the problem
def make_task(n=1400, seed=3, label_noise=0.06):
    """2-D pool, curved true boundary, a slab of irreducible label noise."""
    rng = np.random.default_rng(seed)
    X = rng.uniform(-3, 3, size=(n, 2))
    margin = X[:, 1] - (0.55 * X[:, 0] ** 2 - 1.15)     # curved boundary
    p = 1.0 / (1.0 + np.exp(-2.6 * margin))
    y = (rng.random(n) < p).astype(float)
    # extra aleatoric noise in a band, so uncertainty sampling has something to
    # waste money on
    band = np.abs(X[:, 0] + 2.1) < 0.55
    flip = band & (rng.random(n) < 0.42)
    y[flip] = 1 - y[flip]
    flip2 = rng.random(n) < label_noise
    y[flip2] = 1 - y[flip2]
    return X, y


def features(X):
    """Quadratic lift, so the linear model can represent the curved boundary."""
    return np.column_stack([np.ones(len(X)), X[:, 0], X[:, 1],
                            X[:, 0] ** 2, X[:, 0] * X[:, 1]])


# ------------------------------------------------------------------ the model
class LogReg:
    def __init__(self, lam=2e-2, steps=320, lr=0.55):
        self.lam, self.steps, self.lr = lam, steps, lr

    def fit(self, Phi, y):
        w = np.zeros(Phi.shape[1])
        n = max(len(y), 1)
        for _ in range(self.steps):
            p = 1.0 / (1.0 + np.exp(-Phi @ w))
            g = Phi.T @ (p - y) / n + self.lam * w
            w -= self.lr * g
        self.w = w
        return self

    def prob(self, Phi):
        return 1.0 / (1.0 + np.exp(-Phi @ self.w))


# -------------------------------------------------------------- the strategies
def _kcenter(Phi, chosen, k):
    """k-centre greedy (farthest-first traversal)."""
    picked = []
    if len(chosen) == 0:
        d = np.full(len(Phi), np.inf)
    else:
        d = np.linalg.norm(Phi[:, None, :] - Phi[None, chosen, :], axis=2).min(1)
    for _ in range(k):
        j = int(np.argmax(d))
        picked.append(j)
        dj = np.linalg.norm(Phi - Phi[j], axis=1)
        d = np.minimum(d, dj)
        d[j] = -np.inf
    return picked


def _kmeanspp(G, k, rng):
    """k-means++ (D^2) seeding on the gradient embedding -- this is BADGE."""
    n = len(G)
    first = int(rng.integers(n))
    picked = [first]
    d2 = np.sum((G - G[first]) ** 2, axis=1)
    for _ in range(k - 1):
        pr = d2 / max(d2.sum(), 1e-12)
        j = int(rng.choice(n, p=pr))
        picked.append(j)
        d2 = np.minimum(d2, np.sum((G - G[j]) ** 2, axis=1))
    return picked


def select(strategy, Phi, labelled, model, batch, rng):
    """Return `batch` indices drawn from the unlabelled part of the pool."""
    unl = np.setdiff1d(np.arange(len(Phi)), labelled)
    if strategy == "random" or model is None:
        return rng.choice(unl, size=batch, replace=False)

    p = model.prob(Phi[unl])
    unc = 1.0 - np.abs(2 * p - 1.0)                 # 1 at the boundary

    if strategy == "uncertainty":
        return unl[np.argsort(-unc)[:batch]]

    if strategy == "coreset":
        sub = _kcenter(Phi, list(labelled), batch * 3)
        sub = [j for j in sub if j in set(unl.tolist())][:batch]
        while len(sub) < batch:
            extra = int(rng.choice(unl))
            if extra not in sub:
                sub.append(extra)
        return np.array(sub)

    if strategy == "badge":
        # gradient of the CE loss wrt the last layer, at the hallucinated label:
        # g = (p - e_yhat) (x) phi   ->   direction = phi, length = |p - yhat|
        yhat = (p > 0.5).astype(float)
        G = (p - yhat)[:, None] * Phi[unl]
        return unl[_kmeanspp(G, batch, rng)]

    raise ValueError(strategy)


# ------------------------------------------------------------------ the loop
def run(strategy, X, y, n_seed=8, batch=8, rounds=22, seed=0, test_idx=None):
    """One campaign.  Returns per-round test error and pool-measured error."""
    rng = np.random.default_rng(1000 + seed)
    Phi = features(X)
    pool_idx = np.setdiff1d(np.arange(len(X)), test_idx)

    labelled = list(rng.choice(pool_idx, size=n_seed, replace=False))
    n_seen, test_err, pool_err = [], [], []

    for r in range(rounds + 1):
        m = LogReg().fit(Phi[labelled], y[labelled])
        pt = m.prob(Phi[test_idx])
        test_err.append(float(np.mean((pt > 0.5) != (y[test_idx] > 0.5))))
        pl = m.prob(Phi[labelled])
        pool_err.append(float(np.mean((pl > 0.5) != (y[labelled] > 0.5))))
        n_seen.append(len(labelled))
        if r == rounds:
            break
        cand = select(strategy, Phi[pool_idx], np.array(
            [int(np.where(pool_idx == i)[0][0]) for i in labelled]), m, batch, rng)
        labelled += [int(pool_idx[c]) for c in cand]

    return dict(n=np.array(n_seen), test_err=np.array(test_err),
                pool_err=np.array(pool_err), labelled=np.array(labelled))


def replicate(strategy, X, y, test_idx, n_rep=12, **kw):
    """Mean and sd of the test-error curve over independent runs."""
    runs = [run(strategy, X, y, seed=s, test_idx=test_idx, **kw) for s in range(n_rep)]
    E = np.stack([r["test_err"] for r in runs])
    P = np.stack([r["pool_err"] for r in runs])
    return dict(n=runs[0]["n"], mean=E.mean(0), sd=E.std(0),
                pool_mean=P.mean(0), pool_sd=P.std(0))
