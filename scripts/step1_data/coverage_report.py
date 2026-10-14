
from pathlib import Path
import zipfile
import pandas as pd

ZIP_PATH = next(Path("data/raw").glob("*.zip"))
OUTPUT = Path("data/processed/coverage_report.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

def load_table(name, usecols=None):
    with zipfile.ZipFile(ZIP_PATH) as archive:
        filename = next(
            n for n in archive.namelist()
            if n.endswith(f"/{name}.csv")
        )
        with archive.open(filename) as file:
            return pd.read_csv(file, usecols=usecols)

keys = ["id", "study_interval", "day_in_study"]

# 1. Diary and hormone coverage
diary = load_table("hormones_and_selfreport")

symptoms = ["fatigue", "cramps", "bloating", "foodcravings"]

diary["has_diary"] = diary[symptoms].notna().any(axis=1)
diary["has_lh"] = diary["lh"].notna()
diary["has_estrogen"] = diary["estrogen"].notna()
diary["has_pdg"] = diary["pdg"].notna()
diary["has_hormones"] = diary[
    ["has_lh", "has_estrogen", "has_pdg"]
].any(axis=1)

daily = diary[
    keys + [
        "has_diary", "has_lh", "has_estrogen",
        "has_pdg", "has_hormones"
    ]
].copy()

# 2. Fitbit coverage (steps as a proxy)
# Read in chunks to avoid loading millions of rows at once.
fitbit_days = set()

with zipfile.ZipFile(ZIP_PATH) as archive:
    filename = next(
        n for n in archive.namelist()
        if n.endswith("/steps.csv")
    )
    with archive.open(filename) as file:
        for chunk in pd.read_csv(
            file, usecols=keys, chunksize=200000
        ):
            fitbit_days.update(
                chunk.itertuples(index=False, name=None)
            )

# 3. CGM coverage
glucose_days = set()

with zipfile.ZipFile(ZIP_PATH) as archive:
    filename = next(
        n for n in archive.namelist()
        if n.endswith("/glucose.csv")
    )
    with archive.open(filename) as file:
        for chunk in pd.read_csv(
            file, usecols=keys, chunksize=200000
        ):
            glucose_days.update(
                chunk.itertuples(index=False, name=None)
            )

daily_keys = list(
    daily[keys].itertuples(index=False, name=None)
)

daily["has_fitbit_data"] = [
    key in fitbit_days for key in daily_keys
]
daily["has_cgm"] = [
    key in glucose_days for key in daily_keys
]

# 4. Summarize per participant and interval
coverage = (
    daily.groupby(["id", "study_interval"])
    .agg(
        observed_days=("day_in_study", "nunique"),
        diary_days=("has_diary", "sum"),
        lh_days=("has_lh", "sum"),
        estrogen_days=("has_estrogen", "sum"),
        pdg_days=("has_pdg", "sum"),
        hormone_days=("has_hormones", "sum"),
        fitbit_data_days=("has_fitbit_data", "sum"),
        cgm_days=("has_cgm", "sum")
    )
    .reset_index()
)

coverage["diary_pct"] = (
    100 * coverage["diary_days"] /
    coverage["observed_days"]
).round(1)

coverage["cgm_pct"] = (
    100 * coverage["cgm_days"] /
    coverage["observed_days"]
).round(1)

coverage.to_csv(OUTPUT, index=False)

print("\n=== COVERAGE SUMMARY ===")
print(coverage.groupby("study_interval")[
    ["observed_days", "diary_days",
     "hormone_days", "fitbit_data_days", "cgm_days"]
].sum())

print("\n=== PARTICIPANT COVERAGE ===")
print(coverage.to_string(index=False))

print("\nSaved:", OUTPUT)