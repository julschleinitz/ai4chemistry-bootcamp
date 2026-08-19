"""
Single source of truth for the descriptor set.

The labels are the PUBLISHED DFT descriptors from

    Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.;
    Paton, R. S.; Sigman, M. S. "Rapid prediction of conformationally-dependent
    DFT-level descriptors using graph neural networks for carboxylic acids and
    alkyl amines." Digital Discovery 2025, 4, 222-233.
    DOI 10.1039/D4DD00284A                                        CC BY 4.0
    Data: DOI 10.6084/m9.figshare.25213742
    API:  https://descriptor-libraries.molssi.org/api/acids/

Nothing here is recomputed. The published library is 8,528 acids / 71,324
conformers, optimised at B3LYP-D3(BJ)/6-31G(d,p) with M06-2X/def2-TZVP
single points, and cost the authors over 1,000,000 CPU hours -- about 117
CPU-hours per molecule. That is what makes the oracle in this tutorial honest.

    ATOM LABELS, as the paper defines them for the (R)3C4-C1O2O3H5 group:
        C1  carboxyl carbon      O2  carbonyl oxygen
        O3  hydroxyl oxygen      H5  acidic hydrogen
        C4  alpha carbon

--------------------------------------------------------------------------
WHAT WE SHIP: 39 base properties x 4 aggregations = 156 targets
--------------------------------------------------------------------------
The published set is 55 bases x 5 aggregations = 275. We make two changes,
both deliberate and both reversible from this file alone:

1. DROP `_boltz_stdev`. The tutorial predicts the four aggregations that
   describe *where* a descriptor sits (min / max / lowest-energy conformer /
   Boltzmann average). `_boltz_stdev` is still shipped to students in the free
   dev set as an UNSCORED extra, because it is the paper's own measure of
   conformational spread and section (a) of the notebook uses it.

2. TRIM the buried-volume radius scan from 28 columns to 12. The published set
   has %Vbur at nine radii on C1, nine on C4, and five each for the C1 max/min
   hemispheres -- 28 of 55 bases, so more than half the score would have been
   one smooth, highly redundant scan. We keep three radii per series
   (3, 4, 5 A). Buried volume is still the largest family at 12/39 = 31%, which
   is honest: it is what the Sigman workflow measures most of.

To go back to the full published set, set TRIM_VBUR = False.

--------------------------------------------------------------------------
TWO TRAPS IN THE PUBLISHED COLUMN NAMES -- both verified against the live API
--------------------------------------------------------------------------
1. The API CSV is SUFFIX-MAJOR: `molecule_id, smiles`, then all 55 `_min`
   columns, then all 55 `_max`, then `_boltz`, `_low_e`, `_boltz_stdev`.
   It is NOT property-major. `API_COLUMN_ORDER` reproduces it exactly.

2. `min` and `max` appear BOTH as aggregation suffixes AND inside the
   hemisphere base names, so `%Vbur_C1_min_hemisphere_3A_min` is a real
   column. Never strip with a bare regex; use `split_target()`, which peels
   exactly one suffix, longest-first.

Also note the inconsistent radius formatting in the published names, which we
reproduce verbatim rather than tidy:
    plain scan  -> `%Vbur_C1_3.0A`   (one decimal, always)
    hemispheres -> `%Vbur_C1_max_hemisphere_3A`   (no `.0`)
(with U+00C5 for the Angstrom sign, and no underscore before it)
"""

from __future__ import annotations

# The Angstrom sign used throughout the published columns is U+00C5
# (LATIN CAPITAL LETTER A WITH RING ABOVE), *not* U+212B. Written as an escape
# so that this file survives any re-encoding.
A = "Å"          # noqa: E741
SQ = "²"         # superscript two
CU = "³"         # superscript three
DEG = "°"        # degree sign
ETA, MU, OMEGA = "η", "μ", "ω"

TRIM_VBUR = True
DROP_BOLTZ_STDEV = True

