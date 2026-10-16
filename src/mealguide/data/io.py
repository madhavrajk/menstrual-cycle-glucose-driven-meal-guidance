"""Read mcPHASES tables straight from the zip, or from data/synthetic/.

Both sources return the same columns, so downstream code doesn't care which one it got.
"""

import zipfile
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from mealguide import paths


def _zip_member(archive: zipfile.ZipFile, table: str) -> str:
    for name in archive.namelist():
        if name.endswith(f"/{table}.csv") or name == f"{table}.csv":
            return name
    raise KeyError(f"{table}.csv not found in {archive.filename}")


def read_table(table: str, synthetic: bool = False, usecols=None) -> pd.DataFrame:
    if synthetic:
        return pd.read_csv(paths.SYNTHETIC / f"{table}.csv", usecols=usecols)
    with zipfile.ZipFile(paths.raw_zip()) as archive:
        with archive.open(_zip_member(archive, table)) as f:
            return pd.read_csv(f, usecols=usecols)


def iter_table(
    table: str, synthetic: bool = False, usecols=None, chunksize: int = 2_000_000
) -> Iterator[pd.DataFrame]:
    """Chunked reader for the big minute-level tables (heart_rate, steps)."""
    if synthetic:
        yield from pd.read_csv(paths.SYNTHETIC / f"{table}.csv", usecols=usecols,
                               chunksize=chunksize)
        return
    with zipfile.ZipFile(paths.raw_zip()) as archive:
        with archive.open(_zip_member(archive, table)) as f:
            yield from pd.read_csv(f, usecols=usecols, chunksize=chunksize)


def read_daily_table(synthetic: bool = False) -> pd.DataFrame:
    """Ava's participant-day table with symptoms, hormones, and phase labels."""
    path: Path = (paths.SYNTHETIC if synthetic else paths.PROCESSED) / "daily_master_labeled.csv"
    if not path.exists():
        hint = "make synthetic" if synthetic else "make step1"
        raise FileNotFoundError(f"{path} not found. Run `{hint}` first.")
    return pd.read_csv(path)


def time_of_day(ts: pd.Series) -> pd.Series:
    """Parse mcPHASES timestamps to a Timedelta since midnight.

    The dataset page doesn't document the format. Dates are de-identified (day_in_study),
    so clock times like "13:05:00" are most likely. Also accepted: full datetimes, and
    numbers of seconds since midnight. Unparseable values become NaT. If more than 1% fail,
    this raises with examples so the format can be fixed in one place.
    """
    if pd.api.types.is_numeric_dtype(ts):
        if ts.dropna().between(0, 86_400).all():
            return pd.to_timedelta(ts, unit="s")
        raise ValueError(f"Numeric timestamps not in seconds-of-day: {ts.head(3).tolist()}")

    s = ts.astype("string").str.strip()
    clock = s.str.fullmatch(r"\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?").fillna(False)
    if clock[s.notna()].all():
        out = pd.to_timedelta(s.where(s.str.count(":") == 2, s + ":00"), errors="coerce")
    else:
        dt = pd.to_datetime(s, format="mixed", errors="coerce")
        out = dt - dt.dt.normalize()

    failed = out.isna() & s.notna()
    if failed.mean() > 0.01:
        raise ValueError(f"Could not parse {failed.mean():.1%} of timestamps, e.g. "
                         f"{s[failed].head(3).tolist()}. Update data/io.py::time_of_day.")
    return out
