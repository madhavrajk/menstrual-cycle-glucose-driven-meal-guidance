"""USDA FoodData Central lookups.

Fill in missing FDC IDs for every recipe ingredient:

    make fdc          # same as: python -m mealguide.guidance.fdc resolve

Needs FDC_API_KEY in .env (free key: https://fdc.nal.usda.gov/api-key-signup).
Searches Foundation and SR Legacy foods with each ingredient's fdc_query, writes the best
match's fdc_id and fdc_description back into the recipe YAML with fdc_verified: false,
and re-searches any earlier match that is neither exact nor verified by hand,
and writes data/fdc_review.csv (gitignored) listing non-exact matches first. Check each
match is the right food in the right state (dry vs cooked, drained), then set
fdc_verified: true by hand.
"""

import csv
import os
import re
import sys
import time

import requests
import yaml

from mealguide.guidance.knowledge import RECIPES_DIR
from mealguide.paths import REPO_ROOT

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DATA_TYPES = ["Foundation", "SR Legacy"]
REVIEW_FILE = REPO_ROOT / "data" / "fdc_review.csv"


def api_key() -> str:
    key = os.environ.get("FDC_API_KEY")
    if not key:
        sys.exit("FDC_API_KEY is not set. Add it to .env (see .env.example).")
    return key


def normalize(text: str) -> str:
    """Lowercase letters and digits only, so names differing in punctuation compare equal."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def is_exact(query: str, description: str) -> bool:
    return normalize(query) == normalize(description)


def search(query: str, key: str) -> dict | None:
    """Best Foundation/SR Legacy match for a description: exact match if any, else top hit.

    FDC's search treats some punctuation as query syntax (quotes, slashes, a leading hyphen),
    so only letters, digits, commas and spaces are sent; the exact-match check still uses the
    full description. A failed lookup is reported and returns None, so one bad query doesn't
    stop the run.
    """
    resp = requests.get(SEARCH_URL, timeout=30, params={
        "api_key": key,
        "query": " ".join(re.sub(r"[^\w, ]", " ", query).split()),
        "dataType": ",".join(DATA_TYPES),
        "pageSize": 50,
    })
    if not resp.ok:
        print(f"  lookup failed ({resp.status_code}) for: {query}", file=sys.stderr)
        return None
    foods = resp.json().get("foods", [])
    for food in foods:
        if is_exact(query, food["description"]):
            return food
    return foods[0] if foods else None


def resolve() -> None:
    key = api_key()
    cache: dict[str, dict | None] = {}
    rows = []
    for path in sorted(RECIPES_DIR.glob("*.yaml")):
        recipe = yaml.safe_load(path.read_text())
        changed = False
        for ing in recipe["ingredients"]:
            query = ing["fdc_query"]
            redo = (ing.get("fdc_id") is not None and not ing.get("fdc_verified")
                    and not is_exact(query, ing.get("fdc_description", "")))
            if ing.get("fdc_id") is None or redo:
                if query not in cache:
                    cache[query] = search(query, key)
                    time.sleep(0.3)
                match = cache[query]
                if match:
                    ing["fdc_id"] = match["fdcId"]
                    ing["fdc_description"] = match["description"]
                    ing["fdc_verified"] = False
                    changed = True
            rows.append({
                "recipe": recipe["id"],
                "ingredient": ing["name"],
                "query": query,
                "fdc_id": ing.get("fdc_id"),
                "matched_description": ing.get("fdc_description", "NO MATCH"),
                "exact_match": is_exact(query, ing.get("fdc_description", "")),
                "verified": ing.get("fdc_verified", False),
            })
        if changed:
            path.write_text(yaml.safe_dump(recipe, sort_keys=False, allow_unicode=True, width=100))

    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["exact_match"], r["recipe"])))

    missing = sum(r["fdc_id"] is None for r in rows)
    inexact = sum(bool(r["fdc_id"]) and not r["exact_match"] for r in rows)
    print(f"{len(rows)} ingredients, {len(cache)} lookups: {missing} unmatched, "
          f"{inexact} non-exact matches to review in {REVIEW_FILE}")


if __name__ == "__main__":
    if sys.argv[1:] != ["resolve"]:
        sys.exit("Usage: python -m mealguide.guidance.fdc resolve")
    resolve()
