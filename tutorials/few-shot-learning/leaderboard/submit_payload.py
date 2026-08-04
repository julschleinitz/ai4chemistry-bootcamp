"""Helpers for validating, exporting, and submitting leaderboard payloads.

Mirrors tutorials/neural-networks-mlp/leaderboard/submit_payload.py, adapted to this
tutorial's results_schema.csv. The notebook imports `build_payload` / `submit_payload`
directly (or students can copy the relevant bits inline) to POST their run to the
Apps Script Web App endpoint described in SETUP.md.
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
    "model_family",
    "pretrained",
    "fine_tune_fraction",
    "n_frozen_layers",
    "learning_rate",
    "epochs_trained",
    "param_count",
    "train_time_sec",
    "test_mae_ppm",
    "test_rmse_ppm",
    "n_atoms_scored",
    "n_atoms_expected",
    "coverage_pct",
    "split_version",
    "notebook_version",
    "seed",
    "device",
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
        "model_family": "pretrain+finetune",
        "pretrained": True,
        "fine_tune_fraction": 0.10,
        "n_frozen_layers": 2,
        "learning_rate": 0.0001,
        "epochs_trained": 25,
        "param_count": 184193,
        "train_time_sec": 41.7,
        "test_mae_ppm": 0.284,
        "test_rmse_ppm": 0.391,
        "n_atoms_scored": 118,
        "n_atoms_expected": 120,
        "coverage_pct": 98.3,
        "split_version": "v1",
        "notebook_version": "few-shot-learning.ipynb v1",
        "seed": 42,
        "device": "cpu",
        "notes": "demo",
    }
    write_payload_json(demo_payload, "./demo_submission.json")
    append_payload_csv(demo_payload, "./local_leaderboard_log.csv")
    print("Wrote demo submission artifacts.")
