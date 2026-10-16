"""First Fitbit daily features: resting HR, sleep, steps, and wear time.

Wear time is the number of distinct minutes with a heart-rate reading. Steps records exist
even when the watch is off, so they can't measure wear (this is the caveat on Ava's coverage
report). Nighttime HR, HRV, and skin temperature come in Weeks 4-5.
"""

import pandas as pd

from mealguide import KEYS
from mealguide.data.io import iter_table, read_table, time_of_day


def resting_hr_daily(synthetic: bool = False) -> pd.DataFrame:
    rhr = read_table("resting_heart_rate", synthetic, usecols=KEYS + ["value"])
    rhr = rhr[rhr["value"] > 0]  # Fitbit writes 0 when it can't estimate
    return rhr.groupby(KEYS, as_index=False)["value"].mean().rename(
        columns={"value": "resting_hr"})


def sleep_daily(synthetic: bool = False) -> pd.DataFrame:
    """Main sleep, assigned to the day it ends (last night's sleep -> today's row)."""
    cols = ["id", "study_interval", "sleep_end_day_in_study", "minutesasleep",
            "efficiency", "mainsleep"]
    s = read_table("sleep", synthetic, usecols=cols)
    s = s[s["mainsleep"].astype(str).str.lower().isin(["true", "1"])]
    s = s.rename(columns={"sleep_end_day_in_study": "day_in_study"})
    return s.groupby(KEYS, as_index=False).agg(
        sleep_minutes=("minutesasleep", "sum"), sleep_efficiency=("efficiency", "mean"))


def steps_daily(synthetic: bool = False) -> pd.DataFrame:
    parts = [c.groupby(KEYS)["steps"].sum()
             for c in iter_table("steps", synthetic, usecols=KEYS + ["steps"])]
    total = pd.concat(parts).groupby(level=list(range(len(KEYS)))).sum()
    return total.rename("steps").reset_index()


def wear_minutes_daily(synthetic: bool = False) -> pd.DataFrame:
    parts = []
    for c in iter_table("heart_rate", synthetic, usecols=KEYS + ["timestamp", "bpm"]):
        c = c[c["bpm"] > 0]
        minute = (time_of_day(c["timestamp"]).dt.total_seconds() // 60).astype("int16")
        parts.append(c[KEYS].assign(minute=minute).drop_duplicates())
    worn = pd.concat(parts).drop_duplicates()  # chunk boundaries can split a minute
    return worn.groupby(KEYS).size().rename("wear_minutes").reset_index()


def fitbit_daily(synthetic: bool = False) -> pd.DataFrame:
    out = None
    for part in (resting_hr_daily(synthetic), sleep_daily(synthetic),
                 steps_daily(synthetic), wear_minutes_daily(synthetic)):
        out = part if out is None else out.merge(part, on=KEYS, how="outer")
    out["wear_pct"] = 100 * out["wear_minutes"] / 1440
    return out.sort_values(KEYS).reset_index(drop=True)
