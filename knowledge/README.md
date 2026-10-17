# knowledge/ (Step 3, Sneha)

Curated inputs for grounded meal guidance. These are not participant data, so they're safe to commit.
One YAML file per item, named `<id>.yaml`. Field rules are enforced by
`src/mealguide/guidance/knowledge.py` and checked in CI by `tests/test_knowledge.py`.

## `recipes/` (15 now, about 50 by Week 5)

| Field | Meaning |
|---|---|
| `id`, `name` | Slug (matches the file name) and display name |
| `meal_type` | `breakfast`, `lunch`, `dinner`, or `snack` |
| `diets` | Every pattern it fits. Vegan recipes list all three, vegetarian list `vegetarian` + `omnivore` |
| `allergens` | Any of the nine major US allergens: `milk egg fish shellfish tree_nuts peanuts wheat soy sesame` |
| `active_time_min`, `total_time_min` | Hands-on minutes vs. start to finish (soaking, baking) |
| `servings` | Servings the ingredient weights make |
| `ingredients` | `name`, `grams` (whole recipe, in the state `fdc_query` names), `fdc_query`, `fdc_id` |
| `evidence_tags` | Tags that match evidence cards' `food_tags` |
| `steps`, `notes` | Method; swaps and cautions |

Nutrition is never typed into a recipe. It is computed from FoodData Central (FDC) by `fdc_id` and `grams`.
New ingredients start with `fdc_id: null`; `make fdc` fills them and marks `fdc_verified: false`
until a person checks the match in `data/fdc_review.csv`. Fiber is not a tag on purpose: the bloating
rule reads the computed fiber value.

## `evidence_cards/` (5 now)

Each card is the one approved statement the app may make for a trigger: `trigger`, `claim`,
`allowed_wording` (the strongest sentence the LLM may say), `food_tags`, `foods`, `research_dose`
(never shown as advice), `population`, `source`, `strength` (`low`, `very_low`, `unsupported`),
`cautions`, `conflicts_with`, and `never_say` (phrases the RQ3 evaluation flags).
