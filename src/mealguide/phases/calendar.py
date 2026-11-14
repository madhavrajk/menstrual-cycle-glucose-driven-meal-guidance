"""Past-only calendar estimates; no hormones or future cycle boundaries."""
import numpy as np
import pandas as pd

from mealguide import KEYS

BLEEDING = {"Light", "Somewhat Light", "Moderate", "Somewhat Heavy", "Heavy", "Very Heavy"}


def calendar_phases(daily: pd.DataFrame) -> pd.DataFrame:
    """End-of-day feature. Starts require observed adjacent nonbleeding -> bleeding.

    Estimate cycle length from the last three completed, plausible (18–45 day)
    inter-onset intervals. Five menstrual days, estimated ovulation L-14, and
    fertility days ovulation-5 through ovulation are explicit exploratory assumptions.
    No completed history or a cycle beyond its estimated length yields unknown.
    """
    if daily[KEYS].isna().any().any() or daily.duplicated(KEYS).any():
        raise ValueError("Calendar input requires unique nonmissing daily keys")
    out = daily.sort_values(KEYS).copy()
    out["calendar_phase"] = "Unknown"
    out["calendar_confidence"] = "unknown"
    out["calendar_cycle_length"] = np.nan
    out["calendar_day"] = np.nan
    for _, group in out.groupby(["id", "study_interval"]):
        starts, lengths = [], []
        previous_day, previous_flow = None, None
        for idx, row in group.iterrows():
            day, flow = row.day_in_study, row.get("flow_volume")
            onset = (flow in BLEEDING and previous_day == day - 1
                     and pd.notna(previous_flow) and previous_flow not in BLEEDING
                     and previous_flow != "Spotting")
            if onset:
                if starts and 18 <= day - starts[-1] <= 45:
                    lengths.append(day - starts[-1])
                starts.append(day)
            if starts:
                age = day - starts[-1] + 1
                out.at[idx, "calendar_day"] = age
                if lengths:
                    length = float(np.median(lengths[-3:]))
                    out.at[idx, "calendar_cycle_length"] = length
                    if age <= length:
                        ovulation = length - 14
                        phase = ("Menstrual" if age <= 5 else "Luteal" if age > ovulation
                                 else "Fertility" if age >= ovulation - 5 else "Follicular")
                        out.at[idx, "calendar_phase"] = phase
                        out.at[idx, "calendar_confidence"] = "low"
            previous_day, previous_flow = day, flow
    return out
