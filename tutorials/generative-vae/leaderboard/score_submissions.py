"""Instructor-run grading script for the Molecular Generation leaderboard.

Run this periodically during class (every few minutes is plenty), or manually between sessions:

    python score_submissions.py

It reads new rows from the published "Submissions" tab, dockes each SMILES for real (smina,
exhaustiveness=8 / num_modes=10 -- the docking tutorial's own demo defaults, not the notebook's
cheap exploration settings), computes QED and a PAINS+BRENK structural-alert count, and POSTs the
graded result to the "Leaderboard" tab via the same Apps Script Web App the notebook posts to.

Requires: rdkit, requests, and a working `smina` on PATH (install via
`conda install -c conda-forge smina openbabel`, or reuse the same conda env you validated the
notebook's docking cells in). Uses receptor_2ito.pdbqt + pocket.json in this directory -- committed
once (see SETUP.md) so grading always uses the exact same receptor/pocket as everyone's notebook.
"""

import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

import requests
from rdkit import Chem
from rdkit.Chem import Descriptors, FilterCatalog
from openbabel import pybel

HERE = Path(__file__).parent

# ---- Fill these in after completing SETUP.md ----
LEADERBOARD_SHEET_ID = "1RWD5l7Kz48E_O8F-k0xOSlUBgwjNT_5ABlIPy0zqUjU"
SUBMISSIONS_GID = "0"
LEADERBOARD_GID = "1327045070"
LEADERBOARD_ENDPOINT_URL = "https://script.google.com/macros/s/AKfycbyJQ0x9g_e6XUAK2i6LYArJHU8azphCqfiZhTvxX4Xp1A8lmIG36LUHg7fy2u2Nf_zn/exec"

EXHAUSTIVENESS_OFFICIAL = 8
NUM_MODES_OFFICIAL = 10
NOTEBOOK_VERSION = "generative-vae.ipynb v1"

RECEPTOR_PDBQT = HERE / "receptor_2ito.pdbqt"
POCKET_JSON = HERE / "pocket.json"


def fetch_gviz_rows(sheet_id, gid):
    """Same zero-auth read mechanism the HTML leaderboard widget uses: the published gviz JSON
    feed, wrapped in a `google.visualization.Query.setResponse({...});` JS-callback shell."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?gid={gid}&tqx=out:json"
    with urllib.request.urlopen(url, timeout=30) as r:
        text = r.read().decode("utf-8", errors="ignore")
    start, end = text.index("{"), text.rindex("}")
    payload = json.loads(text[start:end + 1])
    cols = [(c.get("label") or c.get("id") or "").strip() for c in payload["table"]["cols"]]
    rows = []
    for row in payload["table"]["rows"]:
        cells = row["c"]
        rows.append({cols[i]: (cells[i]["v"] if cells[i] else None) for i in range(len(cols))})
    return rows


def build_alert_catalog():
    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)
    return FilterCatalog.FilterCatalog(params)


ALERT_CATALOG = build_alert_catalog()


def parse_best_affinity(smina_stdout):
    match = re.search(r"^\s*1\s+(-?\d+\.\d+)", smina_stdout, re.MULTILINE)
    return float(match.group(1)) if match else None


def top_pose_sdf(sdf_path):
    """The first record in smina's output SDF is the best (mode 1) pose -- return just that
    record's text, not the whole (num_modes-record) file, to keep the Sheet cell small."""
    text = Path(sdf_path).read_text()
    end = text.find("$$$$")
    return text[: end + len("$$$$")] if end != -1 else text


def dock_and_score(smiles):
    """Real, official-settings docking + cheap RDKit properties for one submission.
    Returns a dict of the Leaderboard columns that depend on the molecule, or None if the
    submission can't be scored at all (invalid SMILES, embedding failure, smina crash)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        print(f"  skipping invalid SMILES: {smiles!r}")
        return None
    canonical = Chem.MolToSmiles(mol)

    pocket = json.loads(POCKET_JSON.read_text())
    pocket_center, pocket_size = pocket["pocket_center"], pocket["pocket_size"]

    ligand_pdbqt = HERE / "_tmp_submission_ligand.pdbqt"
    poses_sdf = HERE / "_tmp_submission_poses.sdf"
    try:
        molecule = pybel.readstring("smi", canonical)
        molecule.OBMol.CorrectForPH(7.4)
        molecule.addh()
        molecule.make3D(forcefield="mmff94s", steps=10000)
        for atom in molecule.atoms:
            atom.OBAtom.GetPartialCharge()
        molecule.write("pdbqt", str(ligand_pdbqt), overwrite=True)

        result = subprocess.run(
            ["smina",
             "--ligand", str(ligand_pdbqt), "--receptor", str(RECEPTOR_PDBQT), "--out", str(poses_sdf),
             "--center_x", str(pocket_center[0]), "--center_y", str(pocket_center[1]),
             "--center_z", str(pocket_center[2]),
             "--size_x", str(pocket_size[0]), "--size_y", str(pocket_size[1]), "--size_z", str(pocket_size[2]),
             "--num_modes", str(NUM_MODES_OFFICIAL), "--exhaustiveness", str(EXHAUSTIVENESS_OFFICIAL)],
            capture_output=True, text=True, timeout=300,
        )
        affinity = parse_best_affinity(result.stdout)
        if affinity is None:
            print(f"  smina produced no pose for {canonical!r}:\n{result.stdout}\n{result.stderr}")
            return None
        pose_sdf = top_pose_sdf(poses_sdf)
    except Exception as exc:
        print(f"  docking failed for {canonical!r}: {exc}")
        return None
    finally:
        ligand_pdbqt.unlink(missing_ok=True)
        poses_sdf.unlink(missing_ok=True)

    return {
        "smiles": canonical,
        "best_affinity_kcal_mol": affinity,
        "qed": Descriptors.qed(mol),
        "toxicity_alerts": len(ALERT_CATALOG.GetMatches(mol)),
        "exhaustiveness": EXHAUSTIVENESS_OFFICIAL,
        "num_modes": NUM_MODES_OFFICIAL,
        "pose_sdf": pose_sdf,
        "pocket_pdb_id": pocket["pdb_id"],
    }


def main():
    submissions = fetch_gviz_rows(LEADERBOARD_SHEET_ID, SUBMISSIONS_GID)
    graded = fetch_gviz_rows(LEADERBOARD_SHEET_ID, LEADERBOARD_GID)
    already_scored = {r["run_id"] for r in graded}
    pending = [r for r in submissions if r["run_id"] not in already_scored]

    print(f"{len(submissions)} total submissions, {len(already_scored)} already scored, "
          f"{len(pending)} pending.")

    for row in pending:
        print(f"scoring run_id={row['run_id']}  team={row['team_name']}  smiles={row['smiles']}")
        result = dock_and_score(row["smiles"])
        if result is None:
            continue

        payload = {
            "action": "record_score",
            "run_id": row["run_id"],
            "timestamp_utc_submitted": row["timestamp_utc"],
            "timestamp_utc_scored": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "team_name": row["team_name"],
            "notebook_version": NOTEBOOK_VERSION,
            "notes": f"graded by score_submissions.py ({row.get('method_family', 'unknown')})",
            **result,
        }
        resp = requests.post(LEADERBOARD_ENDPOINT_URL, json=payload, timeout=15)
        print(f"  -> {resp.status_code} {resp.text}")


if __name__ == "__main__":
    main()