# --------------------------------------------------------------------------
# The published 55 base properties, in the EXACT order the API returns them.
# Do not sort this list: `API_COLUMN_ORDER` depends on it.
# --------------------------------------------------------------------------
PUBLISHED_BASES: list[str] = [
    # -- buried volume, C1 radius scan (9) --
    f"%Vbur_C1_2.0{A}", f"%Vbur_C1_2.5{A}", f"%Vbur_C1_3.0{A}",
    f"%Vbur_C1_3.5{A}", f"%Vbur_C1_4.0{A}", f"%Vbur_C1_4.5{A}",
    f"%Vbur_C1_5.0{A}", f"%Vbur_C1_5.5{A}", f"%Vbur_C1_6.0{A}",
    # -- C1 max hemisphere (5) -- note: lexicographic order, and no ".0"
    f"%Vbur_C1_max_hemisphere_3.5{A}", f"%Vbur_C1_max_hemisphere_3{A}",
    f"%Vbur_C1_max_hemisphere_4.5{A}", f"%Vbur_C1_max_hemisphere_4{A}",
    f"%Vbur_C1_max_hemisphere_5{A}",
    # -- C1 min hemisphere (5) --
    f"%Vbur_C1_min_hemisphere_3.5{A}", f"%Vbur_C1_min_hemisphere_3{A}",
    f"%Vbur_C1_min_hemisphere_4.5{A}", f"%Vbur_C1_min_hemisphere_4{A}",
    f"%Vbur_C1_min_hemisphere_5{A}",
    # -- buried volume, C4 radius scan (9). No C4 hemispheres exist. --
    f"%Vbur_C4_2.0{A}", f"%Vbur_C4_2.5{A}", f"%Vbur_C4_3.0{A}",
    f"%Vbur_C4_3.5{A}", f"%Vbur_C4_4.0{A}", f"%Vbur_C4_4.5{A}",
    f"%Vbur_C4_5.0{A}", f"%Vbur_C4_5.5{A}", f"%Vbur_C4_6.0{A}",
    # -- everything else, alphabetically as the API returns it --
    "HOMO",
    "IR_freq_C1_O2",
    "LUMO",
    "NBO_charge_C1", "NBO_charge_C4", "NBO_charge_H5",
    "NBO_charge_O2", "NBO_charge_O3",
    "NMR_shift_C1", "NMR_shift_C4", "NMR_shift_H5",
    "SASA_sphericity", f"SASA_surface_area({A}{SQ})", f"SASA_volume({A}{CU})",
    f"Sterimol_B1_C1_C4({A})_morfeus",
    f"Sterimol_B5_C1_C4({A})_morfeus",
    f"Sterimol_L_C1_C4({A})_morfeus",
    f"dihedral_C4_C1_O3_H5({DEG})", f"dihedral_O2_C1_O3_H5({DEG})",
    "dipole(Debye)",
    f"distance_O3_H5({A})",
    "polar_aniso(Debye)", "polar_iso(Debye)",
    f"volume(Bohr_radius{CU}/mol)",
    ETA, MU, OMEGA,
]

# The %Vbur columns we drop when TRIM_VBUR is on: keep 3 / 4 / 5 A per series.
VBUR_DROPPED: list[str] = [
    f"%Vbur_C1_2.0{A}", f"%Vbur_C1_2.5{A}", f"%Vbur_C1_3.5{A}",
    f"%Vbur_C1_4.5{A}", f"%Vbur_C1_5.5{A}", f"%Vbur_C1_6.0{A}",
    f"%Vbur_C4_2.0{A}", f"%Vbur_C4_2.5{A}", f"%Vbur_C4_3.5{A}",
    f"%Vbur_C4_4.5{A}", f"%Vbur_C4_5.5{A}", f"%Vbur_C4_6.0{A}",
    f"%Vbur_C1_max_hemisphere_3.5{A}", f"%Vbur_C1_max_hemisphere_4.5{A}",
    f"%Vbur_C1_min_hemisphere_3.5{A}", f"%Vbur_C1_min_hemisphere_4.5{A}",
]

BASE_NAMES: list[str] = [
    b for b in PUBLISHED_BASES
    if not (TRIM_VBUR and b in VBUR_DROPPED)
]

# --------------------------------------------------------------------------
# Families, for the leaderboard breakdown
# --------------------------------------------------------------------------
FAMILIES: list[str] = ["vbur", "charge", "fmo", "spectroscopic", "sterimol",
                       "sasa", "geometry", "electrostatic"]


