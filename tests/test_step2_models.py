"""Step 2 model grid, feature groups, and the forecast API (synthetic data only)."""

import json

import numpy as np
import pandas as pd
import pytest

from mealguide import paths, synthetic
from mealguide.guidance.forecast import Forecast, triggers
from mealguide.models import step2
from mealguide.models.baselines import person_base_rate
from mealguide.models.configs import (
    LH_PHASE,
    NO_CGM_CONFIGS,
    calendar_phase_at,
    config_features,
)
from mealguide.models.harness import evaluate, within_person_auroc
from mealguide.phases.calendar import calendar_phases


@pytest.fixture(scope="module")
def synthetic_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("step2")
    mp = pytest.MonkeyPatch()
    mp.setattr(paths, "SYNTHETIC", root / "synthetic")
    mp.setattr(paths, "RESULTS", root / "results")
    paths.SYNTHETIC.mkdir()
    for name, df in synthetic.generate(n_participants=4, n_days=45).items():
        df.to_csv(paths.SYNTHETIC / f"{name}.csv", index=False)
    yield root
    mp.undo()


def test_calendar_projection_matches_avas_rule():
    daily = synthetic.generate(n_participants=6, n_days=90)["daily_master_labeled"]
    cal = calendar_phases(daily)
    assert (cal["calendar_phase"] != "Unknown").any()
    same_day = calendar_phase_at(cal["calendar_day"], cal["calendar_cycle_length"])
    pd.testing.assert_series_equal(same_day, cal["calendar_phase"], check_names=False)


def test_calendar_projection_edges():
    day = pd.Series([1.0, 5, 6, 14, 15, 28, 29, np.nan, 3])
    length = pd.Series([28.0] * 8 + [np.nan])
    assert calendar_phase_at(day, length).tolist() == [
        "Menstrual", "Menstrual", "Follicular", "Fertility", "Luteal", "Luteal",
        "Unknown", "Unknown", "Unknown"]


def test_fixed_prior_base_rate_ignores_other_participants():
    df = pd.DataFrame({"id": np.repeat([1, 2], 10), "study_interval": 2022,
                       "day_in_study": np.tile(np.arange(1, 11), 2),
                       "y": np.r_[np.ones(10), np.zeros(10)]})
    a = person_base_rate(df, "y", prior=0.5)
    b = person_base_rate(df.assign(y=np.r_[np.ones(10), np.ones(10)]), "y", prior=0.5)
    pd.testing.assert_series_equal(a[df["id"] == 1], b[df["id"] == 1])
    assert a.iloc[0] == 0.5  # nothing known yet: the prior


def test_within_person_auroc_ignores_between_person_offsets():
    # Each person's score ranks their own days perfectly, but person 2's scores sit below
    # person 1's while person 2 has more positive days: pooled AUROC suffers, within doesn't.
    y = np.array([0, 1, 0, 1, 1, 1])
    score = np.array([0.8, 0.9, 0.1, 0.2, 0.3, 0.4])
    groups = np.array([1, 1, 2, 2, 2, 2])
    assert within_person_auroc(y, score, groups).tolist() == [1.0, 1.0]
    res = evaluate(pd.DataFrame({"id": groups, "y": y, "s": score}), "y", "s", n_boot=50)
    assert res["auroc_within"] == 1.0 and res["auroc"] < 0.8
    assert res["n_within"] == 2 and 0 <= res["brier"] <= 1


def test_config_features():
    assert "fatigue_score" in config_features("fatigue_high", "watch")
    assert "fatigue_high_past_rate" in config_features("fatigue_high", "history")
    glucose = config_features("high_cv", "watch+phase+glucose")
    assert not any(f.endswith("_past_rate") or f.endswith("_score") for f in glucose)
    for config in NO_CGM_CONFIGS:  # hormone phase is never deployable
        assert not set(LH_PHASE) & set(config_features("cramps_high", config))
    with pytest.raises(ValueError):
        config_features("high_cv", "history")
    with pytest.raises(ValueError):
        config_features("high_cv", "phase")


def test_grid_headline_and_forecast_api(synthetic_dir):
    grid = step2.run_models(synthetic=True, n_boot=30)
    # 5 targets x 2 baselines + 2 models x (4 configs, or 3 for glucose: no history)
    assert len(grid) == 5 * 2 + 2 * (4 * 4 + 3)
    assert grid.loc[grid["model"] != "baseline", "auroc"].notna().all()
    for name in ("step2_models", "step2_thresholds", "step2_phase_comparison"):
        assert (paths.RESULTS / f"{name}_synthetic.csv").exists()
    headline = json.loads((paths.RESULTS / "step2_headline_synthetic.json").read_text())
    assert headline["symptom_config"] in NO_CGM_CONFIGS

    from mealguide.models.forecast_api import Forecaster
    f = Forecaster(synthetic=True)
    fc = f.forecast("2", 20)
    assert isinstance(fc, Forecast) and fc.person == "2" and fc.day == 20
    assert {"fatigue", "cramps", "bloating", "cravings"} <= set(fc.risks)
    assert all(0 <= p <= 1 for p in fc.risks.values())
    assert {exclude for _, exclude in f._models} == {2}  # trained without person 2
    triggers(fc)  # Step 3 accepts it

    # No valid CGM the day before -> no glucose risk, rather than a guess
    f.rows.loc[(2, 19), "glucose_cv"] = np.nan
    assert "unstable_glucose" not in f.forecast(2, 20).risks
    with pytest.raises(KeyError):
        f.forecast(2, 999)


def test_shap_for_headline(synthetic_dir):
    if not (paths.RESULTS / "step2_headline_synthetic.json").exists():
        step2.run_models(synthetic=True, n_boot=10)
    out = step2.run_shap(synthetic=True)
    assert set(out["target"]) == {"high_cv", "fatigue_high", "cramps_high", "bloating_high",
                                  "cravings_high"}
    assert (out["mean_abs_shap"] >= 0).all()
    assert (paths.RESULTS / "figures" / "step2_shap_synthetic.png").exists()
