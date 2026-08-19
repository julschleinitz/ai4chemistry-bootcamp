#!/usr/bin/env python3
"""
Step 01 -- fetch the published DFT descriptors. No chemistry is computed here.

Source: the MolSSI Descriptor Libraries REST API, which serves the acid library
from Haas et al., Digital Discovery 2025, 4, 222 (CC BY 4.0).

    https://descriptor-libraries.molssi.org/api/acids/
    OpenAPI: .../api/acids/openapi.json      docs: .../api/acids/docs

Endpoint used (verified working, no authentication):

    /molecules/data/export/batch?molecule_ids=Ac1,Ac2&data_type=dft&return_type=csv

Three things that will bite you if you touch this:

  * `data_type=dft` -- NOT `dft_data`, even though /molecules/data_types
    reports {"available_types":["dft_data"]}. The wrong value returns empty.
  * The CSV is SUFFIX-MAJOR: molecule_id, smiles, then all 55 `_min` columns,
    then all 55 `_max`, `_boltz`, `_low_e`, `_boltz_stdev`. 277 columns.
  * `min`/`max` occur inside the hemisphere base names, so
    `%Vbur_C1_min_hemisphere_3A_min` is a real column. Parsing goes through
    descriptor_spec.split_target(), never a regex.

Molecule ids are Ac1 ... Ac8528, contiguous.

Chunk responses are cached under data/api_cache/, so a re-run costs nothing and
an interrupted run resumes. Delete the cache directory to force a refetch.

Usage
-----
    python 01_fetch_dft_labels.py                  # the whole library
    python 01_fetch_dft_labels.py --limit 300      # quick smoke test
    python 01_fetch_dft_labels.py --xlsx ~/Downloads/Acid_Library.xlsx
                                                   # offline fallback

Output
------
    data/labels_all.csv         acid_id, molecule_id, smiles, published_smiles,
                                inchikey, murcko_scaffold, mw, n_heavy, n_rot,
                                subclass, <156 targets>, <39 _boltz_stdev extras>
    data/labels_all.report.md   provenance, coverage, what was dropped
    data/published_benchmark.csv  the paper's own 3D-GNN test numbers
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://descriptor-libraries.molssi.org/api/acids"
CHUNK = 100
RETRIES = 4
BACKOFF = 2.0

CITATION = (
    "Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.; "
    "Paton, R. S.; Sigman, M. S. Digital Discovery 2025, 4, 222-233. "
    "DOI 10.1039/D4DD00284A. Data: DOI 10.6084/m9.figshare.25213742. "
    "Served via https://descriptor-libraries.molssi.org/. CC BY 4.0."
)

# Metadata we derive ourselves with RDKit -- the API gives SMILES, not scaffolds.
SUBCLASS_SMARTS = [
    ("benzoic",     "c1ccccc1[CX3](=[OX1])[OX2H1]"),
    ("heteroaryl",  "[a;!c][a,c][CX3](=[OX1])[OX2H1]"),
    ("aryl_other",  "a[CX3](=[OX1])[OX2H1]"),
    ("alpha_amino", "[NX3][CX4][CX3](=[OX1])[OX2H1]"),
    ("alpha_quat",  "[CX4]([#6])([#6])([#6])[CX3](=[OX1])[OX2H1]"),
    ("cyclic_ali",  "[CX4;R][CX3](=[OX1])[OX2H1]"),
    ("acyclic_ali", "[CX4;!R][CX3](=[OX1])[OX2H1]"),
]
ACID_SMARTS = "[#6][CX3](=[OX1])[OX2H1]"


# --------------------------------------------------------------------------
# API access
# --------------------------------------------------------------------------
def _get(url: str, timeout: int = 180) -> bytes:
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "ai4chem-bootcamp/1.0",
                              "Accept": "text/csv, application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            wait = BACKOFF ** attempt
            print(f"    retry {attempt + 1}/{RETRIES} in {wait:.0f}s "
                  f"({type(exc).__name__})", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}") from last


def fetch_chunk(ids: list[str], cache_dir: Path, tag: str) -> str:
    """Return the CSV text for these molecule ids, using the on-disk cache."""
    cached = cache_dir / f"chunk_{tag}.csv"
    if cached.exists() and cached.stat().st_size > 0:
        return cached.read_text(encoding="utf-8")
    q = urllib.parse.urlencode({"molecule_ids": ",".join(ids),
                                "data_type": "dft", "return_type": "csv"})
    text = _get(f"{API}/molecules/data/export/batch?{q}").decode("utf-8")
    if not text.strip():
        raise RuntimeError(
            f"empty response for {ids[0]}..{ids[-1]}. If this persists, check "
            "that data_type=dft is still correct (see the module docstring)."
        )
    cached.write_text(text, encoding="utf-8")
    return text


def parse_csv(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse with the csv module -- never str.split(','), in case a SMILES is
    ever quoted."""
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = [r for r in reader if r]
    return rows[0], rows[1:]


