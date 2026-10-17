"""Nutrition math, with made-up FDC data so the test needs no API key or network."""

import pytest

from mealguide.guidance.nutrition import _per_100g, recipe_nutrition

# Per 100 g, keyed by FDC nutrient number.
FAKE = {
    1: {"208": 100.0, "203": 10.0, "307": 50.0, "291": 2.0, "629": 0.5, "621": 1.0},
    2: {"958": 200.0, "203": 4.0, "307": 0.0},  # energy only as Atwater (958); no fiber
}

RECIPE = {
    "id": "test", "servings": 2,
    "ingredients": [
        {"name": "fish", "grams": 200, "fdc_id": 1},
        {"name": "grain", "grams": 50, "fdc_id": 2},
    ],
}


def test_scales_by_grams_and_servings():
    out = recipe_nutrition(RECIPE, FAKE.__getitem__)["per_serving"]
    assert out["energy_kcal"] == pytest.approx((100 * 2 + 200 * 0.5) / 2)  # 150
    assert out["protein_g"] == pytest.approx((10 * 2 + 4 * 0.5) / 2)       # 11
    assert out["sodium_mg"] == pytest.approx(50 * 2 / 2)
    assert out["omega3_epa_dha_g"] == pytest.approx(1.5 * 2 / 2)


def test_missing_nutrients_are_reported():
    missing = recipe_nutrition(RECIPE, FAKE.__getitem__)["missing"]
    assert missing["fiber_g"] == ["grain"]
    assert "energy_kcal" not in missing  # found via the 958 fallback


def test_unresolved_ingredient_raises():
    bad = {**RECIPE, "ingredients": [{"name": "x", "grams": 10, "fdc_id": None}]}
    with pytest.raises(ValueError, match="make fdc"):
        recipe_nutrition(bad, FAKE.__getitem__)


def test_reads_both_fdc_formats():
    full = {"foodNutrients": [{"nutrient": {"number": "208"}, "amount": 52.0}]}
    abridged = {"foodNutrients": [{"number": "208", "amount": 52.0}]}
    assert _per_100g(full) == _per_100g(abridged) == {"208": 52.0}
