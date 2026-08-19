# DFT Active Learning — leaderboard

This tutorial has **two boards**, and the difference between them is the closing lesson.

| board | what it ranks | who computes it | when |
|---|---|---|---|
| **Live board** (on the tutorial page) | self-reported score on the **public dev set** | the student, in the notebook | during the session |
| **Final board** (`leaderboard.md`) | score on the **hidden, scaffold-disjoint test set** | you, via `score_submissions.py` | after the session |

Students cannot compute the second one — they never see the test SMILES. So the live board exists
for pacing and competitive energy during the 90 minutes, and the final board is the result.

**Say this out loud when you show the live board.** Teams will reorder between the two, sometimes
dramatically, because dev and test are different scaffold draws and a team that over-tuned on dev
will fall. That reordering is worth five minutes of discussion and it is the honest version of
"does your model generalise".

---

## Files

- `results_schema.csv` — canonical live-board columns, one row per submitted run.
- `submit_payload.py` — `validate_payload`, `build_payload`, `write_payload_json`,
  `append_payload_csv`, `submit_payload`. `build_payload` reads a finished `LoopResult` directly,
  so the only field a student types is the team name.
- `apps_script.gs` — Google Apps Script Web App: accepts a JSON POST and appends a row.
- `submission_payload.example.json` — regenerate with `python submit_payload.py`.
- `SETUP.md` — click-by-click deployment.
- `score_submissions.py` — **the authoritative scorer.** Walks the Drive folder of uploaded zips,
  runs each `predict.py` in a subprocess against `data/instructor/test_hidden.csv`, and writes
  `data/instructor/leaderboard.md` and `.csv`.

The 19 columns are defined in three places (`results_schema.csv`, `submit_payload.REQUIRED_FIELDS`,
and `COLUMNS` in `apps_script.gs`). They must stay identical; there is a consistency check in the
`__main__` block of `submit_payload.py`.

---

## Fixed setup policy

Everyone gets the same pool, the same dev set, the same hidden test set, and the same budget:

1. **600 labels.** 100 seed + 10 rounds × 50. Enforced in the notebook by `al_toolkit.Oracle`,
   which refuses to exceed it and writes an append-only `al_log.jsonl`.
2. **The same splits**, produced once by `instructor/02_make_splits.py` with `--seed 20260819` and
   committed to `data/`. Students must not regenerate them.
3. **The same target list and order**, pinned in `data/student/targets.json`. A permuted target
   order is a disqualification, and `validate_submission.py` catches it before upload — this
   matters more than usual here, because the buried-volume column names contain the substrings
   `min` and `max`, so a stray `sorted()` silently scrambles them.
4. **`predict.py` unmodified**, SHA-256 checked on both sides.

Students *are* free to choose the model, the seed-selection method, and the acquisition function.
Those choices are exactly what the boards are meant to compare, which is why they are columns.

## Resubmission

Students may submit as many runs as they like — trying three acquisition functions is the point of
section (d). The page's widget keeps each team's **best `dev_combined` per team**. For the final
board they upload **one** zip; re-uploading replaces it.

## Trust model, stated plainly

The live board is honour-system. The final board is not:

- the budget is read from the submitted `al_log.jsonl`, not from what the student claims;
- `predict.py` is hash-checked;
- `--audit` evaluates each model on 500 pool molecules **absent from that team's log**. If a model
  fits those as well as it fits its own logged training molecules, it has probably seen more data
  than the log admits. That is a prompt for a conversation, not an automatic verdict — a
  well-regularised model with a good acquisition strategy can legitimately generalise inside the
  pool.

The sealed `pool_labels.enc` is a speed bump, not a lock, and the notebook says so. Tell the room
at the start rather than at the leaderboard.

---

## Running the final board

```bash
cd tutorials/13-dft-active-learning/leaderboard
python score_submissions.py \
    --submissions ~/Drive/AI4Chem/lecture_13_tutorial/submissions \
    --audit
```

Writes `../data/instructor/leaderboard.md` and `.csv`. Ranked on
`combined = mean_sMAE + mean_ENCE` (lower is better), with per-family sMAE and ENCE tables and a
`MAE_over_published` column comparing against the paper's own GNN.

`--family-balanced` ranks on the family-averaged score instead, if you would rather buried volume
(31% of the targets even after trimming) not dominate.
