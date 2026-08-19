"""
al_toolkit -- everything you need for the active learning tutorial.

You are not expected to read all of this. The pieces you will actually touch:

    Oracle              buys labels, enforces the 600-label budget, writes the log
    seed_selectors      the four initialisation methods for section (c)
    ACQUISITION         the acquisition function zoo for section (d)
    ModelSpec           your GNN choice for section (b)
    run_al_loop         the driver that ties them together
    scaled_mae, ence    the two leaderboard metrics

Written against chemprop 2.3.1. If you get an ImportError on `chemprop`, run
the install cell at the top of the notebook again and restart the runtime.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# 0. bundle loading
# --------------------------------------------------------------------------
DEFAULT_BUNDLE = Path("data/student")
BUDGET_TOTAL = 600
SEED_SIZE = 100
N_ROUNDS = 10
BATCH_SIZE_AL = 50

# Not a secret. See the note in the instructor's obfuscate.py: the budget is a
# rule, not a lock, and submissions are audited.
_KEY = b"ai4chem-bootcamp-2026-carboxylic-acid-active-learning"
_MAGIC = b"AL4CHEM1"


def _keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:n])


def _unseal(blob: bytes, key: bytes = _KEY) -> bytes:
    if blob[: len(_MAGIC)] != _MAGIC:
        raise ValueError("not a sealed label file")
    digest = blob[len(_MAGIC) : len(_MAGIC) + 8]
    body = blob[len(_MAGIC) + 8 :]
    payload = bytes(a ^ b for a, b in zip(body, _keystream(key, len(body))))
    if hashlib.sha256(payload).digest()[:8] != digest:
        raise ValueError("sealed label file is corrupt or the key is wrong")
    return payload


@dataclass
class Bundle:
    """The data the instructor handed out."""
    root: Path
    pool_meta: "object"          # pandas DataFrame
    dev: "object"                # pandas DataFrame
    targets: list[str]           # the scored targets, in the required order
    spec: dict
    selftest_smiles: list[str]
    extras: list[str] = field(default_factory=list)
    published_benchmark: "object" = None   # DataFrame or None

    @property
    def n_targets(self) -> int:
        return len(self.targets)

    @property
    def provenance(self) -> dict:
        return self.spec.get("provenance", {})

    def family_of(self, target: str) -> str:
        return self.spec["family_of_target"][target]

    def targets_in_family(self, family: str) -> list[str]:
        return [t for t in self.targets if self.family_of(t) == family]

    def base_of(self, target: str) -> str:
        """Strip the aggregation suffix. Longest-first, because the buried
        volume names contain `min` and `max` themselves."""
        for suffix in sorted(self.spec["aggregations"]
                             + self.spec.get("extra_aggregations", []),
                             key=len, reverse=True):
            if target.endswith("_" + suffix):
                return target[: -len(suffix) - 1]
        return target

    def ascii(self, target: str) -> str:
        """ASCII-safe alias, for filenames and awkward font stacks."""
        return self.spec.get("ascii_of_target", {}).get(target, target)

    def cpu_hours(self, n_labels: int) -> float:
        """What `n_labels` of this oracle would have cost in DFT time."""
        return n_labels * float(self.provenance.get("cpu_hours_per_label", 0.0))

    def describe_oracle(self) -> str:
        p = self.provenance
        total = self.spec.get("budget", {}).get("total", BUDGET_TOTAL)
        return (
            f"labels: published DFT descriptors\n"
            f"  level of theory : {p.get('level_of_theory', '?')}\n"
            f"  conformers      : {p.get('conformer_method', '?')}\n"
            f"  Boltzmann       : {p.get('boltzmann_temperature_K', '?')} K, "
            f"{p.get('energy_window_kcal', '?')} kcal/mol window\n"
            f"  source          : {p.get('paper', '?')}\n"
            f"                    DOI {p.get('doi', '?')} ({p.get('license', '?')})\n"
            f"  cost            : {p.get('published_cpu_hours', 0):,} CPU-hours "
            f"for {p.get('published_acids', 0):,} acids "
            f"(~{p.get('cpu_hours_per_label', 0):.0f} CPU-hours each)\n"
            f"  your budget     : {total} labels "
            f"~ {self.cpu_hours(total):,.0f} CPU-hours of quantum chemistry"
        )


def load_bundle(root: str | Path = DEFAULT_BUNDLE) -> Bundle:
    import pandas as pd

    root = Path(root)
    if not (root / "targets.json").exists():
        raise FileNotFoundError(
            f"{root} does not look like the student bundle "
            "(no targets.json). Check the path in the setup cell."
        )
    spec = json.loads((root / "targets.json").read_text(encoding="utf-8"))
    bench_path = root / "published_benchmark.csv"
    return Bundle(
        root=root,
        pool_meta=pd.read_csv(root / "pool_meta.csv", encoding="utf-8"),
        dev=pd.read_csv(root / "dev.csv", encoding="utf-8"),
        targets=spec["targets"],
        spec=spec,
        selftest_smiles=pd.read_csv(root / "selftest_smiles.csv",
                                    encoding="utf-8")["smiles"].tolist(),
        extras=spec.get("extras_unscored", []),
        published_benchmark=(pd.read_csv(bench_path, encoding="utf-8")
                             if bench_path.exists() else None),
    )


# --------------------------------------------------------------------------
# 1. the oracle
# --------------------------------------------------------------------------
class BudgetExceeded(RuntimeError):
    pass


class Oracle:
    """Buys descriptor labels. Enforces the budget. Logs everything.

    >>> oracle = Oracle(bundle)
    >>> y = oracle.query(["Ac42", "Ac1337"])      # -> DataFrame, 2 rows x 156
    >>> oracle.spent, oracle.remaining
    (2, 598)
    """

    def __init__(self, bundle: Bundle, budget: int = BUDGET_TOTAL,
                 log_path: str | Path = "al_log.jsonl", reset: bool = True):
        import pandas as pd

        ids, cols, values = self._load(bundle.root / "pool_labels.enc")
        self._index = {a: i for i, a in enumerate(ids)}
        self._ids = ids
        self._cols = cols
        self._values = values
        self.bundle = bundle
        self.budget = int(budget)
        self.log_path = Path(log_path)
        self._bought: dict[str, int] = {}   # acid_id -> round first bought
        self.round = 0
        self._pd = pd

        if reset and self.log_path.exists():
            self.log_path.unlink()
        self._append({"event": "init", "budget": self.budget,
                      "pool_size": len(ids), "n_targets": len(cols),
                      "time": time.time()})

    @staticmethod
    def _load(path: Path):
        blob = Path(path).read_bytes()
        with io.BytesIO(_unseal(blob)) as buf:
            z = np.load(buf, allow_pickle=True)
            return ([str(v) for v in z["acid_ids"]],
                    [str(v) for v in z["target_columns"]],
                    z["values"])

    # -- bookkeeping -------------------------------------------------------
    @property
    def spent(self) -> int:
        return len(self._bought)

    @property
    def remaining(self) -> int:
        return self.budget - self.spent

    @property
    def labeled_ids(self) -> list[str]:
        return list(self._bought)

    def _append(self, record: dict) -> None:
        with self.log_path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

    # -- the only method that returns labels -------------------------------
    def query(self, acid_ids, round_label: int | None = None):
        """Buy labels for `acid_ids`. Repeats are free (already paid for)."""
        acid_ids = [str(a) for a in acid_ids]
        unknown = [a for a in acid_ids if a not in self._index]
        if unknown:
            raise KeyError(f"{len(unknown)} id(s) are not in the pool, "
                           f"e.g. {unknown[:3]}")
        new = [a for a in dict.fromkeys(acid_ids) if a not in self._bought]
        if len(new) > self.remaining:
            raise BudgetExceeded(
                f"asked for {len(new)} new labels but only {self.remaining} of "
                f"{self.budget} remain. Nothing was charged."
            )
        r = self.round if round_label is None else int(round_label)
        for a in new:
            self._bought[a] = r
        self._append({"event": "query", "round": r, "n_requested": len(acid_ids),
                      "n_new": len(new), "acid_ids": new, "spent": self.spent,
                      "time": time.time()})

        rows = [self._index[a] for a in acid_ids]
        df = self._pd.DataFrame(self._values[rows], columns=self._cols)
        df.insert(0, "acid_id", acid_ids)
        return df

    def labels_for(self, acid_ids):
        """Labels for molecules already bought. Raises if any are unpaid."""
        unpaid = [a for a in acid_ids if a not in self._bought]
        if unpaid:
            raise BudgetExceeded(
                f"{len(unpaid)} of these have not been bought, e.g. {unpaid[:3]}. "
                "Call query() instead."
            )
        return self.query(acid_ids)

    def next_round(self) -> int:
        self.round += 1
        self._append({"event": "round", "round": self.round,
                      "spent": self.spent, "time": time.time()})
        return self.round

    def finalize(self, note: str = "") -> None:
        self._append({"event": "final", "spent": self.spent, "note": note,
                      "labeled_ids": self.labeled_ids, "time": time.time()})


# --------------------------------------------------------------------------
# 2. featurisation helpers (Morgan fingerprints, scaffolds)
# --------------------------------------------------------------------------
def morgan_matrix(smiles, radius: int = 2, n_bits: int = 2048):
    """Binary Morgan fingerprints as a (n, n_bits) uint8 array."""
    from rdkit import Chem
    from rdkit.Chem import rdFingerprintGenerator

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    out = np.zeros((len(smiles), n_bits), dtype=np.uint8)
    for i, smi in enumerate(smiles):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        out[i] = gen.GetFingerprintAsNumPy(mol).astype(np.uint8)
    return out


def rdkit_fps(smiles, radius: int = 2, n_bits: int = 2048):
    """RDKit ExplicitBitVect list -- needed by MaxMinPicker and BulkTanimoto."""
    from rdkit import Chem
    from rdkit.Chem import rdFingerprintGenerator

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    fps = []
    for smi in smiles:
        mol = Chem.MolFromSmiles(smi)
        fps.append(gen.GetFingerprint(mol) if mol is not None else None)
    return fps


def mean_pairwise_tanimoto(smiles) -> float:
    """Mean pairwise Tanimoto within a set -- the batch-redundancy diagnostic."""
    from rdkit import DataStructs

    fps = [f for f in rdkit_fps(smiles) if f is not None]
    if len(fps) < 2:
        return float("nan")
    sims = []
    for i in range(1, len(fps)):
        sims += list(DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i]))
    return float(np.mean(sims))


# --------------------------------------------------------------------------
# 3. the model -- task (b)
# --------------------------------------------------------------------------
@dataclass
class ModelSpec:
    """Your GNN choice. Defaults are a deliberately mediocre starting point."""

    head: str = "regression"        # regression | mve | evidential
    depth: int = 3                  # message passing steps
    d_h: int = 300                  # hidden width
    ffn_hidden: int = 300
    ffn_layers: int = 1
    dropout: float = 0.0
    aggregation: str = "mean"       # mean | sum | norm
    batch_norm: bool = False
    max_epochs: int = 40
    batch_size: int = 32
    init_lr: float = 1e-4
    max_lr: float = 1e-3
    final_lr: float = 1e-4
    warmup_epochs: int = 2
    ensemble_size: int = 1          # >1 gives you epistemic uncertainty
    mc_dropout_samples: int = 0     # >0 uses MC dropout at predict time
    accelerator: str = "auto"
    seed: int = 0

    def describe(self) -> str:
        unc = {
            ("regression", 1): "NONE -- you cannot run an uncertainty-based AF",
            ("mve", 1): "aleatoric only -- careful, that is the wrong quantity",
            ("evidential", 1): "epistemic + aleatoric, single model",
        }.get((self.head, self.ensemble_size))
        if unc is None:
            unc = f"epistemic from a {self.ensemble_size}-model ensemble"
            if self.head == "mve":
                unc += " + aleatoric from MVE (this is the good combination)"
        if self.mc_dropout_samples:
            unc += f" + MC dropout x{self.mc_dropout_samples}"
        return (f"{self.head} head, depth={self.depth}, d_h={self.d_h}, "
                f"dropout={self.dropout}, agg={self.aggregation}, "
                f"ensemble={self.ensemble_size}\n  uncertainty: {unc}")


def _make_mpnn(spec: ModelSpec, n_tasks: int, output_scaler):
    from chemprop import models, nn

    output_transform = nn.UnscaleTransform.from_standard_scaler(output_scaler)

    agg_cls = {"mean": "MeanAggregation", "sum": "SumAggregation",
               "norm": "NormAggregation"}[spec.aggregation]
    agg = getattr(nn, agg_cls)()

    # The message-passing block must exist first: the FFN's input width is
    # mp.output_dim, and it is NOT inferred. Forgetting this is the classic
    # chemprop v2 shape error when you change d_h away from 300.
    mp = nn.BondMessagePassing(d_h=spec.d_h, depth=spec.depth, dropout=spec.dropout)

    head_cls = {"regression": nn.RegressionFFN, "mve": nn.MveFFN,
                "evidential": nn.EvidentialFFN}[spec.head]
    ffn = head_cls(
        n_tasks=n_tasks,
        input_dim=mp.output_dim,
        hidden_dim=spec.ffn_hidden,
        n_layers=spec.ffn_layers,
        dropout=spec.dropout,
        output_transform=output_transform,
    )
    return models.MPNN(
        mp, agg, ffn,
        batch_norm=spec.batch_norm,
        warmup_epochs=spec.warmup_epochs,
        init_lr=spec.init_lr,
        max_lr=spec.max_lr,
        final_lr=spec.final_lr,
    )


class TrainedEnsemble:
    """One or more Chemprop MPNNs plus the target scaler they were trained with."""

    def __init__(self, models_list, scaler, targets, spec: ModelSpec):
        self.models = models_list
        self.scaler = scaler
        self.targets = list(targets)
        self.spec = spec

    # -- prediction --------------------------------------------------------
    def _dataloader(self, smiles, batch_size=256):
        from chemprop import data, featurizers

        dps = [data.MoleculeDatapoint.from_smi(s) for s in smiles]
        dset = data.MoleculeDataset(
            dps, featurizers.SimpleMoleculeMolGraphFeaturizer())
        return data.build_dataloader(dset, batch_size=batch_size, shuffle=False)

    def predict_raw(self, smiles, batch_size=256):
        """Return (means, aleatoric_vars) each (n_models, n, n_targets).

        `aleatoric_vars` is None for a plain regression head.
        """
        import torch
        from lightning import pytorch as pl

        loader = self._dataloader(smiles, batch_size)
        trainer = pl.Trainer(logger=False, enable_progress_bar=False,
                             enable_checkpointing=False,
                             accelerator=self.spec.accelerator, devices=1)
        means, avars = [], []
        for m in self.models:
            m.eval()
            if self.spec.mc_dropout_samples:
                _enable_dropout(m)
                reps = self.spec.mc_dropout_samples
            else:
                reps = 1
            for _ in range(reps):
                with torch.inference_mode():
                    out = torch.concat(trainer.predict(m, loader), 0)
                out = out.float().cpu().numpy()
                if out.ndim == 3 and self.spec.head == "mve":
                    means.append(out[..., 0])
                    avars.append(out[..., 1])
                elif out.ndim == 3 and self.spec.head == "evidential":
                    mu, v, alpha, beta = (out[..., 0], out[..., 1],
                                          out[..., 2], out[..., 3])
                    means.append(mu)
                    avars.append(beta / np.maximum(alpha - 1.0, 1e-6))
                    # epistemic part is beta / (v (alpha-1)); handled below
                    self._last_evidential = (v, alpha, beta)
                else:
                    means.append(out.reshape(out.shape[0], -1))
        M = np.stack(means)
        A = np.stack(avars) if avars else None
        return M, A

    def predict(self, smiles, batch_size=256):
        """Return (mean (n, T), sigma (n, T)) combining epistemic + aleatoric."""
        M, A = self.predict_raw(smiles, batch_size)
        mean = M.mean(axis=0)
        epistemic = M.var(axis=0, ddof=0) if M.shape[0] > 1 else np.zeros_like(mean)
        aleatoric = A.mean(axis=0) if A is not None else np.zeros_like(mean)
        if self.spec.head == "evidential" and M.shape[0] == 1:
            v, alpha, beta = self._last_evidential
            epistemic = beta / np.maximum(v * (alpha - 1.0), 1e-6)
        total = epistemic + aleatoric
        if not np.any(total > 0):
            # a plain single regression model has no uncertainty at all.
            total = np.full_like(mean, np.nan)
        return mean, np.sqrt(np.maximum(total, 0.0))

    def predict_components(self, smiles, batch_size=256):
        """(mean, sigma_epistemic, sigma_aleatoric) -- for BALD and for teaching."""
        M, A = self.predict_raw(smiles, batch_size)
        mean = M.mean(axis=0)
        epi = M.var(axis=0, ddof=0) if M.shape[0] > 1 else np.zeros_like(mean)
        ale = A.mean(axis=0) if A is not None else np.zeros_like(mean)
        if self.spec.head == "evidential" and M.shape[0] == 1:
            v, alpha, beta = self._last_evidential
            epi = beta / np.maximum(v * (alpha - 1.0), 1e-6)
        return mean, np.sqrt(np.maximum(epi, 0.0)), np.sqrt(np.maximum(ale, 0.0))

    # -- learned embeddings ------------------------------------------------
    def embeddings(self, smiles, batch_size=256):
        """The 300-d post-aggregation Chemprop fingerprint, from model 0."""
        import torch

        loader = self._dataloader(smiles, batch_size)
        m = self.models[0]
        m.eval()
        chunks = []
        with torch.no_grad():
            for batch in loader:
                chunks.append(m.encoding(batch.bmg, batch.V_d, batch.X_d, i=0))
        return torch.cat(chunks, 0).float().cpu().numpy()

    # -- persistence -------------------------------------------------------
    def save(self, directory: str | Path):
        from chemprop.models import save_model

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, m in enumerate(self.models):
            p = directory / f"model_{i}.pt"
            save_model(p, m, output_columns=self.targets)
            paths.append(p.name)
        return paths


def _enable_dropout(model) -> None:
    """Put dropout layers (and only those) back into training mode."""
    import torch.nn as tnn

    for mod in model.modules():
        if isinstance(mod, tnn.Dropout):
            mod.train()


def train_model(smiles, y, spec: ModelSpec, val_frac: float = 0.15,
                targets: list[str] | None = None, verbose: bool = False):
    """Fit `spec.ensemble_size` Chemprop models on (smiles, y).

    y may contain NaN -- Chemprop masks missing targets automatically.
    """
    import torch
    from lightning import pytorch as pl

    from chemprop import data, featurizers

    y = np.asarray(y, dtype=float)
    n_tasks = y.shape[1]
    targets = targets or [f"t{i}" for i in range(n_tasks)]

    rng = np.random.default_rng(spec.seed)
    idx = rng.permutation(len(smiles))
    n_val = max(2, int(round(val_frac * len(smiles))))
    val_idx, train_idx = idx[:n_val], idx[n_val:]

    featurizer = featurizers.SimpleMoleculeMolGraphFeaturizer()

    def mk(ix):
        dps = [data.MoleculeDatapoint.from_smi(smiles[i], y[i]) for i in ix]
        return data.MoleculeDataset(dps, featurizer)

    train_dset, val_dset = mk(train_idx), mk(val_idx)
    scaler = train_dset.normalize_targets()
    val_dset.normalize_targets(scaler)
    train_dset.cache = True
    val_dset.cache = True

    models_list = []
    for k in range(spec.ensemble_size):
        torch.manual_seed(spec.seed + 1000 * k)
        train_loader = data.build_dataloader(
            train_dset, batch_size=spec.batch_size, shuffle=True,
            drop_last=False, seed=spec.seed + k)
        val_loader = data.build_dataloader(
            val_dset, batch_size=spec.batch_size, shuffle=False)
        model = _make_mpnn(spec, n_tasks, scaler)
        trainer = pl.Trainer(
            max_epochs=spec.max_epochs, logger=False,
            enable_checkpointing=False, enable_progress_bar=verbose,
            enable_model_summary=False, accelerator=spec.accelerator, devices=1,
        )
        trainer.fit(model, train_loader, val_loader)
        models_list.append(model)

    return TrainedEnsemble(models_list, scaler, targets, spec)


# --------------------------------------------------------------------------
# 4. metrics
# --------------------------------------------------------------------------
def target_scales(y) -> np.ndarray:
    """Per-task standard deviation, used to make MAEs comparable."""
    s = np.nanstd(np.asarray(y, dtype=float), axis=0, ddof=1)
    return np.where((s > 0) & np.isfinite(s), s, np.nan)


def scaled_mae(y_true, y_pred, scales=None) -> float:
    """Mean over tasks of MAE_t / std_t. 1.0 = no better than the mean."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if scales is None:
        scales = target_scales(y_true)
    mae = np.nanmean(np.abs(y_true - y_pred), axis=0)
    per_task = mae / scales
    return float(np.nanmean(per_task))


