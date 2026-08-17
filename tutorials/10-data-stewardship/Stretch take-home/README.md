# Stretch — build an automated cleaning pipeline

**If you already have the base tutorial working**, or as take-home.

## Why this exists

Yesterday you spent 30 minutes cleaning a messy reactions log by hand. Next week your PI hands you another log in the same format from a different lab. Do you want to spend another 30 minutes?

The DS lecture Arc 3 argued that code + data + docs is a triad. A one-off cleaning script that lives in a notebook is a start. A **reusable pipeline** — with function signatures, tests, and a second dataset you can generalize to — is the mature version.

## What to do

1. Open `pipeline_starter.py`. Each function has a docstring and a `TODO`. Fill them in.
2. Run `pytest test_pipeline.py` from this folder. The first six tests check individual helpers. The final two run the whole pipeline against **two** messy datasets — the one from the tutorial and a second one you haven't seen (`new-experiments-messy.xlsx`).
3. If both end-to-end tests pass, your pipeline is genuinely general.

## The point

If you can hand someone `pipeline_starter.py` + the tidy reference CSVs and they can clean *any* log in this format without you sitting next to them — you've built a real institutional asset. That is the DS takeaway made concrete.
