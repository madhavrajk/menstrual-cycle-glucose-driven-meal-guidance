"""Restriction checks: code, not the LLM, decides whether a recipe fits a user.

Used twice in Step 3: to filter recipes before retrieval, and to check every plan the LLM
returns. A plan that fails is rejected, never shown.
"""

from dataclasses import dataclass, field

from mealguide.guidance.knowledge import ALLERGENS, DIETS


@dataclass(frozen=True)
class Preferences:
    """What the in-app preference form collects that restricts recipes."""

    diet: str = "omnivore"                      # omnivore, vegetarian, or vegan
    allergies: frozenset = field(default_factory=frozenset)
    max_active_min: int | None = None           # hands-on cooking time limit per recipe

    def __post_init__(self):
        if self.diet not in DIETS:
            raise ValueError(f"diet must be one of {sorted(DIETS)}")
        unknown = set(self.allergies) - ALLERGENS
        if unknown:
            raise ValueError(f"unknown allergies {sorted(unknown)}; use {sorted(ALLERGENS)}")


def violations(recipe: dict, prefs: Preferences) -> list[str]:
    """Every reason this recipe breaks the user's restrictions (empty list means it fits)."""
    problems = []
    if prefs.diet not in recipe["diets"]:
        problems.append(f"{recipe['id']}: not {prefs.diet}")
    clash = sorted(set(recipe["allergens"]) & set(prefs.allergies))
    if clash:
        problems.append(f"{recipe['id']}: contains {', '.join(clash)}")
    if prefs.max_active_min is not None and recipe["active_time_min"] > prefs.max_active_min:
        problems.append(f"{recipe['id']}: {recipe['active_time_min']} min hands-on, "
                        f"limit {prefs.max_active_min}")
    return problems


def eligible(recipes: list[dict], prefs: Preferences) -> list[dict]:
    """Recipes the user can be offered; retrieval only ever sees these."""
    return [r for r in recipes if not violations(r, prefs)]


def check_plan(recipe_ids: list[str], recipes: list[dict], prefs: Preferences) -> list[str]:
    """Check an LLM-proposed plan. Unknown recipe IDs count as violations, since the LLM
    must only choose from the curated set."""
    by_id = {r["id"]: r for r in recipes}
    problems = []
    for rid in recipe_ids:
        if rid not in by_id:
            problems.append(f"{rid}: not in the curated recipe set")
        else:
            problems += violations(by_id[rid], prefs)
    return problems