def fetch_all(n_molecules: int, cache_dir: Path, chunk: int = CHUNK):
    """Yield (header, rows) for successive chunks of Ac1..AcN."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    ids = [f"Ac{i}" for i in range(1, n_molecules + 1)]
    for start in range(0, len(ids), chunk):
        block = ids[start : start + chunk]
        tag = f"{start:06d}"
        text = fetch_chunk(block, cache_dir, tag)
        header, rows = parse_csv(text)
        print(f"  {block[0]}..{block[-1]}: {len(rows)} rows", flush=True)
        yield header, rows


# --------------------------------------------------------------------------
# xlsx fallback
# --------------------------------------------------------------------------
def load_from_xlsx(path: Path, targets: list[str]):
    """Find the molecule-level sheet in Acid_Library.xlsx and return it."""
    import pandas as pd

    print(f"reading {path} (this is a 113 MB workbook; be patient)")
    book = pd.ExcelFile(path)
    print(f"  sheets: {book.sheet_names}")
    best, best_hits = None, -1
    for sheet in book.sheet_names:
        head = pd.read_excel(path, sheet_name=sheet, nrows=2)
        hits = sum(1 for t in targets if t in head.columns)
        print(f"  {sheet:<40} {hits}/{len(targets)} target columns")
        if hits > best_hits:
            best, best_hits = sheet, hits
    if best_hits < len(targets) // 2:
        raise SystemExit(
            f"no sheet in {path.name} looks like the molecule-level summary "
            f"(best was {best!r} with {best_hits} of {len(targets)} targets). "
            "Inspect the workbook and pass --xlsx-sheet."
        )
    print(f"  using sheet {best!r}")
    return pd.read_excel(path, sheet_name=best)


# --------------------------------------------------------------------------
def rdkit_metadata(smiles_list: list[str]):
    """Canonical SMILES + scaffold + descriptors + subclass. Returns
    (records, problems)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import Descriptors, Lipinski
    from rdkit.Chem.Scaffolds import MurckoScaffold

    RDLogger.DisableLog("rdApp.*")
    acid_patt = Chem.MolFromSmarts(ACID_SMARTS)
    subclass_patts = [(n, Chem.MolFromSmarts(s)) for n, s in SUBCLASS_SMARTS]

    records, problems = [], []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
        if mol is None:
            records.append(None)
            problems.append({"smiles": smi, "reason": "unparseable"})
            continue
        n_acid = len(mol.GetSubstructMatches(acid_patt))
        subclass = "other"
        for name, patt in subclass_patts:
            if mol.HasSubstructMatch(patt):
                subclass = name
                break
        rec = {
            "smiles": Chem.MolToSmiles(mol),
            "inchikey": Chem.MolToInchiKey(mol) or "",
            "murcko_scaffold": MurckoScaffold.MurckoScaffoldSmiles(mol=mol),
            "mw": round(Descriptors.MolWt(mol), 3),
            "n_heavy": mol.GetNumHeavyAtoms(),
            "n_rot": Lipinski.NumRotatableBonds(mol),
            "subclass": subclass,
            "n_free_cooh": n_acid,
        }
        records.append(rec)
        if n_acid != 1:
            problems.append({"smiles": smi, "reason": f"n_free_cooh={n_acid}"})
    return records, problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="../data/labels_all.csv")
    ap.add_argument("--cache", default="../data/api_cache")
    ap.add_argument("--n-molecules", type=int, default=8528)
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after N molecules (smoke test)")
    ap.add_argument("--chunk", type=int, default=CHUNK)
    ap.add_argument("--xlsx", default=None,
                    help="use a local Acid_Library.xlsx instead of the API")
    ap.add_argument("--xlsx-sheet", default=None)
    ap.add_argument("--keep-multi-cooh", action="store_true",
                    help="keep molecules whose SMILES match more than one free "
                         "COOH instead of dropping them")
    ap.add_argument("--verify-header", action="store_true",
                    help="assert the API header matches descriptor_spec exactly, "
                         "then exit")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))
    import pandas as pd

    from descriptor_spec import (API_COLUMN_ORDER, EXTRA_COLUMNS,
                                 PUBLISHED_AGGREGATIONS, TARGET_COLUMNS,
                                 CPU_HOURS_TOTAL, LEVEL_OF_THEORY,
                                 N_PUBLISHED_ACIDS, published_benchmark_rows,
                                 split_target)

    cache = Path(args.cache)
    n_want = min(args.limit or args.n_molecules, args.n_molecules)

    # ---- verify-header mode ---------------------------------------------
    if args.verify_header:
        cache.mkdir(parents=True, exist_ok=True)
        header, _ = parse_csv(fetch_chunk(["Ac1", "Ac2"], cache, "verify"))
        if header == API_COLUMN_ORDER:
            print(f"OK: API header matches descriptor_spec.API_COLUMN_ORDER "
                  f"({len(header)} columns)")
            return
        only_api = [c for c in header if c not in API_COLUMN_ORDER]
        only_spec = [c for c in API_COLUMN_ORDER if c not in header]
        print("MISMATCH -- the upstream schema has changed.")
        print(f"  api has {len(header)} columns, spec expects "
              f"{len(API_COLUMN_ORDER)}")
        print(f"  only in api : {only_api[:10]}")
        print(f"  only in spec: {only_spec[:10]}")
        if not only_api and not only_spec:
            print("  same set, different ORDER -- update API_COLUMN_ORDER")
        raise SystemExit(1)

    # ---- load -----------------------------------------------------------
    if args.xlsx:
        raw = (load_from_xlsx(Path(args.xlsx).expanduser(), TARGET_COLUMNS)
               if args.xlsx_sheet is None else
               pd.read_excel(args.xlsx, sheet_name=args.xlsx_sheet))
        if "molecule_id" not in raw.columns:
            for alt in ("Name", "name", "log_name", "Molecule", "ID"):
                if alt in raw.columns:
                    raw = raw.rename(columns={alt: "molecule_id"})
                    break
        raw["molecule_id"] = raw["molecule_id"].astype(str).str.split("_").str[0]
        source = f"local xlsx: {Path(args.xlsx).name}"
    else:
        print(f"fetching Ac1..Ac{n_want} from {API}")
        print(f"cache: {cache}")
        header_seen: list[str] | None = None
        header_warned = set()
        frames = []
        for header, rows in fetch_all(n_want, cache, args.chunk):
            if header_seen is None:
                header_seen = header
                if header != API_COLUMN_ORDER:
                    print("\nWARNING: the API header does not match "
                          "descriptor_spec.API_COLUMN_ORDER. Columns will be "
                          "matched BY NAME, which is safe, but run "
                          "--verify-header and update the spec.\n")
            elif set(header) != set(header_seen):
                # A chunk can drop a column outright when every molecule in that
                # chunk has no data for it (seen in practice: a boltz_stdev extra
                # vanishes for a batch where the underlying dihedral is
                # undefined for every molecule). pd.concat aligns by column name
                # and fills the gap with NaN, so this is safe as long as no
                # *scored* TARGET_COLUMNS are among the missing ones -- checked
                # against the full concatenated frame below.
                missing_here = set(header_seen) - set(header)
                extra_here = set(header) - set(header_seen)
                new = (missing_here | extra_here) - header_warned
                if new:
                    print(f"\nNOTE: this chunk's header differs from the first "
                          f"chunk's by {len(new)} column(s): {sorted(new)[:5]}"
                          f"{'...' if len(new) > 5 else ''}. Matching by name; "
                          "concat will fill the gap with NaN.\n")
                    header_warned |= new
            frames.append(pd.DataFrame(rows, columns=header))
        if not frames:
            raise SystemExit("no data returned")
        raw = pd.concat(frames, ignore_index=True)
        source = f"MolSSI API ({API})"

    print(f"\n{len(raw):,} molecules returned")

    missing = [c for c in TARGET_COLUMNS if c not in raw.columns]
    if missing:
        raise SystemExit(
            f"{len(missing)} target column(s) absent from the source, e.g. "
            f"{missing[:5]}. Run --verify-header."
        )

    numeric_cols = [c for c in raw.columns if c not in ("molecule_id", "smiles")]
    raw[numeric_cols] = raw[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # ---- RDKit metadata --------------------------------------------------
    print("deriving scaffolds and metadata with RDKit")
    meta, problems = rdkit_metadata(raw["smiles"].tolist())
    keep_mask = [m is not None for m in meta]
    meta_df = pd.DataFrame([m for m in meta if m is not None])
    raw = raw.loc[keep_mask].reset_index(drop=True)
    raw = raw.rename(columns={"smiles": "published_smiles"})
    df = pd.concat([raw.reset_index(drop=True), meta_df.reset_index(drop=True)],
                   axis=1)

    dropped: list[dict] = list(problems)
    if not args.keep_multi_cooh:
        bad = df["n_free_cooh"] != 1
        if bad.any():
            print(f"dropping {int(bad.sum())} molecules that do not match "
                  "exactly one free COOH (use --keep-multi-cooh to keep them)")
            dropped += [{"smiles": s, "reason": f"n_free_cooh={n}"}
                        for s, n in zip(df.loc[bad, "smiles"],
                                        df.loc[bad, "n_free_cooh"])]
            df = df.loc[~bad].reset_index(drop=True)

    all_nan = df[TARGET_COLUMNS].isna().all(axis=1)
    if all_nan.any():
        print(f"dropping {int(all_nan.sum())} molecules with no descriptor data")
        dropped += [{"smiles": s, "reason": "no_descriptors"}
                    for s in df.loc[all_nan, "smiles"]]
        df = df.loc[~all_nan].reset_index(drop=True)

    # published id is the primary key -- traceable straight back to the paper
    df["acid_id"] = df["molecule_id"]
    df["_order"] = df["molecule_id"].str.extract(r"(\d+)").astype(int)
    df = df.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    lead = ["acid_id", "molecule_id", "smiles", "published_smiles", "inchikey",
            "murcko_scaffold", "mw", "n_heavy", "n_rot", "subclass"]
    extras = [c for c in EXTRA_COLUMNS if c in df.columns]
    df = df[lead + TARGET_COLUMNS + extras]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    if dropped:
        pd.DataFrame(dropped).to_csv(out.with_suffix(".dropped.csv"),
                                     index=False, encoding="utf-8")

    bench = pd.DataFrame(published_benchmark_rows())
    bench.to_csv(out.parent / "published_benchmark.csv", index=False,
                 encoding="utf-8")

    # ---- report ---------------------------------------------------------
    nan_rate = df[TARGET_COLUMNS].isna().mean()
    canon_differs = int((df["smiles"] != df["published_smiles"]).sum())
    lines = [
        "# labels_all.csv provenance report", "",
        f"- source: {source}",
        f"- molecules: **{len(df):,}** of {N_PUBLISHED_ACIDS:,} published",
        f"- scored targets: **{len(TARGET_COLUMNS)}** "
        f"(+{len(extras)} unscored `_boltz_stdev` extras)",
        f"- level of theory: `{LEVEL_OF_THEORY}`",
        f"- reported cost of the source library: **{CPU_HOURS_TOTAL:,} CPU hours** "
        f"(~{CPU_HOURS_TOTAL / N_PUBLISHED_ACIDS:.0f} CPU-hours per molecule)",
        f"- molecules dropped: **{len(dropped)}**",
        f"- unique Murcko scaffolds: **{df['murcko_scaffold'].nunique():,}**",
        f"- RDKit canonicalisation changed the SMILES string for "
        f"{canon_differs:,} molecules (both are kept: `smiles` is ours, "
        f"`published_smiles` is theirs)",
        "", f"**Cite:** {CITATION}", "",
        "## Subclass composition", "",
        "| subclass | n |", "|---|---|",
    ]
    for k, v in df["subclass"].value_counts().items():
        lines.append(f"| {k} | {v:,} |")

    lines += ["", "## Targets with missing values", ""]
    worst = nan_rate[nan_rate > 0].sort_values(ascending=False)
    if len(worst):
        lines += ["| target | NaN fraction |", "|---|---|"]
        for t, v in worst.head(25).items():
            lines.append(f"| `{t}` | {v:.4f} |")
    else:
        lines.append("None. Every scored target is complete for every molecule.")

    lines += ["", "## Conformational spread by base property", "",
              "`mean(_max - _min) / std(_boltz)` -- how much of each "
              "descriptor's variation is conformational rather than structural. "
              "The published `_boltz_stdev` columns are the authors' own "
              "version of this and ship with the dev set.", "",
              "| base property | spread |", "|---|---|"]
    rows = []
    for t in TARGET_COLUMNS:
        base, agg = split_target(t)
        if agg != "boltz":
            continue
        sd = df[t].std()
        lo, hi = f"{base}_min", f"{base}_max"
        if sd and sd > 0 and lo in df.columns and hi in df.columns:
            rows.append((base, float(((df[hi] - df[lo]) / sd).mean())))
    for base, v in sorted(rows, key=lambda r: -r[1]):
        lines.append(f"| `{base}` | {v:.3f} |")

    out.with_suffix(".report.md").write_text("\n".join(lines) + "\n",
                                             encoding="utf-8")

    print(f"\nwrote {out}  ({len(df):,} molecules x {len(TARGET_COLUMNS)} targets)")
    print(f"wrote {out.with_suffix('.report.md')}")
    print(f"wrote {out.parent / 'published_benchmark.csv'} "
          f"({len(bench)} reference rows)")
    print(f"\nCITE: {CITATION}")
    print("\nNext: python 02_make_splits.py")


if __name__ == "__main__":
    main()
