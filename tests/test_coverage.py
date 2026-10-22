from mealguide.guidance.coverage import audit, coverage_tables
from mealguide.guidance.knowledge import load_cards, load_recipes

RECIPES, CARDS = load_recipes(), load_cards()


def _per_serving(**over):
    base = dict.fromkeys(["energy_kcal", "protein_g", "fat_g", "carbohydrate_g", "fiber_g",
                          "sugars_g", "sodium_mg", "calcium_mg", "iron_mg", "magnesium_mg",
                          "vitamin_c_mg", "vitamin_b6_mg", "epa_g", "dha_g",
                          "omega3_epa_dha_g"], 0.0)
    base.update(energy_kcal=400.0, **over)
    return base


RECIPE = {"id": "t", "servings": 1, "diets": ["omnivore", "vegetarian", "vegan"],
          "evidence_tags": ["iron", "omega3", "low_sodium", "ginger"],
          "ingredients": [{"fdc_query": "Ginger root, raw", "grams": 200},
                          {"fdc_query": "Lentils, raw", "grams": 100}]}


def test_audit_flags_unsupported_and_suggests_missing():
    # 600 mg sodium in 300 g is 200 mg per 100 g: above the 140 mg low-sodium limit.
    unsupported, missed = audit(RECIPE, _per_serving(iron_mg=3.0, sodium_mg=600.0,
                                                     calcium_mg=200.0, fat_g=5.0))
    assert unsupported == ["low_sodium", "omega3"]
    assert "calcium" in missed and "plant_based" in missed


def test_coverage_counts_every_card_with_food_tags():
    per_card, per_meal = coverage_tables(RECIPES, CARDS)
    assert set(per_card) == {c["id"] for c in CARDS if c["food_tags"]}
    assert all(per_meal[m]["vegan"] > 0 for m in per_meal)
