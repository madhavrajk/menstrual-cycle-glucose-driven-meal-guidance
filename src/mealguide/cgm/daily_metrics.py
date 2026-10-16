"""Per participant-day CGM metrics (Danne et al. 2017 consensus; Hall et al. 2018).

Dexcom G6 logs every 5 minutes, so a full day has 288 readings. A day counts as valid
when it has at least MIN_COVERAGE of them (provisional 70%; see docs/decisions.md).
"""

import numpy as np
import pandas as pd

from mealguide import INTERVAL_1, KEYS
from mealguide.data.io import time_of_day

READINGS_PER_DAY = 288
MIN_COVERAGE = 0.70
MGDL_PER_MMOL = 18.016
# Dexcom reports 2.2-22.2 mmol/L or 40-400 mg/dL, so 30 separates the units cleanly.
UNIT_CUTOFF = 30


def to_mgdl(values: pd.Series) -> pd.Series:
    """mcPHASES glucose is documented as mmol/L, but 2 participants have some mg/dL
    readings (about 4% of rows). Convert everything to mg/dL; see docs/decisions.md."""
    return values.where(values > UNIT_CUTOFF, values * MGDL_PER_MMOL)


def mage(values: np.ndarray) -> float:
    """Mean amplitude of glycemic excursions (simplified).

    Takes the turning points of the series, measures the rise or fall between consecutive
    turning points, and averages the ones larger than 1 SD of the day. Counts both
    directions, unlike Service's original one-direction rule.
    """
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 3:
        return np.nan
    sd = x.std(ddof=1)
    x = x[np.r_[True, np.diff(x) != 0]]  # collapse plateaus
    if len(x) < 2:
        return np.nan
    direction = np.sign(np.diff(x))
    turns = np.flatnonzero(direction[1:] != direction[:-1]) + 1
    points = x[np.r_[0, turns, len(x) - 1]]
    amplitudes = np.abs(np.diff(points))
    excursions = amplitudes[amplitudes > sd]
    return float(excursions.mean()) if len(excursions) else np.nan


def daily_cgm_metrics(glucose: pd.DataFrame) -> pd.DataFrame:
    """glucose.csv rows -> one row per participant-day (Interval 1 only)."""
    g = glucose[glucose["study_interval"] == INTERVAL_1].copy()
    g = g.dropna(subset=["glucose_value"])
    g["glucose_value"] = to_mgdl(g["glucose_value"])
    g["t"] = time_of_day(g["timestamp"])
    g = g.drop_duplicates(KEYS + ["t"]).sort_values(KEYS + ["t"])

    v = g["glucose_value"]
    g["in_70_180"] = v.between(70, 180)
    g["in_70_140"] = v.between(70, 140)
    g["below_70"] = v < 70
    g["above_180"] = v > 180

    grouped = g.groupby(KEYS)
    daily = grouped.agg(
        n_readings=("glucose_value", "size"),
        glucose_mean=("glucose_value", "mean"),
        glucose_median=("glucose_value", "median"),
        glucose_sd=("glucose_value", "std"),
        tir_70_180=("in_70_180", "mean"),
        tir_70_140=("in_70_140", "mean"),
        tbr_70=("below_70", "mean"),
        tar_180=("above_180", "mean"),
    )
    daily["glucose_cv"] = 100 * daily["glucose_sd"] / daily["glucose_mean"]
    daily["mage"] = grouped["glucose_value"].agg(lambda s: mage(s.to_numpy()))
    for col in ["tir_70_180", "tir_70_140", "tbr_70", "tar_180"]:
        daily[col] *= 100

    daily["cgm_coverage"] = (daily["n_readings"] / READINGS_PER_DAY).clip(upper=1.0)
    daily["cgm_valid"] = daily["cgm_coverage"] >= MIN_COVERAGE
    return daily.reset_index()
