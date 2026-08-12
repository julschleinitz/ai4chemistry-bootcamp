#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the two notebooks for Tutorial 7 (Learned Representations) from a single
source, so the exercise and solution versions can never drift apart:

    ../learned-representations.ipynb            (exercise version)
    ../learned-representations_solutions.ipynb  (solution version)

Cells are declared once. A cell whose `sol` is None is copied verbatim into both
notebooks; a cell with both `src` and `sol` becomes the stub in the exercise
notebook and the worked answer in the solution notebook. Cell counts therefore
always match, which keeps them easy to diff in class.

    python build_notebook.py
"""
import json
from pathlib import Path

CELLS = []


def md(text):
    CELLS.append(("markdown", text.strip("\n"), None))


def code(src, sol=None):
    CELLS.append(("code", src.strip("\n"), sol.strip("\n") if sol else None))


# =====================================================================
md(r"""
<a href="https://colab.research.google.com/github/julschleinitz/ai4chemistry-bootcamp/blob/main/tutorials/learned-representations.ipynb" target="_parent">
<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>
""")

md(r"""
# Tutorial 7: Learned Representations — unsupervised structure and transfer learning

Hands-on companion to **Lecture 7 · Learned Representations**.

In the lecture we argued three things. This notebook makes you test all three on
the same dataset, so you leave with numbers rather than impressions.

1. **Unsupervised methods find real structure — but a 2-D map is a picture of your
   fingerprint, not of chemistry.**
2. **A pre-trained encoder gives you a representation for free.** No labels, no
   training: download weights, push molecules through, keep the vectors.
3. **Pre-training is a prior.** It is worth a lot when you have ~100 labels and
   close to nothing when you have thousands — and the crossover is something you
   measure, not something you look up.

## Learning goals

- Featurize a real dataset with ECFP4 and inspect it with PCA, UMAP and clustering
- See for yourself that neighbour embeddings invent clusters in pure noise
- Count Bemis–Murcko scaffolds and understand why a **scaffold split** is not optional
- Extract frozen embeddings from a pre-trained chemical language model (ChemBERTa)
- Compare a hand-crafted and a learned representation *without training anything*
- Run the three-way head-to-head: ECFP + random forest vs frozen embeddings vs both
- **Measure the learning-curve crossover on your own data** — the key result
- Find the activity-cliff pairs that break every smooth representation

## What this notebook deliberately does not do

We never update the encoder's weights. Everything here is the **frozen** setting
from the lecture's "three knobs" slide — because it is the cheapest, it is the
right first experiment, and it is impossible to fool yourself with. Gradient
fine-tuning is Thursday of week 2 (*Fine-tuning ChemBERTa*).

---
""")

md(r"""
## References & tools used

- **Lipophilicity** (MoleculeNet) — 4,200 compounds with experimental octanol/water
  distribution coefficients (logD at pH 7.4), curated from ChEMBL.
  Wu, Z. *et al.* "MoleculeNet: a benchmark for molecular machine learning."
  *Chem. Sci.* **2018**, 9, 513. DOI 10.1039/C7SC02664A
- **ChemBERTa-2** — Ahmad, W.; Simon, E.; Chithrananda, S.; Grand, G.; Ramsundar, B.
  "ChemBERTa-2: Towards Chemical Foundation Models." arXiv:2209.01712 (2022).
  We use the `DeepChem/ChemBERTa-77M-MTR` checkpoint (77 M PubChem SMILES,
  multi-task-regression pre-training).
- **ECFP / Morgan fingerprints** — Rogers, D.; Hahn, M. *J. Chem. Inf. Model.*
  **2010**, 50, 742. DOI 10.1021/ci100050t
- **Butina clustering** — Butina, D. *J. Chem. Inf. Comput. Sci.* **1999**, 39, 747.
- **Bemis–Murcko scaffolds** — Bemis, G. W.; Murcko, M. A. *J. Med. Chem.* **1996**,
  39, 2887.
- **Why deep models often lose to fingerprints** — Deng, J. *et al.* *Nat. Commun.*
  **2023**, 14, 6395 · Praski, M.; Adamczyk, J.; Czech, W. arXiv:2508.06199 (2025).
- **How to misread t-SNE** — Wattenberg, Viégas & Johnson, *Distill* 2016,
  https://distill.pub/2016/misread-tsne/

Software: RDKit, scikit-learn, UMAP, HuggingFace `transformers`, PyTorch, pandas,
matplotlib.

---
""")

md(r"""
## 0 · Setup

Run once. Colab already has PyTorch, pandas, scikit-learn and matplotlib; we add
RDKit, `transformers` and `umap-learn`.
""")

code(r"""
# --- Cell: dependency installation (Colab) ---
# Safe to re-run: pip is a no-op when the packages are already present.
!pip -q install rdkit transformers umap-learn > /dev/null
print("dependencies ready")
""")

code(r"""
# --- Cell: imports, seed and compute device ---
import os
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator, Draw
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.ML.Cluster import Butina

from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

import torch

RDLogger.DisableLog("rdApp.*")          # RDKit is chatty about sanitization
SEED = 0
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("torch", torch.__version__, "| device:", DEVICE)

# House palette, so the plots match the lecture slides.
TEAL, ORANGE, PURPLE, GRAY, RED = "#156082", "#E97132", "#A02B93", "#6E7480", "#C0392B"
plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False,
                     "axes.spines.right": False})
