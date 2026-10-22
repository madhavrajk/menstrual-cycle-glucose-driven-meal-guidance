# knowledge/ (Step 3, Sneha)

Curated inputs for grounded meal guidance. These are not participant data, so they're safe to commit.
One YAML file per item, named `<id>.yaml`. Field rules are enforced by
`src/mealguide/guidance/knowledge.py` and checked in CI by `tests/test_knowledge.py` and
`tests/test_checks.py` (which also checks each recipe's allergen list against its ingredients).

## `recipes/` (50)

| Meal type | Recipes | Fit vegan users |
|---|---|---|
| Breakfast | 12 | 6 |
| Lunch | 13 | 6 |
| Dinner | 15 | 5 |
| Snack | 10 | 9 |

| Field | Meaning |
|---|---|
| `id`, `name` | Slug (matches the file name) and display name |
| `meal_type` | `breakfast`, `lunch`, `dinner`, or `snack` |
| `diets` | Every pattern it fits. Vegan recipes list all three, vegetarian list `vegetarian` + `omnivore` |
| `allergens` | Any of the nine major US allergens: `milk egg fish shellfish tree_nuts peanuts wheat soy sesame` |
| `active_time_min`, `total_time_min` | Hands-on minutes vs. start to finish (soaking, baking) |
| `servings` | Servings the ingredient weights make |
| `ingredients` | `name`, `grams` (whole recipe, in the state `fdc_query` names), `fdc_query`, `fdc_id` |
| `evidence_tags` | Tags that match evidence cards' `food_tags` (audited by `make coverage`) |
| `steps`, `notes` | Method; swaps and cautions |

Nutrition is never typed into a recipe. It is computed from FoodData Central (FDC) by `fdc_id` and `grams`.
New ingredients start with `fdc_id: null`; `make fdc` fills them and marks `fdc_verified: false`
until a person checks the match in `data/fdc_review.csv`. Fiber is not a tag on purpose: the bloating
rule reads the computed fiber value.

### What each tag means (checked by `make coverage`)

| Tag | Rule |
|---|---|
| `iron`, `calcium`, `magnesium`, `vitamin_c`, `b6` | FDA "good source": at least 10% of the Daily Value per serving |
| `omega3` | At least 0.3 g EPA+DHA per serving (low end of the trial doses). Fish only; plant ALA doesn't count |
| `low_sodium` | At most 140 mg sodium per 100 g (FDA "low sodium" for meals) |
| `protein_first` | At least 15 g protein per serving, with a distinct protein component |
| `plant_based` | Vegan, with at most 30% of energy from fat |
| `ginger`, `cinnamon`, `fennel` | The ingredient is in the recipe |
| `low_gi` | Set by hand from the main carbohydrate; FDC has no glycemic index, so not audited |

## `evidence_cards/` (14)

Each card is the one approved statement the app may make for a trigger: `trigger`, `claim`,
`allowed_wording` (the strongest sentence the LLM may say), `food_tags`, `foods`, `research_dose`
(never shown as advice), `population`, `source`, `strength` (`low`, `very_low`, `unsupported`),
`cautions`, `conflicts_with`, and `never_say` (phrases the RQ3 evaluation flags).

Two cards change portions or meal structure rather than foods, so they have no `food_tags`:
`luteal-portions` (off by default, pending a team decision) and `glucose-spread-carbs` (no supporting
trial found, so it makes no health claim). `mood-b6` is used only if the team forecasts mood.

## Commands

```bash
make fdc          # fill missing FDC IDs (needs FDC_API_KEY in .env)
make nutrition    # nutrients for the 3 starter recipes, or RECIPES="id1 id2"
make coverage     # nutrition for all recipes, tag audit, coverage by card/diet/meal
make coverage FIX=1   # same, and remove tags the nutrition doesn't support
```

Restriction checks (`guidance/checks.py`) and portion sizes (`guidance/portions.py`) are code,
never the LLM's job.
