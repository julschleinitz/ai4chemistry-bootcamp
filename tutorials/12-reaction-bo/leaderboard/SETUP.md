# Leaderboard setup (one-time, before the bootcamp)

Everything below is done once, under your own Google account. Same pattern already used for
`tutorials/06-pretraining_finetuning/leaderboard/` — a Google Sheet plus an Apps Script Web App, no
Drive folder, no file parsing, and no held-out split to freeze (the fixed setup here is instead "same
4 datasets + same batch size of 4 for everyone", see `README.md`'s policy section).

## 1. Publish the datasets

The 4 dataset CSVs already live at `tutorials/12-reaction-bo/data/*.csv` and ship with the repo — no
separate freezing step is needed. Just make sure they're committed before class so every student's
notebook loads the exact same tables.

## 2. Create the master Google Sheet

1. Create a new Google Sheet, e.g. `AI4Chem Reaction BO Leaderboard`.
2. Create one tab named exactly `Leaderboard`.
3. Row 1 (header), matching `results_schema.csv`:
   `run_id | timestamp_utc | team_name | dataset | featurization | init_method | acquisition | acquisition_hparams | batch_size | n_rounds | n_seeds | auc_mean | auc_std | max_score_achieved | notebook_version | notes`
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
   `{"status":"ok","message":"Reaction BO leaderboard endpoint is live."}`.

## 4. Point the notebook and the tutorial page at your setup

- In `reaction-bo.ipynb`, set `LEADERBOARD_ENDPOINT_URL` (Section 8) to the Web App URL from step 3.
- In `reaction-bo.html`, set `LEADERBOARD_SHEET_ID` and `LEADERBOARD_GID` (in the `<script>` block
  near the bottom of the file) to the values from step 2.5.
- Tell students their `team_name` should stay consistent across resubmissions so the leaderboard can
  track their best score per dataset, and that they should pick a `dataset` at the top of the
  notebook (Section 1) before running the full pipeline.

### Status — already configured

Done for this bootcamp run, using the **published-to-web CSV export** variant instead of the gviz
feed (see note below):

- Sheet published at gid `0`, published-ID
  `2PACX-1vQzA7UlegUw-ptH_qPCxaay1bMT_QmAeHm-tu0kxBgKtUo_B1Tx6GTw586rY5jsablWqUtuf9YK5TYj`
  (`reaction-bo.html`'s `LEADERBOARD_PUBLISHED_ID` / `LEADERBOARD_GID`).
- Apps Script Web App deployed at
  `https://script.google.com/macros/s/AKfycbxe3TVsK8wRr1byTKPhw3JCgEp3VISUXxk3MBLI0AJasYt_aG_LQyHjgQuvuRxKLdlq/exec`
  (`reaction-bo.ipynb`'s `LEADERBOARD_ENDPOINT_URL`, Section 8).

**Note on the fetch method — diverges from the other tutorials' leaderboards.** Other tutorials in
this repo (`06-pretraining_finetuning`, `08-molecule-generation`) read the sheet via the gviz JSON
feed (`.../d/<SPREADSHEET_ID>/gviz/tq?...`), which needs the *normal* spreadsheet ID from the Sheet's
own edit URL. What "Publish to web" hands you instead is a different, longer ID in the form
`docs.google.com/spreadsheets/d/e/<PUBLISHED_ID>/pubhtml?gid=...` — that `<PUBLISHED_ID>` is **not**
interchangeable with the gviz-flavored spreadsheet ID. Rather than asking for the other ID, this
tutorial's widget was written against the CSV-export sibling of that same published link
(`.../d/e/<PUBLISHED_ID>/pub?gid=...&output=csv`), which works with exactly the URL "Publish to web"
gives you, no extra digging required. If you ever re-point this at a fresh Sheet, just grab the
published-ID/gid pair the same way (from the "Publish to web" dialog, not from the normal Share
link) and drop them into `reaction-bo.html`.

### Verify it end-to-end

1. Open the CSV URL directly in a browser:
   `https://docs.google.com/spreadsheets/d/e/2PACX-1vQzA7UlegUw-ptH_qPCxaay1bMT_QmAeHm-tu0kxBgKtUo_B1Tx6GTw586rY5jsablWqUtuf9YK5TYj/pub?gid=0&single=true&output=csv`
   — you should get a CSV download/text response with the `results_schema.csv` header row (or just
   the header row if no submissions yet). If you instead get an HTML sign-in page, the sheet is not
   actually published yet (redo step 2.4).
2. Open `https://script.google.com/macros/s/AKfycbxe3TVsK8wRr1byTKPhw3JCgEp3VISUXxk3MBLI0AJasYt_aG_LQyHjgQuvuRxKLdlq/exec`
   directly — should return `{"status":"ok","message":"Reaction BO leaderboard endpoint is live."}`.
   If it prompts for Google sign-in or shows a permissions error, redo step 3 and double check
   "Who has access: Anyone" (not "Anyone with Google account").
3. Run `submit_payload.py`'s `__main__` demo block (or the notebook's Section 8 submit cell) once
   and confirm a new row appears in the Sheet's `Leaderboard` tab within a few seconds, then confirm
   it shows up on `reaction-bo.html`'s live leaderboard widget after a refresh.

## Troubleshooting

- **POST from the notebook fails / times out.** Re-check "Who has access: Anyone" in the deployment
  settings — "Anyone with Google account" will reject students who aren't signed in inside Colab.
- **A submission never appears on the leaderboard.** Open Apps Script → Executions to see the error
  log for `doPost`. The most common cause is a payload missing one of the required
  `results_schema.csv` columns.
- **The tutorial page shows "leaderboard not configured yet."** `LEADERBOARD_SHEET_ID` /
  `LEADERBOARD_GID` in `reaction-bo.html` still have their placeholder values — fill them in from
  step 2.5, and make sure the sheet is actually published (step 2.4).
- **Two datasets look "mixed together" on the page.** Make sure the tutorial page's widget is
  grouping/filtering by `dataset` before sorting by `auc_mean` — see the dataset dropdown described
  in `reaction-bo.html`'s leaderboard section.