""")

code(r"""
# --- Cell: locate the dataset, whether on Colab or running locally ---
# Order of preference:
#   1. a local copy next to the notebook (fastest, works offline)
#   2. the bootcamp repo on GitHub  (what Colab will normally use)
#   3. the MoleculeNet original on the DeepChem S3 bucket (last resort)
LOCAL_CANDIDATES = [
    "learned-representations/lipophilicity.csv",
    "lipophilicity.csv",
    "../learned-representations/lipophilicity.csv",
]
REMOTE_CANDIDATES = [
    "https://raw.githubusercontent.com/julschleinitz/ai4chemistry-bootcamp/"
    "main/tutorials/learned-representations/lipophilicity.csv",
    "https://deepchemdata.s3.us-west-1.amazonaws.com/datasets/Lipophilicity.csv",
]


def load_lipophilicity():
    for path in LOCAL_CANDIDATES:
        if os.path.exists(path):
            print("loaded local copy:", path)
            return pd.read_csv(path)
    for url in REMOTE_CANDIDATES:
        try:
            df = pd.read_csv(url)
            print("downloaded:", url)
            return df
        except Exception as exc:                       # noqa: BLE001
            print("could not fetch", url, "->", type(exc).__name__)
    raise RuntimeError("Lipophilicity.csv not found — see LOCAL_CANDIDATES above.")


raw = load_lipophilicity()
print(raw.shape)
raw.head()
""")

md(r"""
---
## 1 · The dataset

**Lipophilicity** from MoleculeNet: 4,200 molecules with a measured logD at pH 7.4.

Why this dataset for this tutorial:

- It is a **regression** task, so the learning curve is easy to read (RMSE in log units).
- It is *just* big enough to bracket the crossover we care about — a few hundred to
  a few thousand labelled molecules is exactly the interesting regime.
- Lipophilicity is a whole-molecule, fairly smooth property. That makes it a
  **friendly** case for learned representations. Keep that in mind at the end:
  if pre-training struggles here, it will not do better on a spiky assay endpoint.

The columns are `CMPD_CHEMBLID`, `exp` (the logD value) and `smiles`.
""")

code(r"""
# --- Exercise 1: tidy the dataframe and look at the label distribution ---
# your code here!
#
# 1. Build `df` from `raw` with just two columns: "smiles" and "y" (= the `exp`
#    column). Drop rows whose SMILES fail to parse with Chem.MolFromSmiles.
# 2. Add a "mol" column holding the RDKit Mol objects (you will reuse them a lot).
# 3. Print the number of molecules and y.describe().
# 4. Plot a histogram of y.
#
# Hint: df["mol"] = df["smiles"].apply(Chem.MolFromSmiles), then drop the Nones.

raise NotImplementedError
""", r"""
# --- Exercise 1 solution: tidy the dataframe and look at the label distribution ---
df = raw.rename(columns={"exp": "y"})[["smiles", "y"]].copy()
df["mol"] = df["smiles"].apply(Chem.MolFromSmiles)

n_before = len(df)
df = df[df["mol"].notna()].reset_index(drop=True)
print(f"{n_before - len(df)} SMILES failed to parse; {len(df)} molecules kept")
print(df["y"].describe())

fig, ax = plt.subplots(figsize=(5.5, 3.2))
ax.hist(df["y"], bins=45, color=TEAL, edgecolor="white")
ax.set_xlabel("experimental logD (pH 7.4)")
ax.set_ylabel("molecules")
ax.set_title("Lipophilicity label distribution")
plt.tight_layout()
plt.show()
""")

md(r"""
---
## 2 · Part A — unsupervised structure

No labels are used anywhere in this section. We are asking what the *shape* of the
data looks like, which is something we could do for millions of molecules if we
wanted to, because it costs nothing but compute.
""")

code(r"""
# --- Exercise 2: featurize with ECFP4 ---
# your code here!
#
# 1. Create a Morgan fingerprint generator with radius=2 and fpSize=2048 using
#    rdFingerprintGenerator.GetMorganGenerator(...).
#    (radius 2 over a 2048-bit vector is what everyone means by "ECFP4".)
# 2. Build `X_ecfp`, a float32 numpy array of shape (n_molecules, 2048), using
#    gen.GetFingerprintAsNumPy(mol) for each molecule.
# 3. Also keep `fps_bv`, the list of RDKit ExplicitBitVect objects
#    (gen.GetFingerprint(mol)) — Tanimoto similarity needs these, not the arrays.
# 4. Print the shape of X_ecfp and the mean number of bits set per molecule.

raise NotImplementedError
""", r"""
# --- Exercise 2 solution: featurize with ECFP4 ---
gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

X_ecfp = np.array([gen.GetFingerprintAsNumPy(m) for m in df["mol"]], dtype=np.float32)
fps_bv = [gen.GetFingerprint(m) for m in df["mol"]]

print("X_ecfp:", X_ecfp.shape)
print(f"mean bits set per molecule: {X_ecfp.sum(1).mean():.1f} out of 2048 "
      f"({100 * X_ecfp.mean():.2f}% density)")
print(f"bits never set in the whole dataset: {(X_ecfp.sum(0) == 0).sum()}")
""")

md(r"""
### 2.1 PCA — the honest baseline

PCA is a rotation. It is linear, deterministic and invertible, and the scree plot
tells you exactly how much you are throwing away when you look at two components.
""")

code(r"""
# --- Exercise 3: PCA on the fingerprints ---
# your code here!
#
# 1. Fit PCA(n_components=50) on X_ecfp and transform it -> `Z_pca`.
# 2. Left panel: scatter Z_pca[:, 0] vs Z_pca[:, 1], coloured by df["y"],
#    with a colorbar. s=6, alpha=0.6 looks about right for 4k points.
# 3. Right panel: bar chart of the first 20 explained_variance_ratio_ values.
# 4. Print the cumulative variance explained by 2 and by 50 components.
#
# Question to answer in your head before you run it: how much of a 2048-bit
# fingerprint do you expect two linear components to capture?

