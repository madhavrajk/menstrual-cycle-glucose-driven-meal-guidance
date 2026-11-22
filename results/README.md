# results/

Aggregate outputs only: metric tables, figures, and per-target counts. Anything with
participant-day rows goes in `results/private/`, which is gitignored.

- `baselines_synthetic.csv`: persistence and base-rate baselines on synthetic data (`make baselines SYNTHETIC=1`)
- `baselines_real.csv`: the same on real Interval 1 data (`make baselines`)
- `step2_models_<source>.csv`: every target x model (LR, LightGBM) x config, plus both baselines: pooled and within-person AUROC with CIs, AUPRC, Brier (`make model`)
- `step2_phase_comparison_<source>.csv`: calendar vs hormone-confirmed (LH) phase on forecast days with an LH label
- `step2_thresholds_<source>.csv`: how often each risk threshold fires for the headline model, and how often it's right
- `step2_headline_<source>.json`: the headline model the rule picked; `get_forecast` reads it
- `step2_shap_<source>.csv`, `figures/step2_shap_<source>.png`: mean |SHAP| per feature for the headline model (`make shap`)