def _family_of_base(name: str) -> str:
    if name.startswith("%Vbur"):
        return "vbur"
    if name.startswith("NBO_charge"):
        return "charge"
    if name in {"HOMO", "LUMO", ETA, MU, OMEGA}:
        return "fmo"
    if name.startswith("NMR_shift") or name.startswith("IR_freq"):
        return "spectroscopic"
    if name.startswith("Sterimol"):
        return "sterimol"
    if name.startswith("SASA"):
        return "sasa"
    if name.startswith(("dihedral", "distance")):
        return "geometry"
    if name.startswith(("dipole", "polar", "volume")):
        return "electrostatic"
    raise KeyError(f"no family for {name!r}")


FAMILY_OF_BASE: dict[str, str] = {b: _family_of_base(b) for b in BASE_NAMES}

# Units, as the published names imply. NOTE a MolSSI-side mislabel we do not
# propagate silently: polar_iso / polar_aniso are labelled "(Debye)" in the
# acids database but are polarisabilities in ATOMIC UNITS. We keep the column
# name verbatim (it is the join key) and record the correct unit here.
UNIT_OF_BASE: dict[str, str] = {}
for _b in BASE_NAMES:
    if _b.startswith("%Vbur"):
        UNIT_OF_BASE[_b] = "%"
    elif _b.startswith("NBO_charge"):
        UNIT_OF_BASE[_b] = "e"
    elif _b in {"HOMO", "LUMO", ETA, MU, OMEGA}:
        UNIT_OF_BASE[_b] = "Hartree"
    elif _b.startswith("NMR_shift"):
        UNIT_OF_BASE[_b] = "ppm"
    elif _b.startswith("IR_freq"):
        UNIT_OF_BASE[_b] = "cm^-1"
    elif _b.startswith("Sterimol") or _b.startswith("distance"):
        UNIT_OF_BASE[_b] = A
    elif _b == "SASA_sphericity":
        UNIT_OF_BASE[_b] = "-"
    elif _b.startswith("SASA_surface_area"):
        UNIT_OF_BASE[_b] = f"{A}{SQ}"
    elif _b.startswith("SASA_volume"):
        UNIT_OF_BASE[_b] = f"{A}{CU}"
    elif _b.startswith("dihedral"):
        UNIT_OF_BASE[_b] = DEG
    elif _b == "dipole(Debye)":
        UNIT_OF_BASE[_b] = "Debye"
    elif _b.startswith("polar_"):
        UNIT_OF_BASE[_b] = "a.u. (column name says Debye -- mislabelled upstream)"
    elif _b.startswith("volume"):
        UNIT_OF_BASE[_b] = f"Bohr{CU}/mol"
    else:
        UNIT_OF_BASE[_b] = "?"

DESC_OF_BASE: dict[str, str] = {
    "HOMO": "highest occupied molecular orbital energy",
    "LUMO": "lowest unoccupied molecular orbital energy",
    ETA: "chemical hardness",
    MU: "chemical potential",
    OMEGA: "electrophilicity index",
    "IR_freq_C1_O2": "harmonic C=O stretching frequency",
    "NBO_charge_C1": "NBO natural charge on the carboxyl carbon",
    "NBO_charge_C4": "NBO natural charge on the alpha carbon",
    "NBO_charge_H5": "NBO natural charge on the acidic hydrogen",
    "NBO_charge_O2": "NBO natural charge on the carbonyl oxygen",
    "NBO_charge_O3": "NBO natural charge on the hydroxyl oxygen",
    "NMR_shift_C1": "isotropic NMR shift, carboxyl carbon",
    "NMR_shift_C4": "isotropic NMR shift, alpha carbon",
    "NMR_shift_H5": "isotropic NMR shift, acidic hydrogen",
    "SASA_sphericity": "sphericity of the solvent-accessible surface",
    f"SASA_surface_area({A}{SQ})": "solvent-accessible surface area",
    f"SASA_volume({A}{CU})": "volume enclosed by the solvent-accessible surface",
    f"Sterimol_B1_C1_C4({A})_morfeus": "Sterimol B1 along C1->C4 (minimum width of R)",
    f"Sterimol_B5_C1_C4({A})_morfeus": "Sterimol B5 along C1->C4 (maximum width of R)",
    f"Sterimol_L_C1_C4({A})_morfeus": "Sterimol L along C1->C4 (length of R)",
    f"dihedral_C4_C1_O3_H5({DEG})": "C4-C1-O3-H5 dihedral",
    f"dihedral_O2_C1_O3_H5({DEG})": "O2-C1-O3-H5 dihedral (acid proton syn/anti)",
    "dipole(Debye)": "molecular dipole moment",
    f"distance_O3_H5({A})": "O-H bond length of the acid",
    "polar_aniso(Debye)": "anisotropic polarisability",
    "polar_iso(Debye)": "isotropic polarisability",
    f"volume(Bohr_radius{CU}/mol)": "molecular volume",
}
for _b in BASE_NAMES:
    if _b.startswith("%Vbur"):
        DESC_OF_BASE.setdefault(_b, "percent buried volume, " + _b[6:])