raise NotImplementedError
""", r"""
# --- Exercise 3 solution: PCA on the fingerprints ---
pca = PCA(n_components=50, random_state=SEED)
Z_pca = pca.fit_transform(X_ecfp)

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
sc = ax[0].scatter(Z_pca[:, 0], Z_pca[:, 1], c=df["y"], s=6, alpha=0.6, cmap="viridis")
ax[0].set_xlabel("PC1"); ax[0].set_ylabel("PC2")
ax[0].set_title("ECFP4 in its first two principal components")
fig.colorbar(sc, ax=ax[0], label="logD")

evr = pca.explained_variance_ratio_
ax[1].bar(range(1, 21), 100 * evr[:20], color=TEAL)
ax[1].set_xlabel("component"); ax[1].set_ylabel("variance explained (%)")
ax[1].set_title("Scree plot")
plt.tight_layout()
plt.show()

print(f"2 components  : {100 * evr[:2].sum():5.1f}% of the variance")
print(f"50 components : {100 * evr.sum():5.1f}% of the variance")
""")

md(r"""
**Read the numbers, not the picture.** On sparse binary fingerprints two components
typically capture only a few percent of the variance — far less than the
"2 components ≈ 60%" you would get on a handful of physicochemical descriptors.
Sparse bit vectors are near-orthogonal by construction, so there simply is no
low-dimensional *linear* structure to find. That is the motivation for nonlinear
neighbour embeddings.

### 2.2 t-SNE — and the control experiment nobody runs
""")

code(r"""
# --- Exercise 4: a chemical space map, plus the noise control ---
# your code here!
#
# Make a figure with three panels:
#   (a) t-SNE of the first 50 PCs of X_ecfp, coloured by logD.
#       Use TSNE(n_components=2, init="pca", perplexity=30, random_state=SEED)
#       and fit it on Z_pca (running t-SNE on the raw 2048 bits is slow and no better).
#   (b) The same t-SNE, but with perplexity=5. Same data, different picture.
#   (c) THE CONTROL: t-SNE of a matrix of *uniform random numbers* with the same
#       shape as Z_pca. No structure exists in this data at all.
#
# Then look at panel (c) and ask yourself whether you would have believed those
# clusters if someone had put them in a paper.

raise NotImplementedError
""", r"""
# --- Exercise 4 solution: a chemical space map, plus the noise control ---
def run_tsne(M, perplexity):
    return TSNE(n_components=2, init="pca", perplexity=perplexity,
                random_state=SEED).fit_transform(M)


t0 = time.time()
E30 = run_tsne(Z_pca, 30)
E05 = run_tsne(Z_pca, 5)
noise = np.random.rand(*Z_pca.shape)
ENZ = run_tsne(noise, 30)
print(f"three t-SNE runs in {time.time() - t0:.0f} s")

fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
for a, (E, title) in zip(ax, [(E30, "ECFP4 · perplexity 30"),
                              (E05, "ECFP4 · perplexity 5"),
                              (ENZ, "UNIFORM RANDOM NOISE · perplexity 30")]):
    c = df["y"] if E is not ENZ else GRAY
    s = a.scatter(E[:, 0], E[:, 1], c=c, s=5, alpha=0.6,
                  cmap=None if E is ENZ else "viridis")
    a.set_title(title, fontsize=10)
    a.set_xticks([]); a.set_yticks([]); a.grid(False)
    if E is not ENZ:
        fig.colorbar(s, ax=a, label="logD")
ax[2].set_title("UNIFORM RANDOM NOISE · perplexity 30", color=RED, fontsize=10)
plt.tight_layout()
plt.show()

print("Panels (a) and (b) are the SAME molecules and the SAME fingerprint.")
print("Panel (c) contains no structure whatsoever — and still looks clustered.")
""")

md(r"""
Three habits to take away from that figure:

1. **Never read clusters off a map.** If clustering matters to your argument, run a
   clustering algorithm in the original space and use the map only to display it.
2. **Report your hyperparameters.** A t-SNE without a stated perplexity, or a UMAP
   without `n_neighbors` and `min_dist`, is not reproducible.
3. **Run the noise control once in your life** so you never forget what it looks like.

### 2.3 Butina clustering — structure you can defend
""")

code(r"""
# --- Exercise 5: Butina clustering across a range of cut-offs ---
# your code here!
#
# 1. Write tanimoto_dists(fps) that returns the condensed lower-triangle distance
#    list RDKit's Butina wants:
#        for i in 1..n-1:  1 - DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
#    Flatten those into one long list.
# 2. For cutoff in [0.3, 0.4, 0.5, 0.6, 0.7], call
#        Butina.ClusterData(dists, n, cutoff, isDistData=True)
#    and record: number of clusters, size of the largest, and the number of
#    singletons.
# 3. Print the table. Which cut-off would you use to pick a diverse subset?
#
# Note: this is O(n^2). On all 4,200 molecules that is 8.8 M pairs and a few
# hundred MB, so cluster a random subsample of CLUSTER_N = 2500 instead — the
# conclusion is identical and it runs in well under a minute.

raise NotImplementedError
""", r"""
# --- Exercise 5 solution: Butina clustering across a range of cut-offs ---
def tanimoto_dists(fps):
    '''Condensed lower-triangle distance list, the format Butina.ClusterData wants.'''
    out = []
    for i in range(1, len(fps)):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        out.extend(1.0 - s for s in sims)
    return out


CLUSTER_N = 2500
sub_idx = np.random.default_rng(SEED).choice(len(fps_bv), CLUSTER_N, replace=False)
fps_sub = [fps_bv[i] for i in sub_idx]

