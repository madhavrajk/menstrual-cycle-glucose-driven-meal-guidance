"""The forecast Step 3 receives, and the rules that turn it into fired evidence cards.

Contract with Step 2: Madhav's `get_forecast(id, day)` (`models/forecast_api.py`) returns a
`Forecast`. `synthetic_forecast` makes seeded stand-ins with the same fields, so the pipeline
and the RQ3 evaluation can run end to end.

Trigger rules (from the proposal, in priority order):
1. Reactive: a symptom the user logged today fires its cards ("logged").
2. Proactive: a next-day risk at or above RISK_THRESHOLD fires its cards ("forecast").
3. Phase fallback: when nothing above fired, the phase fires its cards ("phase"):
   Menstrual -> menses-iron-vitc. Luteal -> luteal-portions, which the planner applies only
   when the team switches `luteal_upper` on.
"""

import zlib
from dataclasses import dataclass, field

import numpy as np

PHASES = ("Menstrual", "Follicular", "Fertility", "Luteal", "Unknown")
TARGETS = ("fatigue", "cramps", "bloating", "cravings", "unstable_glucose")
RISK_THRESHOLD = 0.5  # confirmed Nov 22 from Step 2 calibration (docs/step2_results.md)
PHASE_TARGETS = {"Menstrual": "menses", "Luteal": "luteal"}


@dataclass(frozen=True)
class Forecast:
    """What Step 2 hands Step 3 for one person and one day (made the morning before)."""

    person: str                      # participant id or synthetic profile id
    day: int                         # day_in_study the forecast is FOR
    phase: str                       # calendar phase on that day
    risks: dict = field(default_factory=dict)       # target -> probability, 0-1
    logged: tuple = ()               # symptoms the user logged today (reactive trigger)
    source: str = "synthetic"        # "synthetic" or the model name

    def __post_init__(self):
        if self.phase not in PHASES:
            raise ValueError(f"phase must be one of {PHASES}")
        bad = {k for k, v in self.risks.items() if k not in TARGETS or not 0 <= v <= 1}
        if bad:
            raise ValueError(f"risks must map {TARGETS} to probabilities; bad: {sorted(bad)}")


@dataclass(frozen=True)
class Trigger:
    target: str      # a card trigger target: a symptom, unstable_glucose, menses, or luteal
    reason: str      # "logged", "forecast", or "phase"
    risk: float | None = None


def triggers(fc: Forecast, threshold: float = RISK_THRESHOLD) -> list[Trigger]:
    out = [Trigger(s, "logged") for s in fc.logged if s in TARGETS]
    seen = {t.target for t in out}
    for target, p in sorted(fc.risks.items(), key=lambda kv: -kv[1]):
        if p >= threshold and target not in seen:
            out.append(Trigger(target, "forecast", round(p, 2)))
    if not out and fc.phase in PHASE_TARGETS:
        out.append(Trigger(PHASE_TARGETS[fc.phase], "phase"))
    return out


# Scenarios used by the evaluation: one typical day per situation the planner must handle.
SCENARIOS = {
    "menstrual_cramps": ("Menstrual", {"cramps": 0.75, "fatigue": 0.55}),
    "luteal_cravings_bloating": ("Luteal", {"cravings": 0.7, "bloating": 0.6}),
    "follicular_unstable_glucose": ("Follicular", {"unstable_glucose": 0.65}),
    "menstrual_quiet": ("Menstrual", {}),
    "logged_fatigue": ("Fertility", {}),
}


def synthetic_forecast(person: str, scenario: str, day: int = 1, seed: int = 0) -> Forecast:
    """A seeded stand-in for get_forecast: the scenario's risks, every other target low."""
    phase, high = SCENARIOS[scenario]
    # crc32, not hash(): Python salts string hashes per run, which would change the forecasts
    rng = np.random.default_rng(zlib.crc32(f"{person}|{scenario}|{seed}".encode()))
    risks = {t: round(float(rng.uniform(0.05, 0.35)), 2) for t in TARGETS}
    risks.update(high)
    logged = ("fatigue",) if scenario == "logged_fatigue" else ()
    return Forecast(person, day, phase, risks, logged)
