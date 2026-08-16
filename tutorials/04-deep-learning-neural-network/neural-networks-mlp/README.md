# Neural Networks Tutorial Data Artifacts

This folder contains protocol artifacts for the tutorial aligned with the
"Neural Networks and Deep Learning" lesson.

## Purpose

- Make the train/validation/test split fixed in advance.
- Keep held-out test evaluation consistent across all students.
- Standardize submission rows for Pareto-front analysis.

## Folder layout

- `splits/`: fixed split files used by notebooks.
- `leaderboard/`: schema and payload templates for final run submission.

## Fixed split policy

1. Instructors publish one set of split files before class.
2. Students must not generate new random splits.
3. Hyperparameter tuning uses only train + validation.
4. Held-out test is used only for final model evaluation.

## Required split file format

Each split CSV contains one column named `sample_id`.

Example:

sample_id
mol_000001
mol_000002

## Submission policy

- Submit only final runs to the leaderboard endpoint/sheet.
- Include model complexity and training cost fields for Pareto plotting.
- Keep `test_score` tied to the fixed split only.
