# Tutorial 7 — Learned Representations

Companion material for **Lecture 7 · Learned Representations** (Wed 12 Aug 2026,
13:30, RSC 275). The tutorial slot is 15:15 in RSC 275.

## Files

| file | what it is |
|---|---|
| `../learned-representations.ipynb` | exercise notebook handed to attendees |
| `../learned-representations_solutions.ipynb` | worked solutions |
| `build_notebook.py` | **single source** for both notebooks — edit this, not the `.ipynb` files |
| `build_dataset.py` | one-off script that caches `lipophilicity.csv` here |
| `lipophilicity.csv` | MoleculeNet Lipophilicity, 4,200 molecules with logD 7.4 (created by `build_dataset.py`) |

## Regenerating the notebooks

The two notebooks are generated from `build_notebook.py` so the exercise and
solution versions can never drift apart — every cell is declared once, and cells
with a solution become a `raise NotImplementedError` stub in the exercise version.

```bash
cd tutorials/learned-representations
python build_dataset.py     # once, to cache the CSV
python build_notebook.py    # regenerates both .ipynb files
```

Both notebooks always have the same number of cells, so `nbdiff` between them
shows exactly the 15 exercises and nothing else.

## Structure of the tutorial (≈ 90 min)

| part | exercises | topic |
|---|---|---|
| A · unsupervised structure | 1–6 | ECFP4, PCA, t-SNE (plus the pure-noise control), Butina clustering, Bemis–Murcko scaffolds |
| B · a learned representation | 7–9 | frozen ChemBERTa embeddings, neighbourhood roughness, side-by-side UMAPs |
| C · does it beat the baseline? | 10–13 | scaffold split, head-to-head, **the learning-curve crossover**, random-vs-scaffold inflation |
| D · where it breaks | 14–15 | activity-cliff pairs and the RMSE they hide |

Exercise **12** is the one to protect if you run short of time — it is the
notebook version of the lecture's key figure, and everything else is scaffolding
for it.

## Notes for whoever runs the session

- Nothing here trains a neural network. The encoder stays frozen throughout, which
  is deliberate: gradient fine-tuning is covered in week 2 (*Fine-tuning ChemBERTa*).
- Runtime on a free Colab CPU runtime is roughly 8–12 minutes of compute in total;
  a GPU runtime cuts the embedding step to a few seconds but is not required.
- The heaviest cells are Exercise 5 (pairwise Tanimoto over a 2,500-molecule
  subsample) and Exercise 12 (the learning curve, ~2 min).
- `DeepChem/ChemBERTa-77M-MTR` is ~44 MB and is pulled from the HuggingFace hub on
  first use. If the venue's network blocks it, download it beforehand and point
  `MODEL_ID` at a local directory.
- Expect the head-to-head in Exercise 11 to be *close*. That is the result, not a
  bug — it is Praski et al. (2025) reproduced in an afternoon.
