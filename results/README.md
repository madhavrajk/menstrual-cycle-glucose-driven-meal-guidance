# results/

Aggregate outputs only: metric tables, figures, and per-target counts. Anything with
participant-day rows goes in `results/private/`, which is gitignored.

- `baselines_synthetic.csv`: persistence and base-rate baselines on synthetic data (`make baselines SYNTHETIC=1`)
- `baselines_real.csv`: the same on real Interval 1 data (`make baselines`)
