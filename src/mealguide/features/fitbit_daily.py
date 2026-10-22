"""Fitbit daily features: resting HR, sleep, steps, wear time, nighttime HR, HRV, and skin
temperature.

Wear time is the number of distinct minutes with a heart-rate reading. Steps records exist
even when the watch is off, so they can't measure wear (this is the caveat on Ava's coverage
report).

Overnight signals (nighttime HR, HRV, skin temperature) belong to the day the night ends,
matching `sleep_daily`: last night's values are today's features, known by this morning.
Each physiological signal also gets a `_dev` column, today's value minus the person's own
mean over the previous 28 days (`features/rolling.py`), because people differ far more from
each other than across their own cycle.
"""

import pandas as pd

from mealguide import KEYS
from mealguide.data.io import iter_table, read_table, time_of_day
from mealguide.features.rolling import past_baseline_deviation

DEV_COLS = ["resting_hr", "night_hr", "hrv_rmssd", "skin_temp"]
GROUP = ["id", "study_interval"]


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


def main_sleep_windows(synthetic: bool = False) -> pd.DataFrame:
    """One row per main sleep, with start and end as absolute minutes since day 0."""
    cols = ["id", "study_interval", "sleep_start_day_in_study", "sleep_start_timestamp",
            "sleep_end_day_in_study", "sleep_end_timestamp", "mainsleep"]
    s = read_table("sleep", synthetic, usecols=cols)
    s = s[s["mainsleep"].astype(str).str.lower().isin(["true", "1"])]
    return sleep_windows_from(s)


def sleep_windows_from(s: pd.DataFrame) -> pd.DataFrame:
    start = s["sleep_start_day_in_study"] * 1440 + (
        time_of_day(s["sleep_start_timestamp"]).dt.total_seconds() // 60)
    end = s["sleep_end_day_in_study"] * 1440 + (
        time_of_day(s["sleep_end_timestamp"]).dt.total_seconds() // 60)
    w = pd.DataFrame({"id": s["id"], "study_interval": s["study_interval"],
                      "start_abs": start, "end_abs": end,
                      "day_in_study": s["sleep_end_day_in_study"]}).dropna()
    w = w[w["end_abs"] > w["start_abs"]]
    return w.astype({"start_abs": "int64", "end_abs": "int64"}).sort_values("start_abs")


def night_hr_from(chunks, windows: pd.DataFrame) -> pd.DataFrame:
    """Mean heart rate during main sleep, from minute-level chunks with KEYS, timestamp, bpm.

    Each reading is matched to the latest sleep that started before it (merge_asof) and
    kept only if it falls before that sleep ended.
    """
    sums = []
    for c in chunks:
        c = c[c["bpm"] > 0]
        t = c["day_in_study"] * 1440 + time_of_day(c["timestamp"]).dt.total_seconds() // 60
        c = c.assign(t_abs=t)[t.notna()]
        c = c.astype({"t_abs": "int64"}).sort_values("t_abs")
        m = pd.merge_asof(c, windows, left_on="t_abs", right_on="start_abs", by=GROUP,
                          direction="backward", suffixes=("", "_night"))
        m = m[m["t_abs"] <= m["end_abs"]]
        sums.append(m.groupby(GROUP + ["day_in_study_night"])["bpm"].agg(["sum", "count"]))
    if not sums:
        return pd.DataFrame(columns=KEYS + ["night_hr"])
    tot = pd.concat(sums).groupby(level=[0, 1, 2]).sum()
    out = (tot["sum"] / tot["count"]).rename("night_hr").reset_index()
    return out.rename(columns={"day_in_study_night": "day_in_study"})


def night_hr_daily(synthetic: bool = False) -> pd.DataFrame:
    chunks = iter_table("heart_rate", synthetic, usecols=KEYS + ["timestamp", "bpm"])
    return night_hr_from(chunks, main_sleep_windows(synthetic))


def hrv_from(h: pd.DataFrame) -> pd.DataFrame:
    """Nightly mean RMSSD. Fitbit records HRV during sleep, so a reading from noon onward
    belongs to the night that ends the next day. (Check on real data: if most readings sit
    between 22:00 and 08:00, this split is right.)"""
    h = h[h["rmssd"] > 0]
    after_noon = time_of_day(h["timestamp"]).dt.total_seconds() >= 12 * 3600
    h = h.assign(day_in_study=h["day_in_study"] + after_noon.astype(int))
    return h.groupby(KEYS, as_index=False)["rmssd"].mean().rename(
        columns={"rmssd": "hrv_rmssd"})


def hrv_daily(synthetic: bool = False) -> pd.DataFrame:
    h = read_table("heart_rate_variability_details", synthetic,
                   usecols=KEYS + ["timestamp", "rmssd"])
    return hrv_from(h)


def skin_temp_daily(synthetic: bool = False) -> pd.DataFrame:
    """Fitbit's nightly skin temperature (°C), assigned to the day the sleep ends."""
    t = read_table("computed_temperature", synthetic,
                   usecols=["id", "study_interval", "sleep_end_day_in_study",
                            "nightly_temperature"])
    t = t[t["nightly_temperature"].between(25, 42)]  # drop missing and sensor-error values
    t = t.rename(columns={"sleep_end_day_in_study": "day_in_study"})
    return t.groupby(KEYS, as_index=False)["nightly_temperature"].mean().rename(
        columns={"nightly_temperature": "skin_temp"})


def fitbit_daily(synthetic: bool = False) -> pd.DataFrame:
    out = None
    for part in (resting_hr_daily(synthetic), sleep_daily(synthetic),
                 steps_daily(synthetic), wear_minutes_daily(synthetic),
                 night_hr_daily(synthetic), hrv_daily(synthetic), skin_temp_daily(synthetic)):
        out = part if out is None else out.merge(part, on=KEYS, how="outer")
    out["wear_pct"] = 100 * out["wear_minutes"] / 1440
    out = past_baseline_deviation(out, DEV_COLS)
    return out.sort_values(KEYS).reset_index(drop=True)
