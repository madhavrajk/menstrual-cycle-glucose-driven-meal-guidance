
from pathlib import Path
import zipfile
import pandas as pd

ZIP_PATH = next(Path("data/raw").glob("*.zip"))
OUTPUT = Path("data/processed/daily_master.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(ZIP_PATH) as archive:
    filename = next(
        name for name in archive.namelist()
        if name.endswith("hormones_and_selfreport.csv")
    )
    with archive.open(filename) as file:
        df = pd.read_csv(file)

# Preserve the shipped phase label
df = df.rename(columns={
    "phase": "mira_phase",
    "estrogen": "estrogen_raw",
    "foodcravings": "cravings"
})

# Preserve raw symptom categories and add numeric versions
scale = {
    "Not at all": 0,
    "Very Low/Little": 1,
    "Low": 2,
    "Moderate": 3,
    "High": 4,
    "Very High": 5
}

for symptom in ["fatigue", "cramps", "bloating", "cravings"]:
    df[f"{symptom}_score"] = df[symptom].map(scale).astype("Int64")

# Placeholder for independently calculated phase
df["lh_phase"] = pd.NA

# Explicit interval labels
df["interval_label"] = df["study_interval"].map({
    2022: "Interval 1",
    2024: "Interval 2"
})

# Check the join keys
keys = ["id", "study_interval", "day_in_study"]

assert not df.duplicated(keys).any(), "Duplicate daily keys!"
assert df[keys].notna().all().all(), "Missing join keys!"
assert df["interval_label"].notna().all(), "Unknown interval!"

df = df.sort_values(keys).reset_index(drop=True)

df.to_csv(OUTPUT, index=False)

print("Saved:", OUTPUT)
print("Rows:", len(df))
print("Participants:", df["id"].nunique())
print("Duplicate keys:", df.duplicated(keys).sum())
print("Columns:", list(df.columns))