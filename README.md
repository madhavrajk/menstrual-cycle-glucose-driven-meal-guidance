# Sensing-Driven Meal Guidance Across the Menstrual Cycle

COMS 6998 Mobile Health, Fall 2026 · Ava Ferrentino, Madhav Rajkondawar, Sneha Bapana

The project forecasts next-day symptoms and glucose instability from consumer wearables, then
turns those forecasts into personalized, evidence-grounded meal guidance. It uses the
[mcPHASES](https://physionet.org/content/mcphases/1.0.0/) dataset (PhysioNet, restricted access).

| Step | Question | Owner | Code |
|---|---|---|---|
| 1. Phase alignment | Does glucose vary by LH-anchored phase? | Ava | `scripts/step1_data/`, `src/mealguide/phases/` |
| 2. Next-day forecasting | RQ1/RQ2: can a watch (+ phase, + glucose) forecast symptoms and high-variability glucose days? | Madhav | `src/mealguide/{cgm,features,models}/` |
| 3. Meal guidance | RQ3: is a grounded LLM safer and more accurate than an ungrounded one? | Sneha | `src/mealguide/guidance/`, `knowledge/` |

Plans: [docs/Weekly Plan/ROADMAP.md](docs/Weekly%20Plan/ROADMAP.md) · Decisions: [docs/decisions.md](docs/decisions.md) · How we work: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

## Data rules (PhysioNet data use agreement)

1. Each person signs the agreement and downloads their own copy. Never share files, links, or access.
2. Never commit participant data. `data/` is gitignored, and a pre-commit hook blocks data files.
3. Keep the raw zip **outside OneDrive** (set `MCPHASES_HOME` in `.env`). Anything inside this folder syncs to the cloud.
4. No real participant rows go to a hosted LLM until the LLM setup in `docs/decisions.md` is approved.
5. Public demos use `data/synthetic/` only.

## Setup

```bash
python3.12 -m venv ~/.venvs/meal-guidance      # outside OneDrive
source ~/.venvs/meal-guidance/bin/activate
make setup                                     # pinned deps + editable install + pre-commit hook
cp .env.example .env                           # then set MCPHASES_HOME
mkdir -p ~/mcphases/data/raw                   # put the mcPHASES zip here
```

## Run

```bash
make test                     # unit + leakage tests
make baselines SYNTHETIC=1    # whole Step 2 pipeline on fake data (no access needed)

make step1                    # Ava's pipeline: zip -> daily_master_labeled.csv
make baselines                # CGM metrics + Fitbit features + baselines on real Interval 1 data
```

`make baselines` prints AUROC/AUPRC for the persistence and per-person base-rate baselines,
for next-day high-CV glucose and each symptom, with 95% participant-bootstrap CIs. It also
writes `results/baselines_real.csv`.

## Layout

```
docs/Weekly Plan/     weekly plans + ROADMAP
docs/                 decisions, contributing, data dictionary, Step 1 notes
scripts/step1_data/   Ava's Step 1 scripts (run via `make step1`)
src/mealguide/
  data/               zip/synthetic loaders
  phases/             cycle phase labels (Ava)
  cgm/                daily CGM metrics, targets (Madhav)
  features/           Fitbit daily features, past-only baselines (Madhav)
  models/             LOSO harness, baselines, models (Madhav)
  guidance/           nutrition, portions, retrieval, LLM, checks (Sneha)
  synthetic.py        fake cohort generator
  pipeline.py         Step 2 CLI
knowledge/            recipes + evidence cards (Sneha)
notebooks/  app/  results/  tests/
```
