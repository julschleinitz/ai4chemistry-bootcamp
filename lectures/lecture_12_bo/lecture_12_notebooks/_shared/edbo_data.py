"""Loader for the EDBO direct-arylation dataset (Shields et al., Nature 2021).

The full dataset is reaction 3 from the paper — the one used for the
human-versus-machine benchmark. 1,728 experiments, exhaustively measured:

    12 ligands x 4 bases x 4 solvents x 3 temperatures x 3 concentrations

Because the design is exhaustive, the ground truth is known, so any
optimization strategy can be replayed offline and instantly.

Source (public, no authentication):
  https://github.com/b-shields/edbo/tree/master/experiments/data
  raw: .../master/experiments/data/direct_arylation/experiment_index.csv

`load()` downloads and caches. If there is no network, it falls back to
`CACHED_LIGANDS` / `CACHED_BASES` / `CACHED_SOLVENTS` below, which are
transcribed verbatim from that file and are enough for the encoding figure.
"""
import os
import numpy as np
import pandas as pd

URL = ("https://raw.githubusercontent.com/b-shields/edbo/master/"
       "experiments/data/direct_arylation/experiment_index.csv")
CACHE = os.path.join(os.path.dirname(__file__), "cache_direct_arylation.csv")

# --- verbatim from the dataset (rows 0-5 give six of the twelve ligands) -----
# Names assigned by matching against Fig. 4a of the paper.
CACHED_LIGANDS = {
    "BrettPhos":
        "CC(C)C1=CC(C(C)C)=C(C(C(C)C)=C1)C2=C(P(C3CCCCC3)C4CCCCC4)C(OC)=CC=C2OC",
    "PPh(t-Bu)2":
        "CC(C)(C)P(C1=CC=CC=C1)C(C)(C)C",
    "t-BuPh-CPhos":
        "CN(C)C1=CC=CC(N(C)C)=C1C2=CC=CC=C2P(C(C)(C)C)C3=CC=CC=C3",
    "PCy3":
        "P(C1CCCCC1)(C2CCCCC2)C3CCCCC3",
    "PPh3":
        "P(C1=CC=CC=C1)(C2=CC=CC=C2)C3=CC=CC=C3",
    "XPhos":
        "CC(C1=C(C2=CC=CC=C2P(C3CCCCC3)C4CCCCC4)C(C(C)C)=CC(C(C)C)=C1)C",
}
CACHED_BASES = {
    "KOAc":   "O=C([O-])C.[K+]",
    "KOPiv":  "O=C([O-])C(C)(C)C.[K+]",
    "CsOAc":  "O=C([O-])C.[Cs+]",
    "CsOPiv": "O=C([O-])C(C)(C)C.[Cs+]",
}
CACHED_SOLVENTS = {
    "DMAc":      "CC(N(C)C)=O",
    "BuCN":      "CCCC#N",
    "BuOAc":     "CCCCOC(C)=O",
    "p-xylene":  "CC1=CC=C(C)C=C1",
}
TEMPS = [90.0, 105.0, 120.0]
CONCS = [0.057, 0.100, 0.153]


def load(url=URL, cache=CACHE):
    """Return the full 1,728-row DataFrame, downloading once and caching."""
    if os.path.exists(cache):
        return pd.read_csv(cache)
    df = pd.read_csv(url)                       # needs network
    df.to_csv(cache, index=False)
    return df


def available():
    """True if the full dataset can be loaded right now."""
    try:
        load()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- descriptors
_ELEMENTS = ["C", "N", "O", "F", "P", "S", "Cl", "Br"]


def smiles_descriptors(smi):
    """A handful of countable, unambiguous descriptors, computed by parsing the
    SMILES string directly. No RDKit needed, and every number is checkable by
    hand from the string.

    This is *not* what the paper uses — Shields et al. use DFT-derived steric
    and electronic descriptors (and Mordred as an alternative). The point of the
    figure this feeds is the CONTRAST WITH ONE-HOT, not the specific descriptor
    set. Swap in better descriptors and the conclusion only gets stronger.
    """
    s = smi
    counts = {}
    # two-letter elements first so Cl/Br are not miscounted as C/B
    tmp = s.replace("Cl", "@").replace("Br", "#")
    counts["nCl"] = tmp.count("@")
    counts["nBr"] = tmp.count("#")
    counts["nC"] = tmp.count("C") + tmp.count("c")
    counts["nN"] = tmp.count("N") + tmp.count("n")
    counts["nO"] = tmp.count("O") + tmp.count("o")
    counts["nF"] = tmp.count("F")
    counts["nP"] = tmp.count("P") + tmp.count("p")
    # These SMILES are written in Kekule form (C1=CC=CC=C1), so lowercase
    # aromatic atoms never appear. Count double bonds instead: it separates
    # saturated ligands (PCy3, 0) from aryl ones (PPh3, 9) cleanly.
    counts["n_double"] = tmp.count("=")
    counts["n_ring_bonds"] = sum(ch.isdigit() for ch in tmp) // 2
    counts["n_branch"] = tmp.count("(")
    heavy = counts["nC"] + counts["nN"] + counts["nO"] + counts["nF"] + \
        counts["nP"] + counts["nCl"] + counts["nBr"]
    counts["n_heavy"] = heavy
    counts["frac_unsat"] = counts["n_double"] / max(heavy, 1)
    return counts


DESC_KEYS = ["n_heavy", "n_ring_bonds", "n_double", "frac_unsat",
             "nO", "nN", "nF", "n_branch"]


def descriptor_matrix(smiles_dict, keys=DESC_KEYS):
    names = list(smiles_dict)
    rows = []
    for n in names:
        d = smiles_descriptors(smiles_dict[n])
        rows.append([d[k] for k in keys])
    return names, np.asarray(rows, float), keys


def onehot_matrix(names):
    return np.eye(len(names))


def zscore(A):
    A = np.asarray(A, float)
    sd = A.std(0)
    sd[sd == 0] = 1.0
    return (A - A.mean(0)) / sd


def pca_2d(A):
    """Plain PCA via SVD — no sklearn."""
    Z = zscore(A)
    U, S, Vt = np.linalg.svd(Z - Z.mean(0), full_matrices=False)
    scores = U[:, :2] * S[:2]
    var = (S ** 2) / (S ** 2).sum()
    return scores, var[:2], Vt[:2]


def pairwise(A):
    A = np.asarray(A, float)
    return np.sqrt(((A[:, None, :] - A[None, :, :]) ** 2).sum(-1))
