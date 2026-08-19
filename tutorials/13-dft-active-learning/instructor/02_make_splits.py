#!/usr/bin/env python3
"""
Step 02 -- splits, sealed pool labels, and the student bundle.

Bemis-Murcko scaffold split, so no scaffold appears in more than one split. The
hidden test set therefore contains skeletons no acquisition strategy can buy at
any budget, which is the honest version of "does your model generalise".

    pool          SMILES + metadata public, labels sealed behind the oracle
    dev           SMILES + labels fully public (free validation set), and the
                  unscored `_boltz_stdev` columns as a bonus
    test_hidden   instructor only

Usage
-----
    python 02_make_splits.py
    python 02_make_splits.py --n-dev 1000 --n-test 1000 --seed 20260819

Outputs
-------
    data/student/       <- commit this; the notebook fetches it from GitHub
        pool_meta.csv          acid_id, smiles, mw, n_heavy, n_rot, subclass, scaffold
        dev.csv                acid_id, smiles + 156 targets + 39 _boltz_stdev extras
        selftest_smiles.csv    50 molecules for the submission self-test
        pool_labels.enc        sealed labels (the oracle reads these)
        targets.json           target order, families, units, provenance, budget
        published_benchmark.csv  the paper's own 3D-GNN test numbers
        README.md
    data/instructor/
        test_hidden.csv        acid_id, smiles + 156 targets
        splits.json            provenance and the exact id lists
        target_scales.csv      per-task std on the test set, used by the scorer
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# Shipped to students inside al_toolkit.py. See obfuscate.py for why this is
# not a secret.
DEFAULT_KEY = b"ai4chem-bootcamp-2026-carboxylic-acid-active-learning"

BUDGET = {"seed": 100, "rounds": 10, "batch": 50, "total": 600}


def scaffold_split(df, n_test: int, n_dev: int, seed: int, balance_subclass: bool):
    """Assign every molecule to pool / dev / test_hidden, scaffold-disjoint."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)

    scaf = df.groupby("murcko_scaffold")
    groups = pd.DataFrame({
        "scaffold": list(scaf.groups.keys()),
        "size": [len(v) for v in scaf.groups.values()],
        "subclass": [df.loc[v, "subclass"].mode().iat[0] for v in scaf.groups.values()],
    })
    size_of = dict(zip(groups["scaffold"], groups["size"]))
    assignment: dict[str, str] = {}

    def fill(order, target_n, label):
        got = 0
        for s in order:
            if got >= target_n:
                break
            if s in assignment:
                continue
            size = size_of[s]
            # Guard against one oversized scaffold single-handedly blowing the
            # quota. Murcko scaffolds collapse many chemically distinct
            # molecules onto a bare-ring skeleton once substituents are
            # stripped -- e.g. every simple substituted benzoic/phenylacetic
            # acid reduces to plain "c1ccccc1" -- and that one scaffold can
            # have hundreds to thousands of members. Without this check it
            # can land entirely in dev/test_hidden and blow a quota several
            # times over. Skip it here; it falls back to `pool` (a fine home
            # for a large, generic scaffold students can buy many labels
            # from) unless nothing smaller remains to reach target_n.
            if size > max(2 * (target_n - got), 10):
                continue
            assignment[s] = label
            got += int(size)
        return got

    if balance_subclass:
        total = int(groups["size"].sum())
        for split, want in (("test_hidden", n_test), ("dev", n_dev)):
            for _sub, sub_groups in groups.groupby("subclass"):
                quota = int(round(want * sub_groups["size"].sum() / total))
                order = sub_groups["scaffold"].sample(
                    frac=1.0, random_state=seed).tolist()
                fill(order, quota, split)
    else:
        order = groups["scaffold"].sample(frac=1.0, random_state=seed).tolist()
        fill(order, n_test, "test_hidden")
        fill(order, n_dev, "dev")

    # top up if proportional rounding undershot
    leftovers = [s for s in groups["scaffold"] if s not in assignment]
    rng.shuffle(leftovers)
    for split, want in (("test_hidden", n_test), ("dev", n_dev)):
        have = sum(size_of[s] for s, lab in assignment.items() if lab == split)
        if have < want:
            fill(leftovers, want - have, split)
            leftovers = [s for s in leftovers if s not in assignment]

    return df["murcko_scaffold"].map(lambda s: assignment.get(s, "pool"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default="../data/labels_all.csv")
    ap.add_argument("--benchmark", default="../data/published_benchmark.csv")
    ap.add_argument("--student-out", default="../data/student")
    ap.add_argument("--instructor-out", default="../data/instructor")
    ap.add_argument("--n-dev", type=int, default=1000)
    ap.add_argument("--n-test", type=int, default=1000)
    ap.add_argument("--n-selftest", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260819)
    ap.add_argument("--no-balance-subclass", action="store_true")
    ap.add_argument("--drop-nan-targets", action="store_true",
                    help="remove target columns that are entirely NaN instead of "
                         "shipping them")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))

    import numpy as np
    import pandas as pd

    from descriptor_spec import (AGG_DESCRIPTION, AGGREGATIONS,
                                 ASCII_OF_TARGET, BASE_NAMES,
                                 BOLTZMANN_TEMPERATURE, CONFORMER_METHOD,
                                 CPU_HOURS_TOTAL, DESC_OF_BASE,
                                 ENERGY_WINDOW_KCAL, EXTRA_AGGREGATIONS,
                                 EXTRA_COLUMNS, FAMILIES, FAMILY_OF_TARGET,
                                 LEVEL_OF_THEORY, N_PUBLISHED_ACIDS,
                                 N_PUBLISHED_CONFORMERS,
                                 PUBLISHED_3D_GNN_SPLIT,
                                 PUBLISHED_3D_GNN_TRAIN_SIZE, TARGET_COLUMNS,
                                 UNIT_OF_BASE)
    from obfuscate import seal_labels

    df = pd.read_csv(args.labels, encoding="utf-8")
    targets = list(TARGET_COLUMNS)

    if args.drop_nan_targets:
        empty = [t for t in targets if df[t].isna().all()]
        if empty:
            print(f"dropping {len(empty)} all-NaN targets: {empty[:6]}...")
            targets = [t for t in targets if t not in empty]

    df = df.dropna(subset=["murcko_scaffold"]).reset_index(drop=True)
    df["split"] = scaffold_split(df, args.n_test, args.n_dev, args.seed,
                                 not args.no_balance_subclass).values

    counts = df["split"].value_counts()
    print("split sizes:")
    print(counts.to_string())

    for a, b in (("pool", "dev"), ("pool", "test_hidden"), ("dev", "test_hidden")):
        sa = set(df.loc[df.split == a, "murcko_scaffold"])
        sb = set(df.loc[df.split == b, "murcko_scaffold"])
        assert not (sa & sb), f"scaffold leak between {a} and {b}: {len(sa & sb)}"
    print("scaffold disjointness: OK")

    sdir = Path(args.student_out)
    idir = Path(args.instructor_out)
    sdir.mkdir(parents=True, exist_ok=True)
    idir.mkdir(parents=True, exist_ok=True)

    meta_cols = [c for c in ("acid_id", "smiles", "mw", "n_heavy", "n_rot",
                             "subclass", "murcko_scaffold") if c in df.columns]
    extras = [c for c in EXTRA_COLUMNS if c in df.columns]

    pool = df[df.split == "pool"].reset_index(drop=True)
    dev = df[df.split == "dev"].reset_index(drop=True)
    test = df[df.split == "test_hidden"].reset_index(drop=True)

    # ---- student bundle --------------------------------------------------
    pool[meta_cols].to_csv(sdir / "pool_meta.csv", index=False, encoding="utf-8")
    dev[meta_cols + targets + extras].to_csv(sdir / "dev.csv", index=False,
                                             encoding="utf-8")
    dev[["acid_id", "smiles"]].sample(
        n=min(args.n_selftest, len(dev)), random_state=args.seed
    ).to_csv(sdir / "selftest_smiles.csv", index=False, encoding="utf-8")

    blob = seal_labels(pool["acid_id"].tolist(), targets,
                       pool[targets].to_numpy(dtype=float), DEFAULT_KEY)
    (sdir / "pool_labels.enc").write_bytes(blob)
    print(f"sealed {len(pool):,} x {len(targets)} pool labels "
          f"({len(blob) / 1e6:.1f} MB)")

    bench_src = Path(args.benchmark)
    if bench_src.exists():
        shutil.copy(bench_src, sdir / "published_benchmark.csv")

    per_label_cpu = CPU_HOURS_TOTAL / N_PUBLISHED_ACIDS
    spec = {
        "targets": targets,
        "n_targets": len(targets),
        "extras_unscored": extras,
        "base_properties": BASE_NAMES,
        "aggregations": AGGREGATIONS,
        "extra_aggregations": EXTRA_AGGREGATIONS,
        "aggregation_description": AGG_DESCRIPTION,
        "families": FAMILIES,
        "family_of_target": {t: FAMILY_OF_TARGET[t] for t in targets},
        "unit_of_base": UNIT_OF_BASE,
        "description_of_base": DESC_OF_BASE,
        "ascii_of_target": {t: ASCII_OF_TARGET[t] for t in targets},
        "budget": BUDGET,
        "sigma_suffix": "_sigma",
        "provenance": {
            "paper": "Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; "
                     "Coley, C. W.; Paton, R. S.; Sigman, M. S. "
                     "Digital Discovery 2025, 4, 222-233.",
            "doi": "10.1039/D4DD00284A",
            "data_doi": "10.6084/m9.figshare.25213742",
            "api": "https://descriptor-libraries.molssi.org/api/acids/",
            "license": "CC BY 4.0",
            "level_of_theory": LEVEL_OF_THEORY,
            "conformer_method": CONFORMER_METHOD,
            "boltzmann_temperature_K": BOLTZMANN_TEMPERATURE,
            "energy_window_kcal": ENERGY_WINDOW_KCAL,
            "published_acids": N_PUBLISHED_ACIDS,
            "published_conformers": N_PUBLISHED_CONFORMERS,
            "published_cpu_hours": CPU_HOURS_TOTAL,
            "cpu_hours_per_label": round(per_label_cpu, 1),
            "published_gnn_train_size": PUBLISHED_3D_GNN_TRAIN_SIZE,
            "published_gnn_split": PUBLISHED_3D_GNN_SPLIT,
            "published_gnn_caveat":
                "The published GNN test numbers use a RANDOM split; this "
                "tutorial's test set is scaffold-disjoint, which is harder. "
                "Treat their numbers as a ceiling, not a like-for-like target.",
        },
    }
    (sdir / "targets.json").write_text(json.dumps(spec, indent=2,
                                                  ensure_ascii=False),
                                       encoding="utf-8")

    (sdir / "README.md").write_text(f"""# Active learning on carboxylic acid DFT descriptors

| file | what it is |
|---|---|
| `pool_meta.csv` | {len(pool):,} acids you may buy labels for. Structures public, labels not. |
| `dev.csv` | {len(dev):,} acids **with** all {len(targets)} labels, free. Also carries {len(extras)} unscored `_boltz_stdev` columns. |
| `selftest_smiles.csv` | {args.n_selftest} molecules used by `validate_submission.py`. |
| `pool_labels.enc` | The oracle's label store. Only `al_toolkit.Oracle` reads it. |
| `targets.json` | Target names in the order your model must emit them, plus provenance. |
| `published_benchmark.csv` | What the paper's own GNN achieved, for comparison. |

**Budget: {BUDGET['seed']} seed + {BUDGET['rounds']} rounds x {BUDGET['batch']} = {BUDGET['total']} labels.**
The `Oracle` enforces it and logs every query to `al_log.jsonl`, which you submit.

## These labels are real DFT

Every label was computed at

> `{LEVEL_OF_THEORY}`

over a Maestro conformer ensemble, Boltzmann-averaged at {BOLTZMANN_TEMPERATURE} K over a
{ENERGY_WINDOW_KCAL} kcal/mol window using quasi-harmonic Gibbs energies. The published library
is {N_PUBLISHED_ACIDS:,} acids and {N_PUBLISHED_CONFORMERS:,} conformers and cost its authors
**over {CPU_HOURS_TOTAL:,} CPU hours** -- roughly **{per_label_cpu:.0f} CPU-hours per molecule**.

So your {BUDGET['total']}-label budget is about **{BUDGET['total'] * per_label_cpu / 1000:.0f},000 CPU-hours**
of quantum chemistry. Spend it as though you were the one queuing the jobs.

## The test set

{len(test):,} acids, **scaffold-disjoint** from both `pool` and `dev`: molecular skeletons that
are not in your pool at all. No acquisition strategy can buy them.

## Attribution (required -- CC BY 4.0)

Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.;
Paton, R. S.; Sigman, M. S. "Rapid prediction of conformationally-dependent
DFT-level descriptors using graph neural networks for carboxylic acids and alkyl
amines." *Digital Discovery* **2025**, *4*, 222-233. DOI 10.1039/D4DD00284A.
Data: DOI 10.6084/m9.figshare.25213742. Served via
<https://descriptor-libraries.molssi.org/>.
""", encoding="utf-8")

    # ---- instructor side -------------------------------------------------
    test[meta_cols + targets].to_csv(idir / "test_hidden.csv", index=False,
                                     encoding="utf-8")

    splits_meta = {
        "seed": args.seed,
        "sizes": {k: int(v) for k, v in counts.items()},
        "n_targets": len(targets),
        "targets": targets,
        "obfuscation_key_note": "see obfuscate.py -- not a secret",
        "ids": {s: df.loc[df.split == s, "acid_id"].tolist()
                for s in ("pool", "dev", "test_hidden")},
        "subclass_composition": {
            s: df.loc[df.split == s, "subclass"].value_counts().to_dict()
            for s in ("pool", "dev", "test_hidden")},
    }
    (idir / "splits.json").write_text(json.dumps(splits_meta, indent=2,
                                                 ensure_ascii=False),
                                      encoding="utf-8")

    scales = test[targets].std(ddof=1)
    scales.to_csv(idir / "target_scales.csv", header=["std"], encoding="utf-8")
    zero = scales[(scales == 0) | scales.isna()]
    if len(zero):
        print(f"WARNING: {len(zero)} targets have zero/NaN spread on the test "
              f"set and will be skipped by the scorer: {list(zero.index)[:6]}")

    print(f"\nstudent bundle -> {sdir}")
    print(f"instructor data -> {idir}   (keep this off the shared drive)")
    print("\nsubclass composition:")
    print(pd.DataFrame(splits_meta["subclass_composition"]).fillna(0).astype(int)
          .to_string())
    print(f"\nbudget of {BUDGET['total']} labels ~ "
          f"{BUDGET['total'] * per_label_cpu:,.0f} CPU-hours of DFT")


if __name__ == "__main__":
    main()
