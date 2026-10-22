"""Checks on knowledge/: every recipe and evidence card is valid, and the two fit together."""

import pytest

from mealguide.guidance.knowledge import load_cards, load_recipes, validate_card, validate_recipe

RECIPES = load_recipes()
CARDS = load_cards()


@pytest.mark.parametrize("recipe", RECIPES, ids=[r["id"] for r in RECIPES])
def test_recipe_valid(recipe):
    assert validate_recipe(recipe) == []


@pytest.mark.parametrize("card", CARDS, ids=[c["id"] for c in CARDS])
def test_card_valid(card):
    assert validate_card(card) == []


def test_ids_unique():
    for items in (RECIPES, CARDS):
        ids = [x["id"] for x in items]
        assert len(ids) == len(set(ids))


def test_every_diet_has_each_meal_type():
    for diet in ("omnivore", "vegetarian", "vegan"):
        meals = {r["meal_type"] for r in RECIPES if diet in r["diets"]}
        assert meals == {"breakfast", "lunch", "dinner", "snack"}, diet


def test_every_card_has_matching_recipes():
    """Retrieval must never come back empty when a card fires."""
    for card in CARDS:
        if not card["food_tags"]:  # portion or meal-structure cards change no foods
            continue
        matches = [r for r in RECIPES if set(card["food_tags"]) & set(r["evidence_tags"])]
        assert matches, f"no recipe carries any of {card['food_tags']} for {card['id']}"


def test_card_conflicts_point_to_real_cards():
    ids = {c["id"] for c in CARDS}
    for card in CARDS:
        assert set(card["conflicts_with"]) <= ids, card["id"]


def test_validator_catches_problems():
    good = dict(RECIPES[0])
    good.pop("_path")
    bad = {**good, "meal_type": "brunch", "diets": ["vegan"], "allergens": ["milk"]}
    errors = validate_recipe(bad)
    assert any("meal_type" in e for e in errors)
    assert any("also list vegetarian" in e for e in errors)