# --------------------------------------------------------------------------
# Aggregations
# --------------------------------------------------------------------------
# Order matters for the API layout. `_boltz_stdev` MUST precede `_boltz` in
# SUFFIXES_LONGEST_FIRST so that split_target() peels the right one.
PUBLISHED_AGGREGATIONS: list[str] = ["min", "max", "boltz", "low_e",
                                     "boltz_stdev"]
AGGREGATIONS: list[str] = [a for a in PUBLISHED_AGGREGATIONS
                           if not (DROP_BOLTZ_STDEV and a == "boltz_stdev")]

#: Shipped to students in dev.csv but never scored.
EXTRA_AGGREGATIONS: list[str] = [a for a in PUBLISHED_AGGREGATIONS
                                 if a not in AGGREGATIONS]

SUFFIXES_LONGEST_FIRST: list[str] = sorted(
    PUBLISHED_AGGREGATIONS, key=len, reverse=True)

AGG_DESCRIPTION: dict[str, str] = {
    "min": "minimum over the conformer ensemble",
    "max": "maximum over the conformer ensemble",
    "boltz": "Boltzmann-weighted average, 298.15 K, quasi-harmonic Gibbs "
             "energies, 5 kcal/mol window",
    "low_e": "value at the lowest-energy conformer",
    "boltz_stdev": "Boltzmann-weighted standard deviation (shipped, not scored)",
}

BOLTZMANN_TEMPERATURE = 298.15   # K, as used by the authors
ENERGY_WINDOW_KCAL = 5.0         # conformers above this were discarded upstream

LEVEL_OF_THEORY = ("M06-2X/def2-TZVP-SDD(I,Sn,Se) // "
                   "B3LYP-D3(BJ)/6-31G(d,p)-LANL2DZ(I,Sn,Se), gas phase")
CONFORMER_METHOD = ("Schrodinger Maestro conformational search + clustering, "
                    "GoodVibes quasi-harmonic thermochemistry")
CPU_HOURS_TOTAL = 1_000_000      # reported by the authors for the acid library
N_PUBLISHED_ACIDS = 8528
N_PUBLISHED_CONFORMERS = 71_324

# --------------------------------------------------------------------------
# Target columns
# --------------------------------------------------------------------------
# Our own order is PROPERTY-MAJOR, which is easier to read in a dataframe and
# is what `targets.json` pins for the students. It is deliberately NOT the
# API's order; `API_COLUMN_ORDER` below is the API's.
TARGET_COLUMNS: list[str] = [f"{b}_{a}" for b in BASE_NAMES
                             for a in AGGREGATIONS]

EXTRA_COLUMNS: list[str] = [f"{b}_{a}" for b in BASE_NAMES
                            for a in EXTRA_AGGREGATIONS]

#: Exactly what the MolSSI batch CSV export returns, in order. Suffix-major.
API_COLUMN_ORDER: list[str] = (
    ["molecule_id", "smiles"]
    + [f"{b}_{a}" for a in PUBLISHED_AGGREGATIONS for b in PUBLISHED_BASES]
)


def split_target(column: str) -> tuple[str, str]:
    """Split a target column into (base, aggregation).

    Peels exactly one suffix, longest first. This is the ONLY correct way to
    parse these names, because the hemisphere bases themselves contain `min`
    and `max`:

    >>> split_target('%Vbur_C1_min_hemisphere_3Å_min')
    ('%Vbur_C1_min_hemisphere_3Å', 'min')
    >>> split_target('%Vbur_C1_max_hemisphere_5Å_max')
    ('%Vbur_C1_max_hemisphere_5Å', 'max')
    >>> split_target('HOMO_boltz_stdev')
    ('HOMO', 'boltz_stdev')
    >>> split_target('NBO_charge_H5_low_e')
    ('NBO_charge_H5', 'low_e')
    >>> split_target('HOMO')
    Traceback (most recent call last):
        ...
    ValueError: 'HOMO' does not end in a known aggregation suffix
    """
    for suffix in SUFFIXES_LONGEST_FIRST:
        tail = "_" + suffix
        if column.endswith(tail):
            return column[: -len(tail)], suffix
    raise ValueError(f"{column!r} does not end in a known aggregation suffix")


