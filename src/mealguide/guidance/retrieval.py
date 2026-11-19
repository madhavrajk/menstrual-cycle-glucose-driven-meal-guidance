"""Retrieval: which evidence cards a forecast fires, then which recipes the LLM may choose from.

Everything here is code, so the same forecast and preferences always give the same
candidates, and the LLM never sees a recipe the user can't eat.
"""

import csv
from dataclasses import dataclass

from mealguide.guidance.checks import Preferences, eligible
from mealguide.guidance.forecast import Trigger
from mealguide.paths import RESULTS

SLOTS = ("breakfast", "lunch", "dinner", "snack")
STRENGTH_ORDER = {"low": 0, "very_low": 1, "unsupported": 2}
MAX_CARDS_PER_TRIGGER = 2
MAX_CARDS = 4
CANDIDATES_PER_SLOT = 3
HIGH_FIBER_G = 8.0  # per serving; bloating days avoid these (see the bloating-sodium card)
NUTRITION_FILE = RESULTS / "recipe_nutrition.csv"


@dataclass(frozen=True)
class Candidate:
    recipe: dict
    cards: tuple          # ids of fired cards this recipe serves
    score: float


def load_nutrition(path=NUTRITION_FILE) -> dict[str, dict]:
    """Per-serving nutrition from `make coverage` (recipes only, no participant data)."""
    if not path.exists():
        return {}
    with open(path) as f:
        return {r["id"]: {k: float(v) for k, v in r.items() if k not in ("id", "meal_type")}
                for r in csv.DictReader(f)}


def fired_cards(trigs: list[Trigger], cards: list[dict]) -> list[dict]:
    """Cards matching each trigger, strongest evidence first, capped so the prompt stays
    short. Cards that change portions or meal structure (no food_tags) are included; the
    planner decides what to do with them."""
    chosen = []
    for t in trigs:
        matches = [c for c in cards if c["trigger"]["target"] == t.target
                   and t.reason in c["trigger"]["fires_on"]]
        matches.sort(key=lambda c: (STRENGTH_ORDER[c["strength"]], c["id"]))
        chosen += [c for c in matches[:MAX_CARDS_PER_TRIGGER] if c not in chosen]
    return chosen[:MAX_CARDS]


def candidates(recipes: list[dict], prefs: Preferences, cards: list[dict],
               nutrition: dict[str, dict], bloating: bool = False) -> dict[str, list[Candidate]]:
    """Top eligible recipes per meal slot, ranked by how many fired cards they serve.

    On a bloating day, high-fiber recipes drop down the ranking, because the bloating-sodium
    card conflicts with fiber-heavy pairing.
    """
    food_cards = [c for c in cards if c["food_tags"]]
    out = {}
    for slot in SLOTS:
        ranked = []
        for r in eligible(recipes, prefs):
            if r["meal_type"] != slot:
                continue
            served = tuple(c["id"] for c in food_cards
                           if set(c["food_tags"]) & set(r["evidence_tags"]))
            score = float(len(served))
            if bloating and nutrition.get(r["id"], {}).get("fiber_g", 0) > HIGH_FIBER_G:
                score -= 1.0  # worth one card: a low-fiber match wins over a high-fiber one
            ranked.append(Candidate(r, served, score))
        fiber = (lambda c: nutrition.get(c.recipe["id"], {}).get("fiber_g", 0)) if bloating \
            else (lambda c: 0)
        ranked.sort(key=lambda c: (-c.score, fiber(c), c.recipe["id"]))
        out[slot] = ranked[:CANDIDATES_PER_SLOT]
    return out
