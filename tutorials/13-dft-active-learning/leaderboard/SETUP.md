# Leaderboard setup (one-time, before the bootcamp)

Same pattern as `tutorials/12-reaction-bo/leaderboard/` — a Google Sheet plus an Apps Script Web
App — with one addition: this tutorial also has a **hidden test set**, so there is a second,
instructor-computed board. Steps 1–4 set up the live board; step 5 is the final one.

---

## 1. Build and commit the data bundle

```bash
cd tutorials/13-dft-active-learning/instructor
./run_all.sh smoke     # 300 molecules, ~2 min -- proves the path works
./run_all.sh full      # all 8,528, ~15 min, almost all of it API paging
```

This fetches the published DFT descriptors from the MolSSI API and writes:

- `../data/student/` — pool, dev, sealed pool labels, `targets.json`, `published_benchmark.csv`
- `../data/instructor/` — `test_hidden.csv`, `splits.json`, `target_scales.csv`

Commit **`data/student/` only**:

```bash
cd ..
git add data/student && git commit -m "tutorial 13: student bundle"
```

**Do not commit `data/instructor/`.** It contains the hidden test labels. The repo's `.gitignore`
excludes it; verify with `git status` before pushing.

The notebook downloads `data/student/` from raw.githubusercontent.com at runtime, so the bundle
must be on `main` before class. ~10 MB total.

## 2. Create the master Google Sheet

1. New Google Sheet, e.g. `AI4Chem DFT Active Learning Leaderboard`.
2. One tab named exactly `Leaderboard`.
3. Row 1 (header), matching `results_schema.csv`:
   `run_id | timestamp_utc | team_name | head | ensemble_size | seed_method | acquisition | n_seed | n_rounds | batch_size | labels_used | dev_smae | dev_ence | dev_combined | dev_aulc | dev_spearman | cpu_hours_bought | notebook_version | notes`
4. **Publish the tab to the web:** File → Share → Publish to web → select `Leaderboard`,
   format **Comma-separated values (.csv)** → Publish. This is what lets the tutorial page read it
   with no server and no API key.
5. From the link Google gives you *after* publishing, copy the **published id** — the long
   `2PACX-1v...` string:

   ```
   https://docs.google.com/spreadsheets/d/e/2PACX-1vQzA7Uleg.../pubhtml?gid=0&single=true
                                            ^^^^^^^^^^^^^^^^^^^ this
   ```

   Also note the tab's **gid** (visible as `#gid=123456` when the tab is open; usually `0`).

   > **This is not the spreadsheet id.** The id in the normal `/d/<id>/edit` URL is a different
   > string and the widget will not work with it — the widget reads
   > `/spreadsheets/d/e/<PUBLISHED_ID>/pub`, which only exists once you have published.

## 3. Deploy the Apps Script Web App

1. In the Sheet: Extensions → Apps Script.
2. Delete the boilerplate and paste in `apps_script.gs`.
3. Deploy → New deployment → gear → **Web app**. Execute as **Me**; access **Anyone**.
4. Deploy, authorise, copy the **Web app URL** (`https://script.google.com/macros/s/AKfycb.../exec`).
5. Sanity check: open that URL in a browser. You should see
   `{"status":"ok","message":"DFT active learning leaderboard endpoint is live."}`

## 4. Point the notebook and the page at your setup

Three files need the values, and two of them are notebook JSON, so use the helper rather than
editing by hand. From the tutorial folder:

```bash
python tools/configure_leaderboard.py \
    --endpoint     'https://script.google.com/macros/s/AKfycb.../exec' \
    --published-id '2PACX-1vQzA7Uleg...'
```

That sets `LEADERBOARD_ENDPOINT_URL` in **both** notebooks and `LEADERBOARD_PUBLISHED_ID` +
`LEADERBOARD_GID` in `../dft-active-learning.html`, then re-parses the notebooks to prove it did
not corrupt them. Add `--gid N` if your tab is not gid 0.

It refuses obviously-wrong input — a Sheet URL where the Web App URL belongs, a `/dev` deployment
URL that only works for you, or the spreadsheet id where the published id belongs. `--force`
overrides if you are sure.

Check the current state at any time, and undo before publishing the repo if you prefer:

```bash
python tools/configure_leaderboard.py --check
python tools/configure_leaderboard.py --reset
```

Until configured, everything still works: the notebook's submit cell prints the payload, writes
`leaderboard_submission.json` and skips the POST, and the page's widget shows "leaderboard not
configured yet" instead of an error. That is deliberate — the tutorial is fully usable without the
Sheet.

### Verify end to end

1. Run the notebook through section (e) and check it prints `posted`.
2. Open the Sheet — one new row on the `Leaderboard` tab.
3. Open the tutorial page, hit **Refresh** — your team should appear.

If step 2 works but step 3 does not, the Apps Script side is fine and the problem is publishing:
re-check step 2.4 and that you used the `2PACX-...` id.

Tell students to keep `team_name` consistent across resubmissions; the widget keeps each team's best
`dev_combined`.

## 5. Create the Drive folder for checkpoints, and score it afterwards

The live board carries only self-reported dev numbers. The real ranking needs the actual models.

1. Create a shared Drive folder: `AI4Chem Bootcamp 2026 / lecture_13_tutorial / submissions/`.
   Give students **edit** access (they upload a zip each).
2. The notebook's last cell copies their zip there automatically when run in Colab.
3. After the session, sync it locally and run:

```bash
cd tutorials/13-dft-active-learning/leaderboard
python score_submissions.py \
    --submissions ~/Drive/AI4Chem/lecture_13_tutorial/submissions \
    --audit
```

That writes `../data/instructor/leaderboard.md`. Commit **that file** (it contains only scores, no
labels) and link it from the tutorial page's leaderboard section.

---

## Checklist before class

- [ ] `data/student/` committed and pushed to `main`
- [ ] `data/instructor/` **not** committed (`git status` clean)
- [ ] Sheet created, `Leaderboard` tab published to web
- [ ] Apps Script deployed; health-check URL returns `status: ok`
- [ ] `python tools/configure_leaderboard.py --check` reports **fully configured**
- [ ] one test row posted from the notebook and visible on the tutorial page
- [ ] Drive submissions folder created, edit access granted
- [ ] `python tests/test_logic.py` passes (96 checks)
- [ ] Opened the Colab link yourself and run the setup cell end to end
