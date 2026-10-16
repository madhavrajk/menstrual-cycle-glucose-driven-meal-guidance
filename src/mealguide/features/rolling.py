"""Per-person rolling baselines that only look at past days.

Day t's feature is today's value minus the person's mean over the previous `window` days,
excluding today. Future days never enter, so a held-out participant's features can be
computed online exactly as a deployed watch would.
"""

import pandas as pd

GROUP = ["id", "study_interval"]


def past_baseline_deviation(df: pd.DataFrame, cols: list[str], window: int = 28,
                            min_periods: int = 7) -> pd.DataFrame:
    out = df.sort_values(GROUP + ["day_in_study"]).copy()
    days = pd.to_timedelta(out["day_in_study"], unit="D")
    for col in cols:
        baseline = (
            out.assign(_t=days)
            .groupby(GROUP, group_keys=False)[["_t", col]]
            .apply(lambda g, c=col: g.rolling(f"{window}D", on="_t", closed="left",
                                              min_periods=min_periods)[c].mean())
        )
        out[f"{col}_dev"] = out[col] - baseline
    return out
