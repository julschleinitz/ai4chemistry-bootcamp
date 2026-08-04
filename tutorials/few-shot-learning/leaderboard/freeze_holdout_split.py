"""
Instructor-only script. Run this ONCE, before the bootcamp, to freeze the fixed test split that
every student's notebook will evaluate against -- matching the "Fixed split policy" used across
this bootcamp (see tutorials/neural-networks-mlp/README.md): the instructor publishes one split
before class, and students self-report their score against it rather than each drawing their own
random test set.

Because this tutorial's leaderboard uses the simpler Apps-Script-POST pattern (students self-compute
and self-report their score, same trust model as the neural-networks-mlp tutorial), the output is a
single PUBLIC file -- there is no secret answer key to manage.

Output:
  official_test_set.csv   -- PUBLIC. Commit this next to the notebook. Columns:
                             mol_id, smiles, atom_idx, true_shift_ppm.
                             Ships with the repo; the notebook downloads it directly.

Usage:
    pip install rdkit pandas
    python freeze_holdout_split.py --n-molecules 30 --seed 42
"""
import argparse
import gzip
import os
import pickle
import random
import tarfile
import urllib.request

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem

MOESM_URL = ("https://static-content.springer.com/esm/art%3A10.1186%2Fs13321-019-0374-3/"
             "MediaObjects/13321_2019_374_MOESM2_ESM.gz")
LOCAL_GZ = "nmr_data_archive.gz"
LOCAL_PICKLE = "data_1H.pickle"
ELEMENTS = {'H', 'C', 'N', 'O', 'F', 'P', 'S', 'Cl'}
N_MAX = 40  # keep in sync with few-shot-learning.ipynb


def download_experimental_data():
    if os.path.exists(LOCAL_PICKLE):
        return
    print("Downloading experimental 1H NMR dataset (Jonas & Kuhn, 2019 SI)...")
    urllib.request.urlretrieve(MOESM_URL, LOCAL_GZ)

    # This supplementary file is a gzip-compressed tarball. The 1H pickle inside is NOT named
    # "data_1H.pickle" -- it's nested under a long, dataset-specific filename containing ".1H."
    # (e.g. "...data.1H.nmrshiftdb_....mol_dict.pickle"), so we match on that substring.
    assert tarfile.is_tarfile(LOCAL_GZ), (
        f"Expected '{LOCAL_GZ}' to be a tar.gz archive -- open it manually to inspect its format.")
    with tarfile.open(LOCAL_GZ, "r:*") as tf:
        names = tf.getnames()
        members = [m for m in tf.getmembers()
                   if ".1H." in os.path.basename(m.name) and m.name.endswith(".pickle")]
        assert members, f"Could not find a '*.1H.*.pickle' member in the archive; contents were: {names}"
        member = members[0]
        member.name = os.path.basename(member.name)
        tf.extract(member, ".")
        if member.name != LOCAL_PICKLE:
            os.replace(member.name, LOCAL_PICKLE)


def usable_test_molecule(mol, shifts):
    if mol is None or mol.GetNumAtoms() > N_MAX:
        return False
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        return False
    for atom in mol.GetAtoms():
        if atom.GetSymbol() not in ELEMENTS:
            return False
    return len(shifts) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-molecules", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", type=str, default=".")
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    download_experimental_data()
    # pd.read_pickle (not raw pickle.load) -- pandas needs its own unpickling machinery to
    # correctly restore DataFrame/Index internals saved by an older pandas version.
    nmr_1h = pd.read_pickle(LOCAL_PICKLE)
    test_df = nmr_1h["test_df"]

    candidates = []
    for _, row in test_df.iterrows():
        mol = row["rdmol"]
        shifts = row["value"][0] if isinstance(row["value"], (list, tuple)) else row["value"]
        if usable_test_molecule(mol, shifts):
            candidates.append((mol, shifts))

    print(f"{len(candidates)} candidate test molecules available "
          f"(<= {N_MAX} atoms, elements in {sorted(ELEMENTS)}).")
    assert len(candidates) >= args.n_molecules, "not enough candidates for requested --n-molecules"

    chosen = random.sample(candidates, k=args.n_molecules)

    public_rows = []
    for mol_id, (mol, shifts) in enumerate(chosen):
        working = Chem.AddHs(Chem.Mol(mol))
        try:
            AllChem.EmbedMolecule(working, randomSeed=args.seed)
        except Exception:
            continue
        smiles_out = Chem.MolToSmiles(Chem.RemoveHs(working))
        for atom in working.GetAtoms():
            if atom.GetSymbol() != 'H':
                continue
            idx = atom.GetIdx()
            if idx not in shifts:
                continue
            public_rows.append({
                "mol_id": mol_id, "smiles": smiles_out, "atom_idx": idx,
                "true_shift_ppm": float(shifts[idx]),
            })

    public_df = pd.DataFrame(public_rows)
    out_path = os.path.join(args.out_dir, "official_test_set.csv")
    public_df.to_csv(out_path, index=False)

    print(f"Wrote {out_path} ({len(public_df)} rows, {args.n_molecules} molecules) -- "
          f"commit this file next to the notebook.")


if __name__ == "__main__":
    main()
