
import pandas as pd
from pathlib import Path

df = pd.read_csv("data/processed/daily_master.csv")

bleeding = {
    "Light", "Somewhat Light", "Moderate",
    "Somewhat Heavy", "Heavy", "Very Heavy"
}

df = df.sort_values(
    ["id", "study_interval", "day_in_study"]
).copy()

# Spotting alone does not count as a period start.
df["bleeding"] = df["flow_volume"].isin(bleeding)

# Compare only with the immediately preceding calendar study day.
groups = df.groupby(["id", "study_interval"])
previous_day = groups["day_in_study"].shift()
previous_bleeding = groups["bleeding"].shift()

df["period_start_candidate"] = (
    df["bleeding"]
    & (
        previous_day.ne(df["day_in_study"] - 1)
        | previous_bleeding.ne(True)
    )
)

starts = df.loc[
    df["period_start_candidate"],
    ["id", "study_interval", "day_in_study", "flow_volume"]
]

output = Path("data/processed/period_start_candidates.csv")
starts.to_csv(output, index=False)

print("\n=== PERIOD START CANDIDATES ===")
print("Total:", len(starts))
print(starts.groupby("study_interval").size())

print("\n=== PARTICIPANT 1 ===")
print(starts[starts["id"] == 1].to_string(index=False))

print("\n=== PARTICIPANTS WITH CANDIDATES ===")
print(starts.groupby("study_interval")["id"].nunique())

print("\nSaved:", output)