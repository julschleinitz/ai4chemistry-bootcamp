# Bayesian Optimization for Reaction Conditions — Leaderboard Setup

This folder defines the submission pipeline for the self-report leaderboard challenge in
`reaction-bo.ipynb`. It follows the same pattern as
`tutorials/06-pretraining_finetuning/leaderboard/`: no fixed held-out split (there isn't one here —
the datasets themselves *are* the fixed lookup tables everyone optimizes against), and a
Sheets-backed pipeline where students self-report a run's score by POSTing a JSON payload to an
Apps Script Web App. Unlike `08-molecule-generation`'s docking oracle, there is no independent
instructor grading here — students compute `auc_mean` / `auc_std` / `max_score_achieved` locally in
the notebook and submit them directly (honor system, same trust model as `06-pretraining_finetuning`).

## Files

- `results_schema.csv` — canonical leaderboard columns (one row per submitted run).
- `submission_payload.example.json` — example payload matching `results_schema.csv`.
- `submit_payload.py` — validation, local export, and POST helper (mirrors
  `06-pretraining_finetuning/leaderboard/submit_payload.py` structure exactly: `validate_payload`,
  `write_payload_json`, `append_payload_csv`, `submit_payload`).
- `apps_script.gs` — Google Apps Script Web App: accepts a JSON POST matching `results_schema.csv`
  and appends one row to the "Leaderboard" tab of the master Google Sheet.
- `SETUP.md` — click-by-click deployment steps.

## Google Sheets handoff

1. Create a shared Google Sheet with one tab, `Leaderboard`, header row = columns from
   `results_schema.csv`.
2. Add an Apps Script Web App (`apps_script.gs`) that accepts JSON payloads and appends rows.
3. Publish the `Leaderboard` tab to the web (File → Share → Publish to web) so the tutorial page's
   live widget can read it with no server or API key (gviz JSON feed).
4. Point the notebook's `LEADERBOARD_ENDPOINT_URL` at the deployed Web App URL, and the tutorial
   page's `LEADERBOARD_SHEET_ID` / `LEADERBOARD_GID` at the published sheet.

## Minimal Apps Script payload contract

- HTTP method: `POST`
- Content type: `application/json`
- Body: fields matching `results_schema.csv`

## Fixed setup policy

Unlike tutorials with a frozen held-out test split, this tutorial's "fixed setup" is: **the same 4
datasets** (`perera_suzuki`, `reizman_suzuki`, `shields_direct_arylation`, `baumgartner_cn_coupling`,
see `../PAPERS-AND-DATASETS.md`) **and the same batch size of 4** for everyone. Students are free to
choose their own dataset, featurization, initialization, and acquisition function/hyperparameters —
those choices are exactly what the leaderboard is meant to compare.

1. The instructor publishes the 4 dataset CSVs (`../data/*.csv`) once, before class; students must
   not substitute their own data.
2. `batch_size` is fixed at 4 in the notebook and is not user-editable — see Section 5 of
   `reaction-bo.ipynb` for why.
3. **Ranking is per dataset** — a run on `perera_suzuki` is not comparable to one on
   `baumgartner_cn_coupling` (different underlying yield landscapes and factor counts), so the
   tutorial page's leaderboard widget groups submissions by `dataset` and sorts by `auc_mean`
   descending *within* each group, not across the whole table.
4. Students may resubmit as many runs as they like (e.g. after trying a different featurization or
   acquisition function per the notebook's exercises); the leaderboard widget keeps each team's best
   (highest) `auc_mean` per dataset.
