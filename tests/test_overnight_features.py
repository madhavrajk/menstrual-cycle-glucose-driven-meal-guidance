"""Nighttime HR, HRV, and skin temperature: which minutes count and which day they land on."""

import pandas as pd
import pytest

from mealguide import paths, pipeline, synthetic
from mealguide.features.fitbit_daily import hrv_from, night_hr_from, sleep_windows_from


def _sleep(start_day, start, end_day, end):
    return pd.DataFrame({"id": [1], "study_interval": [2022],
                         "sleep_start_day_in_study": [start_day],
                         "sleep_start_timestamp": [start],
                         "sleep_end_day_in_study": [end_day], "sleep_end_timestamp": [end]})


def _hr(rows):
    return pd.DataFrame(rows, columns=["id", "study_interval", "day_in_study", "timestamp",
                                       "bpm"])


def test_night_hr_uses_only_minutes_inside_main_sleep():
    windows = sleep_windows_from(_sleep(1, "23:00:00", 2, "06:00:00"))
    hr = _hr([
        (1, 2022, 1, "22:59:00", 100),  # before bed: excluded
        (1, 2022, 1, "23:30:00", 50),   # asleep, before midnight
        (1, 2022, 2, "03:00:00", 60),   # asleep, after midnight
        (1, 2022, 2, "06:00:00", 70),   # last minute of sleep: included
        (1, 2022, 2, "06:01:00", 100),  # awake: excluded
        (1, 2022, 2, "12:00:00", 0),    # zero = no reading: excluded
    ])
    out = night_hr_from([hr], windows)
    assert out.to_dict("records") == [{"id": 1, "study_interval": 2022, "day_in_study": 2,
                                       "night_hr": 60.0}]


def test_night_hr_combines_chunks():
    windows = sleep_windows_from(_sleep(1, "23:00:00", 2, "06:00:00"))
    a = _hr([(1, 2022, 1, "23:30:00", 50)])
    b = _hr([(1, 2022, 2, "03:00:00", 70)])
    assert night_hr_from([a, b], windows)["night_hr"].tolist() == [60.0]


def test_hrv_evening_readings_belong_to_next_day():
    h = pd.DataFrame({"id": 1, "study_interval": 2022, "day_in_study": [1, 2, 2],
                      "timestamp": ["23:30:00", "04:00:00", "23:00:00"],
                      "rmssd": [40.0, 50.0, 30.0]})
    out = hrv_from(h).set_index("day_in_study")["hrv_rmssd"]
    assert out[2] == pytest.approx(45.0)  # night of day 1 -> day 2
    assert out[3] == pytest.approx(30.0)  # 23:00 on day 2 -> day 3


def test_model_runs_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SYNTHETIC", tmp_path / "synthetic")
    monkeypatch.setattr(paths, "RESULTS", tmp_path / "results")
    paths.SYNTHETIC.mkdir()
    for name, df in synthetic.generate(n_participants=4, n_days=30).items():
        df.to_csv(paths.SYNTHETIC / f"{name}.csv", index=False)

    results = pipeline.run_model(synthetic=True)

    assert len(results) == 15  # 5 targets x (2 baselines + LR)
    lr = results[results["baseline"] == "lr_watch"]
    assert lr["auroc"].notna().all()
    assert (paths.RESULTS / "first_model_synthetic.csv").exists()
