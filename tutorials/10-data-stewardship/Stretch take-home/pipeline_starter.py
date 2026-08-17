"""Stretch task — build an automated cleaning pipeline.

Callback to Monday's lecture Arc 3: data + code + docs is a triad. You just cleaned this by hand.
Next week your PI hands you another log in the same format. Build the pipeline so future-you doesn't
have to do this manually again.

Fill in each function below. Run `pytest test_pipeline.py` to check your work.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path


def canonicalize_catalyst_names(series: pd.Series) -> pd.Series:
    """Map free-typed catalyst names in `series` to their canonical form.

    Canonical values come from catalyst_reference_tidy.csv. Examples:
    - 'pd(pph3)4', 'Tetrakis Pd', 'PdPPh3_4'   -> 'Pd(PPh3)4'
    - 'PdCl2·dppf', 'Pd(dppf)Cl2'              -> 'PdCl2(dppf)'
    - 'ni(cod)2', 'Ni COD 2', 'Nickel COD'     -> 'Ni(cod)2'

    Unknown values should raise ValueError (fail loud, not silent).
    """
    # TODO: implement
    raise NotImplementedError


def canonicalize_solvent_names(series: pd.Series) -> pd.Series:
    """Map free-typed solvent names in `series` to their canonical form.

    Canonical values come from solvent_reference_tidy.csv.
    """
    # TODO: implement
    raise NotImplementedError


def parse_yields(series: pd.Series) -> pd.Series:
    """Convert mixed yield string forms into float percent [0-100].

    Handles: '85%' -> 85.0, '0.85' -> 85.0, '85' -> 85.0, '85.5%' -> 85.5.
    """
    # TODO: implement
    raise NotImplementedError


def standardize_temperature(series: pd.Series) -> pd.Series:
    """Convert mixed-unit temperature strings to float degrees Celsius.

    Handles: '80 C' -> 80.0, '353 K' -> 79.85, '80' (assume C) -> 80.0.
    """
    # TODO: implement
    raise NotImplementedError


def build_tidy_reactions(
    messy_xlsx: Path,
    catalyst_ref: pd.DataFrame,
    solvent_ref: pd.DataFrame,
) -> pd.DataFrame:
    """End-to-end: load messy xlsx, produce tidy reactions_log DataFrame.

    Output columns (in this exact order):
        reaction_id, date, catalyst_canonical, solvent_canonical,
        temperature_C, time_min, yield_pct, operator, notes
    """
    # TODO: implement using the helpers above
    raise NotImplementedError


def main() -> None:
    """CLI entry: read the messy xlsx, write three tidy CSVs next to it."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    main()
