"""Forecast API for Step 3: `get_forecast(id, day)` returns a `guidance.forecast.Forecast`.

    from mealguide.models.forecast_api import get_forecast
    fc = get_forecast(7, 31)                    # real data under MCPHASES_HOME
    fc = get_forecast(3, 40, synthetic=True)    # data/synthetic/

    python -m mealguide.models.forecast_api --id 3 --day 40 --synthetic
    make forecast ID=3 DAY=40 SYNTHETIC=1

`day` is the day the forecast is FOR (Interval 1 `day_in_study`). It is made from
everything known by the end of the day before, which is the row the models were trained on:

- risks: the headline model's probability for each target (results/step2_headline_*.json,
  written by `make model`). `unstable_glucose` is included only when the day before had a
  valid CGM day, because without a CGM nothing in Step 2 forecasts it; Step 3 then falls
  back to the phase trigger.
- phase: Ava's past-only calendar phase, projected to `day` (Unknown when the history is
  too short; most days early in the study).
- logged: symptoms the person rated Moderate or worse the day before (reactive trigger).

Each person's forecast comes from models trained **without** that person (LOSO), so even a
participant in the data gets an honest out-of-sample forecast. A person not in the data
gets the model trained on everyone. Trigger rules stay on the Step 3 side
(`guidance.forecast.triggers`).

Real participant forecasts are restricted data: keep them local, and send them only to the
local model (docs/decisions.md, Oct 16).
"""

import argparse
from functools import cache

import pandas as pd

from mealguide import INTERVAL_1
from mealguide.guidance.forecast import Forecast
from mealguide.models.configs import SYMPTOMS, TARGETS
from mealguide.models.step2 import fit_headline, headline_config, load_headline, model_table

# Step 2 target column -> Step 3 Forecast target
STEP3_NAME = {"high_cv": "unstable_glucose"} | {f"{s}_high": s for s in SYMPTOMS}


class Forecaster:
    def __init__(self, synthetic: bool = False, headline: dict | None = None):
        self.synthetic = synthetic
        self.headline = headline or load_headline(synthetic)
        self.table = model_table(synthetic)
        rows = self.table[self.table["study_interval"] == INTERVAL_1]
        self.rows = rows.set_index(["id", "day_in_study"])
        self._models: dict = {}

    def _model(self, target: str, exclude):
        key = (target, exclude)
        if key not in self._models:
            self._models[key] = fit_headline(self.table, self.headline, target, exclude)
        return self._models[key]

    def forecast(self, person, day: int) -> Forecast:
        person = _match_id(person, self.rows.index.get_level_values("id"))
        try:
            today = self.rows.loc[[(person, day - 1)]]
        except KeyError:
            raise KeyError(f"No data for participant {person} on day {day - 1} (the day "
                           f"before the forecast day {day}).") from None
        row = today.iloc[0]
        known = person in self.rows.index.get_level_values("id")
        risks = {}
        for target in TARGETS:
            if target == "high_cv" and pd.isna(row["glucose_cv"]):
                continue
            model, feats = self._model(target, person if known else None)
            p = float(model.predict_proba(today[feats])[0, 1])
            risks[STEP3_NAME[target]] = round(min(max(p, 0.0), 1.0), 3)
        logged = tuple(s for s in SYMPTOMS if row.get(f"{s}_high") == 1)
        source = (f"{self.headline['model']}:"
                  f"{headline_config(self.headline, 'fatigue_high')}")
        return Forecast(person=str(person), day=int(day), phase=row["phase_next"],
                        risks=risks, logged=logged, source=source)


def _match_id(person, ids):
    """Accept '7' or 7 for an integer id column."""
    if pd.api.types.is_integer_dtype(ids) and isinstance(person, str) and person.isdigit():
        return int(person)
    return person


@cache
def _forecaster(synthetic: bool) -> Forecaster:
    return Forecaster(synthetic)


def get_forecast(id, day: int, synthetic: bool = False) -> Forecast:
    """The Step 2 -> Step 3 contract. See the module docstring."""
    return _forecaster(synthetic).forecast(id, day)


def main():
    parser = argparse.ArgumentParser(description="Print one Step 2 forecast")
    parser.add_argument("--id", required=True)
    parser.add_argument("--day", type=int, required=True, help="day the forecast is for")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    fc = get_forecast(args.id, args.day, args.synthetic)
    print(fc)
    from mealguide.guidance.forecast import triggers
    for t in triggers(fc):
        print(f"  trigger: {t.target} ({t.reason}{f', risk {t.risk}' if t.risk else ''})")


if __name__ == "__main__":
    main()
