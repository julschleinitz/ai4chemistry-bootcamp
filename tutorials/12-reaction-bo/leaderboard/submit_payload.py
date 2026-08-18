"""Helpers for validating, exporting, and submitting leaderboard payloads.

Mirrors tutorials/06-pretraining_finetuning/leaderboard/submit_payload.py exactly in structure
(validate_payload / write_payload_json / append_payload_csv / submit_payload), adapted to this
tutorial's results_schema.csv. The notebook imports these directly to POST a run's self-reported
BO metrics (auc_mean, auc_std, max_score_achieved) to the Apps Script Web App endpoint described
in SETUP.md. There is no independent instructor grading/oracle for this tutorial (unlike
08-molecule-generation's docking oracle) -- students compute their own metrics locally and submit
them, same trust model as 06-pretraining_finetuning.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = [
    "run_id",
    "timestamp_utc",
    "team_name",
    "dataset",
    "featurization",
    "init_method",
    "acquisition",
    "acquisition_hparams",
    "batch_size",
    "n_rounds",
    "n_seeds",
    "auc_mean",
    "auc_std",
    "max_score_achieved",
    "notebook_version",
    "notes",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_payload(payload: dict) -> None:
    missing = [key for key in REQUIRED_FIELDS if key not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")


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
    """POSTs `payload` as JSON to the Apps Script Web App endpoint. Used from the notebook;
    requires the `requests` package (preinstalled in Colab)."""
    import requests

    validate_payload(payload)
    resp = requests.post(endpoint_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {"status_code": resp.status_code, "text": resp.text}


if __name__ == "__main__":
    demo_payload = {
        "run_id": "team00_demo",
        "timestamp_utc": utc_now_iso(),
        "team_name": "Team 00",
        "dataset": "perera_suzuki",
        "featurization": "onehot",
        "init_method": "random",
        "acquisition": "EI",
        "acquisition_hparams": "{}",
        "batch_size": 4,
        "n_rounds": 8,
        "n_seeds": 5,
        "auc_mean": 0.8123,
        "auc_std": 0.0417,
        "max_score_achieved": 0.9781,
        "notebook_version": "reaction-bo.ipynb v1",
        "notes": "demo",
    }
    write_payload_json(demo_payload, "./demo_submission.json")
    append_payload_csv(demo_payload, "./local_leaderboard_log.csv")
    print("Wrote demo submission artifacts.")