def scaled_mae_per_task(y_true, y_pred, scales=None) -> np.ndarray:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if scales is None:
        scales = target_scales(y_true)
    return np.nanmean(np.abs(y_true - y_pred), axis=0) / scales


def ence_per_task(y_true, y_pred, sigma, n_bins: int = 10) -> np.ndarray:
    """Expected Normalised Calibration Error, per task.

    Levi et al., Sensors 2022, 22, 5540. For each task, sort molecules by
    predicted sigma, split into `n_bins` equal-count bins, and compare the
    empirical RMSE in the bin with the root-mean predicted variance:

        ENCE = (1/B) sum_b |RMSE_b - RMV_b| / RMV_b

    0 is perfect. A model that reports a constant sigma scores badly, which is
    the point -- you cannot fake this with a global error bar.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    n, T = y_true.shape
    out = np.full(T, np.nan)
    for t in range(T):
        s = sigma[:, t]
        e = np.abs(y_true[:, t] - y_pred[:, t])
        ok = np.isfinite(s) & np.isfinite(e) & (s > 0)
        if ok.sum() < n_bins * 2:
            continue
        s, e = s[ok], e[ok]
        order = np.argsort(s)
        bins = np.array_split(order, n_bins)
        vals = []
        for b in bins:
            if len(b) == 0:
                continue
            rmse = float(np.sqrt(np.mean(e[b] ** 2)))
            rmv = float(np.sqrt(np.mean(s[b] ** 2)))
            if rmv > 0:
                vals.append(abs(rmse - rmv) / rmv)
        if vals:
            out[t] = float(np.mean(vals))
    return out


def ence(y_true, y_pred, sigma, n_bins: int = 10) -> float:
    return float(np.nanmean(ence_per_task(y_true, y_pred, sigma, n_bins)))


def _spearman(a, b) -> float:
    """Spearman rho without scipy (average ranks, then Pearson)."""
    def rank(x):
        order = np.argsort(x, kind="mergesort")
        r = np.empty(len(x), dtype=float)
        r[order] = np.arange(len(x), dtype=float)
        # average ties
        xs = x[order]
        i = 0
        while i < len(xs):
            j = i
            while j + 1 < len(xs) and xs[j + 1] == xs[i]:
                j += 1
            if j > i:
                r[order[i : j + 1]] = np.mean(r[order[i : j + 1]])
            i = j + 1
        return r

    ra, rb = rank(np.asarray(a, float)), rank(np.asarray(b, float))
    ra -= ra.mean()
    rb -= rb.mean()
    denom = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / denom) if denom > 0 else float("nan")


def sigma_error_spearman(y_true, y_pred, sigma) -> float:
    """Mean over tasks of Spearman(sigma, |error|). Higher is better, max 1."""
    try:
        from scipy.stats import spearmanr

        def rho(a, b):
            return float(spearmanr(a, b).statistic)
    except ImportError:
        rho = _spearman

    y_true = np.asarray(y_true, float)
    y_pred = np.asarray(y_pred, float)
    sigma = np.asarray(sigma, float)
    vals = []
    for t in range(y_true.shape[1]):
        e = np.abs(y_true[:, t] - y_pred[:, t])
        s = sigma[:, t]
        ok = np.isfinite(e) & np.isfinite(s)
        if ok.sum() > 10 and np.nanstd(s[ok]) > 0:
            vals.append(rho(s[ok], e[ok]))
    return float(np.nanmean(vals)) if vals else float("nan")


# --------------------------------------------------------------------------
# 5. seed selection -- task (c)
# --------------------------------------------------------------------------
def seed_random(pool_meta, n: int, seed: int = 0, **_):
    rng = np.random.default_rng(seed)
    return list(pool_meta["acid_id"].iloc[
        rng.choice(len(pool_meta), size=n, replace=False)])


def seed_maxmin(pool_meta, n: int, seed: int = 0, **_):
    """MaxMin diversity picker on Morgan fingerprints (RDKit SimDivFilters)."""
    from rdkit import DataStructs
    from rdkit.SimDivFilters.rdSimDivPickers import MaxMinPicker

    fps = rdkit_fps(pool_meta["smiles"].tolist())
    keep = [i for i, f in enumerate(fps) if f is not None]
    fps = [fps[i] for i in keep]

    def dist(i, j):
        return 1.0 - DataStructs.TanimotoSimilarity(fps[i], fps[j])

    picker = MaxMinPicker()
    picked = picker.LazyPick(dist, len(fps), n, seed=seed)
    return list(pool_meta["acid_id"].iloc[[keep[i] for i in picked]])


def seed_kmeans(pool_meta, n: int, seed: int = 0, **_):
    """k-means on Morgan space; take the molecule nearest each centroid."""
    from sklearn.cluster import MiniBatchKMeans

    X = morgan_matrix(pool_meta["smiles"].tolist()).astype(np.float32)
    km = MiniBatchKMeans(n_clusters=n, random_state=seed, n_init=3,
                         batch_size=1024).fit(X)
    chosen = []
    for c in range(n):
        members = np.where(km.labels_ == c)[0]
        if len(members) == 0:
            continue
        d = np.linalg.norm(X[members] - km.cluster_centers_[c], axis=1)
        chosen.append(int(members[int(np.argmin(d))]))
    # top up if some clusters were empty
    rng = np.random.default_rng(seed)
    while len(chosen) < n:
        cand = int(rng.integers(len(X)))
        if cand not in chosen:
            chosen.append(cand)
    return list(pool_meta["acid_id"].iloc[chosen])


def seed_scaffold_balanced(pool_meta, n: int, seed: int = 0, **_):
    """Round-robin over Murcko scaffolds, so no skeleton dominates the seed."""
    rng = np.random.default_rng(seed)
    by_scaffold: dict[str, list[str]] = {}
    for row in pool_meta.itertuples(index=False):
        by_scaffold.setdefault(row.murcko_scaffold, []).append(row.acid_id)
    keys = list(by_scaffold)
    rng.shuffle(keys)
    for k in keys:
        rng.shuffle(by_scaffold[k])
    chosen: list[str] = []
    depth = 0
    while len(chosen) < n:
        added = False
        for k in keys:
            if depth < len(by_scaffold[k]):
                chosen.append(by_scaffold[k][depth])
                added = True
                if len(chosen) >= n:
                    break
        if not added:
            break
        depth += 1
    return chosen[:n]


SEED_SELECTORS = {
    "random": seed_random,
    "maxmin": seed_maxmin,
    "kmeans": seed_kmeans,
    "scaffold_balanced": seed_scaffold_balanced,
}


# --------------------------------------------------------------------------
# 6. acquisition functions -- task (d)
# --------------------------------------------------------------------------
@dataclass
class Candidates:
    """Everything an acquisition function is allowed to look at.

    Note what is NOT here: the true labels. An acquisition function that peeks
    at `oracle._values` is cheating, and the audit will notice.
    """
    acid_ids: list[str]
    smiles: list[str]
    mean: np.ndarray            # (n_cand, T) predicted values
    sigma: np.ndarray           # (n_cand, T) total predictive sd
    sigma_epistemic: np.ndarray  # (n_cand, T)
    sigma_aleatoric: np.ndarray  # (n_cand, T)
    emb: np.ndarray             # (n_cand, D) learned Chemprop embedding
    labeled_emb: np.ndarray     # (n_labeled, D)
    scales: np.ndarray          # (T,) per-task std from the labels bought so far
    rng: np.random.Generator
    extras: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.acid_ids)

    def scaled(self, arr) -> np.ndarray:
        """Divide a (n, T) array by the per-task scale. Use this."""
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.asarray(arr, float) / self.scales


# Each acquisition function takes (k, cand) and returns k POSITIONS into
# cand.acid_ids. Deterministic given cand.rng.

def random_af(k: int, cand: Candidates) -> np.ndarray:
    return cand.rng.choice(cand.n, size=k, replace=False)


def max_variance(k: int, cand: Candidates) -> np.ndarray:
    """Top-k by RAW summed predictive sd.

    With 156 targets in mixed units this is a trap. Look at the magnitudes:
    volume(Bohr_radius^3/mol) runs to ~2000, IR_freq_C1_O2 is ~1800 cm^-1,
    NMR_shift_C1 is ~170 ppm, %Vbur is ~60, and NBO_charge_H5 is ~0.5 e. A raw
    sum of standard deviations over those is, to three significant figures, a
    sum over `volume` and `IR_freq` -- so the whole budget goes on two
    descriptors out of thirty-nine, and the score never tells you, because the
    leaderboard metric scales each task.

    Run it anyway. Then run max_variance_scaled and compare.
    """
    score = np.nansum(cand.sigma, axis=1)
    return np.argsort(-score)[:k]


def max_variance_scaled(k: int, cand: Candidates) -> np.ndarray:
    """Top-k by summed sd AFTER dividing each task by its own spread."""
    score = np.nansum(cand.scaled(cand.sigma), axis=1)
    return np.argsort(-score)[:k]


def max_epistemic(k: int, cand: Candidates) -> np.ndarray:
    """Top-k by scaled EPISTEMIC sd only -- ignores irreducible noise.

    This is the operational form of the lecture's epistemic/aleatoric point.
    Requires an ensemble or an evidential head; with a single MVE model the
    epistemic term is zero and this silently degenerates to random.
    """
    if not np.any(cand.sigma_epistemic > 0):
        return random_af(k, cand)
    score = np.nansum(cand.scaled(cand.sigma_epistemic), axis=1)
    return np.argsort(-score)[:k]


def bald_ensemble(k: int, cand: Candidates) -> np.ndarray:
    """Gaussian BALD: mutual information between the label and the parameters.

    For Gaussian predictives,
        I = 0.5 * log(total_var) - 0.5 * log(aleatoric_var)
    summed over tasks. Reduces to "epistemic relative to noise", so a molecule
    sitting in a noisy corner of descriptor space is NOT bought. Needs an
    ensemble (for total) with a per-model variance (for aleatoric), i.e.
    head="mve" with ensemble_size > 1.
    """
    ale = cand.sigma_aleatoric ** 2
    tot = cand.sigma ** 2
    if not np.any(ale > 0):
        return max_epistemic(k, cand)
    with np.errstate(divide="ignore", invalid="ignore"):
        info = 0.5 * np.log(np.maximum(tot, 1e-12) / np.maximum(ale, 1e-12))
    score = np.nansum(np.where(np.isfinite(info), info, 0.0), axis=1)
    return np.argsort(-score)[:k]


def coreset_greedy(k: int, cand: Candidates) -> np.ndarray:
    """k-centre greedy on the learned embedding (Sener & Savarese, ICLR 2018).

    Pure representativeness: repeatedly take the candidate furthest from
    everything already labelled. Ignores uncertainty entirely, so it is the
    honest counterpart to max_variance -- and the strategy a chemist's instinct
    ("pick a spread of model substrates") actually implements.
    """
    E = cand.emb
    if cand.labeled_emb is not None and len(cand.labeled_emb):
        d = _min_dist(E, cand.labeled_emb)
    else:
        d = np.full(len(E), np.inf)
        d[int(cand.rng.integers(len(E)))] = -1.0
    chosen: list[int] = []
    for _ in range(k):
        i = int(np.argmax(d))
        chosen.append(i)
        d = np.minimum(d, np.linalg.norm(E - E[i], axis=1))
        d[i] = -1.0
    return np.array(chosen)


def badge(k: int, cand: Candidates) -> np.ndarray:
    """Uncertainty-scaled embedding + k-means++ seeding.

    A regression adaptation of BADGE (Ash et al., ICLR 2020). BADGE clusters
    loss-gradient embeddings, whose magnitude grows with predictive error; for
    multi-task regression without labels we use the embedding scaled by the
    molecule's total scaled uncertainty, which has the same magnitude
    behaviour. k-means++ seeding then picks points that are both uncertain
    (large norm) and mutually distant (diverse) -- so the batch is not 50 copies
    of the same scaffold.
    """
    from sklearn.cluster import kmeans_plusplus

    w = np.nansum(cand.scaled(cand.sigma), axis=1)
    w = np.nan_to_num(w, nan=0.0)
    if w.max() <= 0:
        w = np.ones_like(w)
    G = cand.emb * w[:, None]
    _, idx = kmeans_plusplus(G, n_clusters=k,
                             random_state=int(cand.rng.integers(1 << 31)))
    return np.asarray(idx)


def batch_diverse_topk(k: int, cand: Candidates, overshoot: int = 4) -> np.ndarray:
    """Top-(overshoot*k) by scaled sd, then MaxMin down to k on Morgan space.

    The cheap surrogate for BatchBALD (Kirsch et al., NeurIPS 2019): uncertainty
    picks the shortlist, diversity picks the plate.
    """
    from rdkit import DataStructs
    from rdkit.SimDivFilters.rdSimDivPickers import MaxMinPicker

    score = np.nansum(cand.scaled(cand.sigma), axis=1)
    short = np.argsort(-score)[: min(cand.n, overshoot * k)]
    fps = rdkit_fps([cand.smiles[i] for i in short])
    ok = [i for i, f in enumerate(fps) if f is not None]
    fps = [fps[i] for i in ok]
    if len(fps) <= k:
        return short[:k]

    def dist(i, j):
        return 1.0 - DataStructs.TanimotoSimilarity(fps[i], fps[j])

    picker = MaxMinPicker()
    picked = picker.LazyPick(dist, len(fps), k,
                            seed=int(cand.rng.integers(1 << 31)))
    return short[[ok[i] for i in picked]]


def qbc_disagreement(k: int, cand: Candidates) -> np.ndarray:
    """Query by committee: pure ensemble disagreement, scaled. Same as
    max_epistemic, kept under its classical name because the room will
    recognise it."""
    return max_epistemic(k, cand)


def uncertainty_times_novelty(k: int, cand: Candidates) -> np.ndarray:
    """Scaled uncertainty x distance to the labelled set.

    The closest thing in this zoo to the acquisition function in
    Schleinitz et al., JACS 2025, 147, 7476: score the candidate by what you
    do not know about it AND by how far it is from what you already have.
    """
    u = np.nansum(cand.scaled(cand.sigma), axis=1)
    u = np.nan_to_num(u, nan=0.0)
    if cand.labeled_emb is not None and len(cand.labeled_emb):
        nov = _min_dist(cand.emb, cand.labeled_emb)
    else:
        nov = np.ones(cand.n)
    u = (u - u.min()) / (np.ptp(u) + 1e-12)
    nov = (nov - nov.min()) / (np.ptp(nov) + 1e-12)
    return np.argsort(-(u * nov))[:k]


def your_own(k: int, cand: Candidates) -> np.ndarray:
    """YOUR TURN.

    Return `k` integer positions into cand.acid_ids. You may use:
        cand.mean, cand.sigma, cand.sigma_epistemic, cand.sigma_aleatoric  (n, T)
        cand.emb (n, D), cand.labeled_emb (n_lab, D), cand.smiles, cand.scales
        cand.scaled(x)  -- divide a (n, T) array by the per-task spread
        cand.rng        -- use this, not np.random, so your run is reproducible

    Ideas the lecture pointed at:
      * weight the uncertainty by predicted *reactivity* -- here, by how extreme
        the predicted descriptor is (buy the molecules whose predictions are both
        uncertain AND unusual)
      * only count the uncertainty of the descriptor family you care about --
        you named a family to sacrifice in section (a)
      * target the CONFORMATIONAL descriptors. The dihedrals and buried volumes
        moved most between conformers in section (a), so a molecule whose
        predicted `_max - _min` gap is large is one where the ensemble is doing
        real work and one label buys more information
      * penalise candidates similar to something already in this batch
      * anything that beats max_variance_scaled at round 4 rather than round 10
    """
    raise NotImplementedError("write your acquisition function here")


def _min_dist(A, B, block: int = 2048) -> np.ndarray:
    """Distance from each row of A to its nearest row of B."""
    out = np.empty(len(A))
    for s in range(0, len(A), block):
        chunk = A[s : s + block]
        d = np.linalg.norm(chunk[:, None, :] - B[None, :, :], axis=2)
        out[s : s + block] = d.min(axis=1)
    return out


ACQUISITION = {
    "random": random_af,
    "max_variance": max_variance,
    "max_variance_scaled": max_variance_scaled,
    "max_epistemic": max_epistemic,
    "bald_ensemble": bald_ensemble,
    "coreset_greedy": coreset_greedy,
    "badge": badge,
    "batch_diverse_topk": batch_diverse_topk,
    "qbc_disagreement": qbc_disagreement,
    "uncertainty_times_novelty": uncertainty_times_novelty,
    "your_own": your_own,
}


# --------------------------------------------------------------------------
# 7. the loop
# --------------------------------------------------------------------------
@dataclass
class LoopResult:
    history: list[dict]
    final_model: TrainedEnsemble
    oracle: Oracle
    seed_ids: list[str]
    config: dict

    def to_frame(self):
        import pandas as pd
        return pd.DataFrame(self.history)


def run_al_loop(bundle: Bundle, spec: ModelSpec, acquisition="max_variance_scaled",
                seed_method="maxmin", n_seed: int = SEED_SIZE,
                n_rounds: int = N_ROUNDS, batch_size: int = BATCH_SIZE_AL,
                candidate_subsample: int | None = 2000, seed: int = 0,
                oracle: Oracle | None = None, log_path="al_log.jsonl",
                verbose: bool = True) -> LoopResult:
    """The whole exercise in one function.

    candidate_subsample : score a random subset of the pool each round instead
        of all 6,528. Keeps a round under a minute. Set None to score everything
        (slower, and worth doing once so you can see whether it matters).
    """
    import pandas as pd

    rng = np.random.default_rng(seed)
    af = ACQUISITION[acquisition] if isinstance(acquisition, str) else acquisition
    af_name = acquisition if isinstance(acquisition, str) else af.__name__
    sel = (SEED_SELECTORS[seed_method] if isinstance(seed_method, str)
           else seed_method)

    pool = bundle.pool_meta
    smiles_of = dict(zip(pool["acid_id"], pool["smiles"]))
    targets = bundle.targets

    dev = bundle.dev
    dev_smiles = dev["smiles"].tolist()
    dev_y = dev[targets].to_numpy(dtype=float)
    dev_scales = target_scales(dev_y)

    if oracle is None:
        oracle = Oracle(bundle, log_path=log_path)

    seed_ids = list(sel(pool, n_seed, seed=seed))
    y_df = oracle.query(seed_ids, round_label=0)
    labeled = {a: y_df.set_index("acid_id").loc[a, targets].to_numpy(dtype=float)
               for a in seed_ids}

    history: list[dict] = []
    model = None
    t_start = time.time()

    for rnd in range(n_rounds + 1):
        ids = list(labeled)
        X = [smiles_of[a] for a in ids]
        Y = np.stack([labeled[a] for a in ids])

        t0 = time.time()
        model = train_model(X, Y, spec, targets=targets)
        dev_mean, dev_sigma = model.predict(dev_smiles)

        row = {
            "round": rnd,
            "n_labels": len(ids),
            "dev_scaled_mae": scaled_mae(dev_y, dev_mean, dev_scales),
            "dev_ence": ence(dev_y, dev_mean, dev_sigma),
            "dev_spearman": sigma_error_spearman(dev_y, dev_mean, dev_sigma),
            "train_seconds": time.time() - t0,
            "acquisition": af_name,
            "seed_method": seed_method if isinstance(seed_method, str) else "custom",
        }
        for fam in bundle.spec["families"]:
            cols = [targets.index(t) for t in bundle.targets_in_family(fam)]
            if cols:
                row[f"smae_{fam}"] = scaled_mae(
                    dev_y[:, cols], dev_mean[:, cols], dev_scales[cols])
        history.append(row)
        if verbose:
            print(f"round {rnd:>2}  n={row['n_labels']:>4}  "
                  f"sMAE={row['dev_scaled_mae']:.4f}  "
                  f"ENCE={row['dev_ence']:.3f}  "
                  f"rho={row['dev_spearman']:.3f}  "
                  f"({row['train_seconds']:.0f}s)", flush=True)

        if rnd == n_rounds or oracle.remaining <= 0:
            break

        # ---- choose the next batch --------------------------------------
        unlabeled = [a for a in pool["acid_id"] if a not in labeled]
        if candidate_subsample and len(unlabeled) > candidate_subsample:
            pick = rng.choice(len(unlabeled), size=candidate_subsample, replace=False)
            cand_ids = [unlabeled[i] for i in pick]
        else:
            cand_ids = unlabeled
        cand_smiles = [smiles_of[a] for a in cand_ids]

        mean, s_epi, s_ale = model.predict_components(cand_smiles)
        sigma = np.sqrt(s_epi ** 2 + s_ale ** 2)
        if not np.any(sigma > 0):
            sigma = np.full_like(mean, np.nan)

        cand = Candidates(
            acid_ids=cand_ids, smiles=cand_smiles, mean=mean, sigma=sigma,
            sigma_epistemic=s_epi, sigma_aleatoric=s_ale,
            emb=model.embeddings(cand_smiles),
            labeled_emb=model.embeddings(X),
            scales=target_scales(Y), rng=rng,
        )

        k = min(batch_size, oracle.remaining)
        positions = np.asarray(af(k, cand)).astype(int)
        if len(set(positions.tolist())) != len(positions):
            raise ValueError(f"{af_name} returned duplicate positions")
        chosen = [cand_ids[i] for i in positions]

        oracle.next_round()
        new_y = oracle.query(chosen).set_index("acid_id")
        for a in chosen:
            labeled[a] = new_y.loc[a, targets].to_numpy(dtype=float)

        history[-1]["batch_mean_tanimoto"] = mean_pairwise_tanimoto(
            [smiles_of[a] for a in chosen])

    oracle.finalize(note=f"acquisition={af_name} seed_method={seed_method}")
    config = {
        "acquisition": af_name,
        "seed_method": seed_method if isinstance(seed_method, str) else "custom",
        "n_seed": n_seed, "n_rounds": n_rounds, "batch_size": batch_size,
        "candidate_subsample": candidate_subsample, "seed": seed,
        "model_spec": spec.__dict__.copy(),
        "labels_used": oracle.spent,
        "total_seconds": time.time() - t_start,
    }
    if verbose:
        print(f"\ndone: {oracle.spent} labels, "
              f"{config['total_seconds'] / 60:.1f} min")
    return LoopResult(history, model, oracle, seed_ids, config)


# --------------------------------------------------------------------------
# 8. plots
# --------------------------------------------------------------------------
def plot_learning_curves(results: dict[str, LoopResult], metric="dev_scaled_mae",
                         ax=None):
    """results: {label: LoopResult}. Plots metric vs number of labels."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for label, res in results.items():
        df = res.to_frame()
        ax.plot(df["n_labels"], df[metric], marker="o", label=label)
    ax.set_xlabel("labels bought")
    ax.set_ylabel({"dev_scaled_mae": "dev scaled MAE",
                   "dev_ence": "dev ENCE",
                   "dev_spearman": r"Spearman($\sigma$, |error|)"}.get(metric, metric))
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    return ax