t0 = time.time()
dists = tanimoto_dists(fps_sub)
print(f"{len(dists):,} pairwise distances in {time.time() - t0:.0f} s")

rows = []
for cutoff in [0.3, 0.4, 0.5, 0.6, 0.7]:
    cl = Butina.ClusterData(dists, len(fps_sub), cutoff, isDistData=True)
    sizes = [len(c) for c in cl]
    rows.append({"cutoff": cutoff, "clusters": len(cl), "largest": max(sizes),
                 "singletons": sum(s == 1 for s in sizes),
                 "% singletons": round(100 * sum(s == 1 for s in sizes) / len(cl), 1)})

butina_table = pd.DataFrame(rows)
print(butina_table.to_string(index=False))
print("\\nThe cut-off is not a detail: it changes the number of clusters severalfold.")
""")

md(r"""
### 2.4 Bemis–Murcko scaffolds — why random splits lie

In the lecture: 32 frameworks cover half of all known drugs. Let us see how
concentrated *this* dataset is.
""")

code(r"""
# --- Exercise 6: scaffold counts and the cumulative coverage curve ---
# your code here!
#
# 1. Add a "scaffold" column using
#        MurckoScaffold.MurckoScaffoldSmiles(mol=m, includeChirality=False)
#    (wrap it in try/except and fall back to "" for the odd molecule that fails).
# 2. Print how many distinct scaffolds there are and the size of the 5 largest groups.
# 3. Plot the cumulative fraction of molecules covered as you add scaffolds in
#    decreasing size order. Mark how many scaffolds it takes to cover 50%.
#
# This is the same figure as the Bemis-Murcko slide, computed on your own data.

raise NotImplementedError
""", r"""
# --- Exercise 6 solution: scaffold counts and the cumulative coverage curve ---
def murcko(m):
    try:
        return MurckoScaffold.MurckoScaffoldSmiles(mol=m, includeChirality=False)
    except Exception:                                   # noqa: BLE001
        return ""


df["scaffold"] = df["mol"].apply(murcko)
groups = df.groupby("scaffold").size().sort_values(ascending=False)

print(f"{len(df)} molecules -> {len(groups)} distinct Bemis-Murcko scaffolds")
print(f"molecules per scaffold: mean {len(df) / len(groups):.2f}, max {groups.iloc[0]}")
print("\\n5 most common scaffolds:")
print(groups.head())

cum = np.cumsum(groups.values) / len(df)
n_half = int(np.searchsorted(cum, 0.5) + 1)

fig, ax = plt.subplots(figsize=(6, 3.6))
ax.plot(np.arange(1, len(cum) + 1), 100 * cum, color=TEAL, lw=2)
ax.axhline(50, color=GRAY, ls=":", lw=1)
ax.axvline(n_half, color=ORANGE, ls="--", lw=1.5)
ax.set_xlabel("number of scaffolds (largest first)")
ax.set_ylabel("% of molecules covered")
ax.set_title(f"{n_half} scaffolds cover half the dataset")
plt.tight_layout()
plt.show()

print(f"\\n{n_half} scaffolds ({100 * n_half / len(groups):.1f}% of them) cover 50% "
      f"of the molecules.")
print("A random split therefore puts near-identical analogues on both sides of the "
      "train/test line.")
""")

md(r"""
---
## 3 · Part B — a learned representation, for free

Now the other half of the lecture. We download a chemical language model that
someone else pre-trained on 77 million PubChem SMILES, push our 4,200 molecules
through it, and keep the vectors.

**We do not train anything.** No labels are involved. This is the "frozen" column
of the three-knobs slide, and it takes about a minute.
""")

code(r"""
# --- Exercise 7: frozen ChemBERTa embeddings ---
# your code here!
#
# 1. Load the tokenizer and model:
#        from transformers import AutoTokenizer, AutoModel
#        MODEL_ID = "DeepChem/ChemBERTa-77M-MTR"
#    Put the model on DEVICE and call .eval(). (You will see a warning that some
#    checkpoint weights were not used — that is the regression head we are
#    deliberately throwing away. Exactly the "keep the encoder" slide.)
# 2. Write embed(smiles_list, batch_size=64) that, under torch.no_grad():
#      - tokenizes a batch with padding=True, truncation=True, max_length=256
#      - runs the model
#      - MEAN-POOLS last_hidden_state over the tokens, weighting by attention_mask
#        so padding does not contribute
#      - returns a float32 numpy array
# 3. Build `X_bert` for all of df["smiles"] and print its shape.
#
# Mean pooling with a mask:
#     h = out.last_hidden_state                       # (B, T, H)
#     m = mask.unsqueeze(-1).float()                  # (B, T, 1)
#     pooled = (h * m).sum(1) / m.sum(1).clamp(min=1e-9)

raise NotImplementedError
""", r"""
# --- Exercise 7 solution: frozen ChemBERTa embeddings ---
from transformers import AutoTokenizer, AutoModel

MODEL_ID = "DeepChem/ChemBERTa-77M-MTR"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
encoder = AutoModel.from_pretrained(MODEL_ID).to(DEVICE).eval()

n_params = sum(p.numel() for p in encoder.parameters())
print(f"{MODEL_ID}: {n_params/1e6:.1f} M parameters, hidden size "
      f"{encoder.config.hidden_size}")


@torch.no_grad()
def embed(smiles_list, batch_size=64):
    '''Mean-pooled last hidden state. The encoder stays frozen throughout.'''
    chunks = []
    for i in range(0, len(smiles_list), batch_size):
        batch = list(smiles_list[i:i + batch_size])
        tok = tokenizer(batch, padding=True, truncation=True, max_length=256,
                        return_tensors="pt").to(DEVICE)
        out = encoder(**tok)
        h = out.last_hidden_state                       # (B, T, H)
        m = tok["attention_mask"].unsqueeze(-1).float() # (B, T, 1)
        pooled = (h * m).sum(1) / m.sum(1).clamp(min=1e-9)
        chunks.append(pooled.cpu().numpy())
    return np.vstack(chunks).astype(np.float32)


