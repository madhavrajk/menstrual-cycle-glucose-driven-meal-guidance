# How we work

## Branches and PRs

- `main` is always runnable: `make test` and `make baselines SYNTHETIC=1` pass, and CI checks both.
- Branch per task, named `<name>/<topic>`, e.g. `ava/calendar-phase`, `madhav/cgm-metrics`, `sneha/recipes-batch2`.
- Open a PR into `main`. One teammate skims it, mostly for the data checkbox, then you merge. Squash-merge keeps history readable.
- Small, frequent PRs beat one big one on the Wednesday before review.

## Data safety (the only hard rules)

- No CSVs, zips, parquet, or pickles in git. The pre-commit hook blocks them. Aggregate tables in `results/` are allowed.
- Notebook outputs are stripped on commit. Don't paste participant rows into docs, issues, PRs, or chat.
- Screenshots of plots are fine if they show aggregates or synthetic data.

## Hand-offs between steps

| From → To | Artifact | Key |
|---|---|---|
| Ava → Madhav | `data/processed/daily_master_labeled.csv` (via `make step1`) | `id, study_interval, day_in_study` |
| Madhav → Ava | `data/processed/cgm_daily.csv` (via `make cgm`) | same |
| Madhav → Sneha | forecast scores per participant-day (Week 7: `get_forecast(id, day)`) | same |
| Sneha → Madhav/Ava | `knowledge/` + `mealguide.guidance` API | n/a |

Everyone generates processed files locally from their own raw copy. We share code, never files.

## Weekly cadence

- Each week's plan lives in `Weekly Plan/weekNN_<dates>.md`. Check off tasks there in your PRs.
- Monday: async update (done / blocked). Wednesday: 30-minute review.
- Decisions go in `docs/decisions.md` with the date.