def package_submission(result: LoopResult, bundle: Bundle, team: str,
                       out_dir: str | Path | None = None,
                       predict_py: str | Path = "predict.py",
                       notes: str = "") -> Path:
    """Write a complete, validatable submission directory.

    Copies `predict.py` verbatim (do not edit it), saves the checkpoints, writes
    manifest.json, learning_curve.csv, and the oracle log.
    """
    import shutil

    import pandas as pd

    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in team).strip("_")
    out = Path(out_dir or f"submission_{slug}")
    if out.exists():
        shutil.rmtree(out)
    (out / "models").mkdir(parents=True)

    model_files = result.final_model.save(out / "models")

    src = Path(predict_py)
    if not src.exists():
        raise FileNotFoundError(
            f"{src} not found -- predict.py must be copied verbatim; do not "
            "rewrite it.")
    shutil.copyfile(src, out / "predict.py")

    log = Path(result.oracle.log_path)
    if not log.exists():
        raise FileNotFoundError(f"oracle log {log} is missing")
    shutil.copyfile(log, out / "al_log.jsonl")

    result.to_frame().to_csv(out / "learning_curve.csv", index=False)

    spec = result.final_model.spec
    manifest = {
        "team": team,
        "targets": bundle.targets,
        "head": spec.head,
        "ensemble_size": spec.ensemble_size,
        "mc_dropout_samples": spec.mc_dropout_samples,
        "accelerator": "auto",
        "model_files": model_files,
        "labels_used": result.oracle.spent,
        "acquisition": result.config["acquisition"],
        "seed_method": result.config["seed_method"],
        "config": result.config,
        "notes": notes,
        "toolkit_version": 1,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    n_lab = result.oracle.spent
    print(f"wrote {out}/")
    print(f"  {len(model_files)} checkpoint(s), {n_lab} labels used, "
          f"{len(result.history)} rounds")
    print(f"\nNow run:\n  python validate_submission.py --submission-dir {out} "
          f"--bundle {bundle.root}")
    return out


def aulc(res: LoopResult, metric="dev_scaled_mae") -> float:
    """Area under the learning curve, normalised by the label range.

    Lower is better for error metrics. Rewards being good EARLY, which is what
    active learning is actually for.
    """
    df = res.to_frame()
    x = df["n_labels"].to_numpy(dtype=float)
    y = df[metric].to_numpy(dtype=float)
    if len(x) < 2:
        return float("nan")
    trap = getattr(np, "trapezoid", None) or np.trapz  # numpy <2.0 compatibility
    return float(trap(y, x) / (x[-1] - x[0]))