t0 = time.time()
X_bert = embed(df["smiles"].tolist())
print(f"X_bert: {X_bert.shape}  ({time.time() - t0:.0f} s on {DEVICE})")
""")

md(r"""
### 3.1 Are the learned vectors *better*? Ask without training anything

Here is a cheap, training-free way to compare two representations. For each
molecule, find its **k nearest neighbours** in representation space and measure how
different their labels are. A representation in which neighbours share a property
is a representation a model can exploit.

$$\text{neighbourhood roughness} = \frac{1}{N}\sum_i \frac{1}{k}\sum_{j \in \mathcal{N}_k(i)} |y_i - y_j|$$

Lower is better. Compare it against the roughness you get from *random* pairs —
that is the number to beat.
""")

code(r"""
# --- Exercise 8: neighbourhood roughness, ECFP vs ChemBERTa ---
# your code here!
#
# 1. Write roughness(M, y, k=5, metric="euclidean") that:
#      - fits NearestNeighbors(n_neighbors=k+1, metric=metric) on M
#      - for every point, takes its k neighbours (excluding itself, i.e. drop
#        column 0 of the returned indices)
#      - returns the mean |y_i - y_j| over all those pairs
# 2. Compute it for:
#      - ECFP4 with metric="jaccard"   (Jaccard distance == 1 - Tanimoto).
#        Pass X_ecfp.astype(bool) — sklearn wants booleans for this metric.
#      - ChemBERTa embeddings, standardized, with metric="euclidean"
#      - a random baseline: mean |y_i - y_j| over randomly paired molecules
# 3. Print all three. Which representation puts chemically similar molecules
#    closer together *in the sense that matters for this label*?

raise NotImplementedError
""", r"""
# --- Exercise 8 solution: neighbourhood roughness, ECFP vs ChemBERTa ---
def roughness(M, y, k=5, metric="euclidean"):
    '''Mean |y_i - y_j| over each point's k nearest neighbours in M.'''
    nn = NearestNeighbors(n_neighbors=k + 1, metric=metric).fit(M)
    _, idx = nn.kneighbors(M)
    idx = idx[:, 1:]                                     # drop self
    y = np.asarray(y)
    return float(np.abs(y[:, None] - y[idx]).mean())


y_all = df["y"].values
X_bert_std = StandardScaler().fit_transform(X_bert)

r_ecfp = roughness(X_ecfp.astype(bool), y_all, k=5, metric="jaccard")
r_bert = roughness(X_bert_std, y_all, k=5, metric="euclidean")

rng = np.random.default_rng(SEED)
r_random = float(np.abs(y_all - y_all[rng.permutation(len(y_all))]).mean())

print(f"random pairs                : {r_random:.3f} log units   <- the number to beat")
print(f"ECFP4      (Tanimoto, k=5)  : {r_ecfp:.3f} log units")
print(f"ChemBERTa  (Euclidean, k=5) : {r_bert:.3f} log units")
print()
better = "ChemBERTa" if r_bert < r_ecfp else "ECFP4"
print(f"-> {better} neighbourhoods are smoother in logD.")
print("Both are far below the random baseline, which is the real message: both "
      "representations already encode a great deal about lipophilicity, with no "
      "training at all.")
""")

code(r"""
# --- Exercise 9 (optional, but it makes a nice slide): the two maps side by side ---
# your code here!
#
# Run UMAP on both representations and plot them next to each other, coloured by
# logD:
#     import umap
#     reducer = umap.UMAP(n_neighbors=25, min_dist=0.1, random_state=SEED, metric=...)
# Use metric="jaccard" for ECFP and metric="euclidean" for the standardized
# ChemBERTa embeddings.
#
# Do the two maps tell the same story? Remember the caveats from Exercise 4 before
# you answer.

raise NotImplementedError
""", r"""
# --- Exercise 9 solution: the two maps side by side ---
import umap

t0 = time.time()
U_ecfp = umap.UMAP(n_neighbors=25, min_dist=0.1, metric="jaccard",
                   random_state=SEED).fit_transform(X_ecfp.astype(bool))
U_bert = umap.UMAP(n_neighbors=25, min_dist=0.1, metric="euclidean",
                   random_state=SEED).fit_transform(X_bert_std)
print(f"two UMAP runs in {time.time() - t0:.0f} s")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
for a, (U, title) in zip(ax, [(U_ecfp, "ECFP4 (hand-crafted)"),
                              (U_bert, "ChemBERTa (learned, frozen)")]):
    s = a.scatter(U[:, 0], U[:, 1], c=y_all, s=5, alpha=0.65, cmap="viridis")
    a.set_title(title)
    a.set_xticks([]); a.set_yticks([]); a.grid(False)
    fig.colorbar(s, ax=a, label="logD")
plt.tight_layout()
plt.show()

print("ECFP maps tend to fragment into many small substructure islands; the "
      "language-model map is usually smoother, with logD varying more gradually "
      "across it. Neither picture is evidence on its own — Exercise 8 was the "
      "evidence, and Part C is the test.")
""")

md(r"""
---
## 4 · Part C — does any of it beat the baseline?

This is the part that decides what you should actually do in your own project.

Ground rules, both taken straight from the lecture:

- **Scaffold split.** Random splits scatter analogues across train and test and
  inflate every number on the page.
