# Active learning on carboxylic acid DFT descriptors

| file | what it is |
|---|---|
| `pool_meta.csv` | 5,890 acids you may buy labels for. Structures public, labels not. |
| `dev.csv` | 1,032 acids **with** all 156 labels, free. Also carries 39 unscored `_boltz_stdev` columns. |
| `selftest_smiles.csv` | 50 molecules used by `validate_submission.py`. |
| `pool_labels.enc` | The oracle's label store. Only `al_toolkit.Oracle` reads it. |
| `targets.json` | Target names in the order your model must emit them, plus provenance. |
| `published_benchmark.csv` | What the paper's own GNN achieved, for comparison. |

**Budget: 100 seed + 10 rounds x 50 = 600 labels.**
The `Oracle` enforces it and logs every query to `al_log.jsonl`, which you submit.

## These labels are real DFT

Every label was computed at

> `M06-2X/def2-TZVP-SDD(I,Sn,Se) // B3LYP-D3(BJ)/6-31G(d,p)-LANL2DZ(I,Sn,Se), gas phase`

over a Maestro conformer ensemble, Boltzmann-averaged at 298.15 K over a
5.0 kcal/mol window using quasi-harmonic Gibbs energies. The published library
is 8,528 acids and 71,324 conformers and cost its authors
**over 1,000,000 CPU hours** -- roughly **117 CPU-hours per molecule**.

So your 600-label budget is about **70,000 CPU-hours**
of quantum chemistry. Spend it as though you were the one queuing the jobs.

## The test set

1,027 acids, **scaffold-disjoint** from both `pool` and `dev`: molecular skeletons that
are not in your pool at all. No acquisition strategy can buy them.

## Attribution (required -- CC BY 4.0)

Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.;
Paton, R. S.; Sigman, M. S. "Rapid prediction of conformationally-dependent
DFT-level descriptors using graph neural networks for carboxylic acids and alkyl
amines." *Digital Discovery* **2025**, *4*, 222-233. DOI 10.1039/D4DD00284A.
Data: DOI 10.6084/m9.figshare.25213742. Served via
<https://descriptor-libraries.molssi.org/>.
