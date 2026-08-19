#!/usr/bin/env python3
"""
Logic tests that need only numpy + pandas -- no chemprop, no rdkit, no torch.

    python tests/test_logic.py

They cover the parts that are easy to get silently wrong:

  * the descriptor spec is internally consistent (39 x 4 = 156)
  * `API_COLUMN_ORDER` reproduces the real MolSSI header BYTE FOR BYTE, checked
    against tests/api_header_reference.txt (captured from the live API)
  * `split_target` survives the `min`/`max`-inside-a-base-name trap
  * a synthetic API response parses back to the right (base, aggregation) grid
  * seal / unseal round-trips, and detects a wrong key
  * the Oracle enforces the budget, never double-charges, and logs correctly
  * scaled MAE, ENCE and the Spearman fallback behave as advertised, and a
    constant-sigma model really is punished by ENCE
  * every numpy-only acquisition function returns k distinct in-range positions
  * the scaffold split is disjoint and deterministic
  * a fabricated submission passes validate_submission's static checks, and six
    specific ways of breaking it are all caught

Run this after any edit to descriptor_spec.py, obfuscate.py or al_toolkit.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "instructor"))
sys.path.insert(0, str(ROOT))

PASS, FAIL = "\033[32mpass\033[0m", "\033[31mFAIL\033[0m"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {PASS if cond else FAIL}  {name}"
          + (f"  -- {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def load_module(path: Path, name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ==========================================================================
def test_spec() -> None:
    print("\ndescriptor_spec")
    import descriptor_spec as ds

    check("55 published bases", len(ds.PUBLISHED_BASES) == 55,
          str(len(ds.PUBLISHED_BASES)))
    check("39 shipped bases", ds.N_BASE == 39, str(ds.N_BASE))
    check("156 shipped targets", ds.N_TARGETS == 156, str(ds.N_TARGETS))
    check("no duplicate targets", len(set(ds.TARGET_COLUMNS)) == ds.N_TARGETS)
    check("shipped bases are a subset of the published ones",
          set(ds.BASE_NAMES) <= set(ds.PUBLISHED_BASES))
    check("16 vbur columns dropped", len(ds.VBUR_DROPPED) == 16,
          str(len(ds.VBUR_DROPPED)))
    check("vbur is 12 of 39 bases",
          sum(1 for b in ds.BASE_NAMES if ds.FAMILY_OF_BASE[b] == "vbur") == 12)
    check("vbur is under a third of the targets",
          sum(1 for t in ds.TARGET_COLUMNS
              if ds.FAMILY_OF_TARGET[t] == "vbur") / ds.N_TARGETS < 0.34)
    check("our order is property-major",
          ds.TARGET_COLUMNS[:4] == [f"{ds.BASE_NAMES[0]}_{a}"
                                    for a in ds.AGGREGATIONS])
    check("boltz_stdev is excluded from the scored set",
          "boltz_stdev" not in ds.AGGREGATIONS
          and "boltz_stdev" in ds.EXTRA_AGGREGATIONS)
    check("39 unscored extras shipped", len(ds.EXTRA_COLUMNS) == 39,
          str(len(ds.EXTRA_COLUMNS)))
    check("every family is populated",
          set(ds.FAMILY_OF_BASE.values()) == set(ds.FAMILIES))
    check("Angstrom sign is U+00C5, not U+212B", ord(ds.A) == 0x00C5,
          hex(ord(ds.A)))
    check("ASCII aliases are unique",
          len(set(ds.ASCII_OF_TARGET.values())) == ds.N_TARGETS)
    check("ASCII aliases are pure ASCII",
          all(v.isascii() for v in ds.ASCII_OF_TARGET.values()))
    check("published benchmark rows all name shipped targets",
          all(r["target"] in ds.TARGET_COLUMNS
              for r in ds.published_benchmark_rows()))
    check("published benchmark is non-empty",
          len(ds.published_benchmark_rows()) >= 16,
          str(len(ds.published_benchmark_rows())))


def test_api_header() -> None:
    print("\nAPI header (against the live-captured reference)")
    import descriptor_spec as ds

    ref_path = ROOT / "tests" / "api_header_reference.txt"
    if not ref_path.exists():
        check("reference header file present", False, str(ref_path))
        return
    real = ref_path.read_text(encoding="utf-8").strip()
    mine = ",".join(ds.API_COLUMN_ORDER)

    check("API_COLUMN_ORDER matches the real header byte for byte",
          real == mine,
          f"{len(real)} vs {len(mine)} chars")
    cols = real.split(",")
    check("277 columns", len(cols) == 277, str(len(cols)))
    check("first two columns are molecule_id, smiles",
          cols[:2] == ["molecule_id", "smiles"])
    check("layout is suffix-major, not property-major",
          cols[2] == f"{ds.PUBLISHED_BASES[0]}_min"
          and cols[3] == f"{ds.PUBLISHED_BASES[1]}_min")

    # the trap
    trap = [c for c in cols if "hemisphere" in c and c.endswith(("_min", "_max"))]
    check("the min/max hemisphere trap exists in the real data",
          len(trap) == 20, str(len(trap)))
    mis = [c for c in trap if ds.split_target(c)[0] not in ds.PUBLISHED_BASES]
    check("split_target parses every trap column correctly", not mis,
          str(mis[:3]))
    unparsed = [c for c in cols[2:]
                if ds.split_target(c)[0] not in ds.PUBLISHED_BASES
                or ds.split_target(c)[1] not in ds.PUBLISHED_AGGREGATIONS]
    check("split_target parses all 275 descriptor columns", not unparsed,
          str(unparsed[:3]))

    # a naive suffix strip must fail, or the trap test is not testing anything
    naive = "%Vbur_C1_min_hemisphere_3" + ds.A + "_min"
    check("a naive rstrip WOULD corrupt the trap (so the test is meaningful)",
          naive.replace("_min", "") != ds.split_target(naive)[0])

    check("every shipped target exists in the real header",
          set(ds.TARGET_COLUMNS) <= set(cols))
    check("every shipped extra exists in the real header",
          set(ds.EXTRA_COLUMNS) <= set(cols))
    check("split_target rejects a bare base name",
          _raises(ds.split_target, "HOMO", ValueError))


def _raises(fn, arg, exc) -> bool:
    try:
        fn(arg)
    except exc:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def test_api_parsing() -> None:
    print("\nAPI response parsing")
    import descriptor_spec as ds

    fetcher = load_module(ROOT / "instructor" / "01_fetch_dft_labels.py", "fetcher")

    header = ",".join(ds.API_COLUMN_ORDER)
    # synthetic rows in the numeric formats the real API actually emits:
    # full-precision floats, scientific notation, exact 0.0, negatives
    vals1 = ["93.91464359504133", "-0.35996", "2.055481493385033e-05", "0.0"]
    row1 = ["Ac1", "OC(CCCCCCCCC)=O"] + [vals1[i % 4] for i in range(275)]
    row2 = ["Ac2", "OC(=O)c1ccccc1"] + [vals1[(i + 1) % 4] for i in range(275)]
    text = header + "\n" + ",".join(row1) + "\n" + ",".join(row2) + "\n"

    got_header, rows = fetcher.parse_csv(text)
    check("parse_csv recovers the header exactly",
          got_header == ds.API_COLUMN_ORDER)
    check("parse_csv recovers both rows", len(rows) == 2)
    check("each row has 277 fields", all(len(r) == 277 for r in rows))

    df = pd.DataFrame(rows, columns=got_header)
    num = [c for c in df.columns if c not in ("molecule_id", "smiles")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    check("scientific notation parses",
          np.isfinite(df[num].to_numpy(float)).all())
    check("all 156 shipped targets are selectable by name",
          df[ds.TARGET_COLUMNS].shape == (2, 156))
    check("all 39 extras are selectable by name",
          df[ds.EXTRA_COLUMNS].shape == (2, 39))
    check("smiles survives with parentheses intact",
          df["smiles"].iloc[1] == "OC(=O)c1ccccc1")

    # a quoted SMILES containing a comma must not break the parser
    tricky = (",".join(["molecule_id", "smiles", "HOMO_min"]) + "\n"
              + 'Ac3,"CC(C)C,weird",-0.3\n')
    h2, r2 = fetcher.parse_csv(tricky)
    check("a quoted field containing a comma parses as one field",
          len(r2[0]) == 3 and r2[0][1] == "CC(C)C,weird",
          str(r2[0]))


def test_seal() -> None:
    print("\nobfuscate")
    import obfuscate as ob

    ids = [f"Ac{i}" for i in range(1, 38)]
    cols = [f"t{i}" for i in range(11)]
    vals = np.random.default_rng(0).normal(size=(37, 11))
    key = b"a-key"
    blob = ob.seal_labels(ids, cols, vals, key)

    got_ids, got_cols, got_vals = ob.unseal_labels(blob, key)
    check("ids round-trip", got_ids == ids)
    check("columns round-trip", got_cols == cols)
    check("values round-trip exactly", np.array_equal(got_vals, vals))
    check("sealed bytes do not contain a plaintext id", b"Ac1," not in blob)
    check("wrong key rejected",
          _raises(lambda b: ob.unseal_labels(b, b"wrong"), blob, ValueError))

    corrupt = bytearray(blob)
    corrupt[-5] ^= 0xFF
    check("corruption detected",
          _raises(lambda b: ob.unseal_labels(b, key), bytes(corrupt), ValueError))

    import al_toolkit as al
    check("student _unseal matches instructor seal",
          al._unseal(ob.seal(b"hello world", al._KEY)) == b"hello world")


def make_fake_bundle(root: Path, n_pool=300, n_dev=120, seed=0):
    """A tiny bundle with the real spec's shape but fake molecules."""
    import descriptor_spec as ds
    import obfuscate as ob
    from al_toolkit import _KEY

    rng = np.random.default_rng(seed)
    # use REAL target names -- that is the point, they contain the traps
    targets = ds.TARGET_COLUMNS[:24]
    extras = ds.EXTRA_COLUMNS[:6]
    fam_of = {t: ds.FAMILY_OF_TARGET[t] for t in targets}
    families = sorted(set(fam_of.values()))

    root.mkdir(parents=True, exist_ok=True)
    pool = pd.DataFrame({
        "acid_id": [f"Ac{i + 1}" for i in range(n_pool)],
        "smiles": [f"C{'C' * (i % 5)}C(=O)O" for i in range(n_pool)],
        "mw": rng.uniform(80, 350, n_pool),
        "n_heavy": rng.integers(5, 30, n_pool),
        "n_rot": rng.integers(0, 8, n_pool),
        "subclass": rng.choice(["benzoic", "acyclic_ali", "heteroaryl"], n_pool),
        "murcko_scaffold": [f"S{i % 40}" for i in range(n_pool)],
    })
    pool.to_csv(root / "pool_meta.csv", index=False, encoding="utf-8")

    dev = pd.DataFrame({
        "acid_id": [f"Dev{i}" for i in range(n_dev)],
        "smiles": [f"C{'C' * (i % 4)}C(=O)O" for i in range(n_dev)],
        "mw": rng.uniform(80, 350, n_dev),
        "n_heavy": rng.integers(5, 30, n_dev),
        "n_rot": rng.integers(0, 8, n_dev),
        "subclass": rng.choice(["benzoic", "acyclic_ali"], n_dev),
        "murcko_scaffold": [f"D{i % 20}" for i in range(n_dev)],
    })
    for j, t in enumerate(targets):
        dev[t] = rng.normal(10 * j, 1 + j, n_dev)
    for t in extras:
        dev[t] = np.abs(rng.normal(1, 0.3, n_dev))
    dev.to_csv(root / "dev.csv", index=False, encoding="utf-8")
    dev[["acid_id", "smiles"]].head(20).to_csv(
        root / "selftest_smiles.csv", index=False, encoding="utf-8")

    vals = rng.normal(size=(n_pool, len(targets)))
    (root / "pool_labels.enc").write_bytes(
        ob.seal_labels(pool["acid_id"].tolist(), targets, vals, _KEY))

    (root / "targets.json").write_text(json.dumps({
        "targets": targets, "n_targets": len(targets),
        "extras_unscored": extras,
        "base_properties": sorted({ds.split_target(t)[0] for t in targets}),
        "aggregations": ds.AGGREGATIONS,
        "extra_aggregations": ds.EXTRA_AGGREGATIONS,
        "families": families, "family_of_target": fam_of,
        "unit_of_base": ds.UNIT_OF_BASE,
        "description_of_base": ds.DESC_OF_BASE,
        "ascii_of_target": {t: ds.ASCII_OF_TARGET[t] for t in targets},
        "budget": {"seed": 10, "rounds": 3, "batch": 10, "total": 40},
        "sigma_suffix": "_sigma",
        "provenance": {"cpu_hours_per_label": 117.3,
                       "published_cpu_hours": 1_000_000,
                       "published_acids": 8528,
                       "level_of_theory": "test",
                       "published_gnn_train_size": 7290},
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return targets


def test_bundle(tmp: Path) -> None:
    print("\nBundle helpers")
    import al_toolkit as al
    import descriptor_spec as ds

    bdir = tmp / "bundle"
    targets = make_fake_bundle(bdir)
    bundle = al.load_bundle(bdir)

    check("targets load in order", bundle.targets == targets)
    check("extras load", len(bundle.extras) == 6)
    check("unicode target names survive the json round-trip",
          any(ds.A in t for t in bundle.targets))
    check("cpu_hours scales linearly",
          abs(bundle.cpu_hours(600) - 600 * 117.3) < 1e-6)
    check("describe_oracle mentions the cost",
          "CPU-hours" in bundle.describe_oracle())
    check("ascii() strips unicode",
          all(bundle.ascii(t).isascii() for t in bundle.targets))

    # base_of must survive the min/max hemisphere trap
    trap = [t for t in ds.TARGET_COLUMNS
            if "hemisphere" in t and ds.AGG_OF_TARGET[t] in ("min", "max")]
    if trap:
        b2 = al.Bundle(root=bdir, pool_meta=bundle.pool_meta, dev=bundle.dev,
                       targets=ds.TARGET_COLUMNS, spec=bundle.spec,
                       selftest_smiles=[], extras=[])
        wrong = [t for t in trap if b2.base_of(t) != ds.BASE_OF_TARGET[t]]
        check("Bundle.base_of survives the hemisphere trap", not wrong,
              str(wrong[:2]))
    check("families partition the targets",
          {bundle.family_of(t) for t in bundle.targets}
          <= set(bundle.spec["families"]))


def test_oracle(tmp: Path) -> None:
    print("\nOracle")
    import al_toolkit as al

    bdir = tmp / "bundle"
    if not (bdir / "targets.json").exists():
        make_fake_bundle(bdir)
    bundle = al.load_bundle(bdir)
    targets = bundle.targets

    log = tmp / "log.jsonl"
    oracle = al.Oracle(bundle, budget=40, log_path=log)
    ids = bundle.pool_meta["acid_id"].tolist()

    y = oracle.query(ids[:10])
    check("query returns the right shape", y.shape == (10, len(targets) + 1),
          str(y.shape))
    check("spent counted", oracle.spent == 10)
    oracle.query(ids[:10])
    check("repeat purchase is free", oracle.spent == 10)
    oracle.query(ids[5:20])
    check("partial overlap charged only for the new ones", oracle.spent == 20)

    check("budget enforced",
          _raises(oracle.query, ids[20:100], al.BudgetExceeded))
    check("failed query charged nothing", oracle.spent == 20)
    check("unknown id rejected", _raises(oracle.query, ["NOT_AN_ID"], KeyError))
    check("labels_for refuses unpaid molecules",
          _raises(oracle.labels_for, [ids[299]], al.BudgetExceeded))

    oracle.finalize()
    recs = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    bought = [a for r in recs if r.get("event") == "query" for a in r["acid_ids"]]
    check("log has no duplicates", len(bought) == len(set(bought)))
    check("log count == spent", len(set(bought)) == oracle.spent)
    check("log ends with a final record", recs[-1]["event"] == "final")
    check("query only returns requested rows", len(oracle.query([ids[0]])) == 1)


def test_metrics() -> None:
    print("\nmetrics")
    import al_toolkit as al

    rng = np.random.default_rng(0)
    n, T = 400, 8
    # magnitudes deliberately spanning the real dataset's range:
    # NBO charge ~0.5 e up to volume ~2000 Bohr^3
    scale = np.array([0.05, 0.3, 60.0, 170.0, 1800.0, 2000.0, 1.5, 0.02])
    y = rng.normal(size=(n, T)) * scale

    check("perfect prediction -> sMAE 0", abs(al.scaled_mae(y, y.copy())) < 1e-12)

    mean_pred = np.tile(np.nanmean(y, axis=0), (n, 1))
    smae_mean = al.scaled_mae(y, mean_pred)
    check("predicting the mean -> sMAE ~ 0.8 (E|z| for a normal)",
          0.7 < smae_mean < 0.9, f"{smae_mean:.3f}")

    y2 = y * 1000.0
    pred = y + rng.normal(size=(n, T)) * scale * 0.3
    check("sMAE invariant under per-task rescaling",
          abs(al.scaled_mae(y, pred) - al.scaled_mae(y2, pred * 1000.0)) < 1e-9)

    sigma_true = np.abs(rng.normal(size=(n, T))) * scale * 0.5 + 0.1 * scale
    y_h = np.zeros((n, T))
    pred_h = rng.normal(size=(n, T)) * sigma_true
    good = al.ence(y_h, pred_h, sigma_true, n_bins=8)
    const = al.ence(y_h, pred_h, np.tile(sigma_true.mean(axis=0), (n, 1)), n_bins=8)
    check("ENCE small for a well-calibrated sigma", good < 0.25, f"{good:.3f}")
    check("ENCE punishes a constant sigma", const > good * 1.5,
          f"constant {const:.3f} vs calibrated {good:.3f}")

    rho = al.sigma_error_spearman(y_h, pred_h, sigma_true)
    check("Spearman(sigma,|err|) positive for an informative sigma", rho > 0.3,
          f"{rho:.3f}")
    check("Spearman fallback: perfect correlation",
          abs(al._spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-12)
    check("Spearman fallback: anti-correlation",
          abs(al._spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-12)
    check("Spearman fallback: ties",
          np.isfinite(al._spearman([1, 1, 2, 2], [1, 2, 1, 2])))

    per_task = al.scaled_mae_per_task(y, pred)
    check("per-task sMAE has one entry per task", per_task.shape == (T,))
    check("per-task mean equals scalar sMAE",
          abs(np.nanmean(per_task) - al.scaled_mae(y, pred)) < 1e-12)

    y_nan = y.copy()
    y_nan[::7, 3] = np.nan
    check("sMAE tolerates NaN targets", np.isfinite(al.scaled_mae(y_nan, pred)))


def test_acquisition() -> None:
    print("\nacquisition functions (numpy-only ones)")
    import al_toolkit as al

    rng = np.random.default_rng(0)
    n, T, D, k = 200, 8, 16, 20
    # same brutal magnitude spread as the real descriptor set
    scales = np.array([0.05, 0.3, 60.0, 170.0, 1800.0, 2000.0, 1.5, 0.02])
    epi = np.abs(rng.normal(size=(n, T))) * scales * 0.2
    ale = np.abs(rng.normal(size=(n, T))) * scales * 0.2
    cand = al.Candidates(
        acid_ids=[f"Ac{i}" for i in range(n)], smiles=["CC(=O)O"] * n,
        mean=rng.normal(size=(n, T)) * scales,
        sigma=np.sqrt(epi ** 2 + ale ** 2),
        sigma_epistemic=epi, sigma_aleatoric=ale,
        emb=rng.normal(size=(n, D)), labeled_emb=rng.normal(size=(30, D)),
        scales=scales, rng=rng)

    for name in ["random", "max_variance", "max_variance_scaled",
                 "max_epistemic", "bald_ensemble", "coreset_greedy",
                 "qbc_disagreement", "uncertainty_times_novelty"]:
        idx = np.asarray(al.ACQUISITION[name](k, cand)).astype(int)
        ok = (len(idx) == k and len(set(idx.tolist())) == k
              and idx.min() >= 0 and idx.max() < n)
        check(f"{name} returns {k} distinct valid positions", ok,
              f"len={len(idx)} unique={len(set(idx.tolist()))}")

    raw = np.asarray(al.max_variance(k, cand))
    sc = np.asarray(al.max_variance_scaled(k, cand))
    check("max_variance and max_variance_scaled disagree",
          len(set(raw.tolist()) & set(sc.tolist())) < k,
          "identical batches -- the notebook 04 lesson will not land")

    big = int(np.argmax(scales))
    share = (cand.sigma[:, big] / cand.sigma.sum(axis=1)).mean()
    check("the largest-unit task dominates the raw score", share > 1.5 / T,
          f"share {share:.3f} vs 1/T={1 / T:.3f}")

    s = cand.scaled(cand.sigma)
    spread = s.mean(axis=0)
    check("scaled() equalises task magnitudes",
          spread.max() / spread.min() < 5.0,
          f"ratio {spread.max() / spread.min():.2f}")

    cand2 = al.Candidates(
        acid_ids=cand.acid_ids, smiles=cand.smiles, mean=cand.mean,
        sigma=cand.sigma, sigma_epistemic=epi, sigma_aleatoric=ale.copy(),
        emb=cand.emb, labeled_emb=cand.labeled_emb, scales=scales,
        rng=np.random.default_rng(1))
    cand2.sigma_aleatoric[0] *= 50
    cand2.sigma = np.sqrt(cand2.sigma_epistemic ** 2 + cand2.sigma_aleatoric ** 2)
    check("total-uncertainty sampling buys the noisy molecule",
          0 in np.asarray(al.max_variance_scaled(k, cand2)))
    check("BALD refuses the noisy molecule",
          0 not in np.asarray(al.bald_ensemble(k, cand2)))

    cand3 = al.Candidates(
        acid_ids=cand.acid_ids, smiles=cand.smiles, mean=cand.mean, sigma=ale,
        sigma_epistemic=np.zeros_like(ale), sigma_aleatoric=ale, emb=cand.emb,
        labeled_emb=cand.labeled_emb, scales=scales,
        rng=np.random.default_rng(2))
    check("max_epistemic falls back to random with no epistemic signal",
          len(set(np.asarray(al.max_epistemic(k, cand3)).tolist())) == k)
    check("your_own raises NotImplementedError until written",
          _raises(lambda c: al.your_own(k, c), cand, NotImplementedError))


def test_scaffold_split() -> None:
    print("\nscaffold split (step 02 logic)")
    mk = load_module(ROOT / "instructor" / "02_make_splits.py", "mk")

    rng = np.random.default_rng(0)
    n = 2000
    df = pd.DataFrame({
        "acid_id": [f"Ac{i + 1}" for i in range(n)],
        "murcko_scaffold": [f"S{i % 250}" for i in range(n)],
        "subclass": rng.choice(["benzoic", "acyclic_ali", "heteroaryl"], n),
    })
    split = mk.scaffold_split(df, n_test=200, n_dev=200, seed=1,
                              balance_subclass=True)
    df["split"] = split.values
    counts = df["split"].value_counts().to_dict()
    check("all three splits populated",
          {"pool", "dev", "test_hidden"} <= set(counts), str(counts))
    for a, b in (("pool", "dev"), ("pool", "test_hidden"),
                 ("dev", "test_hidden")):
        sa = set(df.loc[df.split == a, "murcko_scaffold"])
        sb = set(df.loc[df.split == b, "murcko_scaffold"])
        check(f"{a} / {b} scaffold-disjoint", not (sa & sb),
              f"{len(sa & sb)} shared")
    check("every molecule assigned", df["split"].notna().all())
    check("test size in the right ballpark",
          100 <= counts.get("test_hidden", 0) <= 400,
          str(counts.get("test_hidden")))
    split2 = mk.scaffold_split(df.drop(columns="split"), 200, 200, 1, True)
    check("split is deterministic given the seed",
          (split.values == split2.values).all())


def test_validator(tmp: Path) -> None:
    print("\nvalidate_submission (static checks)")
    import al_toolkit as al

    bdir = tmp / "bundle"
    if not (bdir / "targets.json").exists():
        make_fake_bundle(bdir)
    bundle = al.load_bundle(bdir)
    targets = bundle.targets

    sub = tmp / "submission_fake"
    (sub / "models").mkdir(parents=True, exist_ok=True)
    (sub / "models" / "model_0.pt").write_bytes(b"not-a-real-checkpoint")
    (sub / "predict.py").write_bytes((ROOT / "predict.py").read_bytes())

    ids = bundle.pool_meta["acid_id"].tolist()[:40]
    with (sub / "al_log.jsonl").open("w") as fh:
        fh.write(json.dumps({"event": "init", "budget": 40}) + "\n")
        fh.write(json.dumps({"event": "query", "round": 0,
                             "acid_ids": ids}) + "\n")
    pd.DataFrame({"round": [0, 1], "n_labels": [20, 40],
                  "dev_scaled_mae": [0.9, 0.7],
                  "dev_ence": [0.4, 0.3]}).to_csv(
        sub / "learning_curve.csv", index=False, encoding="utf-8")
    (sub / "manifest.json").write_text(json.dumps({
        "team": "fake", "targets": targets, "head": "mve",
        "model_files": ["model_0.pt"], "labels_used": len(ids),
        "acquisition": "max_variance_scaled", "seed_method": "maxmin",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    cmd = [sys.executable, str(ROOT / "validate_submission.py"),
           "--submission-dir", str(sub), "--bundle", str(bdir),
           "--skip-inference"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    check("a well-formed submission passes the static checks",
          "READY TO SUBMIT" in proc.stdout, proc.stdout[-900:])

    def expect_fail(label: str, mutate) -> None:
        paths = [sub / "manifest.json", sub / "al_log.jsonl", sub / "predict.py"]
        backup = {p: p.read_bytes() for p in paths}
        mutate()
        p = subprocess.run(cmd, capture_output=True, text=True)
        check(label, p.returncode != 0, p.stdout[-500:])
        for path, data in backup.items():
            path.write_bytes(data)

    def shuffle_targets():
        m = json.loads((sub / "manifest.json").read_text(encoding="utf-8"))
        m["targets"] = list(reversed(m["targets"]))
        (sub / "manifest.json").write_text(json.dumps(m, ensure_ascii=False),
                                           encoding="utf-8")

    def sorted_targets():
        # the realistic version of the mistake: someone calls sorted()
        m = json.loads((sub / "manifest.json").read_text(encoding="utf-8"))
        m["targets"] = sorted(m["targets"])
        (sub / "manifest.json").write_text(json.dumps(m, ensure_ascii=False),
                                           encoding="utf-8")

    def over_budget():
        with (sub / "al_log.jsonl").open("w") as fh:
            fh.write(json.dumps({"event": "query", "round": 0,
                                 "acid_ids": bundle.pool_meta["acid_id"]
                                 .tolist()[:250]}) + "\n")
        m = json.loads((sub / "manifest.json").read_text(encoding="utf-8"))
        m["labels_used"] = 250
        (sub / "manifest.json").write_text(json.dumps(m, ensure_ascii=False),
                                           encoding="utf-8")

    def duplicate_purchases():
        with (sub / "al_log.jsonl").open("w") as fh:
            fh.write(json.dumps({"event": "query", "round": 0,
                                 "acid_ids": ids + ids[:5]}) + "\n")

    def tamper_predict():
        (sub / "predict.py").write_text(
            (sub / "predict.py").read_text() + "\n# sneaky\n")

    def wrong_labels_used():
        m = json.loads((sub / "manifest.json").read_text(encoding="utf-8"))
        m["labels_used"] = 39
        (sub / "manifest.json").write_text(json.dumps(m, ensure_ascii=False),
                                           encoding="utf-8")

    def dev_ids_in_log():
        dev_ids = pd.read_csv(bdir / "dev.csv", encoding="utf-8")["acid_id"]\
            .tolist()[:5]
        with (sub / "al_log.jsonl").open("w") as fh:
            fh.write(json.dumps({"event": "query", "round": 0,
                                 "acid_ids": ids + dev_ids}) + "\n")

    expect_fail("rejects reversed target order", shuffle_targets)
    expect_fail("rejects sorted() target order", sorted_targets)
    expect_fail("rejects an over-budget log", over_budget)
    expect_fail("rejects duplicate purchases", duplicate_purchases)
    expect_fail("rejects a modified predict.py", tamper_predict)
    expect_fail("rejects labels_used disagreeing with the log", wrong_labels_used)
    expect_fail("rejects dev molecules in the purchase log", dev_ids_in_log)


def test_predict_hash() -> None:
    print("\npredict.py checksum file")
    import hashlib

    p = ROOT / "predict.py"
    h = ROOT / "predict.py.sha256"
    check("checksum file exists", h.exists())
    if h.exists():
        want = h.read_text().split()[0].strip()
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        check("checksum matches the shipped predict.py", want == got,
              "regenerate with tools/refresh_checksum.sh")


def main() -> int:
    print("=" * 72)
    print("active learning tutorial -- logic tests")
    print("=" * 72)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        test_spec()
        test_api_header()
        test_api_parsing()
        test_seal()
        test_bundle(tmp)
        test_oracle(tmp)
        test_metrics()
        test_acquisition()
        test_scaffold_split()
        test_validator(tmp)
        test_predict_hash()

    print("\n" + "=" * 72)
    if _failures:
        print(f"\033[31m{len(_failures)} FAILURE(S)\033[0m")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("\033[32mall checks passed\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