- **The baseline is ECFP + random forest.** Every claim is measured against it.
""")

code(r"""
# --- Exercise 10: a scaffold split ---
# your code here!
#
# Write scaffold_split(df, frac_train=0.8, seed=SEED) that:
#   1. groups the row indices by df["scaffold"]
#   2. sorts the groups from largest to smallest (the standard deterministic
#      "scaffold split"; the big, well-populated series go into training)
#   3. fills the train set until it reaches frac_train of the data, then puts
#      everything else in test
#   4. returns (train_idx, test_idx) as numpy arrays
#
# Then build train/test index arrays and check that NO scaffold appears on both
# sides — that assertion is the whole point of the exercise.

raise NotImplementedError
""", r"""
# --- Exercise 10 solution: a scaffold split ---
def scaffold_split(frame, frac_train=0.8, seed=SEED):
    '''Deterministic Bemis-Murcko scaffold split: whole scaffold groups are
    assigned to one side or the other, largest groups first.'''
    groups = {}
    for i, sc in enumerate(frame["scaffold"].values):
        groups.setdefault(sc, []).append(i)
    ordered = sorted(groups.values(), key=len, reverse=True)

    n_train = int(frac_train * len(frame))
    train, test = [], []
    for g in ordered:
        (train if len(train) + len(g) <= n_train else test).extend(g)

    frac = len(train) / len(frame)
    if abs(frac - frac_train) > 0.05:
        print(f"warning: realised train fraction {frac:.0%}, not {frac_train:.0%} — "
              "one scaffold group is too large to fit the budget.")
    return np.array(sorted(train)), np.array(sorted(test))


tr_idx, te_idx = scaffold_split(df)
sc_tr = set(df["scaffold"].values[tr_idx])
sc_te = set(df["scaffold"].values[te_idx])

print(f"train {len(tr_idx)}   test {len(te_idx)}")
print(f"scaffolds shared between train and test: {len(sc_tr & sc_te)}")
assert not (sc_tr & sc_te), "scaffold leakage!"
print("no scaffold leakage ✓")
""")

code(r"""
# --- Exercise 11: the head-to-head against the baseline ---
# your code here!
#
# On the SAME scaffold split, evaluate:
#   (a) ECFP4        + RandomForestRegressor(n_estimators=500, n_jobs=-1)
#   (b) ChemBERTa    + RidgeCV(alphas=np.logspace(-2, 4, 25))   <- the linear probe
#   (c) ChemBERTa    + RandomForestRegressor(n_estimators=500, n_jobs=-1)
#   (d) ECFP + ChemBERTa concatenated + RandomForest            <- do they add up?
#
# Report RMSE and R^2 for each in a small DataFrame, sorted by RMSE.
# Standardize the ChemBERTa features (fit the scaler on TRAIN only!).
#
# Write down your prediction before you run it.

raise NotImplementedError
""", r"""
# --- Exercise 11 solution: the head-to-head against the baseline ---
def evaluate(Xtr, ytr, Xte, yte, model):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    return {"RMSE": float(np.sqrt(mean_squared_error(yte, pred))),
            "R2": float(r2_score(yte, pred))}


# Scaler fitted on train only — fitting it on everything is a classic leak.
scaler = StandardScaler().fit(X_bert[tr_idx])
B_tr, B_te = scaler.transform(X_bert[tr_idx]), scaler.transform(X_bert[te_idx])
E_tr, E_te = X_ecfp[tr_idx], X_ecfp[te_idx]
y_tr, y_te = y_all[tr_idx], y_all[te_idx]

def rf():
    return RandomForestRegressor(n_estimators=500, n_jobs=-1, random_state=SEED)

results = {
    "ECFP4 + random forest  (BASELINE)": evaluate(E_tr, y_tr, E_te, y_te, rf()),
    "ChemBERTa + ridge  (linear probe)": evaluate(
        B_tr, y_tr, B_te, y_te, RidgeCV(alphas=np.logspace(-2, 4, 25))),
    "ChemBERTa + random forest":          evaluate(B_tr, y_tr, B_te, y_te, rf()),
    "ECFP4 + ChemBERTa + random forest":  evaluate(
        np.hstack([E_tr, B_tr]), y_tr, np.hstack([E_te, B_te]), y_te, rf()),
}

table = pd.DataFrame(results).T.sort_values("RMSE")
print(table.round(3).to_string())

base = results["ECFP4 + random forest  (BASELINE)"]["RMSE"]
best_name = table.index[0]
print(f"\\nbaseline RMSE {base:.3f} | best {best_name} "
      f"({table.iloc[0]['RMSE']:.3f}, {100 * (base - table.iloc[0]['RMSE']) / base:+.1f}%)")
""")

md(r"""
Whatever you got: notice how *small* the differences are compared with the way
these methods are usually described. That is the Praski et al. (2025) result
reproduced on a single dataset in a single afternoon.

### 4.1 The key experiment — where is the crossover?

This is the notebook version of the lecture's most important figure. Full training
set, then progressively starve both models and watch what happens.
""")

code(r"""
# --- Exercise 12: the learning curve, and the crossover ---
# your code here!
#
# 1. For each n in SIZES = [50, 100, 200, 400, 800, 1600, 3000] (capped at the
#    training-set size), and for each of N_REPEATS = 3 random subsamples of the
#    TRAINING indices:
#       - fit ECFP + random forest  and  ChemBERTa + ridge  on that subsample
#       - evaluate both on the FULL (fixed) scaffold test set
# 2. Collect mean and standard deviation of the test RMSE per (model, n).
# 3. Plot RMSE vs n on a log x-axis, with error bars.
# 4. Report the smallest n at which the baseline overtakes the pre-trained model
#    (or state that it never does).
#
# Reuse the `evaluate` helper and the `rf()` factory you wrote in Exercise 11.
# Keep the test set fixed throughout — only the training subsample changes.
# Runtime: a couple of minutes.

