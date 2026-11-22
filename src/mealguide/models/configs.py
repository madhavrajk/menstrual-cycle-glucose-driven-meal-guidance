"""Step 2 feature groups and the model configurations built from them.

Every row is day t, and every feature is known by the end of day t; the targets are day t+1.

Feature groups:
- history: today's diary scores and the person's past rate of the target. Symptom targets
  only, because the app needs the diary to know a symptom happened at all. (Real data: the
  person's own history alone reaches AUROC 0.81-0.86, so every symptom config starts here.)
- watch: Fitbit signals as deviations from the person's own past 28 days.
- phase: Ava's past-only calendar phase, projected one day ahead to the forecast day.
- glucose: today's CGM summary (needs a CGM, so it's the most expensive configuration).
- lh_phase: the hormone-confirmed phase of the forecast day. It uses future cycle
  boundaries, so it is a retrospective best case for comparison, never a deployable feature.

The glucose target gets no history group: a past rate of high-CV days would leak, because
each past label's threshold uses all of the person's days, including future ones.
"""

import numpy as np
import pandas as pd

from mealguide.cgm.targets import add_next_day
from mealguide.features.rolling import past_baseline_deviation
from mealguide.models.baselines import person_base_rate

SYMPTOMS = ["fatigue", "cramps", "bloating", "cravings"]
TARGETS = ["high_cv"] + [f"{s}_high" for s in SYMPTOMS]
PHASES = ["Menstrual", "Follicular", "Fertility", "Luteal"]

WATCH = ["resting_hr_dev", "night_hr_dev", "hrv_rmssd_dev", "skin_temp_dev",
         "sleep_minutes_dev", "sleep_efficiency_dev", "steps_dev"]
PHASE = [f"phase_next_{p}" for p in PHASES]
LH_PHASE = [f"lh_next_{p}" for p in PHASES]
GLUCOSE = ["glucose_cv", "glucose_cv_dev", "glucose_mean_dev", "mage_dev", "tir_70_140"]
DIARY = [f"{s}_score" for s in SYMPTOMS]

CONFIGS = ["history", "watch", "watch+phase", "watch+phase+glucose"]
# Deployable without a CGM: what the headline model is chosen from.
NO_CGM_CONFIGS = ["watch", "watch+phase"]


def history(target: str) -> list[str]:
    return [] if target == "high_cv" else DIARY + [f"{target}_past_rate"]


def config_features(target: str, config: str) -> list[str]:
    """Feature columns for one target and configuration (see CONFIGS, plus 'watch+lh')."""
    groups = {"history": [], "watch": WATCH, "phase": PHASE, "glucose": GLUCOSE,
              "lh": LH_PHASE}
    parts = config.split("+")
    if parts[0] not in ("history", "watch"):
        raise ValueError(f"Unknown config {config!r}")
    feats = history(target) + [f for p in parts for f in groups[p]]
    if not feats:
        raise ValueError(f"{config!r} has no features for {target}: the glucose target has "
                         "no history group")
    return list(dict.fromkeys(feats))


def calendar_phase_at(day: pd.Series, length: pd.Series) -> pd.Series:
    """Ava's calendar rule (`phases/calendar.py`) for a cycle day and estimated length:
    days 1-5 Menstrual, ovulation at length-14, Fertility the 5 days before it through
    ovulation, Luteal after, and Unknown with no length estimate or past the length."""
    ovulation = length - 14
    phase = np.select(
        [day.isna() | length.isna() | (day > length), day <= 5, day > ovulation,
         day >= ovulation - 5],
        ["Unknown", "Menstrual", "Luteal", "Fertility"], default="Follicular")
    return pd.Series(phase, index=day.index)


def add_model_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add every feature group to the model table from `pipeline.build_model_table`."""
    out = past_baseline_deviation(df, ["sleep_minutes", "sleep_efficiency", "steps"])

    # CGM: today's summary, only on days that meet the coverage rule.
    invalid = ~out["cgm_valid"].fillna(False).astype(bool)
    for col in ("glucose_cv", "glucose_mean", "mage", "tir_70_140"):
        out[col] = out[col].mask(invalid)
    out = past_baseline_deviation(out, ["glucose_cv", "glucose_mean", "mage"])

    # Phase of the forecast day: today's calendar day + 1, same estimated length. A bleed
    # starting tomorrow can't be known today, so this is what a deployed app would see.
    out["phase_next"] = calendar_phase_at(out["calendar_day"] + 1,
                                          out["calendar_cycle_length"])
    for p in PHASES:
        out[f"phase_next_{p}"] = (out["phase_next"] == p).astype(float)

    out = add_next_day(out, "lh_phase", "lh_phase_next")
    for p in PHASES:
        out[f"lh_next_{p}"] = (out["lh_phase_next"] == p).astype(float)

    # Past rate of each symptom. The prior is a fixed 0.5 (weight 1), not the other
    # participants' rate, so no held-out labels reach the training features.
    for s in SYMPTOMS:
        out[f"{s}_high_past_rate"] = person_base_rate(out, f"{s}_high_next", prior=0.5)
    return out
