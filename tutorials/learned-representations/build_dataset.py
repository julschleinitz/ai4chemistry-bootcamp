#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch the MoleculeNet Lipophilicity dataset and cache it next to this file as
`lipophilicity.csv`, so the tutorial notebook works offline and does not depend
on a third-party bucket staying up during the session.

Run once, then commit the CSV:

    python build_dataset.py

The notebook looks for the local copy first, then this repo on GitHub, then the
DeepChem bucket — so it keeps working either way.
"""
import sys
import urllib.request
from pathlib import Path

SOURCE = "https://deepchemdata.s3.us-west-1.amazonaws.com/datasets/Lipophilicity.csv"
OUT = Path(__file__).resolve().parent / "lipophilicity.csv"

EXPECTED_COLUMNS = {"CMPD_CHEMBLID", "exp", "smiles"}
EXPECTED_ROWS = 4200


def main():
    print(f"downloading {SOURCE}")
    try:
        with urllib.request.urlopen(SOURCE, timeout=60) as r:
            data = r.read()
    except Exception as exc:                                    # noqa: BLE001
        sys.exit(f"download failed ({type(exc).__name__}: {exc}).\n"
                 f"Grab it by hand from {SOURCE} and save it as {OUT}.")

    OUT.write_bytes(data)
    print(f"wrote {OUT}  ({len(data) / 1024:.0f} kB)")

    # Cheap sanity check so a captive-portal HTML page never gets committed as data.
    try:
        import pandas as pd
    except ImportError:
        print("pandas not installed — skipping validation")
        return
    df = pd.read_csv(OUT)
    print(f"{len(df)} rows, columns: {list(df.columns)}")
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        sys.exit(f"unexpected columns; missing {missing}")
    if len(df) != EXPECTED_ROWS:
        print(f"warning: expected {EXPECTED_ROWS} rows, found {len(df)} — "
              "MoleculeNet may have been revised. Check before use.")
    print("logD range:", round(df["exp"].min(), 2), "to", round(df["exp"].max(), 2))
    print("ok")


if __name__ == "__main__":
    main()