raise NotImplementedError
""", r"""
# --- Exercise 12 solution: the learning curve, and the crossover ---
SIZES = [n for n in [50, 100, 200, 400, 800, 1600, 3000] if n <= len(tr_idx)]
N_REPEATS = 3

curve = []
t0 = time.time()
for n in SIZES:
    for rep in range(N_REPEATS):
        rs = np.random.default_rng(1000 * rep + n)
        sub = rs.choice(len(tr_idx), size=n, replace=False)

        m1 = evaluate(E_tr[sub], y_tr[sub], E_te, y_te, rf())
        m2 = evaluate(B_tr[sub], y_tr[sub], B_te, y_te,
                      RidgeCV(alphas=np.logspace(-2, 4, 25)))
        curve.append({"n": n, "model": "ECFP4 + random forest", **m1})
        curve.append({"n": n, "model": "ChemBERTa (frozen) + ridge", **m2})
    print(f"  n = {n:5d} done")
print(f"learning curve in {time.time() - t0:.0f} s")

curve = pd.DataFrame(curve)
agg = curve.groupby(["model", "n"])["RMSE"].agg(["mean", "std"]).reset_index()

fig, ax = plt.subplots(figsize=(7, 4.4))
for model, color in [("ECFP4 + random forest", ORANGE),
                     ("ChemBERTa (frozen) + ridge", TEAL)]:
    g = agg[agg["model"] == model]
    ax.errorbar(g["n"], g["mean"], yerr=g["std"], marker="o", capsize=3,
                color=color, lw=2, label=model)
ax.set_xscale("log")
ax.set_xlabel("labelled training molecules")
ax.set_ylabel("test RMSE (log units), fixed scaffold test set")
ax.set_title("Where does pre-training earn its keep?")
ax.legend(frameon=False)
plt.tight_layout()
plt.show()

piv = agg.pivot(index="n", columns="model", values="mean")
piv["gap (ECFP - ChemBERTa)"] = (piv["ECFP4 + random forest"]
                                 - piv["ChemBERTa (frozen) + ridge"])
print(piv.round(3).to_string())

crossed = piv.index[piv["gap (ECFP - ChemBERTa)"] < 0]
if len(crossed):
    print(f"\\nThe fingerprint baseline overtakes the frozen encoder at "
          f"n ≈ {crossed[0]}.")
else:
    print("\\nThe frozen encoder stays ahead across every size tested here — "
          "extend SIZES if you want to find the crossing point.")
print("Either way: read the GAP column. Its magnitude shrinks as n grows. That "
      "shrinking gap is the entire argument of the lecture.")
""")

code(r"""
# --- Exercise 13: how much does the split type flatter you? ---
# your code here!
#
# Re-run the head-to-head from Exercise 11, but with a RANDOM 80/20 split instead
# of the scaffold split, and print the two sets of RMSEs side by side.
#
# The difference between the two columns is the amount of credit a random split
# would have handed you for free.

raise NotImplementedError
""", r"""
# --- Exercise 13 solution: how much does the split type flatter you? ---
perm = np.random.default_rng(SEED).permutation(len(df))
cut = int(0.8 * len(df))
rtr, rte = np.sort(perm[:cut]), np.sort(perm[cut:])

# Same two models, same sizes, only the split rule changed.
sc_rand = StandardScaler().fit(X_bert[rtr])
random_split = {
    "ECFP4 + random forest": evaluate(
        X_ecfp[rtr], y_all[rtr], X_ecfp[rte], y_all[rte], rf())["RMSE"],
    "ChemBERTa (frozen) + ridge": evaluate(
        sc_rand.transform(X_bert[rtr]), y_all[rtr],
        sc_rand.transform(X_bert[rte]), y_all[rte],
        RidgeCV(alphas=np.logspace(-2, 4, 25)))["RMSE"],
}
scaffold_split_rmse = {
    "ECFP4 + random forest": results["ECFP4 + random forest  (BASELINE)"]["RMSE"],
    "ChemBERTa (frozen) + ridge": results["ChemBERTa + ridge  (linear probe)"]["RMSE"],
}

comp = pd.DataFrame({"random split RMSE": random_split,
                     "scaffold split RMSE": scaffold_split_rmse})
comp["flattery"] = comp["scaffold split RMSE"] - comp["random split RMSE"]
print(comp.round(3).to_string())
print("\\n'flattery' = how many log units better a random split makes you look.")
print("It is rarely small, and it is the most common reason published chemistry ML "
      "results do not reproduce prospectively.")
""")

md(r"""
---
## 5 · Part D — where smooth representations break

Every representation we have used assumes that similar molecules have similar
properties. Activity cliffs are the counterexample, and they are exactly the
compounds a medicinal chemist cares about.
""")

code(r"""
# --- Exercise 14: hunt for cliffs ---
# your code here!
#
# 1. Using ECFP4 with Tanimoto, find every pair of molecules with similarity > 0.8.
#    (Reuse the BulkTanimotoSimilarity loop from Exercise 5, but keep the pairs.)
# 2. Among those, keep the pairs whose |Δ logD| > 1.0 — near-identical structures
#    with a tenfold difference in lipophilicity.
# 3. Report how many such pairs exist and what fraction of the high-similarity
#    pairs they represent.
# 4. Draw the most extreme pair with Draw.MolsToGridImage and look at what changed.

raise NotImplementedError
""", r"""
# --- Exercise 14 solution: hunt for cliffs ---
SIM_CUT, DELTA_CUT = 0.8, 1.0

