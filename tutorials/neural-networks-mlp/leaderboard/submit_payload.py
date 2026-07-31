"""Helpers for validating and exporting leaderboard submissions."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = [
    "run_id",
    "timestamp_utc",
    "student_or_team",
    "dataset_name",
    "task_type",
    "split_version",
    "model_family",
    "hidden_layers",
    "hidden_width",
    "activation",
    "dropout",
    "optimizer",
    "learning_rate",
    "batch_size",
    "weight_decay",
    "epochs_trained",
    "param_count",
    "train_time_sec",
    "best_val_score",
    "test_score",
    "metric_name",
    "device",
    "seed",
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


if __name__ == "__main__":
    demo_payload = {
        "run_id": "team00_demo",
        "timestamp_utc": utc_now_iso(),
        "student_or_team": "Team 00",
        "dataset_name": "tox21_fingerprints",
        "task_type": "multi_label_classification",
        "split_version": "v1",
        "model_family": "MLP",
        "hidden_layers": 2,
        "hidden_width": 128,
        "activation": "relu",
        "dropout": 0.2,
        "optimizer": "adam",
        "learning_rate": 0.001,
        "batch_size": 128,
        "weight_decay": 0.0001,
        "epochs_trained": 20,
        "param_count": 54321,
        "train_time_sec": 95.4,
        "best_val_score": 0.75,
        "test_score": 0.73,
        "metric_name": "roc_auc",
        "device": "cpu",
        "seed": 42,
        "notebook_version": "nn_tutorial_v2",
        "notes": "demo",
    }
    write_payload_json(demo_payload, "./demo_submission.json")
    append_payload_csv(demo_payload, "./local_leaderboard_log.csv")
    print("Wrote demo submission artifacts.")
