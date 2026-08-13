# Leaderboard setup (one-time, before the bootcamp)

Everything below is done once, under your own Google account, plus one script you keep running on
your own machine during class (there's no serverless way to run `smina` from Apps Script, so the
grading step can't live purely in the Sheet like `few-shot-learning`'s does).

## 1. Create the master Google Sheet

1. Create a new Google Sheet, e.g. `AI4Chem Molecular Generation Leaderboard`.
2. Create **two** tabs:
   - `Submissions` — row 1 header, matching `submissions_schema.csv`:
     `run_id | timestamp_utc | team_name | smiles | method_family | notes`
   - `Leaderboard` — row 1 header, matching `results_schema.csv`:
     `run_id | timestamp_utc_submitted | timestamp_utc_scored | team_name | smiles | best_affinity_kcal_mol | qed | toxicity_alerts | exhaustiveness | num_modes | pose_sdf | pocket_pdb_id | notebook_version | notes`
3. **Publish both tabs to the web:** File → Share → Publish to web → publish each sheet
   individually (so both `Submissions` and `Leaderboard` are readable via the gviz JSON feed with
   no server or API key — `score_submissions.py` needs to read `Submissions`, and the tutorial
   page needs to read `Leaderboard`).
4. From the published URLs, note the **spreadsheet ID** (the long string between `/d/` and `/edit`)
   and each tab's **gid** (visible in the URL when that tab is open, `...#gid=123456`).

## 2. Deploy the Apps Script Web App

1. In the Sheet: Extensions → Apps Script.
2. Delete the boilerplate `Code.gs` content and paste in `apps_script.gs`.
3. Deploy → New deployment → gear icon → type **Web app**.
   - Execute as: **Me**.
   - Who has access: **Anyone**.
4. Click **Deploy**, authorize the requested permissions, and copy the **Web app URL** it gives you.
5. Sanity check: open that URL directly in a browser — you should see
   `{"status":"ok","message":"Molecular generation leaderboard endpoint is live."}`.

## 3. Point the notebook, the grading script, and the tutorial page at your setup

- In `generative-vae.ipynb`'s challenge cell, set `LEADERBOARD_ENDPOINT_URL` to the Web App URL
  from step 2.4.
- In `score_submissions.py`, set `LEADERBOARD_SHEET_ID`, `SUBMISSIONS_GID`, `LEADERBOARD_GID`, and
  `LEADERBOARD_ENDPOINT_URL` to the values from steps 1.4 and 2.4.
- In `generative-vae.html`, set `LEADERBOARD_SHEET_ID` and `LEADERBOARD_GID` (in the `<script>`
  block near the bottom of the file) to the `Leaderboard` tab's values from step 1.4 — the tutorial
  page only ever reads `Leaderboard`, never `Submissions`.

## 4. The receptor/pocket files are already committed

`receptor_2ito.pdb`, `receptor_2ito.pdbqt`, and `pocket.json` in this folder were generated once
(by running the notebook's own section-(a) PDB-fetch-and-parse code and saving its output) and are
already checked in — `score_submissions.py` reads them directly, no regeneration needed. If EGFR/
`2ITO` is ever swapped for a different target, regenerate these three files the same way and
re-commit them.

## 5. Run the grading script during class

```bash
conda install -y -c conda-forge smina openbabel      # if not already installed
pip install rdkit requests
python score_submissions.py
```

Re-run it every few minutes during the session (a simple loop or a calendar reminder is enough —
there's no need for anything fancier for a single class). Each run only dockes submissions it
hasn't scored yet, so re-running it often is cheap and safe.

## Troubleshooting

- **A submission never appears on the leaderboard.** First check `score_submissions.py`'s own
  console output — it logs every submission it skips (invalid SMILES, embedding failure, smina
  crash/timeout) and every POST response. If it's not running at all, re-check "Who has access:
  Anyone" in the Apps Script deployment settings.
- **`score_submissions.py` can't find `smina`.** Make sure you're running it from the same
  conda env you installed `smina`/`openbabel` into (`conda activate <env>` first).
- **The tutorial page shows "leaderboard not configured yet."** `LEADERBOARD_SHEET_ID` /
  `LEADERBOARD_GID` in `generative-vae.html` still have placeholder values, or the `Leaderboard`
  tab isn't published yet (step 1.3).
- **The 3D viewer on the tutorial page stays empty.** It only renders once `Leaderboard` has at
  least one graded row with a non-empty `pose_sdf` — check that `score_submissions.py` is actually
  reaching the `record_score` POST for at least one submission.
