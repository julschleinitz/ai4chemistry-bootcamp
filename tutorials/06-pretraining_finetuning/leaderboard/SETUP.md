# Leaderboard setup (one-time, before the bootcamp)

Everything below is done once, under your own Google account. It's the same pattern already used
for `tutorials/04-deep-learning-neural-network/neural-networks-mlp/leaderboard/` — a Google Sheet plus an Apps Script Web App, no
Drive folder, no file parsing.

## 1. Freeze the test split

```bash
pip install rdkit pandas
python freeze_holdout_split.py --n-molecules 30 --seed 42
```

This writes `official_test_set.csv` (SMILES + atom index + true shift, all public). Commit it to
the repo alongside the notebook, at `tutorials/06-pretraining_finetuning/leaderboard/official_test_set.csv`
— the notebook downloads it from that path.

## 2. Create the master Google Sheet

1. Create a new Google Sheet, e.g. `AI4Chem Few-Shot Leaderboard`.
2. Create one tab named exactly `Leaderboard`.
3. Row 1 (header), matching `results_schema.csv`:
   `run_id | timestamp_utc | team_name | model_family | pretrained | fine_tune_fraction | n_frozen_layers | learning_rate | epochs_trained | param_count | train_time_sec | test_mae_ppm | test_rmse_ppm | n_atoms_scored | n_atoms_expected | coverage_pct | split_version | notebook_version | seed | device | notes`
4. **Publish the `Leaderboard` tab to the web:** File → Share → Publish to web → select the
   `Leaderboard` sheet → Publish. This is what lets the tutorial page's JS widget read it with no
   server or API key.
5. From the published URL, note the **spreadsheet ID** (the long string between `/d/` and
   `/edit` in the Sheet's normal URL) and the tab's **gid** (visible in the URL when that tab is
   open, `...#gid=123456`).

## 3. Deploy the Apps Script Web App

1. In the Sheet: Extensions → Apps Script.
2. Delete the boilerplate `Code.gs` content and paste in `apps_script.gs`.
3. Deploy → New deployment → gear icon → type **Web app**.
   - Execute as: **Me**.
   - Who has access: **Anyone**.
4. Click **Deploy**, authorize the requested permissions, and copy the **Web app URL** it gives you
   (looks like `https://script.google.com/macros/s/AKfycb.../exec`).
5. Sanity check: open that URL directly in a browser — you should see
   `{"status":"ok","message":"Few-shot learning leaderboard endpoint is live."}`.

## 4. Point the notebook and the tutorial page at your setup

- In `pretraining_finetuning.ipynb`, set `LEADERBOARD_ENDPOINT_URL` (in the challenge section) to the
  Web App URL from step 3.
- In `pretraining_finetuning.html`, set `LEADERBOARD_SHEET_ID` and `LEADERBOARD_GID` (in the `<script>`
  block near the bottom of the file) to the values from step 2.4.
- Tell students their `team_name` should stay consistent across resubmissions so the leaderboard can
  track their best score.

## Troubleshooting

- **POST from the notebook fails / times out.** Re-check "Who has access: Anyone" in the deployment
  settings — "Anyone with Google account" will reject students who aren't signed in inside Colab.
- **A submission never appears on the leaderboard.** Open Apps Script → Executions to see the error
  log for `doPost`. The most common cause is a payload missing one of the required
  `results_schema.csv` columns.
- **The tutorial page shows "leaderboard not configured yet."** `LEADERBOARD_SHEET_ID` /
  `LEADERBOARD_GID` in `pretraining_finetuning.html` still have their placeholder values — fill them in
  from step 2.5, and make sure the sheet is actually published (step 2.4).
