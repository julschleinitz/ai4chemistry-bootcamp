# Start here

Everything for today is in the shared Drive folder **OpenADMET Hackathon!**.

## One-time setup, takes a minute

1. Open the shared folder link you were given.
1. Open `Notebooks/00_start_here.ipynb`.
1. **File &rarr; Save a copy in Drive.** The shared copy is read-only, so if you
   skip this you will lose your work when the tab closes.
1. Work in *your* copy. Do the same for every notebook you open.

## Then

Change `CHANGE-ME` in the first cell to your pair name and run it. Use the same
pair name in every notebook &mdash; that is what links your work together, so
your split and your saved models follow you from one notebook to the next.

Read `README.md` for the plan for the day and `REPORT_TEMPLATE.md` for what you
are presenting at the end. Read the report template early; it tells you what to
write down as you go.

## What is in the folder

```
Notebooks/   the seven notebooks -- start with 00, then 01 and 02, then pick
Data/        the training set and the blinded test set
Setup/       common.py, the shared helper module (you never edit this)
Artifacts/   precomputed descriptors, so you are not waiting on your laptop
```

## If the first cell fails

- *"Could not find common.py"* &rarr; you skipped a setup step above.
- Anything else &rarr; Runtime &rarr; Restart session, then re-run from the top.
  After a restart you have to run the cells above the one you were on.
