"""Features and baselines at day t must not change when future days change."""

import numpy as np
import pandas as pd

from mealguide.features.rolling import past_baseline_deviation
from mealguide.models.baselines import person_base_rate


def _frame(seed=0, n=40):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "id": np.repeat([1, 2], n), "study_interval": 2022,
        "day_in_study": np.tile(np.arange(1, n + 1), 2),
        "rhr": rng.normal(60, 3, 2 * n),
        "y": rng.integers(0, 2, 2 * n).astype(float),
    })


def _scramble_future(df, cutoff):
    future = df["day_in_study"] > cutoff
    out = df.copy()
    out.loc[future, "rhr"] = 999.0
    out.loc[future, "y"] = 1 - out.loc[future, "y"]
    return out


def test_rolling_baseline_uses_only_past():
    df, cutoff = _frame(), 25
    a = past_baseline_deviation(df, ["rhr"]).set_index(["id", "day_in_study"])
    b = past_baseline_deviation(_scramble_future(df, cutoff), ["rhr"]).set_index(
        ["id", "day_in_study"])
    past = a.index.get_level_values("day_in_study") <= cutoff
    pd.testing.assert_series_equal(a.loc[past, "rhr_dev"], b.loc[past, "rhr_dev"])


def test_rolling_baseline_excludes_today():
    df = _frame()
    out = past_baseline_deviation(df, ["rhr"], window=28, min_periods=1)
    p1 = out[out["id"] == 1].reset_index(drop=True)
    assert np.isnan(p1.loc[0, "rhr_dev"])  # no past days yet
    assert p1.loc[1, "rhr_dev"] == p1.loc[1, "rhr"] - p1.loc[0, "rhr"]


def test_person_base_rate_uses_only_known_outcomes():
    # y at row t is day t+1's outcome, known on day t+1. So the score at day t may use
    # rows < t only. Scrambling rows >= cutoff must not change scores at rows <= cutoff.
    # The LOSO prior uses other participants' labels, which is allowed, so scramble only
    # participant 1 and compare participant 1.
    df, cutoff = _frame(), 25
    scrambled = df.copy()
    mask = (df["id"] == 1) & (df["day_in_study"] >= cutoff)
    scrambled.loc[mask, "y"] = 1 - scrambled.loc[mask, "y"]
    keep = (df["id"] == 1) & (df["day_in_study"] <= cutoff)
    a, b = person_base_rate(df, "y"), person_base_rate(scrambled, "y")
    np.testing.assert_allclose(a[keep], b[keep])
