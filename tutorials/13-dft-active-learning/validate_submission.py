#!/usr/bin/env python3
"""
validate_submission.py -- run this before you upload. It is the "little test".

    python validate_submission.py --submission-dir submission_teamname \
                                  --bundle data/student

It checks everything the instructor's scorer will check, in the same way, and
then actually runs your `predict.py` on 50 public molecules. If it prints

    READY TO SUBMIT

your checkpoint works. If it does not, nothing you upload will be scored, so fix
it now rather than at the leaderboard.

Exit code 0 = pass, 1 = fail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED = ["manifest.json", "predict.py", "al_log.jsonl", "learning_curve.csv"]

MANIFEST_REQUIRED = ["team", "targets", "head", "model_files", "labels_used",
                     "acquisition", "seed_method"]

BUDGET = 600

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def ok(self, msg: str) -> None:
        print(f"  {GREEN}pass{RESET}  {msg}")

    def fail(self, msg: str) -> None:
        print(f"  {RED}FAIL{RESET}  {msg}")
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        print(f"  {YELLOW}warn{RESET}  {msg}")
        self.warnings.append(msg)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--bundle", default="data/student")
    ap.add_argument("--reference-predict", default=None,
                    help="path to the pristine predict.py (default: next to this file)")
    ap.add_argument("--skip-inference", action="store_true",
                    help="skip actually running predict.py (not recommended)")
    args = ap.parse_args()

    import numpy as np
    import pandas as pd

    r = Report()
    sub = Path(args.submission_dir)
    bundle = Path(args.bundle)
    here = Path(__file__).parent

    print(f"\nvalidating {sub}\n")

    # ---- 1. files exist --------------------------------------------------
    print("files")
    if not sub.is_dir():
        print(f"  {RED}FAIL{RESET}  {sub} is not a directory")
        return 1
    for name in REQUIRED:
        (r.ok if (sub / name).exists() else r.fail)(name)
    if not (sub / "models").is_dir():
        r.fail("models/ directory")
    else:
        pts = sorted((sub / "models").glob("*.pt"))
        (r.ok if pts else r.fail)(f"models/ contains {len(pts)} .pt file(s)")

    if r.errors:
        print(f"\n{RED}cannot continue -- fix the missing files first{RESET}\n")
        return 1

    # ---- 2. predict.py unmodified ---------------------------------------
    print("\npredict.py integrity")
    ref = Path(args.reference_predict) if args.reference_predict else here / "predict.py"
    expected_file = here / "predict.py.sha256"
    got = sha256(sub / "predict.py")
    expected = None
    if expected_file.exists():
        expected = expected_file.read_text().split()[0].strip()
    elif ref.exists() and ref.resolve() != (sub / "predict.py").resolve():
        expected = sha256(ref)
    if expected is None:
        r.warn("no reference hash available; cannot verify predict.py")
    elif got == expected:
        r.ok(f"sha256 matches ({got[:12]}...)")
    else:
        r.fail(f"predict.py has been modified\n        expected {expected}\n"
               f"        got      {got}\n"
               "        Copy the pristine predict.py back into your submission.")

    # ---- 3. manifest -----------------------------------------------------
    print("\nmanifest.json")
    try:
        manifest = json.loads((sub / "manifest.json").read_text())
    except Exception as exc:  # noqa: BLE001
        r.fail(f"unparseable: {exc}")
        return 1
    for k in MANIFEST_REQUIRED:
        (r.ok if k in manifest else r.fail)(f"key `{k}`")

    spec = json.loads((bundle / "targets.json").read_text())
    ref_targets = spec["targets"]
    budget = int(spec.get("budget", {}).get("total", BUDGET))
    if manifest.get("targets") == ref_targets:
        r.ok(f"targets match targets.json exactly ({len(ref_targets)} targets)")
    else:
        mt = manifest.get("targets") or []
        if set(mt) == set(ref_targets):
            r.fail("targets are the right set but the WRONG ORDER -- your model's "
                   "output columns would be permuted. Use "
                   "json.load(open('targets.json'))['targets'] verbatim.")
        else:
            r.fail(f"targets do not match: you list {len(mt)}, expected "
                   f"{len(ref_targets)}")

    if manifest.get("head") not in {"regression", "mve", "evidential"}:
        r.fail(f"head must be regression|mve|evidential, got {manifest.get('head')!r}")
    else:
        r.ok(f"head = {manifest['head']}")
    n_models = len(manifest.get("model_files", []))
    listed_missing = [f for f in manifest.get("model_files", [])
                      if not (sub / "models" / f).exists()]
    if listed_missing:
        r.fail(f"manifest lists checkpoints that are not in models/: {listed_missing}")
    else:
        r.ok(f"{n_models} checkpoint(s) listed and present")
    if manifest.get("head") == "regression" and n_models == 1:
        r.warn("single regression head: your sigma will be all-zero and your "
               "calibration score will be the worst possible. Use an ensemble, "
               "MVE, or evidential.")

    # ---- 4. the oracle log ----------------------------------------------
    print("\nal_log.jsonl")
    bought: list[str] = []
    rounds_seen = set()
    try:
        for line in (sub / "al_log.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("event") == "query":
                bought += list(rec.get("acid_ids", []))
                rounds_seen.add(rec.get("round"))
    except Exception as exc:  # noqa: BLE001
        r.fail(f"unparseable: {exc}")
        return 1

    if len(bought) == len(set(bought)):
        r.ok(f"{len(bought)} unique labels bought")
    else:
        r.fail(f"{len(bought) - len(set(bought))} duplicate purchases in the log")
    if len(set(bought)) <= budget:
        r.ok(f"budget respected ({len(set(bought))} <= {budget})")
    else:
        r.fail(f"budget EXCEEDED: {len(set(bought))} > {budget}")

    pool_ids = set(pd.read_csv(bundle / "pool_meta.csv")["acid_id"])
    dev_ids = set(pd.read_csv(bundle / "dev.csv")["acid_id"])
    outside = set(bought) - pool_ids
    if outside:
        r.fail(f"{len(outside)} logged id(s) are not in the pool, "
               f"e.g. {sorted(outside)[:3]}")
    else:
        r.ok("every logged id is in the pool")
    leaked = set(bought) & dev_ids
    if leaked:
        r.fail(f"{len(leaked)} logged id(s) are dev molecules -- the log should "
               "only contain pool purchases")
    else:
        r.ok("no dev molecules in the purchase log")

    if manifest.get("labels_used") == len(set(bought)):
        r.ok(f"manifest labels_used agrees with the log ({len(set(bought))})")
    else:
        r.fail(f"manifest says labels_used={manifest.get('labels_used')} but the "
               f"log shows {len(set(bought))}")

    # ---- 5. learning curve ----------------------------------------------
    print("\nlearning_curve.csv")
    try:
        lc = pd.read_csv(sub / "learning_curve.csv")
    except Exception as exc:  # noqa: BLE001
        r.fail(f"unreadable: {exc}")
        lc = None
    if lc is not None:
        need = {"round", "n_labels", "dev_scaled_mae", "dev_ence"}
        if need <= set(lc.columns):
            r.ok(f"{len(lc)} rounds recorded, final dev sMAE = "
                 f"{lc['dev_scaled_mae'].iloc[-1]:.4f}")
        else:
            r.fail(f"missing column(s): {sorted(need - set(lc.columns))}")
        if len(lc) < 2:
            r.warn("fewer than 2 rounds -- did the loop actually run?")

    # ---- 6. run predict.py ----------------------------------------------
    if args.skip_inference:
        r.warn("inference skipped by request; the instructor will NOT skip it")
    else:
        print("\ninference on the public self-test molecules")
        selftest = bundle / "selftest_smiles.csv"
        if not selftest.exists():
            r.fail(f"{selftest} not found -- check --bundle")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "selftest_out.csv"
                cmd = [sys.executable, str(sub / "predict.py"),
                       "--smiles-csv", str(selftest),
                       "--submission-dir", str(sub),
                       "--out", str(out)]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode != 0:
                    r.fail("predict.py crashed:\n" +
                           "\n".join(f"        {ln}" for ln in
                                     (proc.stderr or proc.stdout).strip()
                                     .splitlines()[-15:]))
                else:
                    r.ok("predict.py ran without error")
                    pred = pd.read_csv(out)
                    st = pd.read_csv(selftest)
                    if len(pred) == len(st):
                        r.ok(f"{len(pred)} rows out for {len(st)} rows in")
                    else:
                        r.fail(f"{len(pred)} rows out for {len(st)} rows in")

                    want = ["acid_id", "smiles"] + ref_targets + \
                           [t + "_sigma" for t in ref_targets]
                    if list(pred.columns) == want:
                        r.ok(f"columns exactly as required "
                             f"({len(want)} columns)")
                    else:
                        extra = set(pred.columns) - set(want)
                        miss = set(want) - set(pred.columns)
                        r.fail("column mismatch"
                               + (f"; missing {sorted(miss)[:4]}" if miss else "")
                               + (f"; unexpected {sorted(extra)[:4]}" if extra else "")
                               + ("; right names, wrong order"
                                  if not miss and not extra else ""))

                    mu = pred[[c for c in ref_targets if c in pred.columns]]
                    sg = pred[[c + "_sigma" for c in ref_targets
                               if c + "_sigma" in pred.columns]]
                    if mu.shape[1] and np.isfinite(mu.to_numpy()).all():
                        r.ok("no NaN / inf in the predictions")
                    else:
                        r.fail("predictions contain NaN or inf")
                    if sg.shape[1]:
                        sv = sg.to_numpy()
                        if not np.isfinite(sv).all():
                            r.fail("sigma contains NaN or inf")
                        elif (sv <= 0).all():
                            r.fail("every sigma is zero -- your calibration score "
                                   "will be the worst possible. Train an ensemble "
                                   "or use head='mve'/'evidential'.")
                        elif float(np.nanstd(sv)) == 0.0:
                            r.warn("sigma is constant across all molecules and "
                                   "targets; ENCE will be poor")
                        else:
                            r.ok(f"sigma looks like a real distribution "
                                 f"(median {np.median(sv):.4g}, "
                                 f"IQR {np.percentile(sv, 75) - np.percentile(sv, 25):.4g})")

    # ---- verdict ---------------------------------------------------------
    print()
    if r.errors:
        print(f"{RED}NOT READY -- {len(r.errors)} problem(s):{RESET}")
        for e in r.errors:
            print(f"  - {e.splitlines()[0]}")
        print()
        return 1
    if r.warnings:
        print(f"{YELLOW}{len(r.warnings)} warning(s) -- you may submit, but read "
              f"them:{RESET}")
        for w in r.warnings:
            print(f"  - {w}")
        print()
    print(f"{GREEN}READY TO SUBMIT{RESET}")
    print(f"\n  1. zip it:    zip -r {sub.name}.zip {sub}")
    print(f"  2. upload {sub.name}.zip to the shared Drive folder:")
    print("       AI4Chem Bootcamp 2026 / lecture_13_tutorial / submissions/")
    print("  3. one zip per team. Re-uploading replaces your entry.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