pairs = []
for i in range(1, len(fps_bv)):
    sims = np.array(DataStructs.BulkTanimotoSimilarity(fps_bv[i], fps_bv[:i]))
    for j in np.where(sims > SIM_CUT)[0]:
        pairs.append((i, int(j), float(sims[j]), abs(y_all[i] - y_all[j])))

pairs = pd.DataFrame(pairs, columns=["i", "j", "similarity", "delta_y"])
cliffs = pairs[pairs["delta_y"] > DELTA_CUT].sort_values("delta_y", ascending=False)

print(f"pairs with Tanimoto > {SIM_CUT}      : {len(pairs)}")
print(f"of those, |delta logD| > {DELTA_CUT}   : {len(cliffs)} "
      f"({100 * len(cliffs) / max(len(pairs), 1):.1f}%)")
print("\\nmost extreme cliffs:")
print(cliffs.head(5).round(3).to_string(index=False))

if len(cliffs):
    top = cliffs.iloc[0]
    a, b = int(top["i"]), int(top["j"])
    print(f"\\nTanimoto {top['similarity']:.2f}, delta logD {top['delta_y']:.2f}")
    display(Draw.MolsToGridImage(
        [df['mol'][a], df['mol'][b]], molsPerRow=2, subImgSize=(340, 260),
        legends=[f"logD = {y_all[a]:.2f}", f"logD = {y_all[b]:.2f}"]))
""")

code(r"""
# --- Exercise 15 (optional): how badly do the models do on the cliff pairs? ---
# your code here!
#
# Take the model you trained in Exercise 11 on the scaffold split. Compute its
# test RMSE on:
#    (a) the whole test set
#    (b) only those test molecules that appear in at least one cliff pair
#
# Compare. This is the van Tilborg et al. (2022) analysis in miniature, and it is
# the number you should report in any med-chem paper.

raise NotImplementedError
""", r"""
# --- Exercise 15 solution: how badly do the models do on the cliff pairs? ---
cliff_members = set(cliffs["i"]).union(set(cliffs["j"]))
te_set = set(te_idx.tolist())
cliff_te = np.array(sorted(cliff_members & te_set))

model = rf().fit(E_tr, y_tr)
pred_all = model.predict(E_te)
rmse_all = float(np.sqrt(mean_squared_error(y_te, pred_all)))

if len(cliff_te) >= 5:
    mask = np.isin(te_idx, cliff_te)
    rmse_cliff = float(np.sqrt(mean_squared_error(y_te[mask], pred_all[mask])))
    print(f"test molecules            : {len(te_idx)}   RMSE {rmse_all:.3f}")
    print(f"of which are cliff members: {mask.sum()}   RMSE {rmse_cliff:.3f}")
    print(f"\\nRMSE is {rmse_cliff - rmse_all:+.3f} log units worse on cliff compounds.")
    print("Your headline RMSE hides this. Report it separately.")
else:
    print(f"only {len(cliff_te)} cliff members landed in the test set — too few to "
          "estimate a separate RMSE. Lower SIM_CUT or DELTA_CUT and re-run.")
""")

md(r"""
---
## 6 · Wrap-up

Write down your answers — we will compare across the room.

1. **How much of your ECFP variance did two principal components capture?** Would
   you be comfortable showing a PC1/PC2 plot as evidence that two chemotypes are
   distinct?
2. **Did the frozen ChemBERTa embeddings beat ECFP + random forest** on the full
   scaffold split? By how much, in log units? Is that difference larger than the
   spread you saw across repeats in the learning curve?
3. **Where was your crossover?** At what training-set size did the gap between the
   two curves become smaller than the error bars?
4. **How much did a random split flatter you?** Which of your two models benefited
   more from the leak — and can you explain why?
5. **Bring your own project to this.** How many labelled examples do you have? Which
   column of the "What to do on Monday" slide are you in?

### What to try next

- Swap `DeepChem/ChemBERTa-77M-MTR` for `DeepChem/ChemBERTa-77M-MLM` and re-run
  Exercises 8 and 11. The lecture claimed MTR beats MLM downstream — does it here?
- Use the `[CLS]` token instead of mean pooling. Usually worse; check.
- Replace ridge with a small MLP on the frozen embeddings. Does the extra capacity
  buy anything at n = 200?
- Concatenate 200 RDKit descriptors onto ECFP and re-run the baseline. Deng et al.
  found this combination hard to beat — see whether you agree.

### Where this goes next in the bootcamp

- **Thursday PM · Diffusion generative models** — the generative half of the story
  that VAEs lost.
- **Week 2, Thursday PM · Fine-tuning ChemBERTa** — the same model, but this time
  you unfreeze it and watch the learning rate.

---

*AI4Chemical Sciences Bootcamp 2026 · Caltech · jul@caltech.edu*
""")


# =====================================================================
def build(which):
    cells = []
    for kind, src, sol in CELLS:
        body = src if (which == "exercise" or sol is None) else sol
        cells.append({
            "cell_type": kind,
            "metadata": {},
            "source": [ln + "\n" for ln in body.split("\n")[:-1]] + [body.split("\n")[-1]],
            **({"execution_count": None, "outputs": []} if kind == "code" else {}),
        })
    return {"cells": cells,
            "metadata": {"language_info": {"name": "python"},
                         "kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"}},
            "nbformat": 4, "nbformat_minor": 5}


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent
    for which, name in [("exercise", "learned-representations.ipynb"),
                        ("solution", "learned-representations_solutions.ipynb")]:
        p = out / name
        p.write_text(json.dumps(build(which), indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {p}  ({len(CELLS)} cells)")
    n_ex = sum(1 for k, s, so in CELLS if so is not None)
    print(f"{n_ex} exercise cells differ between the two versions")
