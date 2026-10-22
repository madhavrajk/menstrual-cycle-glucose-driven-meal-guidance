"""Load and validate the curated knowledge base in knowledge/ (recipes and evidence cards).

Each recipe and each card is one YAML file. The field rules live here so the test suite,
retrieval, and the restriction checker all agree on them. Nutrition is never stored in a
recipe; it is computed from FoodData Central using each ingredient's fdc_id and grams.
"""

from pathlib import Path

import yaml

from mealguide.paths import REPO_ROOT

KNOWLEDGE = REPO_ROOT / "knowledge"
RECIPES_DIR = KNOWLEDGE / "recipes"
CARDS_DIR = KNOWLEDGE / "evidence_cards"

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}
DIETS = {"omnivore", "vegetarian", "vegan"}
# The nine major US food allergens.
ALLERGENS = {"milk", "egg", "fish", "shellfish", "tree_nuts", "peanuts", "wheat", "soy", "sesame"}
# Shared vocabulary: a card's food_tags must match recipes' evidence_tags.
FOOD_TAGS = {
    "ginger", "cinnamon", "fennel", "omega3", "iron", "vitamin_c", "calcium", "magnesium",
    "b6", "low_sodium", "low_gi", "protein_first", "plant_based",
}
TRIGGER_TARGETS = {"cramps", "fatigue", "bloating", "cravings", "mood", "unstable_glucose",
                   "menses", "luteal"}
FIRES_ON = {"forecast", "logged", "phase"}
STRENGTHS = {"low", "very_low", "unsupported"}

RECIPE_FIELDS = {"id", "name", "meal_type", "diets", "allergens", "active_time_min",
                 "total_time_min", "servings", "ingredients", "evidence_tags", "steps"}
OPTIONAL_RECIPE_FIELDS = {"notes"}
INGREDIENT_FIELDS = {"name", "grams", "fdc_query", "fdc_id"}
OPTIONAL_INGREDIENT_FIELDS = {"fdc_description", "fdc_verified"}
CARD_FIELDS = {"id", "trigger", "claim", "allowed_wording", "food_tags", "foods",
               "research_dose", "population", "source", "strength", "strength_reason",
               "cautions", "conflicts_with", "never_say"}


def _load_dir(folder: Path) -> list[dict]:
    items = []
    for path in sorted(folder.glob("*.yaml")):
        with open(path) as f:
            item = yaml.safe_load(f)
        item["_path"] = path
        items.append(item)
    return items


def load_recipes(folder: Path = RECIPES_DIR) -> list[dict]:
    return _load_dir(folder)


def load_cards(folder: Path = CARDS_DIR) -> list[dict]:
    return _load_dir(folder)


def _check_fields(obj: dict, required: set, optional: set, where: str) -> list[str]:
    keys = set(obj) - {"_path"}
    errors = [f"{where}: missing {k}" for k in sorted(required - keys)]
    errors += [f"{where}: unknown field {k}" for k in sorted(keys - required - optional)]
    return errors


def _check_subset(values, allowed: set, field: str, where: str) -> list[str]:
    if not isinstance(values, list):
        return [f"{where}: {field} must be a list"]
    errors = [f"{where}: {field} has unknown value {v!r}" for v in values if v not in allowed]
    if len(values) != len(set(values)):
        errors.append(f"{where}: {field} has duplicates")
    return errors


def validate_recipe(r: dict) -> list[str]:
    """Return a list of problems with one recipe (empty list means valid)."""
    where = f"recipe {r.get('id', r.get('_path'))}"
    errors = _check_fields(r, RECIPE_FIELDS, OPTIONAL_RECIPE_FIELDS, where)
    if errors:
        return errors

    path = r.get("_path")
    if path is not None and Path(path).stem != r["id"]:
        errors.append(f"{where}: file name must be {r['id']}.yaml")
    if r["meal_type"] not in MEAL_TYPES:
        errors.append(f"{where}: meal_type {r['meal_type']!r} not in {sorted(MEAL_TYPES)}")
    errors += _check_subset(r["diets"], DIETS, "diets", where)
    if not r["diets"]:
        errors.append(f"{where}: diets is empty")
    if "vegan" in r["diets"] and "vegetarian" not in r["diets"]:
        errors.append(f"{where}: a vegan recipe must also list vegetarian")
    if "vegetarian" in r["diets"] and "omnivore" not in r["diets"]:
        errors.append(f"{where}: a vegetarian recipe must also list omnivore")
    if "vegan" in r["diets"] and {"milk", "egg", "fish", "shellfish"} & set(r["allergens"]):
        errors.append(f"{where}: vegan recipe lists an animal-product allergen")
    if "vegetarian" in r["diets"] and {"fish", "shellfish"} & set(r["allergens"]):
        errors.append(f"{where}: vegetarian recipe lists fish or shellfish")
    errors += _check_subset(r["allergens"], ALLERGENS, "allergens", where)
    errors += _check_subset(r["evidence_tags"], FOOD_TAGS, "evidence_tags", where)

    for field in ("active_time_min", "total_time_min", "servings"):
        if not isinstance(r[field], int) or r[field] < 0:
            errors.append(f"{where}: {field} must be a non-negative integer")
    if isinstance(r["active_time_min"], int) and isinstance(r["total_time_min"], int):
        if r["active_time_min"] > r["total_time_min"]:
            errors.append(f"{where}: active_time_min exceeds total_time_min")
    if r["servings"] == 0:
        errors.append(f"{where}: servings must be at least 1")
    if not r["steps"]:
        errors.append(f"{where}: steps is empty")

    if not r["ingredients"]:
        errors.append(f"{where}: ingredients is empty")
    for i, ing in enumerate(r["ingredients"]):
        iw = f"{where} ingredient {i} ({ing.get('name')})"
        errs = _check_fields(ing, INGREDIENT_FIELDS, OPTIONAL_INGREDIENT_FIELDS, iw)
        if errs:
            errors += errs
            continue
        if not isinstance(ing["grams"], (int, float)) or ing["grams"] <= 0:
            errors.append(f"{iw}: grams must be a positive number")
        if ing["fdc_id"] is not None and not isinstance(ing["fdc_id"], int):
            errors.append(f"{iw}: fdc_id must be an integer or null")
        if not ing["fdc_query"]:
            errors.append(f"{iw}: fdc_query is empty")
    return errors


def validate_card(c: dict) -> list[str]:
    """Return a list of problems with one evidence card (empty list means valid)."""
    where = f"card {c.get('id', c.get('_path'))}"
    errors = _check_fields(c, CARD_FIELDS, set(), where)
    if errors:
        return errors

    path = c.get("_path")
    if path is not None and Path(path).stem != c["id"]:
        errors.append(f"{where}: file name must be {c['id']}.yaml")
    trigger = c["trigger"]
    if trigger.get("target") not in TRIGGER_TARGETS:
        errors.append(f"{where}: trigger.target {trigger.get('target')!r} not recognized")
    errors += _check_subset(trigger.get("fires_on", []), FIRES_ON, "trigger.fires_on", where)
    errors += _check_subset(c["food_tags"], FOOD_TAGS, "food_tags", where)
    if c["strength"] not in STRENGTHS:
        errors.append(f"{where}: strength {c['strength']!r} not in {sorted(STRENGTHS)}")
    if not c["source"].get("citation"):
        errors.append(f"{where}: source.citation is empty")
    if c["strength"] != "unsupported" and not c["source"].get("url"):
        errors.append(f"{where}: a sourced card needs source.url")
    if not c["never_say"]:
        errors.append(f"{where}: never_say is empty")
    return errors
