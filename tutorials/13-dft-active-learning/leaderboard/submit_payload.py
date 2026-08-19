"""Validate, export, and submit a leaderboard payload.

Mirrors tutorials/12-reaction-bo/leaderboard/submit_payload.py in structure
(`validate_payload` / `write_payload_json` / `append_payload_csv` / `submit_payload`), adapted to
this tutorial's results_schema.csv.

WHAT THIS BOARD IS. Students self-report their score on the PUBLIC dev set. It is a progress board
for the session, not the result. The real ranking comes from `score_submissions.py`, which the
instructor runs over the uploaded checkpoints against the scaffold-disjoint hidden test set that
students never see. Both numbers get published, and the movement between them is the point.

So the trust model is deliberately split:

  * dev score  -- honour system, self-reported, instant, wrong-ish on purpose
  * test score -- instructor-computed from your checkpoint, authoritative, and audited
                  (`score_submissions.py --audit` checks each model's error on 500 pool molecules
                  absent from its own oracle log)

`build_payload` pulls everything it can straight out of a `LoopResult`, so there is nothing for a
student to mistype except the team name.
"""

from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

NOTEBOOK_VERSION = "13-dft-active-learning/1.0"

REQUIRED_FIELDS = [
    "run_id",
    "timestamp_utc",
    "team_name",
    "head",
    "ensemble_size",
    "seed_method",
    "acquisition",
    "n_seed",
    "n_rounds",
    "batch_size",
    "labels_used",
    "dev_smae",
    "dev_ence",
    "dev_combined",
    "dev_aulc",
    "dev_spearman",
    "cpu_hours_bought",
    "notebook_version",
    "notes",
]


def utc_now_iso() -> str:
    return (datetime.now(timezone.utc).replace(microsecond=0)
            .isoformat().replace("+00:00", "Z"))


def validate_payload(payload: dict) -> None:
    missing = [key for key in REQUIRED_FIELDS if key not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    extra = [key for key in payload if key not in REQUIRED_FIELDS]
    if extra:
        raise ValueError(f"Unexpected fields (the Sheet has fixed columns): {extra}")


def build_payload(result, bundle, team_name: str, notes: str = "") -> dict:
    """Assemble a payload from a finished `al_toolkit.LoopResult`.

    Everything numeric is read off the run itself, so the only thing a student
    can get wrong is `team_name`.
    """
    import al_toolkit as al

    df = result.to_frame()
    last = df.iloc[-1]
    cfg = result.config
    spec = cfg.get("model_spec", {})

    smae = float(last["dev_scaled_mae"])
    ence = float(last["dev_ence"])
    slug = "".join(c if c.isalnum() else "_" for c in team_name).strip("_").lower()

    return {
        "run_id": f"{slug}_{uuid.uuid4().hex[:8]}",
        "timestamp_utc": utc_now_iso(),
        "team_name": team_name,
        "head": spec.get("head", "?"),
        "ensemble_size": int(spec.get("ensemble_size", 1)),
        "seed_method": cfg.get("seed_method", "?"),
        "acquisition": cfg.get("acquisition", "?"),
        "n_seed": int(cfg.get("n_seed", 0)),
        "n_rounds": int(cfg.get("n_rounds", 0)),
        "batch_size": int(cfg.get("batch_size", 0)),
        "labels_used": int(result.oracle.spent),
        "dev_smae": round(smae, 5),
        "dev_ence": round(ence, 5),
        "dev_combined": round(smae + ence, 5),
        "dev_aulc": round(float(al.aulc(result)), 5),
        "dev_spearman": round(float(last.get("dev_spearman", float("nan"))), 5),
        "cpu_hours_bought": round(bundle.cpu_hours(result.oracle.spent), 1),
        "notebook_version": NOTEBOOK_VERSION,
        "notes": notes,
    }


def write_payload_json(payload: dict, out_path: str | Path) -> Path:
    validate_payload(payload)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def append_payload_csv(payload: dict, csv_path: str | Path) -> Path:
    validate_payload(payload)
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(payload)
    return csv_path


def submit_payload(payload: dict, endpoint_url: str, timeout: int = 15) -> dict:
    """POST `payload` as JSON to the Apps Script Web App. Requires `requests`
    (preinstalled in Colab)."""
    import requests

    validate_payload(payload)
    resp = requests.post(endpoint_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {"status_code": resp.status_code, "text": resp.text}


if __name__ == "__main__":
    demo = {
        "run_id": "team00_demo",
        "timestamp_utc": utc_now_iso(),
        "team_name": "Team 00",
        "head": "mve",
        "ensemble_size": 3,
        "seed_method": "maxmin",
        "acquisition": "max_variance_scaled",
        "n_seed": 100,
        "n_rounds": 10,
        "batch_size": 50,
        "labels_used": 600,
        "dev_smae": 0.3821,
        "dev_ence": 0.1904,
        "dev_combined": 0.5725,
        "dev_aulc": 0.4713,
        "dev_spearman": 0.612,
        "cpu_hours_bought": 70380.0,
        "notebook_version": NOTEBOOK_VERSION,
        "notes": "demo row",
    }
    validate_payload(demo)
    print(json.dumps(demo, indent=2))
