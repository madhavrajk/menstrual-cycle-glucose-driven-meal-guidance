# Preference form (Step 3)

What the app asks before it plans meals, and where each answer goes in the code. Nothing here
is stored with mcPHASES data. In the evaluation, Ava's 20 synthetic profiles
(`notebooks/synthetic_profiles.json`) stand in for real answers.

## Fields

| # | Question shown | Answer type | Allowed values | Code field | Used by |
|---|---|---|---|---|---|
| 1 | Which best describes how you eat? | one choice | omnivore, vegetarian, vegan | `Preferences.diet` | `checks.eligible`, `checks.check_plan` |
| 2 | Do you have any of these food allergies? | any number | milk, egg, fish, shellfish, tree nuts, peanuts, wheat, soy, sesame (the nine major US allergens) | `Preferences.allergies` | same |
| 3 | Most hands-on cooking time you want per recipe | one choice | 10, 15, 20, 30 min, or no limit | `Preferences.max_active_min` (`None` = no limit) | same |
| 4 | Height | number | 120–220 cm (or ft/in, converted) | `height_cm` | `portions.daily_target` |
| 5 | Weight | number | 30–250 kg (or lb, converted) | `weight_kg` | same |
| 6 | Age | whole number | 18–55 | `age` | same |
| 7 | How active is a usual week? | one choice | sedentary, light, moderate, active, very active | `activity` (default `light`) | same |
| 8 | Goal for your weight | one choice | keep it steady, lose, gain | `goal`: maintain / lose / gain (default maintain) | same |
| 9 | Meals and snacks per day | fixed for now | 3 meals + 1 snack | `meal_targets(meals=3, snacks=1)` | `portions.meal_targets` |

Questions 4–8 are optional. If any is skipped, the plan still picks meals but shows one
serving of each and no energy range.

## Rules the form enforces

- **Allergies are hard limits.** A recipe containing any ticked allergen is never a candidate,
  and any plan that includes one is rejected by `check_plan`, whichever planner made it.
- **Unknown values are refused.** `Preferences` raises an error for a diet or allergen outside
  the lists above, so the form must use exactly these values (`tree_nuts`, not "nuts").
- **Under-18s are not asked for weight goals.** The project scope is adults (the mcPHASES
  participants are 18+), so the form stops at age < 18.
- **No weight loss at a low BMI.** If BMI (weight ÷ height²) is under 18.5, a "lose" goal is
  ignored, the plan uses "maintain", and the plan shows the note "BMI under 18.5: weight-loss
  goal not applied". No message about the user's body is shown beyond that note.
- **Deficit cap and floor.** A loss goal is at most 500 kcal/day below estimated needs, and no
  target goes below estimated resting needs (`portions.py`).
- **Ranges, not single numbers.** Energy is shown as a range (±10%, the Mifflin-St Jeor
  accuracy band), because the equation can be off for any one person.

## Wording notes

- "Goal" offers *keep it steady* first, as the default.
- The form never asks about symptoms. Those come from the day's log and Madhav's forecast.
- A short line under the form: "These suggestions are general food ideas, not medical advice.
  Talk to a doctor about severe or new symptoms."

## Not in the first version

Dislikes and cuisines, budget, other diets (halal, kosher, low-FODMAP), medical conditions
(diabetes, PCOS, kidney disease), pregnancy. Anyone reporting a medical condition or
pregnancy should get a "talk to your doctor" message instead of a plan; this is listed as a
limitation in the report.
