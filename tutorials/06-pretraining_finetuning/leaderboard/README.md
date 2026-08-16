# Few-Shot Learning Tutorial — Leaderboard Setup

This folder defines the fixed test split and the submission pipeline for the NMR chemical-shift
leaderboard challenge in `pretraining_finetuning.ipynb`. It follows the exact same pattern as
`tutorials/04-deep-learning-neural-network/neural-networks-mlp/leaderboard/`: a fixed split published in advance, and a
Sheets-backed grading pipeline where students self-report a run's score by POSTing a JSON payload
to an Apps Script Web App.

## Files

- `official_test_set.csv` — **public.** The fixed class-wide test split: SMILES, the H atom index
  to predict, and its true `delta(1H)` value. Ships with the notebook, which downloads it directly
  and computes its own MAE/RMSE against it (same trust model as `neural-networks-mlp`: the split
  is fixed so everyone is compared on the same molecules, not held secret).
- `results_schema.csv` — canonical leaderboard columns (one row per submitted run).
- `submission_payload.example.json` — example payload matching `results_schema.csv`.
- `submit_payload.py` — validation, local export, and POST helper (mirrors
  `neural-networks-mlp/leaderboard/submit_payload.py`, plus a `submit_payload()` function that
  POSTs to the Web App).
- `apps_script.gs` — Google Apps Script Web App: accepts a JSON POST matching `results_schema.csv`
  and appends one row to the "Leaderboard" tab of the master Google Sheet.
- `freeze_holdout_split.py` — **run once, by the instructor, before the bootcamp.** Deterministically
  (seed=42) samples molecules from the real experimental test split used in the notebook and writes
  `official_test_set.csv`.
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

## Fixed split policy

Same policy as the other tutorials in this bootcamp:

1. The instructor publishes `official_test_set.csv` once, before class.
2. Students must not generate their own random test split — everyone evaluates against the same
   fixed molecules.
3. Students may resubmit as many runs as they like; the tutorial page's widget keeps each team's
   best (lowest) `test_mae_ppm`.
4. `coverage_pct` is reported alongside the error so a partial-coverage submission (e.g. a model
   that silently skips atoms it can't handle) isn't mistaken for a genuinely more accurate one.