FAMILY_OF_TARGET: dict[str, str] = {
    t: FAMILY_OF_BASE[split_target(t)[0]] for t in TARGET_COLUMNS
}
BASE_OF_TARGET: dict[str, str] = {t: split_target(t)[0] for t in TARGET_COLUMNS}
AGG_OF_TARGET: dict[str, str] = {t: split_target(t)[1] for t in TARGET_COLUMNS}

N_BASE = len(BASE_NAMES)
N_TARGETS = len(TARGET_COLUMNS)

SMILES_COLUMN = "smiles"
ID_COLUMN = "acid_id"
MOLECULE_ID_COLUMN = "molecule_id"     # the published Ac1..Ac8528 identifier
SIGMA_SUFFIX = "_sigma"
SIGMA_COLUMNS: list[str] = [c + SIGMA_SUFFIX for c in TARGET_COLUMNS]


# --------------------------------------------------------------------------
# ASCII aliases -- for filenames, matplotlib labels on unlucky font stacks,
# and anyone who opens a CSV in a tool that mangles UTF-8.
# --------------------------------------------------------------------------
_ASCII_MAP = {A: "A", SQ: "2", CU: "3", DEG: "deg",
              ETA: "eta", MU: "mu", OMEGA: "omega",
              "%": "pct", "(": "_", ")": "", "/": "_per_"}


def to_ascii(name: str) -> str:
    out = name
    for k, v in _ASCII_MAP.items():
        out = out.replace(k, v)
    return "_".join(out.split()).replace("__", "_").strip("_")


ASCII_OF_TARGET: dict[str, str] = {t: to_ascii(t) for t in TARGET_COLUMNS}
ASCII_OF_BASE: dict[str, str] = {b: to_ascii(b) for b in BASE_NAMES}


# --------------------------------------------------------------------------
# Published GNN benchmark -- the reference line for the closing slide.
# From 3D/test_acids.ipynb stored outputs (DimeNet++, 7,290 training molecules,
# RANDOM split). See the caveat in PLAN.md section 5: their split is random and
# ours is scaffold-disjoint, so their numbers are optimistic relative to the
# leaderboard. Quote them as a ceiling, not a like-for-like target.
# --------------------------------------------------------------------------
PUBLISHED_3D_GNN: dict[tuple[str, str], tuple[float, float]] = {
    # (base, aggregation): (MAE, R2)
    ("IR_freq_C1_O2", "boltz"): (2.82, 0.917),
    ("IR_freq_C1_O2", "min"): (3.78, 0.818),
    ("IR_freq_C1_O2", "max"): (3.05, 0.923),
    ("IR_freq_C1_O2", "low_e"): (4.36, 0.869),
    (f"Sterimol_B1_C1_C4({A})_morfeus", "boltz"): (0.077, 0.841),
    (f"Sterimol_B1_C1_C4({A})_morfeus", "min"): (0.049, 0.912),
    (f"Sterimol_B1_C1_C4({A})_morfeus", "max"): (0.139, 0.766),
    (f"Sterimol_B1_C1_C4({A})_morfeus", "low_e"): (0.122, 0.647),
    (f"Sterimol_B5_C1_C4({A})_morfeus", "boltz"): (0.413, 0.896),
    (f"Sterimol_B5_C1_C4({A})_morfeus", "min"): (0.361, 0.817),
    (f"Sterimol_B5_C1_C4({A})_morfeus", "max"): (0.300, 0.968),
    (f"Sterimol_B5_C1_C4({A})_morfeus", "low_e"): (0.671, 0.748),
    (f"Sterimol_L_C1_C4({A})_morfeus", "boltz"): (0.506, 0.804),
    (f"Sterimol_L_C1_C4({A})_morfeus", "min"): (0.196, 0.969),
    (f"Sterimol_L_C1_C4({A})_morfeus", "max"): (0.490, 0.882),
    (f"Sterimol_L_C1_C4({A})_morfeus", "low_e"): (0.800, 0.631),
    ("dipole(Debye)", "boltz"): (0.416, 0.738),
    ("dipole(Debye)", "min"): (0.427, 0.700),
    ("dipole(Debye)", "max"): (0.392, 0.856),
    ("dipole(Debye)", "low_e"): (0.709, 0.545),
}
PUBLISHED_3D_GNN_TRAIN_SIZE = 7290
PUBLISHED_3D_GNN_SPLIT = "random (7290 train / 478 val / 476 test)"


