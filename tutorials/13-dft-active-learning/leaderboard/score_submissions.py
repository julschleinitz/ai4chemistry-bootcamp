#!/usr/bin/env python3
"""
Score every submission against the hidden test set and write the leaderboard.

    python score_submissions.py \
        --submissions ~/Drive/AI4Chem/lecture_13_tutorial/submissions \
        --audit

Accepts directories or .zip files. Each is unpacked to a temporary directory,
`predict.py` is run in a SUBPROCESS on the hidden SMILES (without labels), and
the predictions are scored.

Ranking
-------
    combined = mean_sMAE + mean_ENCE          (lower is better)

`mean_sMAE` is the mean over the 156 targets of MAE_t / std_t, so a partial
charge and a buried volume contribute equally. `mean_ENCE` is the mean expected
normalised calibration error, which is what forces a submission to know what it
does not know.

Buried volume is 12 of the 39 base properties (31% of the targets) even after
the radius scan was trimmed. `--family-balanced` averages the eight families
first, so no single family can decide the leaderboard. Both numbers are always
reported; the flag only changes which one `rank` sorts on.

Reference line
--------------
`published_benchmark.csv` carries the paper's own 3D-GNN test-set MAEs. Where a
submission covers one of those targets, the leaderboard reports the ratio
`MAE / published_MAE`. IMPORTANT CAVEAT, and say it out loud when you show the
table: the published numbers come from a RANDOM split with 7,290 training
molecules, while this test set is scaffold-disjoint and the budget is 600. Their
numbers are a ceiling, not a like-for-like target.

The audit
---------
`--audit` evaluates each model on 500 pool molecules absent from that team's
`al_log.jsonl`. A model trained on 600 molecules should fit those 600 noticeably
better than 500 it has never seen. If

    sMAE(unpurchased pool) / sMAE(purchased)

is close to 1, the model has probably seen more data than the log admits. That
is evidence for a conversation, not a verdict -- a well-regularised model with a
good acquisition strategy can legitimately generalise within the pool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

AUDIT_RATIO_FLAG = 1.15
AUDIT_N = 500


def unpack(entry: Path, workdir: Path) -> Path | None:
    """Return a directory containing manifest.json, or None."""
    if entry.is_dir():
        target = entry
    elif entry.suffix.lower() == ".zip":
        target = workdir / entry.stem
        target.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(entry) as z:
                z.extractall(target)
        except zipfile.BadZipFile:
            return None
    else:
        return None
    if (target / "manifest.json").exists():
        return target
    hits = sorted(target.rglob("manifest.json"))
    return hits[0].parent if hits else None


def read_log(path: Path) -> list[str]:
    bought: list[str] = []
    if not path.exists():
        return bought
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("event") == "query":
            bought += list(rec.get("acid_ids", []))
    return list(dict.fromkeys(bought))


def run_predict(subdir: Path, smiles_csv: Path, out_csv: Path,
                timeout: int = 1800) -> tuple[bool, str]:
    cmd = [sys.executable, str(subdir / "predict.py"),
           "--smiles-csv", str(smiles_csv),
           "--submission-dir", str(subdir),
           "--out", str(out_csv)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-8:]
        return False, "predict.py failed: " + " | ".join(tail)
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submissions", required=True)
    ap.add_argument("--test", default="../data/instructor/test_hidden.csv")
    ap.add_argument("--bundle", default="../data/student")
    ap.add_argument("--labels", default="../data/labels_all.csv",
                    help="full label table, needed for --audit")
    ap.add_argument("--benchmark", default="../data/published_benchmark.csv")
    ap.add_argument("--out", default="../data/instructor")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--family-balanced", action="store_true",
                    help="rank on the family-averaged score instead of the "
                         "target-averaged one")
    ap.add_argument("--check-predict-hash",
                    default="../predict.py.sha256")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    here = Path(__file__).parent
    sys.path.insert(0, str((here / ".." / "instructor").resolve()))
    sys.path.insert(0, str((here / "..").resolve()))

    import numpy as np
    import pandas as pd

    from al_toolkit import (ence, ence_per_task, scaled_mae, scaled_mae_per_task,
                            sigma_error_spearman, target_scales)

    spec = json.loads((Path(args.bundle) / "targets.json").read_text(
        encoding="utf-8"))
    ref_targets = spec["targets"]
    families = spec["families"]
    fam_of = spec["family_of_target"]
    budget = int(spec.get("budget", {}).get("total", 600))
    prov = spec.get("provenance", {})
    fam_cols_idx = {f: [i for i, t in enumerate(ref_targets) if fam_of[t] == f]
                    for f in families}

    test = pd.read_csv(args.test, encoding="utf-8")
    y_true = test[ref_targets].to_numpy(dtype=float)
    scales = target_scales(y_true)
    print(f"hidden test set: {len(test)} molecules x {len(ref_targets)} targets")
    n_bad = int(np.isnan(scales).sum())
    if n_bad:
        print(f"  ({n_bad} target(s) have no spread and are skipped)")
    print(f"budget: {budget} labels "
          f"~ {budget * prov.get('cpu_hours_per_label', 0):,.0f} CPU-hours of DFT")

    bench = None
    bp = Path(args.benchmark)
    if bp.exists():
        bench = pd.read_csv(bp, encoding="utf-8")
        bench = bench[bench["target"].isin(ref_targets)]
        print(f"published reference: {len(bench)} target(s) "
              f"(train size {prov.get('published_gnn_train_size', '?')}, "
              f"{prov.get('published_gnn_split', '?')})")

    expected_hash = None
    hp = Path(args.check_predict_hash)
    if hp.exists():
        expected_hash = hp.read_text().split()[0].strip()

    pool_labels = None
    if args.audit:
        pool_labels = pd.read_csv(args.labels, encoding="utf-8").set_index("acid_id")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    entries = sorted(Path(args.submissions).iterdir())
    print(f"found {len(entries)} entr(y/ies) in {args.submissions}\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        hidden_csv = tmp / "hidden_smiles.csv"
        test[["acid_id", "smiles"]].to_csv(hidden_csv, index=False,
                                           encoding="utf-8")

        for entry in entries:
            sub = unpack(entry, tmp / "unpacked")
            if sub is None:
                if not entry.name.startswith("leaderboard"):
                    print(f"skip   {entry.name} (no manifest.json)")
                continue
            try:
                manifest = json.loads((sub / "manifest.json").read_text(
                    encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                print(f"skip   {entry.name}: unreadable manifest ({exc})")
                continue
            team = manifest.get("team") or entry.stem
            print(f"score  {team}")

            row: dict = {
                "team": team, "entry": entry.name,
                "acquisition": manifest.get("acquisition"),
                "seed_method": manifest.get("seed_method"),
                "head": manifest.get("head"),
                "n_models": len(manifest.get("model_files", [])),
                "labels_used": manifest.get("labels_used"),
                "status": "ok", "notes": [],
            }

            got = (hashlib.sha256((sub / "predict.py").read_bytes()).hexdigest()
                   if (sub / "predict.py").exists() else None)
            if expected_hash and got != expected_hash:
                row["status"] = "disqualified"
                row["notes"].append("predict.py modified")

            bought = read_log(sub / "al_log.jsonl")
            row["labels_logged"] = len(bought)
            if len(bought) > budget:
                row["status"] = "disqualified"
                row["notes"].append(f"budget exceeded ({len(bought)})")
            if manifest.get("targets") != ref_targets:
                row["status"] = "disqualified"
                row["notes"].append("target list/order mismatch")

            if row["status"] == "ok":
                out_csv = tmp / f"pred_{team.replace('/', '_')}.csv"
                ok, msg = run_predict(sub, hidden_csv, out_csv, args.timeout)
                if not ok:
                    row["status"] = "error"
                    row["notes"].append(msg)
                else:
                    pred = pd.read_csv(out_csv, encoding="utf-8")
                    if len(pred) != len(test):
                        row["status"] = "error"
                        row["notes"].append(
                            f"row count {len(pred)} != {len(test)}")
                    elif not set(ref_targets) <= set(pred.columns):
                        row["status"] = "error"
                        row["notes"].append("missing target columns")
                    else:
                        y_hat = pred[ref_targets].to_numpy(dtype=float)
                        sg_cols = [t + "_sigma" for t in ref_targets]
                        sigma = (pred[sg_cols].to_numpy(dtype=float)
                                 if set(sg_cols) <= set(pred.columns) else None)

                        per_task = scaled_mae_per_task(y_true, y_hat, scales)
                        row["mean_sMAE"] = float(np.nanmean(per_task))
                        if sigma is None:
                            row["mean_ENCE"] = float("nan")
                            row["notes"].append("no sigma columns")
                            ence_task = None
                        else:
                            ence_task = ence_per_task(y_true, y_hat, sigma)
                            row["mean_ENCE"] = float(np.nanmean(ence_task))
                            row["spearman_sigma_err"] = sigma_error_spearman(
                                y_true, y_hat, sigma)
                            row["frac_tasks_calibrated"] = float(
                                np.mean(np.isfinite(ence_task)))

                        fam_smae, fam_ence = [], []
                        for fam in families:
                            cols = fam_cols_idx[fam]
                            if not cols:
                                continue
                            v = float(np.nanmean(per_task[cols]))
                            row[f"sMAE_{fam}"] = v
                            fam_smae.append(v)
                            if ence_task is not None:
                                e = float(np.nanmean(ence_task[cols]))
                                row[f"ENCE_{fam}"] = e
                                fam_ence.append(e)
                        row["famavg_sMAE"] = float(np.nanmean(fam_smae))
                        if fam_ence:
                            row["famavg_ENCE"] = float(np.nanmean(fam_ence))

                        # ---- published reference ------------------------
                        if bench is not None and len(bench):
                            ratios = []
                            for r in bench.itertuples(index=False):
                                j = ref_targets.index(r.target)
                                mae = float(np.nanmean(
                                    np.abs(y_true[:, j] - y_hat[:, j])))
                                if r.published_3D_GNN_MAE > 0:
                                    ratios.append(mae / r.published_3D_GNN_MAE)
                            if ratios:
                                row["MAE_over_published"] = float(np.mean(ratios))

                        # ---- audit --------------------------------------
                        if args.audit and pool_labels is not None and bought:
                            try:
                                rng = np.random.default_rng(0)
                                unseen = [a for a in pool_labels.index
                                          if a not in set(bought)]
                                pick = rng.choice(len(unseen),
                                                  size=min(AUDIT_N, len(unseen)),
                                                  replace=False)
                                unseen = [unseen[i] for i in pick]
                                for tag, ids in (("train", bought),
                                                 ("unseen", unseen)):
                                    csv_a = tmp / f"audit_{tag}.csv"
                                    sub_df = pool_labels.loc[ids].reset_index()
                                    sub_df[["acid_id", "smiles"]].to_csv(
                                        csv_a, index=False, encoding="utf-8")
                                    out_a = tmp / f"audit_{tag}_pred.csv"
                                    ok_a, _ = run_predict(sub, csv_a, out_a,
                                                          args.timeout)
                                    if not ok_a:
                                        raise RuntimeError("audit inference failed")
                                    pa = pd.read_csv(out_a, encoding="utf-8")
                                    row[f"sMAE_{tag}"] = scaled_mae(
                                        sub_df[ref_targets].to_numpy(float),
                                        pa[ref_targets].to_numpy(float), scales)
                                if row.get("sMAE_train", 0) > 0:
                                    ratio = row["sMAE_unseen"] / row["sMAE_train"]
                                    row["audit_ratio"] = ratio
                                    if ratio < AUDIT_RATIO_FLAG:
                                        row["notes"].append(
                                            f"AUDIT: unseen/train sMAE = "
                                            f"{ratio:.2f} -- ask about this")
                            except Exception as exc:  # noqa: BLE001
                                row["notes"].append(f"audit skipped ({exc})")

            lc = sub / "learning_curve.csv"
            if lc.exists():
                try:
                    df = pd.read_csv(lc, encoding="utf-8")
                    x = df["n_labels"].to_numpy(float)
                    y = df["dev_scaled_mae"].to_numpy(float)
                    if len(x) > 1:
                        trap = getattr(np, "trapezoid", None) or np.trapz
                        row["AULC_dev"] = float(trap(y, x) / (x[-1] - x[0]))
                    row["n_rounds"] = len(df)
                except Exception:  # noqa: BLE001
                    pass

            if "mean_sMAE" in row and np.isfinite(row.get("mean_ENCE", np.nan)):
                row["combined"] = row["mean_sMAE"] + row["mean_ENCE"]
                row["combined_famavg"] = (row["famavg_sMAE"]
                                          + row.get("famavg_ENCE", np.nan))
            row["notes"] = "; ".join(row["notes"])
            rows.append(row)
            if row["status"] == "ok":
                print(f"       sMAE={row.get('mean_sMAE', float('nan')):.4f}  "
                      f"ENCE={row.get('mean_ENCE', float('nan')):.3f}  "
                      f"combined={row.get('combined', float('nan')):.4f}")
            else:
                print(f"       {row['status'].upper()}: {row['notes']}")

    if not rows:
        print("\nnothing to score.")
        return 1

    lb = pd.DataFrame(rows)
    rank_on = "combined_famavg" if args.family_balanced else "combined"
    if rank_on not in lb.columns:
        rank_on = "combined"
    lb["_status_order"] = lb["status"].map({"ok": 0, "error": 1,
                                            "disqualified": 2}).fillna(3)
    lb = lb.sort_values(["_status_order", rank_on]).drop(columns="_status_order")
    lb.insert(0, "rank", [i + 1 if s == "ok" else ""
                          for i, s in enumerate(lb["status"])])
    lb.to_csv(outdir / "leaderboard.csv", index=False, encoding="utf-8")

    show = [c for c in ["rank", "team", rank_on, "mean_sMAE", "mean_ENCE",
                        "famavg_sMAE", "spearman_sigma_err",
                        "MAE_over_published", "labels_used", "acquisition",
                        "seed_method", "head", "AULC_dev", "audit_ratio",
                        "status", "notes"] if c in lb.columns]

    md = ["# Leaderboard", "",
          f"Ranked on `{rank_on}` (lower is better). "
          f"`combined = mean_sMAE + mean_ENCE`.", "",
          f"- budget: **{budget} labels** "
          f"(~{budget * prov.get('cpu_hours_per_label', 0):,.0f} CPU-hours of DFT)",
          f"- hidden test set: **{len(test)}** scaffold-disjoint acids, "
          f"**{len(ref_targets)}** targets",
          f"- labels: published DFT descriptors, "
          f"`{prov.get('level_of_theory', '?')}`", ""]
    if "MAE_over_published" in lb.columns:
        md += [f"`MAE_over_published` compares against the paper's own 3D GNN on "
               f"{0 if bench is None else len(bench)} targets. That model saw "
               f"**{prov.get('published_gnn_train_size', '?')}** training "
               f"molecules on a **random** split; this test set is "
               f"scaffold-disjoint. A ratio above 1 is expected and is not a "
               f"failure.", ""]
    md += [lb[show].to_markdown(index=False, floatfmt=".4f"), ""]

    fam_cols = [f"sMAE_{f}" for f in families if f"sMAE_{f}" in lb.columns]
    if fam_cols:
        md += ["## Scaled MAE by descriptor family", "",
               "Buried volume is 31% of the targets even after trimming, so read "
               "this table before reading the ranking.", "",
               lb[["rank", "team"] + fam_cols].to_markdown(
                   index=False, floatfmt=".4f"), ""]
    ence_cols = [f"ENCE_{f}" for f in families if f"ENCE_{f}" in lb.columns]
    if ence_cols:
        md += ["## ENCE by descriptor family", "",
               lb[["rank", "team"] + ence_cols].to_markdown(
                   index=False, floatfmt=".4f"), ""]

    (outdir / "leaderboard.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nwrote {outdir / 'leaderboard.md'}")
    print(lb[show].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
