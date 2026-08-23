"""The synthetic 2-D unlabelled pool shared by the query-strategy figures.

Two elongated clusters plus a handful of deliberate outliers sitting in empty
space.  Every strategy figure runs on THIS pool so the comparisons are honest,
and the outliers are what make figure 5 (the outlier trap) work.
"""
import numpy as np

N_POOL = 500
N_OUTLIERS = 10


def make_pool(seed=7):
    """Return (X, y, is_outlier).  y is a binary class label."""
    rng = np.random.default_rng(seed)
    n = (N_POOL - N_OUTLIERS) // 2

    def elong(cx, cy, angle, sx, sy, k):
        pts = rng.normal(size=(k, 2)) * np.array([sx, sy])
        c, s = np.cos(angle), np.sin(angle)
        R = np.array([[c, -s], [s, c]])
        return pts @ R.T + np.array([cx, cy])

    A = elong(-1.15, -0.35, 0.55, 0.78, 0.30, n)          # class 0
    B = elong(1.15, 0.45, 0.55, 0.78, 0.30, N_POOL - N_OUTLIERS - n)  # class 1

    # Outliers: far from both clusters.  The first TWO sit almost exactly ON the
    # decision boundary of logistic_posterior() while being isolated -- they are
    # what makes figure 5 (the outlier trap) work, so do not move them without
    # re-checking that figure.
    out = np.array([[2.40, 3.20], [-2.60, -3.15],
                    [-0.10, 2.45], [0.35, 2.15], [-0.55, -2.35], [0.10, -2.60],
                    [-3.05, 1.55], [3.10, -1.35], [2.75, 2.05], [-2.85, -1.85]])

    X = np.vstack([A, B, out])
    y = np.concatenate([np.zeros(len(A)), np.ones(len(B)),
                        (out[:, 0] > 0).astype(float)])
    is_out = np.concatenate([np.zeros(len(A) + len(B), bool),
                             np.ones(len(out), bool)])
    idx = rng.permutation(len(X))
    return X[idx], y[idx], is_out[idx]


def logistic_posterior(X, w=(0.95, -0.75), b=0.12):
    """A fixed 'trained model': P(class 1 | x).  Boundary runs between the clusters."""
    z = X @ np.array(w) + b
    return 1.0 / (1.0 + np.exp(-z))


def decision_boundary(w=(0.95, -0.75), b=0.12, xlim=(-3.6, 3.6)):
    """Return (xs, ys) tracing P = 0.5."""
    w = np.asarray(w, dtype=float)
    xs = np.linspace(*xlim, 200)
    ys = -(w[0] * xs + b) / w[1]
    return xs, ys