def published_benchmark_rows() -> list[dict]:
    """Flatten PUBLISHED_3D_GNN into rows, skipping anything we do not ship."""
    rows = []
    for (base, agg), (mae, r2) in PUBLISHED_3D_GNN.items():
        col = f"{base}_{agg}"
        if col not in TARGET_COLUMNS:
            continue
        rows.append({"target": col, "base": base, "aggregation": agg,
                     "family": FAMILY_OF_BASE[base],
                     "published_3D_GNN_MAE": mae,
                     "published_3D_GNN_R2": r2,
                     "published_train_size": PUBLISHED_3D_GNN_TRAIN_SIZE,
                     "published_split": PUBLISHED_3D_GNN_SPLIT})
    return rows


# --------------------------------------------------------------------------
# Consistency checks -- these run on import, deliberately.
# --------------------------------------------------------------------------
assert len(PUBLISHED_BASES) == 55, len(PUBLISHED_BASES)
assert len(set(PUBLISHED_BASES)) == 55, "duplicate published base name"
assert len(API_COLUMN_ORDER) == 2 + 5 * 55 == 277, len(API_COLUMN_ORDER)
assert all(b in PUBLISHED_BASES for b in VBUR_DROPPED), "typo in VBUR_DROPPED"
assert N_BASE == 39, f"expected 39 trimmed bases, got {N_BASE}"
assert N_TARGETS == 156, f"expected 156 targets, got {N_TARGETS}"
assert len(set(TARGET_COLUMNS)) == N_TARGETS
assert sum(1 for b in BASE_NAMES if FAMILY_OF_BASE[b] == "vbur") == 12
assert set(FAMILY_OF_BASE.values()) == set(FAMILIES), (
    set(FAMILIES) ^ set(FAMILY_OF_BASE.values()))
assert all(split_target(f"{b}_{a}") == (b, a)
           for b in PUBLISHED_BASES for a in PUBLISHED_AGGREGATIONS), \
    "split_target is not the inverse of the naming convention"
assert len(set(ASCII_OF_TARGET.values())) == N_TARGETS, \
    "ASCII aliases collide -- fix _ASCII_MAP"


def summary() -> str:
    lines = [
        f"published set : 55 bases x 5 aggregations = 275 targets",
        f"shipped set   : {N_BASE} bases x {len(AGGREGATIONS)} aggregations "
        f"= {N_TARGETS} targets",
        f"trim_vbur={TRIM_VBUR}  drop_boltz_stdev={DROP_BOLTZ_STDEV}",
        f"level of theory: {LEVEL_OF_THEORY}",
        f"oracle cost    : ~{CPU_HOURS_TOTAL / N_PUBLISHED_ACIDS:.0f} "
        f"CPU-hours per molecule",
        "",
        f"{'base':<38} {'family':<14} {'unit':<12} description",
        "-" * 118,
    ]
    for b in BASE_NAMES:
        lines.append(f"{b:<38} {FAMILY_OF_BASE[b]:<14} "
                     f"{UNIT_OF_BASE[b][:11]:<12} {DESC_OF_BASE.get(b, '')}")
    lines += ["", "aggregations (scored):"]
    for a in AGGREGATIONS:
        lines.append(f"  _{a:<12} {AGG_DESCRIPTION[a]}")
    if EXTRA_AGGREGATIONS:
        lines += ["", "aggregations (shipped, not scored):"]
        for a in EXTRA_AGGREGATIONS:
            lines.append(f"  _{a:<12} {AGG_DESCRIPTION[a]}")
    lines += ["", "targets per family:"]
    for fam in FAMILIES:
        n = sum(1 for t in TARGET_COLUMNS if FAMILY_OF_TARGET[t] == fam)
        lines.append(f"  {fam:<15} {n:>3}  ({100 * n / N_TARGETS:.0f}%)")
    lines += ["", f"dropped %Vbur columns ({len(VBUR_DROPPED)}):"]
    for b in VBUR_DROPPED:
        lines.append(f"  {b}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary())
