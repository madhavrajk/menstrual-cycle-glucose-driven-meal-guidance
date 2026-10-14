
from pathlib import Path
import pandas as pd

DATA = Path("data/processed")

base = pd.read_csv(DATA / "daily_master.csv")
labeled = pd.read_csv(DATA / "daily_master_labeled.csv")
cycles = pd.read_csv(DATA / "cycle_summary.csv")
coverage = pd.read_csv(DATA / "coverage_report.csv")

keys = ["id", "study_interval", "day_in_study"]

# Check daily table integrity
assert len(base) == len(labeled)
assert len(labeled) == 5659
assert labeled["id"].nunique() == 42
assert not labeled.duplicated(keys).any()
assert labeled[keys].notna().all().all()

# Check original columns are preserved
# Compare only original columns that labeling should not modify
original_columns = [
    col for col in base.columns
    if col not in {
        "lh_phase",
        "cycle_id",
        "lh_peak_day",
        "phase_quality"
    }
]

pd.testing.assert_frame_equal(
    base[original_columns].sort_values(keys).reset_index(drop=True),
    labeled[original_columns].sort_values(keys).reset_index(drop=True),
    check_dtype=False
)

# Check phase values
valid_phases = {
    "Menstrual", "Follicular", "Fertility", "Luteal"
}
assert set(labeled["lh_phase"].dropna()).issubset(valid_phases)

# Check that only provisional peaks received labels
assert labeled.loc[
    labeled["lh_phase"].notna(), "phase_quality"
].eq("provisional_lh_peak").all()

# Check participant-interval coverage
assert not coverage.duplicated(["id", "study_interval"]).any()

print("\n=== VALIDATION PASSED ===")
print("Rows:", len(labeled))
print("Participants:", labeled["id"].nunique())
print("Duplicate keys:", labeled.duplicated(keys).sum())
print("Cycles inspected:", len(cycles))
print("Provisional LH peaks:",
      cycles["phase_quality"].eq("provisional_lh_peak").sum())
print("Labeled days:", labeled["lh_phase"].notna().sum())
print("Unclassified days:", labeled["lh_phase"].isna().sum())