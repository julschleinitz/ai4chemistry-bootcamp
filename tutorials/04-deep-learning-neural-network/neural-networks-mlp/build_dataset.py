"""Instructor-only script: regenerate dataset.csv and the fixed train/val/test
splits for the Neural Networks tutorial from the real Tox21 dataset.

This is NOT run by students — per splits/README.md, instructors publish one
fixed set of split files before class, and students must not re-split. Run
this once, commit the resulting dataset.csv/splits/*.csv, and the tutorial
notebook (deep-learning-neural-network.ipynb) reads them as fixed artifacts.

Usage:
    python build_dataset.py

Requires deepchem + rdkit (instructor-side only; the student notebook only
needs rdkit to turn the published `smiles` column into features).
"""

import numpy as np
import pandas as pd
import deepchem as dc

SEED = 42
PRIMARY_TASK = "SR-MMP"
VAL_FRAC = 0.15
TEST_FRAC = 0.15


def load_tox21_dataframe():
    """Load the full (unsplit) Tox21 dataset and flatten it into one row per
    molecule: sample_id, smiles, and one column per of the 12 assay tasks
    (1/0/NaN — NaN wherever DeepChem's per-task weight is 0, i.e. untested)."""
    tasks, datasets, _transformers = dc.molnet.load_tox21(featurizer="Raw", splitter=None)
    ds = datasets[0]

    y = np.asarray(ds.y, dtype=float)
    w = np.asarray(ds.w, dtype=float)
    y[w == 0] = np.nan  # untested assay -> missing label, not a real 0

    sample_ids = [f"mol_{i + 1:06d}" for i in range(len(ds))]
    df = pd.DataFrame(y, columns=tasks)
    df.insert(0, "smiles", list(ds.ids))
    df.insert(0, "sample_id", sample_ids)
    return df, tasks


def report_label_stats(df, tasks):
    print(f"Loaded {len(df)} molecules across {len(tasks)} Tox21 tasks.\n")
    print(f"{'task':<16}{'n_labeled':>10}{'n_positive':>12}{'positive_rate':>16}")
    for task in tasks:
        col = df[task]
        n_labeled = int(col.notna().sum())
        n_pos = int((col == 1).sum())
        rate = n_pos / n_labeled if n_labeled else float("nan")
        print(f"{task:<16}{n_labeled:>10}{n_pos:>12}{rate:>16.3f}")
    print()


def make_fixed_splits(df, primary_task, val_frac, test_frac, seed):
    """Stratified (on the primary task's non-missing label) train/val/test
    split over every molecule that has a label for that task. Molecules with
    a missing primary-task label are still assigned a split (needed so the
    same fixed splits can be reused by the multi-task section), placed via a
    plain random split since they have no label to stratify on."""
    rng = np.random.RandomState(seed)

    labeled = df[df[primary_task].notna()].copy()
    unlabeled = df[df[primary_task].isna()].copy()

    def stratified_split(sub_df, strata_col):
        parts = {"train": [], "val": [], "test": []}
        for _, group in sub_df.groupby(strata_col):
            idx = group.index.to_numpy()
            rng.shuffle(idx)
            n = len(idx)
            n_test = max(1, int(round(n * test_frac))) if n >= 3 else 0
            n_val = max(1, int(round(n * val_frac))) if n - n_test >= 3 else 0
            parts["test"].append(idx[:n_test])
            parts["val"].append(idx[n_test:n_test + n_val])
            parts["train"].append(idx[n_test + n_val:])
        return {k: np.concatenate(v) if v else np.array([], dtype=int) for k, v in parts.items()}

    labeled_split = stratified_split(labeled, primary_task)

    idx = unlabeled.index.to_numpy()
    rng.shuffle(idx)
    n = len(idx)
    n_test = int(round(n * test_frac))
    n_val = int(round(n * val_frac))
    unlabeled_split = {
        "test": idx[:n_test],
        "val": idx[n_test:n_test + n_val],
        "train": idx[n_test + n_val:],
    }

    split_ids = {}
    for name in ("train", "val", "test"):
        rows = np.concatenate([labeled_split[name], unlabeled_split[name]])
        split_ids[name] = df.loc[rows, "sample_id"].tolist()
    return split_ids


def main():
    df, tasks = load_tox21_dataframe()
    report_label_stats(df, tasks)

    if PRIMARY_TASK not in tasks:
        raise ValueError(f"PRIMARY_TASK={PRIMARY_TASK!r} not among Tox21 tasks: {tasks}")

    split_ids = make_fixed_splits(df, PRIMARY_TASK, VAL_FRAC, TEST_FRAC, SEED)
    for name, ids in split_ids.items():
        print(f"{name}: {len(ids)} molecules")

    df.to_csv("dataset.csv", index=False)
    print("\nWrote dataset.csv")

    for name, ids in split_ids.items():
        pd.DataFrame({"sample_id": ids}).to_csv(f"splits/{name}.csv", index=False)
        print(f"Wrote splits/{name}.csv")


if __name__ == "__main__":
    main()
