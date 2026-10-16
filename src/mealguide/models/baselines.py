"""The two baselines every Step 2 model must beat.

- persistence: tomorrow looks like today (score = today's value of the target signal).
- person base rate: this person's past frequency of the outcome, shrunk toward the rate
  among the *other* participants (LOSO-safe). It only uses outcomes already known at day t.
"""

import pandas as pd

GROUP = ["id", "study_interval"]


def persistence(df: pd.DataFrame, today_col: str) -> pd.Series:
    return df[today_col].astype(float)


def person_base_rate(df: pd.DataFrame, y_col: str, prior_weight: float = 1.0) -> pd.Series:
    """Row t's y is the outcome on day t+1, which is known by day t+1. So at day t the
    known outcomes are the rows before t: an expanding sum shifted by one row."""
    d = df.sort_values(GROUP + ["day_in_study"])
    y = d[y_col]
    known = y.notna().astype(float)
    pos = y.fillna(0.0)

    by_person = d.groupby("id")
    tot_pos, tot_n = pos.sum(), known.sum()
    prior = (tot_pos - by_person[y_col].transform("sum")) / (
        tot_n - by_person[y_col].transform("count"))

    keys = [d[c] for c in GROUP]
    past_pos = pos.groupby(keys).transform(lambda s: s.shift(1).cumsum()).fillna(0.0)
    past_n = known.groupby(keys).transform(lambda s: s.shift(1).cumsum()).fillna(0.0)
    score = (past_pos + prior_weight * prior) / (past_n + prior_weight)
    return score.reindex(df.index)
