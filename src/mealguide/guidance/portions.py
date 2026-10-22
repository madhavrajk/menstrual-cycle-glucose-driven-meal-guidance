"""Daily energy targets and recipe portion sizes (Mifflin-St Jeor). DRAFT for team review.

Resting energy (REE), Mifflin et al. 1990 (kg, cm, years):
    female: 10*weight + 6.25*height - 5*age - 161
    male:   10*weight + 6.25*height - 5*age + 5

Mifflin-St Jeor predicted REE within 10% of measured in more people than any other equation,
but individual errors can be larger (Frankenfield et al., J Am Diet Assoc 2005;105(5):775-789),
so targets are shown as a +/-10% range, never as one exact number.

Safety rules from the proposal:
- a weight-loss deficit is capped (MAX_DEFICIT_KCAL), and
- no target, or low end of a range, ever goes below estimated resting needs (REE);
- a loss goal is ignored when BMI is under 18.5.

Pending team decisions: GAIN_SURPLUS_KCAL and the luteal option (off by default; see the
`luteal-portions` evidence card).
"""

from dataclasses import dataclass

ACTIVITY_FACTORS = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725,
                    "very_active": 1.9}
MAX_DEFICIT_KCAL = 500   # about 0.5 kg a week; our choice, not from the proposal's sources
GAIN_SURPLUS_KCAL = 250  # provisional
RANGE_FRACTION = 0.10    # Mifflin-St Jeor accuracy band (Frankenfield 2005)
SNACK_SHARE = 0.10       # each snack gets 10% of the day; meals split the rest evenly


@dataclass(frozen=True)
class EnergyTarget:
    ree: float      # estimated resting needs
    tdee: float     # with activity
    low: float
    target: float   # the number portions are sized to
    high: float
    notes: tuple[str, ...] = ()


def ree(weight_kg: float, height_cm: float, age: int, sex: str = "female") -> float:
    if not 30 <= weight_kg <= 250 or not 120 <= height_cm <= 220 or not 18 <= age <= 80:
        raise ValueError("weight 30-250 kg, height 120-220 cm, and age 18-80 are supported")
    if sex not in ("female", "male"):
        raise ValueError("sex must be 'female' or 'male' (the equation's two constants)")
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + (-161 if sex == "female" else 5)


def daily_target(weight_kg: float, height_cm: float, age: int, activity: str = "light",
                 goal: str = "maintain", sex: str = "female", luteal: bool = False,
                 luteal_upper: bool = False) -> EnergyTarget:
    """Daily energy range for one user.

    luteal: the user is in the luteal phase today.
    luteal_upper: team setting; when True, luteal days aim at the top of the range.
    """
    if activity not in ACTIVITY_FACTORS:
        raise ValueError(f"activity must be one of {sorted(ACTIVITY_FACTORS)}")
    if goal not in ("maintain", "lose", "gain"):
        raise ValueError("goal must be maintain, lose, or gain")

    rest = ree(weight_kg, height_cm, age, sex)
    tdee = rest * ACTIVITY_FACTORS[activity]
    notes = []

    bmi = weight_kg / (height_cm / 100) ** 2
    if goal == "lose" and bmi < 18.5:
        goal = "maintain"
        notes.append("BMI under 18.5: weight-loss goal not applied")

    center = {"maintain": tdee, "lose": tdee - MAX_DEFICIT_KCAL,
              "gain": tdee + GAIN_SURPLUS_KCAL}[goal]
    if center < rest:
        center = rest
        notes.append("deficit limited so the target stays at or above resting needs")

    low = max(rest, center * (1 - RANGE_FRACTION))
    high = center * (1 + RANGE_FRACTION)
    target = high if (luteal and luteal_upper) else center
    if luteal and luteal_upper:
        notes.append("luteal phase: aiming at the top of the range")
    return EnergyTarget(round(rest), round(tdee), round(low), round(target), round(high),
                        tuple(notes))


def meal_targets(daily_kcal: float, meals: int = 3, snacks: int = 1) -> dict[str, float]:
    """Split a day's target across meals and snacks."""
    if not 1 <= meals <= 6 or not 0 <= snacks <= 3:
        raise ValueError("1-6 meals and 0-3 snacks are supported")
    snack_kcal = daily_kcal * SNACK_SHARE
    meal_kcal = (daily_kcal - snacks * snack_kcal) / meals
    return {"meal": round(meal_kcal), "snack": round(snack_kcal) if snacks else 0}


def scale_factor(recipe_kcal_per_serving: float, slot_kcal: float) -> float:
    """How many servings of a recipe fill one meal or snack slot: nearest quarter serving,
    kept between 0.5 and 2 so portions stay realistic."""
    if recipe_kcal_per_serving <= 0:
        raise ValueError("recipe energy must be positive")
    raw = slot_kcal / recipe_kcal_per_serving
    return min(2.0, max(0.5, round(raw * 4) / 4))
