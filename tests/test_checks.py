"""Restriction checker, plus a cross-check that recipe allergen lists match their ingredients."""

import re

import pytest

from mealguide.guidance.checks import Preferences, check_plan, eligible, violations
from mealguide.guidance.knowledge import load_recipes

RECIPES = load_recipes()
BY_ID = {r["id"]: r for r in RECIPES}

# Allergen -> pattern on the FDC description of an ingredient that contains it.
ALLERGEN_PATTERNS = {
    "milk": r"\b(milk|cheese|yogurt|kefir|cream)\b",  # soymilk is renamed before matching
    "egg": r"\begg\b",
    "fish": r"\bfish\b",
    "shellfish": r"\bcrustaceans?\b|\bshrimp\b|\bmollusks?\b",
    "tree_nuts": r"\b(almonds?|walnuts?|cashews?|pecans?|pistachios?|hazelnuts?|"
                 r"macadamia|brazilnuts?)\b",
    "peanuts": r"\bpeanuts?\b",
    "wheat": r"\b(wheat|bread|pasta|english muffins?|shoyu)\b",
    "soy": r"\b(soy|soymilk|tofu|tempeh|edamame|shoyu)\b",
    "sesame": r"\b(sesame|tahini|hummus)\b",
}


def implied_allergens(recipe: dict) -> set[str]:
    found = set()
    for ing in recipe["ingredients"]:
        text = ing["fdc_query"].lower().replace("soymilk", "soy drink")
        for allergen, pattern in ALLERGEN_PATTERNS.items():
            if re.search(pattern, text):
                found.add(allergen)
    return found


@pytest.mark.parametrize("recipe", RECIPES, ids=[r["id"] for r in RECIPES])
def test_allergen_list_covers_ingredients(recipe):
    """A missing allergen is a safety bug: the checker would offer the recipe to someone
    allergic to it."""
    missing = implied_allergens(recipe) - set(recipe["allergens"])
    assert not missing, f"{recipe['id']} contains {sorted(missing)} but doesn't list it"


def test_allergen_patterns_catch_known_cases():
    assert "soy" in implied_allergens(BY_ID["ginger-garlic-salmon"])
    assert "wheat" in implied_allergens(BY_ID["ginger-garlic-salmon"])  # shoyu has wheat
    assert "milk" not in implied_allergens(BY_ID["ginger-cinnamon-overnight-oats"])  # soymilk


def test_vegan_user_never_gets_animal_products():
    prefs = Preferences(diet="vegan")
    for r in eligible(RECIPES, prefs):
        assert not {"milk", "egg", "fish", "shellfish"} & set(r["allergens"])
        assert "vegan" in r["diets"]


def test_allergy_filter():
    prefs = Preferences(allergies=frozenset({"tree_nuts", "sesame"}))
    for r in eligible(RECIPES, prefs):
        assert not {"tree_nuts", "sesame"} & set(r["allergens"])


def test_cooking_time_limit():
    prefs = Preferences(max_active_min=10)
    assert all(r["active_time_min"] <= 10 for r in eligible(RECIPES, prefs))


def test_every_restrictive_profile_still_has_every_meal():
    """Retrieval must never come back empty for a reasonable restrictive user."""
    prefs = Preferences(diet="vegan", allergies=frozenset({"soy", "tree_nuts"}),
                        max_active_min=20)
    meals = {r["meal_type"] for r in eligible(RECIPES, prefs)}
    assert meals == {"breakfast", "lunch", "dinner", "snack"}


def test_deliberate_violations_are_all_caught():
    prefs = Preferences(diet="vegetarian", allergies=frozenset({"milk"}), max_active_min=10)
    plan = [
        "ginger-garlic-salmon",           # fish: not vegetarian, and 15 min hands-on
        "spinach-feta-scramble-toast",    # feta: milk
        "moroccan-chickpea-stew",         # 20 min hands-on
        "made-up-recipe",                 # not in the curated set
        "ginger-lemon-tea",               # fine
    ]
    problems = check_plan(plan, RECIPES, prefs)
    assert len(problems) == 5
    assert not any("ginger-lemon-tea" in p for p in problems)
    assert any("not vegetarian" in p for p in problems)
    assert any("contains milk" in p for p in problems)
    assert any("hands-on" in p for p in problems)
    assert any("not in the curated" in p for p in problems)


def test_bad_preferences_rejected():
    with pytest.raises(ValueError):
        Preferences(diet="pescatarian")
    with pytest.raises(ValueError):
        Preferences(allergies=frozenset({"gluten"}))


def test_violations_empty_for_fitting_recipe():
    assert violations(BY_ID["ginger-lemon-tea"], Preferences(diet="vegan")) == []
