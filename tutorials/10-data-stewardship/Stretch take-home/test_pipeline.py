"""Tests for the stretch pipeline. Students run: `pytest test_pipeline.py`."""
from pathlib import Path
import pandas as pd
import pytest

from pipeline_starter import (
    canonicalize_catalyst_names,
    canonicalize_solvent_names,
    parse_yields,
    standardize_temperature,
    build_tidy_reactions,
)

HERE = Path(__file__).resolve().parent
GOLD = HERE.parent / "sprint-dataset-tidy"


def test_canonicalize_catalysts_handles_variants():
    s = pd.Series(["pd(pph3)4", "Tetrakis Pd", "PdPPh3_4"])
    out = canonicalize_catalyst_names(s)
    assert (out == "Pd(PPh3)4").all()


def test_canonicalize_catalysts_raises_on_unknown():
    with pytest.raises(ValueError):
        canonicalize_catalyst_names(pd.Series(["unknown catalyst xyz"]))


def test_canonicalize_solvents_handles_variants():
    s = pd.Series(["acetonitrile", "MeCN", "ACN", "CH3CN"])
    out = canonicalize_solvent_names(s)
    assert (out == "MeCN").all()


def test_parse_yields_handles_forms():
    s = pd.Series(["85%", "0.85", "85", "85.5%"])
    out = parse_yields(s)
    assert (out.round(1) == pd.Series([85.0, 85.0, 85.0, 85.5])).all()


def test_standardize_temperature():
    s = pd.Series(["80 C", "353 K", "80"])
    out = standardize_temperature(s)
    assert abs(out.iloc[0] - 80.0) < 0.01
    assert abs(out.iloc[1] - 79.85) < 0.02
    assert abs(out.iloc[2] - 80.0) < 0.01


def test_build_tidy_reactions_on_sprint_dataset():
    """End-to-end: pipeline should reproduce the gold-standard tidy reactions_log."""
    cats = pd.read_csv(GOLD / "catalyst_reference_tidy.csv")
    solvs = pd.read_csv(GOLD / "solvent_reference_tidy.csv")
    tidy = build_tidy_reactions(HERE.parent / "sprint-dataset-messy.xlsx", cats, solvs)
    gold = pd.read_csv(GOLD / "reactions_log_tidy.csv")
    # Compare after sorting (row order may differ)
    tidy_sorted = tidy.sort_values("reaction_id").reset_index(drop=True)
    gold_sorted = gold.sort_values("reaction_id").reset_index(drop=True)
    pd.testing.assert_frame_equal(
        tidy_sorted[gold.columns], gold_sorted, check_dtype=False, atol=0.5
    )


def test_pipeline_generalizes_to_second_dataset():
    """Pipeline must work on the second messy dataset too (see stretch/README.md)."""
    cats = pd.read_csv(GOLD / "catalyst_reference_tidy.csv")
    solvs = pd.read_csv(GOLD / "solvent_reference_tidy.csv")
    tidy = build_tidy_reactions(HERE / "new-experiments-messy.xlsx", cats, solvs)
    # Same schema
    assert list(tidy.columns) == [
        "reaction_id", "date", "catalyst_canonical", "solvent_canonical",
        "temperature_C", "time_min", "yield_pct", "operator", "notes",
    ]
    # All FKs resolve
    assert set(tidy["catalyst_canonical"]) <= set(cats["catalyst_canonical"])
    assert set(tidy["solvent_canonical"]) <= set(solvs["solvent_canonical"])
    # Yields in valid range
    assert tidy["yield_pct"].between(0, 100).all()
