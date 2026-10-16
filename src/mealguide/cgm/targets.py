"""Forecast targets and next-day alignment."""

import numpy as np
import pandas as pd

from mealguide import KEYS

GROUP = ["id", "study_interval"]


def label_high_cv(cgm_daily: pd.DataFrame, quantile: float = 2 / 3,
                  min_days: int = 10) -> pd.DataFrame:
    """Target (b): a day is high-variability when its CV is in the top third of that
    participant's own valid days. Participants with fewer than min_days valid days get NaN.

    The threshold uses all of the participant's days. That is fine for a label, but it must
    never be used as a feature.
    """
    df = cgm_daily.copy()
    valid = df[df["cgm_valid"]]
    stats = valid.groupby(GROUP)["glucose_cv"].agg(
        cv_threshold=lambda s: s.quantile(quantile), n_valid_days="size"
    )
    stats.loc[stats["n_valid_days"] < min_days, "cv_threshold"] = np.nan
    df = df.merge(stats.reset_index(), on=GROUP, how="left")
    high = (df["glucose_cv"] >= df["cv_threshold"]).astype(float)
    df["high_cv"] = high.where(df["cgm_valid"] & df["cv_threshold"].notna())
    return df


def symptom_high(daily: pd.DataFrame, symptom: str, threshold: int = 3) -> pd.Series:
    """Binary symptom day: score >= threshold (3 = "Moderate"). NaN when not reported."""
    score = daily[f"{symptom}_score"].astype(float)
    return (score >= threshold).astype(float).where(score.notna())


def add_next_day(df: pd.DataFrame, col: str, new_col: str | None = None) -> pd.DataFrame:
    """Add the value of `col` on day t+1 (same participant and interval) to row t.

    Matches on day_in_study + 1 exactly, so gaps give NaN instead of a later day.
    """
    new_col = new_col or f"{col}_next"
    nxt = df[KEYS + [col]].rename(columns={col: new_col}).copy()
    nxt["day_in_study"] = nxt["day_in_study"] - 1
    return df.merge(nxt, on=KEYS, how="left")
