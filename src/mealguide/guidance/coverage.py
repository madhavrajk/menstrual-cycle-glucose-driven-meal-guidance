"""Check the knowledge base as a whole: nutrition for every recipe, tag audit, and coverage.

    make coverage              # report only
    make coverage FIX=1        # also remove tags the nutrition doesn't support

1. Coverage (no API needed): recipes per evidence card x diet, and per meal type x diet.
2. Nutrition for every recipe from FoodData Central (needs FDC_API_KEY; cached), written to
   results/recipe_nutrition.csv. Recipes only, no participant data.
3. Tag audit: each nutrient tag must be backed by the computed nutrition.
   - iron, calcium, magnesium, vitamin_c, b6: FDA "good source", at least 10% of the
     Daily Value per serving (DV: iron 18 mg, calcium 1300 mg, magnesium 420 mg,
     vitamin C 90 mg, B6 1.7 mg).
   - omega3: at least 0.3 g EPA+DHA per serving, the low end of the trial doses.
   - low_sodium: at most 140 mg sodium per 100 g (FDA "low sodium" for meals).
   - protein_first: at least 15 g protein per serving (our rule).
   - plant_based: vegan, with at most 30% of energy from fat.
   - ginger, cinnamon, fennel: the ingredient is in the recipe.
   - low_gi: set by hand; FDC has no glycemic index, so it is not audited.
   It also lists tags a recipe qualifies for but doesn't carry.
"""

import csv
import sys

import yaml

from mealguide.guidance.knowledge import load_cards, load_recipes
from mealguide.paths import RESULTS

DIETS = ("omnivore", "vegetarian", "vegan")
MEALS = ("breakfast", "lunch", "dinner", "snack")
GOOD_SOURCE = {  # tag: (nutrient, 10% of Daily Value)
    "iron": ("iron_mg", 1.8),
    "calcium": ("calcium_mg", 130),
    "magnesium": ("magnesium_mg", 42),
    "vitamin_c": ("vitamin_c_mg", 9),
    "b6": ("vitamin_b6_mg", 0.17),
}
INGREDIENT_TAGS = {"ginger": "ginger", "cinnamon": "cinnamon", "fennel": "fennel"}


def coverage_tables(recipes: list[dict], cards: list[dict]) -> tuple[dict, dict]:
    """(recipes per card per diet, recipes per meal type per diet)."""
    per_card = {}
    for card in cards:
        if card["food_tags"]:
            per_card[card["id"]] = {
                d: sum(1 for r in recipes if d in r["diets"]
                       and set(card["food_tags"]) & set(r["evidence_tags"]))
                for d in DIETS}
    per_meal = {m: {d: sum(1 for r in recipes if r["meal_type"] == m and d in r["diets"])
                    for d in DIETS} for m in MEALS}
    return per_card, per_meal


def qualifying_tags(recipe: dict, per_serving: dict) -> set[str]:
    """Tags this recipe's computed nutrition and ingredients support."""
    tags = {t for t, (n, cut) in GOOD_SOURCE.items() if per_serving[n] >= cut}
    if per_serving["omega3_epa_dha_g"] >= 0.3:
        tags.add("omega3")
    grams_per_serving = sum(i["grams"] for i in recipe["ingredients"]) / recipe["servings"]
    if per_serving["sodium_mg"] / grams_per_serving * 100 <= 140:
        tags.add("low_sodium")
    if per_serving["protein_g"] >= 15:
        tags.add("protein_first")
    kcal = per_serving["energy_kcal"]
    if "vegan" in recipe["diets"] and kcal > 0 and per_serving["fat_g"] * 9 / kcal <= 0.30:
        tags.add("plant_based")
    queries = " ".join(i["fdc_query"].lower() for i in recipe["ingredients"])
    tags |= {t for t, word in INGREDIENT_TAGS.items() if word in queries}
    return tags


def audit(recipe: dict, per_serving: dict) -> tuple[list[str], list[str]]:
    """(tags the recipe carries but its nutrition doesn't support, tags it could add)."""
    supported = qualifying_tags(recipe, per_serving)
    carried = set(recipe["evidence_tags"]) - {"low_gi"}
    return sorted(carried - supported), sorted(supported - carried)


def main(fix: bool = False) -> None:
    recipes, cards = load_recipes(), load_cards()
    per_card, per_meal = coverage_tables(recipes, cards)

    print("Recipes per evidence card (omnivore / vegetarian / vegan):")
    for cid, counts in per_card.items():
        flag = "  <- fewer than 2 for some diet" if min(counts.values()) < 2 else ""
        print(f"  {cid:<24}{counts['omnivore']:>4}{counts['vegetarian']:>4}"
              f"{counts['vegan']:>4}{flag}")
    print("\nRecipes per meal type (omnivore / vegetarian / vegan):")
    for meal, counts in per_meal.items():
        print(f"  {meal:<24}{counts['omnivore']:>4}{counts['vegetarian']:>4}{counts['vegan']:>4}")

    unresolved = [r["id"] for r in recipes if any(i["fdc_id"] is None for i in r["ingredients"])]
    if unresolved:
        sys.exit(f"\n{len(unresolved)} recipes have ingredients without FDC IDs. "
                 f"Run `make fdc` first: {', '.join(unresolved)}")

    from mealguide.guidance.nutrition import fdc_lookup, recipe_nutrition
    lookup = fdc_lookup([i["fdc_id"] for r in recipes for i in r["ingredients"]])
    rows, problems, suggestions = [], [], []
    for r in recipes:
        per_serving = recipe_nutrition(r, lookup)["per_serving"]
        rows.append({"id": r["id"], "meal_type": r["meal_type"], "servings": r["servings"],
                     **{k: round(v, 2) for k, v in per_serving.items()}})
        unsupported, missed = audit(r, per_serving)
        if unsupported:
            problems.append(f"  {r['id']}: tagged but not supported: {', '.join(unsupported)}")
            if fix:
                path = r["_path"]
                data = yaml.safe_load(path.read_text())
                data["evidence_tags"] = [t for t in data["evidence_tags"] if t not in unsupported]
                path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True,
                                               width=100))
        if missed:
            suggestions.append(f"  {r['id']}: qualifies for {', '.join(missed)}")

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "recipe_nutrition.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nNutrition for {len(rows)} recipes written to {out}")
    print("\nTag audit: tags the nutrition doesn't support (fix these):")
    print("\n".join(problems) or "  none")
    if problems and fix:
        print("  (removed from the recipe files; rerun `make test`)")
    elif problems:
        print("  Run `make coverage FIX=1` to remove them.")
    print("\nTags recipes qualify for but don't carry (optional):")
    print("\n".join(suggestions) or "  none")


if __name__ == "__main__":
    main(fix="--fix" in sys.argv[1:])
