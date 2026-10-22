
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path("data/processed")
df = pd.read_csv(DATA / "daily_master.csv")

# Exploratory parameters, not clinically validated thresholds
MIN_PEAK_LH = 10.0
MIN_PEAK_RATIO = 2.5
MIN_CYCLE_DAYS = 18
MAX_CYCLE_DAYS = 45
FERTILE_DAYS_BEFORE = 5

df["lh_phase"] = pd.NA
df["cycle_id"] = pd.NA
df["lh_peak_day"] = pd.NA
df["phase_quality"] = "unclassified"

starts = pd.read_csv(DATA / "period_start_candidates.csv")

cycle_records = []
cycle_number = 0

for (pid, interval), group in df.groupby(
    ["id", "study_interval"], sort=False
):
    group = group.sort_values("day_in_study")

    period_days = sorted(
        starts.loc[
            (starts["id"] == pid) &
            (starts["study_interval"] == interval),
            "day_in_study"
        ].astype(int).unique()
    )

    # Only complete intervals between two observed
    # period starts are used for phase assignment.
    for start, end in zip(period_days, period_days[1:]):
        length = end - start

        if not MIN_CYCLE_DAYS <= length <= MAX_CYCLE_DAYS:
            continue

        cycle = group[
            (group["day_in_study"] >= start) &
            (group["day_in_study"] < end)
        ].copy()

        if cycle.empty:
            continue

        cycle_number += 1
        cycle_id = f"{pid}_{interval}_{cycle_number}"

        df.loc[cycle.index, "cycle_id"] = cycle_id

        # Candidate LH peak within a plausible
        # post-menstrual, premenstrual window.
        candidate = cycle[
            (cycle["day_in_study"] >= start + 5) &
            (cycle["day_in_study"] <= end - 8) &
            cycle["lh"].notna()
        ]

        quality = "no_valid_lh_peak"
        peak_day = np.nan
        peak_lh = np.nan

        if len(candidate) >= 3:
            peak_idx = candidate["lh"].idxmax()
            peak_day = int(
                candidate.loc[peak_idx, "day_in_study"]
            )
            peak_lh = float(
                candidate.loc[peak_idx, "lh"]
            )

            baseline = candidate["lh"].median()

            if (
                pd.notna(baseline)
                and baseline > 0
                and peak_lh >= MIN_PEAK_LH
                and peak_lh / baseline >= MIN_PEAK_RATIO
            ):
                quality = "provisional_lh_peak"

        if quality == "provisional_lh_peak":
            # Day after LH peak is an approximate
            # ovulation anchor, not confirmation.
            estimated_ovulation = peak_day + 1

            for idx, row in cycle.iterrows():
                day = int(row["day_in_study"])

                if day >= estimated_ovulation + 1:
                    phase = "Luteal"
                elif day >= (
                    estimated_ovulation - FERTILE_DAYS_BEFORE
                ):
                    phase = "Fertility"
                else:
                    phase = "Follicular"

                df.at[idx, "lh_phase"] = phase

            # Override days with reported menstrual bleeding.
            bleeding = {
                "Light",
                "Somewhat Light",
                "Moderate",
                "Somewhat Heavy",
                "Heavy",
                "Very Heavy"
            }

            bleeding_idx = cycle[
                cycle["flow_volume"].isin(bleeding)
            ].index

            df.loc[bleeding_idx, "lh_phase"] = "Menstrual"
            df.loc[cycle.index, "lh_peak_day"] = peak_day

        df.loc[cycle.index, "phase_quality"] = quality

        cycle_records.append({
            "cycle_id": cycle_id,
            "id": pid,
            "study_interval": interval,
            "start_day": start,
            "end_day_exclusive": end,
            "cycle_length": length,
            "lh_peak_day": peak_day,
            "peak_lh": peak_lh,
            "phase_quality": quality
        })

from mealguide.phases.calendar import calendar_phases

df = calendar_phases(df)

# Save labeled dataset separately
df.to_csv(
    DATA / "daily_master_labeled.csv",
    index=False
)

cycles = pd.DataFrame(cycle_records, columns=[
    "cycle_id", "id", "study_interval", "start_day", "end_day_exclusive",
    "cycle_length", "lh_peak_day", "peak_lh", "phase_quality"
])
cycles.to_csv(
    DATA / "cycle_summary.csv",
    index=False
)

# Compare only days with both labels available
comparison = df.dropna(
    subset=["mira_phase", "lh_phase"]
)

matrix = pd.crosstab(
    comparison["mira_phase"],
    comparison["lh_phase"],
    margins=True
)

matrix.to_csv(DATA / "phase_comparison.csv")

print("\n=== CYCLE SUMMARY ===")
print("Cycles inspected:", len(cycles))

if not cycles.empty:
    print(cycles["phase_quality"].value_counts())

print("\n=== PHASE COVERAGE ===")
print("Total days:", len(df))
print("Days assigned:", df["lh_phase"].notna().sum())

print("\n=== MIRA VS LH-DERIVED PHASES ===")
print(matrix)

print("\nSaved:")
print(" - data/processed/daily_master_labeled.csv")
print(" - data/processed/cycle_summary.csv")
print(" - data/processed/phase_comparison.csv")