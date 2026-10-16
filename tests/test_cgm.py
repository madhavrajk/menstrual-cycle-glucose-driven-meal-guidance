import numpy as np
import pandas as pd
import pytest

from mealguide.cgm.daily_metrics import daily_cgm_metrics, mage
from mealguide.cgm.targets import add_next_day, label_high_cv


def test_mage_hand_computed():
    # Every point is a turning point. Amplitudes: 40, 40, 5, 5, 50, 60. SD ~ 23.07,
    # so the excursions that count are 40, 40, 50, 60 -> mean 47.5.
    assert mage(np.array([100, 140, 100, 105, 100, 150, 90])) == pytest.approx(47.5)


def test_mage_collapses_plateaus():
    assert mage(np.array([100, 100, 150, 150, 100])) == pytest.approx(50.0)


def _day(pid, day, values, interval=2022):
    t = [f"{(5 * i) // 60:02d}:{(5 * i) % 60:02d}:00" for i in range(len(values))]
    return pd.DataFrame({"id": pid, "study_interval": interval, "day_in_study": day,
                         "timestamp": t, "glucose_value": values})


def test_daily_metrics_values_and_coverage():
    full = _day(1, 1, [100.0] * 144 + [160.0] * 144)
    sparse = _day(1, 2, [100.0] * 100)
    other_interval = _day(1, 905, [100.0] * 288, interval=2024)
    m = daily_cgm_metrics(pd.concat([full, sparse, other_interval])).set_index("day_in_study")

    assert list(m.index) == [1, 2]  # Interval 2 dropped
    assert m.loc[1, "glucose_mean"] == pytest.approx(130)
    assert m.loc[1, "tir_70_180"] == pytest.approx(100)
    assert m.loc[1, "tir_70_140"] == pytest.approx(50)
    assert m.loc[1, "glucose_cv"] == pytest.approx(100 * m.loc[1, "glucose_sd"] / 130)
    assert bool(m.loc[1, "cgm_valid"]) and not bool(m.loc[2, "cgm_valid"])


def test_high_cv_is_top_third_of_own_days():
    cv = np.arange(1, 13, dtype=float)  # 12 valid days, CV 1..12
    df = pd.DataFrame({"id": 1, "study_interval": 2022, "day_in_study": range(1, 13),
                       "glucose_cv": cv, "cgm_valid": True})
    labeled = label_high_cv(df)
    assert labeled["high_cv"].sum() == 4  # days with CV >= 2/3 quantile


def test_high_cv_needs_enough_days():
    df = pd.DataFrame({"id": 1, "study_interval": 2022, "day_in_study": range(1, 6),
                       "glucose_cv": [1.0, 2, 3, 4, 5], "cgm_valid": True})
    assert label_high_cv(df)["high_cv"].isna().all()


def test_next_day_respects_gaps():
    df = pd.DataFrame({"id": 1, "study_interval": 2022, "day_in_study": [1, 2, 4],
                       "x": [10, 20, 40]})
    out = add_next_day(df, "x")
    assert out["x_next"].iloc[0] == 20
    assert out["x_next"].iloc[1:].isna().all()  # day 3 is missing, so day 2 has no t+1
