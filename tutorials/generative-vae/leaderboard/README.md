# Molecular Generation Tutorial — Leaderboard Setup

This folder defines the externally-graded submission pipeline for the docking-optimization
leaderboard challenge in `generative-vae.ipynb`. It diverges from the pattern used by
`tutorials/few-shot-learning/leaderboard/` in one structural way: **students never self-report a
score.** They submit a single SMILES; an instructor-run script does the real, accurate docking run
and writes the graded result. This keeps every team's score directly comparable, since nobody can
report a lucky number from an under-powered exploratory docking run.

## Two Google Sheet tabs, not one

- **`Submissions`** (raw, ungraded) — header row = `submissions_schema.csv`. The notebook's
  challenge cell POSTs here (`action: "submit"`).
- **`Leaderboard`** (graded) — header row = `results_schema.csv`, including `pose_sdf` (the docked
  pose's SDF text, a few KB — comfortably under a Sheets cell's ~50,000-character limit) so the
  tutorial page's 3D viewer can render the current best candidate with no separate file hosting.
  Populated by `score_submissions.py` (`action: "record_score"`). The tutorial page's live
  leaderboard widget only ever reads this tab.

## Files

- `submissions_schema.csv` / `results_schema.csv` — canonical column headers for each tab.
- `submission_payload.example.json` / `record_score_payload.example.json` — example payloads for
  each `action`.
- `apps_script.gs` — Google Apps Script Web App: dispatches on the `action` field, appending to
  whichever tab that action targets. Same "execute as Me, access Anyone" trust model as
  `few-shot-learning`'s endpoint — no auth distinction between a student's submission and the
  instructor's grading script.
- `score_submissions.py` — **run periodically by the instructor during class** (every few minutes,
  or manually between sessions). Reads pending `Submissions` rows, docks each SMILES for real
  (`smina`, `exhaustiveness=8, num_modes=10` — the docking tutorial's own demo defaults, not the
  notebook's cheap exploration settings), computes QED and a PAINS+BRENK structural-alert count,
  and POSTs the graded row.
- `receptor_2ito.pdb` / `receptor_2ito.pdbqt` / `pocket.json` — **committed, pre-prepared receptor
  and pocket definition**, generated once so `score_submissions.py` and the tutorial page's 3D
  viewer always use an identical, reproducible target. (The student notebook still fetches and
  derives its own copy fresh from RCSB in its own Exercise 1 — this committed copy is only for the
  external-grading and website-visualization paths, and is numerically identical since the parsing
  is deterministic over the same fixed PDB.)
- `SETUP.md` — click-by-click deployment steps.

## Fixed target, not a fixed split

There's no held-out dataset here (unlike `few-shot-learning`) — every submission is scored fresh
against the same fixed protein pocket (EGFR, PDB `2ITO`) with the same docking settings, so
"fairness" comes from using one shared, committed receptor and one shared docking configuration for
everyone's grading run, not from a published test split.

## Policy

1. Students may resubmit as many candidate SMILES as they like; the tutorial page's widget keeps
   each team's best (lowest) `best_affinity_kcal_mol`.
2. `qed` and `toxicity_alerts` are shown alongside the affinity so a molecule that "wins" purely on
   docking score isn't mistaken for an unambiguously good candidate — see the notebook's multi-objective
   bonus section.
3. Submissions the instructor's script can't score (invalid SMILES, embedding failure, smina
   crash/timeout) are skipped and logged to the console; they never appear on the graded leaderboard.
