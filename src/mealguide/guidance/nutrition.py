"""Recipe nutrition computed from USDA FoodData Central (FDC).

Nutrition is never typed into a recipe or estimated by the LLM. Each ingredient's FDC food
gives nutrients per 100 g; this module scales them by the ingredient's grams, sums over the
recipe, and divides by servings.

    make nutrition                                  # 3 starter recipes, one per diet
    python -m mealguide.guidance.nutrition <recipe id> [<recipe id> ...]

Needs FDC_API_KEY in .env. FDC responses are cached in data/fdc_cache.json (gitignored),
so each food is downloaded once.
"""

import json
import sys
from collections.abc import Callable

import requests

from mealguide.guidance.fdc import api_key
from mealguide.guidance.knowledge import load_recipes
from mealguide.paths import REPO_ROOT

FOODS_URL = "https://api.nal.usda.gov/fdc/v1/foods"
CACHE_FILE = REPO_ROOT / "data" / "fdc_cache.json"
DEFAULT_RECIPES = ["ginger-garlic-salmon", "lemony-lentil-spinach-soup", "tofu-pepper-scramble"]

# Our name -> (FDC nutrient numbers, tried in order, unit). Energy has fallbacks because
# Foundation foods often report Atwater energy (958/957) instead of 208.
NUTRIENTS = {
    "energy_kcal": (["208", "958", "957"], "kcal"),
    "protein_g": (["203"], "g"),
    "fat_g": (["204"], "g"),
    "carbohydrate_g": (["205"], "g"),
    "fiber_g": (["291"], "g"),
    "sugars_g": (["269"], "g"),
    "sodium_mg": (["307"], "mg"),
    "calcium_mg": (["301"], "mg"),
    "iron_mg": (["303"], "mg"),
    "magnesium_mg": (["304"], "mg"),
    "vitamin_c_mg": (["401"], "mg"),
    "vitamin_b6_mg": (["415"], "mg"),
    "epa_g": (["629"], "g"),
    "dha_g": (["621"], "g"),
}

# A function from FDC ID to {nutrient number: amount per 100 g}.
Lookup = Callable[[int], dict[str, float]]


def _per_100g(food: dict) -> dict[str, float]:
    """Nutrient number -> amount per 100 g, from either FDC response format."""
    out = {}
    for item in food.get("foodNutrients", []):
        info = item.get("nutrient", item)  # "full" nests it; "abridged" doesn't
        number = str(info.get("number", "")).strip()
        amount = item.get("amount")
        if number and amount is not None:
            out[number] = float(amount)
    return out


def fdc_lookup(fdc_ids: list[int]) -> Lookup:
    """Fetch the given FDC foods (cached on disk) and return a lookup function."""
    cache = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
    missing = sorted({i for i in fdc_ids if str(i) not in cache})
    if missing:
        key = api_key()
        for start in range(0, len(missing), 20):  # the endpoint takes up to 20 IDs
            resp = requests.post(f"{FOODS_URL}?api_key={key}", timeout=60,
                                 json={"fdcIds": missing[start:start + 20]})
            resp.raise_for_status()
            for food in resp.json():
                cache[str(food["fdcId"])] = _per_100g(food)
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=1))
    absent = [i for i in fdc_ids if str(i) not in cache]
    if absent:
        raise KeyError(f"FDC returned no data for IDs {absent}")
    return lambda fdc_id: cache[str(fdc_id)]


def recipe_nutrition(recipe: dict, lookup: Lookup) -> dict:
    """Per-serving nutrients for one recipe.

    Returns {"per_serving": {name: value}, "missing": {name: [ingredient names]}}.
    A nutrient FDC doesn't report for an ingredient counts as 0 and is listed in
    "missing", so that total is a lower bound.
    """
    totals = dict.fromkeys(NUTRIENTS, 0.0)
    missing: dict[str, list[str]] = {}
    for ing in recipe["ingredients"]:
        if ing["fdc_id"] is None:
            raise ValueError(f"{recipe['id']}: {ing['name']} has no fdc_id; run `make fdc`")
        per100 = lookup(ing["fdc_id"])
        scale = ing["grams"] / 100
        for name, (numbers, _unit) in NUTRIENTS.items():
            value = next((per100[n] for n in numbers if n in per100), None)
            if value is None:
                missing.setdefault(name, []).append(ing["name"])
            else:
                totals[name] += value * scale
    per_serving = {k: v / recipe["servings"] for k, v in totals.items()}
    per_serving["omega3_epa_dha_g"] = per_serving["epa_g"] + per_serving["dha_g"]
    return {"per_serving": per_serving, "missing": missing}


def _fmt(name: str, value: float) -> str:
    unit = "kcal" if name == "energy_kcal" else name.rsplit("_", 1)[-1]
    label = name.removesuffix(f"_{unit}")
    digits = 2 if unit == "g" and value < 1 else 0 if unit == "kcal" else 1
    return f"  {label:<18}{value:>9.{digits}f} {unit}"


def main(recipe_ids: list[str]) -> None:
    recipes = {r["id"]: r for r in load_recipes()}
    unknown = [i for i in recipe_ids if i not in recipes]
    if unknown:
        sys.exit(f"Unknown recipe ids: {unknown}")
    chosen = [recipes[i] for i in recipe_ids]
    lookup = fdc_lookup([ing["fdc_id"] for r in chosen for ing in r["ingredients"]
                         if ing["fdc_id"] is not None])
    for r in chosen:
        result = recipe_nutrition(r, lookup)
        print(f"\n{r['name']}  ({r['id']}, per serving, {r['servings']} serving(s))")
        for name, value in result["per_serving"].items():
            if name not in ("epa_g", "dha_g"):
                print(_fmt(name, value))
        # EPA/DHA are only reported for foods that contain them, so gaps there are expected.
        for name, ings in result["missing"].items():
            if name not in ("epa_g", "dha_g"):
                print(f"  note: FDC has no {name} for {', '.join(ings)} (counted as 0)")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_RECIPES)
