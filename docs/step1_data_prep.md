
# MCPHASES Menstrual Health Data Preparation

## Overview

This project prepares the MCPHASES dataset for downstream
menstrual-health modeling and evaluation.

The primary output is a participant-day dataset containing
hormonal measurements, self-reported symptoms, original
Mira phase labels, and exploratory LH-derived phase labels.

## Dataset

- 23 source tables
- 42 unique participants
- Two study intervals: 2022 and 2024
- 5,659 participant-day observations
- Unique key: (id, study_interval, day_in_study)

## Outputs

All generated CSV files are in `data/processed/`.

- daily_master.csv:
  Cleaned hormone and symptom participant-day baseline.

- daily_master_labeled.csv:
  Baseline dataset with provisional LH-derived phases,
  cycle IDs, LH peak days, and quality flags.

- cycle_summary.csv:
  Candidate complete cycles, lengths, LH peak values,
  and phase-quality classifications.

- phase_comparison.csv:
  Cross-tabulation of Mira phases against LH-derived phases.

- coverage_report.csv:
  Participant-interval coverage for diary responses,
  hormones, steps-record presence, and CGM records.

- period_start_candidates.csv:
  Potential menstrual onset dates identified from
  non-spotting bleeding reports.

## Phase Labeling Method

Cycle boundaries are provisionally identified from
reported non-spotting menstrual bleeding.

Cycles of 18–45 days are inspected.

Candidate LH peaks are selected within a restricted
window inside each cycle.

A provisional peak must have:
- LH >= 10
- LH >= 2.5 times the within-window median

An estimated ovulation anchor is set to one day after
the LH peak. Fertility, follicular, and luteal labels
are assigned relative to this anchor. Reported
non-spotting bleeding days are labeled Menstrual.

These thresholds and assignments are exploratory,
not clinically validated. An LH peak does not
independently confirm ovulation.

## Initial Results

- 70 cycles inspected
- 59 cycles with provisional LH peaks
- 11 cycles without qualifying peaks
- 1,746 participant-days assigned LH-derived phases
- 3,913 participant-days left unclassified
- 1,536 / 1,746 labels agree with Mira (~88.0%)

Agreement is descriptive, not proof of clinical validity.

## Important Limitations

2022 contains symptom diary, bleeding, and CGM data.
2024 contains hormone and wearable data but almost no
symptom diary entries, no recorded menstrual flow,
and no CGM records.

PdG is absent in 2022.

Phase labeling currently covers only complete cycles
with usable bleeding boundaries and qualifying LH peaks.
Missing bleeding entries may produce false boundaries.

The daily master currently originates from the
hormones_and_selfreport table. Wearable and CGM
measurements have not yet been aggregated and joined
as numerical daily features.

The coverage report's Fitbit indicator represents
presence of steps records, not verified wear time.

## Reproduce

From the project root with the virtual environment active (or just `make step1`):

python scripts/step1_data/build_dictionary.py
python scripts/step1_data/build_daily_table.py
python scripts/step1_data/coverage_report.py
python scripts/step1_data/inspect_cycles.py
python scripts/step1_data/label_phases.py
python scripts/step1_data/validate_output.py

The original MCPHASES ZIP must be present in data/raw/.

## Downstream Handoff

Madhav:
Use participant-day keys for glucose and wearable
aggregation. CGM records are available in 2022 only.
Do not interpret missing 2024 CGM as zero glucose.

Sneha:
Use mira_phase and lh_phase for exploratory comparison.
Restrict LH-derived evaluation to rows with nonmissing
lh_phase, and account for cycle-level clustering and
selection bias from excluded cycles.

For modeling, use participant-level splits to avoid
leakage across days from the same participant.
