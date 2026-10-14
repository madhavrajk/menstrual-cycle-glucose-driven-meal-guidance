# MCPHAS​ES Data Dictionary

## Table Inventory

| Table | Rows | Participants | Intervals | Study days |
|---|---:|---:|---|---|
| active_minutes.csv | 5,552 | 42 | 2022, 2024 | 1–1004 |
| active_zone_minutes.csv | 154,482 | 42 | 2022, 2024 | 1–1004 |
| altitude.csv | 90,878 | 42 | 2022, 2024 | 1–1004 |
| calories.csv | 20,166,975 | 42 | 2022, 2024 | 1–1004 |
| computed_temperature.csv | 5,575 | 42 | 2022, 2024 | N/A |
| demographic_vo2_max.csv | 11,482 | 42 | 2022, 2024 | 1–1004 |
| distance.csv | 7,666,949 | 42 | 2022, 2024 | 1–1004 |
| estimated_oxygen_variation.csv | 3,070,312 | 42 | 2022, 2024 | 1–1004 |
| exercise.csv | 7,282 | 31 | 2022, 2024 | N/A |
| glucose.csv | 837,130 | 42 | 2022 | 1–90 |
| heart_rate.csv | 63,100,276 | 42 | 2022, 2024 | 1–1004 |
| heart_rate_variability_details.csv | 436,262 | 40 | 2022, 2024 | 1–1004 |
| height_and_weight.csv | 42 | 42 | N/A | N/A |
| hormones_and_selfreport.csv | 5,659 | 42 | 2022, 2024 | 1–1004 |
| respiratory_rate_summary.csv | 6,301 | 40 | 2022, 2024 | 1–1004 |
| resting_heart_rate.csv | 13,737 | 42 | 2022, 2024 | 1–1004 |
| sleep.csv | 14,765 | 42 | 2022, 2024 | N/A |
| sleep_score.csv | 5,308 | 42 | 2022, 2024 | 1–1004 |
| steps.csv | 7,666,949 | 42 | 2022, 2024 | 1–1004 |
| stress_score.csv | 7,932 | 36 | 2022, 2024 | 1–1004 |
| subject-info.csv | 42 | 42 | N/A | N/A |
| time_in_heart_rate_zones.csv | 5,553 | 42 | 2022, 2024 | 1–1004 |
| wrist_temperature.csv | 6,856,019 | 42 | 2022, 2024 | 1–1004 |

## Column Inventory

### active_minutes.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `sedentary`, `lightly`, `moderately`, `very`

**Grain:** To be verified.

**Unique key:** To be verified.

### active_zone_minutes.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `heart_zone_id`, `total_minutes`

**Grain:** To be verified.

**Unique key:** To be verified.

### altitude.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `altitude`

**Grain:** To be verified.

**Unique key:** To be verified.

### calories.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `calories`

**Grain:** To be verified.

**Unique key:** To be verified.

### computed_temperature.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `sleep_start_day_in_study`, `sleep_start_timestamp`, `sleep_end_day_in_study`, `sleep_end_timestamp`, `type`, `temperature_samples`, `nightly_temperature`, `baseline_relative_sample_sum`, `baseline_relative_sample_sum_of_squares`, `baseline_relative_nightly_standard_deviation`, `baseline_relative_sample_standard_deviation`

**Grain:** To be verified.

**Unique key:** To be verified.

### demographic_vo2_max.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `demographic_vo2_max`, `demographic_vo2_max_error`, `filtered_demographic_vo2_max`, `filtered_demographic_vo2_max_error`

**Grain:** To be verified.

**Unique key:** To be verified.

### distance.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `distance`

**Grain:** To be verified.

**Unique key:** To be verified.

### estimated_oxygen_variation.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `infrared_to_red_signal_ratio`

**Grain:** To be verified.

**Unique key:** To be verified.

