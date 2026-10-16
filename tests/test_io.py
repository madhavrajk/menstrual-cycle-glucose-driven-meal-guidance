import pandas as pd
import pytest

from mealguide.data.io import time_of_day


@pytest.mark.parametrize("values", [
    ["13:05:00", "00:00:00"],                          # clock time
    ["13:05", "00:00"],                                # clock time, no seconds
    ["2022-01-01 13:05:00", "2022-01-02 00:00:00"],    # full datetime
    ["2022-01-01T13:05:00Z", "2022-01-02T00:00:00Z"],  # ISO with timezone
])
def test_time_of_day_formats(values):
    out = time_of_day(pd.Series(values))
    assert out.tolist() == [pd.Timedelta(hours=13, minutes=5), pd.Timedelta(0)]


def test_time_of_day_seconds_and_missing():
    out = time_of_day(pd.Series([47100.0, None]))
    assert out.iloc[0] == pd.Timedelta(hours=13, minutes=5) and pd.isna(out.iloc[1])


def test_time_of_day_raises_on_garbage():
    with pytest.raises(ValueError, match="Could not parse"):
        time_of_day(pd.Series(["not a time"] * 10))
