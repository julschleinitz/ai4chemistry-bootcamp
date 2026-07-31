# Leaderboard Setup

This folder defines the submission format used for Pareto-front analysis.

## Files

- `results_schema.csv`: canonical leaderboard columns.
- `submission_payload.example.json`: example final-run payload.
- `submit_payload.py`: validation and local export helper.

## Google Sheets handoff

1. Create a shared Google Sheet with columns from `results_schema.csv`.
2. Add an Apps Script endpoint that accepts JSON payloads and appends rows.
3. Replace the tutorial page resource link with the shared sheet URL.

## Minimal Apps Script payload contract

- HTTP method: `POST`
- Content type: `application/json`
- Body: fields matching `results_schema.csv`
