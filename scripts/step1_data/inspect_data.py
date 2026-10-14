
from pathlib import Path
import zipfile
import pandas as pd

zip_path = next(Path("data/raw").glob("*.zip"))

with zipfile.ZipFile(zip_path) as archive:
    filename = next(
        name for name in archive.namelist()
        if name.endswith("hormones_and_selfreport.csv")
    )

    with archive.open(filename) as file:
        df = pd.read_csv(file)

print("\n=== DATASET SHAPE ===")
print(df.shape)

print("\n=== ALL COLUMN NAMES ===")
for column in df.columns:
    print(column)

print("\n=== FIRST 5 ROWS ===")
print(df.head().to_string(index=False))

print("\n=== DATA TYPES ===")
print(df.dtypes)

print("\n=== SYMPTOM SCALES ===")

symptoms = [
    "fatigue",
    "cramps",
    "bloating",
    "foodcravings"
]

for symptom in symptoms:
    print(f"\n{symptom}:")
    print(df[symptom].value_counts(dropna=False))

print("\n=== PHASE LABELS ===")
print(df["phase"].value_counts(dropna=False))

print("\n=== STUDY INTERVALS ===")
print(df["study_interval"].value_counts(dropna=False))

print("\n=== PARTICIPANTS ===")
print("Unique participants:", df["id"].nunique())

print("\n=== KEY VALIDATION ===")

keys = ["id", "study_interval", "day_in_study"]

print("Total rows:", len(df))
print("Duplicate participant-interval-days:",
      df.duplicated(subset=keys).sum())

print("Duplicate participant-days without interval:",
      df.duplicated(subset=["id", "day_in_study"]).sum())

print("\n=== PARTICIPANTS BY INTERVAL ===")
print(df.groupby("study_interval")["id"].nunique())

print("\n=== HORMONE COVERAGE ===")
print(df[["lh", "estrogen", "pdg"]].notna().sum())

print("\n=== DAY RANGES BY INTERVAL ===")
print(
    df.groupby("study_interval")["day_in_study"]
    .agg(["min", "max", "nunique"])
)

print("\n=== MENSTRUAL FLOW VALUES ===")
print(df["flow_volume"].value_counts(dropna=False))

print("\n=== FLOW BY INTERVAL ===")
print(pd.crosstab(
    df["study_interval"],
    df["flow_volume"],
    dropna=False
))

print("\n=== SAMPLE PARTICIPANT CYCLE ===")

sample = df[
    (df["id"] == 1) &
    (df["study_interval"] == 2022)
].sort_values("day_in_study")

print(
    sample[
        ["day_in_study", "phase", "lh",
         "estrogen", "pdg", "flow_volume"]
    ].head(45).to_string(index=False)
)