### exercise.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `start_day_in_study`, `start_timestamp`, `last_modified_day_in_study`, `last_modified_timestamp`, `original_start_day_in_study`, `original_start_timestamp`, `originalduration`, `activityname`, `activitytypeid`, `activitylevel`, `averageheartrate`, `calories`, `duration`, `activeduration`, `steps`, `logtype`, `manualvaluesspecified`, `heartratezones`, `activezoneminutes`, `elevationgain`, `hasgps`, `shouldfetchdetails`, `hasactivezoneminutes`

**Grain:** To be verified.

**Unique key:** To be verified.

### glucose.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `glucose_value`

**Grain:** To be verified.

**Unique key:** To be verified.

### heart_rate.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `bpm`, `confidence`

**Grain:** To be verified.

**Unique key:** To be verified.

### heart_rate_variability_details.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `rmssd`, `coverage`, `low_frequency`, `high_frequency`

**Grain:** To be verified.

**Unique key:** To be verified.

### height_and_weight.csv

**Columns:** `id`, `height_2022`, `weight_2022`, `height_2024`, `weight_2024`

**Grain:** To be verified.

**Unique key:** To be verified.

### hormones_and_selfreport.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `phase`, `lh`, `estrogen`, `pdg`, `flow_volume`, `flow_color`, `appetite`, `exerciselevel`, `headaches`, `cramps`, `sorebreasts`, `fatigue`, `sleepissue`, `moodswing`, `stress`, `foodcravings`, `indigestion`, `bloating`

**Grain:** To be verified.

**Unique key:** To be verified.

### respiratory_rate_summary.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `full_sleep_breathing_rate`, `full_sleep_standard_deviation`, `full_sleep_signal_to_noise`, `deep_sleep_breathing_rate`, `deep_sleep_standard_deviation`, `deep_sleep_signal_to_noise`, `light_sleep_breathing_rate`, `light_sleep_standard_deviation`, `light_sleep_signal_to_noise`, `rem_sleep_breathing_rate`, `rem_sleep_standard_deviation`, `rem_sleep_signal_to_noise`

**Grain:** To be verified.

**Unique key:** To be verified.

### resting_heart_rate.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `value`, `error`

**Grain:** To be verified.

**Unique key:** To be verified.

### sleep.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `sleep_start_day_in_study`, `sleep_start_timestamp`, `sleep_end_day_in_study`, `sleep_end_timestamp`, `duration`, `minutestofallasleep`, `minutesasleep`, `minutesawake`, `minutesafterwakeup`, `timeinbed`, `efficiency`, `type`, `infocode`, `levels`, `mainsleep`

**Grain:** To be verified.

**Unique key:** To be verified.

### sleep_score.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `overall_score`, `composition_score`, `revitalization_score`, `duration_score`, `deep_sleep_in_minutes`, `resting_heart_rate`, `restlessness`

**Grain:** To be verified.

**Unique key:** To be verified.

### steps.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `steps`

**Grain:** To be verified.

**Unique key:** To be verified.

### stress_score.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `stress_score`, `sleep_points`, `max_sleep_points`, `responsiveness_points`, `max_responsiveness_points`, `exertion_points`, `max_exertion_points`, `status`, `calculation_failed`

**Grain:** To be verified.

**Unique key:** To be verified.

### subject-info.csv

**Columns:** `id`, `birth_year`, `gender`, `ethnicity`, `education`, `sexually_active`, `self_report_menstrual_health_literacy`, `age_of_first_menarche`

**Grain:** To be verified.

**Unique key:** To be verified.

### time_in_heart_rate_zones.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `in_default_zone_3`, `in_default_zone_2`, `in_default_zone_1`, `below_default_zone_1`

**Grain:** To be verified.

**Unique key:** To be verified.

### wrist_temperature.csv

**Columns:** `id`, `study_interval`, `is_weekend`, `day_in_study`, `timestamp`, `temperature_diff_from_baseline`

**Grain:** To be verified.

**Unique key:** To be verified.
