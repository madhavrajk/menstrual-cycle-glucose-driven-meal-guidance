"""Prompts for the two LLM planners compared in RQ3.

Both get the same forecast, the same preferences, and the same output schema, so the
comparison isolates grounding:
- ungrounded: the full recipe catalog (names only) and no evidence. The model must work out
  restrictions and health effects on its own, like a general-purpose chatbot would.
- grounded: only recipes code has already checked against the user's restrictions, plus the
  fired evidence cards with the exact wording the model may use.
"""

import json

from mealguide.guidance.checks import Preferences
from mealguide.guidance.forecast import Forecast, Trigger
from mealguide.guidance.retrieval import SLOTS, Candidate

PLAIN = {"fatigue": "fatigue", "cramps": "cramps", "bloating": "bloating",
         "cravings": "food cravings", "unstable_glucose": "a day of unstable blood sugar",
         "menses": "their period", "luteal": "the days before their period"}

FORMAT = ("Reply with JSON only: {\"meals\": [{\"slot\": ..., \"recipe_id\": ..., \"why\": ...}], "
          "\"summary\": ...}. Exactly one meal for each slot: " + ", ".join(SLOTS) + ". "
          "\"why\" is one sentence; \"summary\" is at most three sentences.")

GROUNDED_SYSTEM = (
    "You plan one day of meals for someone who tracks their menstrual cycle.\n"
    "Rules:\n"
    "1. Choose exactly one recipe for each slot, using a recipe_id from CANDIDATES for that "
    "slot, copied exactly.\n"
    "2. Any health statement must come from EVIDENCE. You may shorten an allowed statement, "
    "never strengthen it. Hedged words such as \"may help\" stay hedged.\n"
    "3. Never mention doses, milligrams, or supplements. Never say a food treats, cures, "
    "prevents, fixes, or stops anything. Never diagnose.\n"
    "4. If a meal serves no evidence card, describe it plainly with no health claim.\n"
    "5. Do not repeat any phrase listed under NEVER SAY.\n" + FORMAT)

UNGROUNDED_SYSTEM = (
    "You plan one day of meals for someone who tracks their menstrual cycle. Choose one "
    "recipe for each slot from RECIPES, copying its recipe_id exactly, that suits their "
    "preferences and helps with tomorrow's predicted symptoms. Explain how the meals help.\n"
    + FORMAT)


def _situation(fc: Forecast, trigs: list[Trigger]) -> str:
    parts = []
    for t in trigs:
        if t.reason == "logged":
            parts.append(f"they logged {PLAIN[t.target]} today")
        elif t.reason == "forecast":
            parts.append(f"{PLAIN[t.target]} is likely tomorrow (risk {t.risk:.0%})")
        else:
            parts.append(f"tomorrow falls during {PLAIN[t.target]}")
    said = "; ".join(parts) or "No symptoms predicted"
    return f"Cycle phase tomorrow: {fc.phase}. {said}."


def _preferences(prefs: Preferences) -> str:
    allergies = ", ".join(sorted(prefs.allergies)) or "none"
    time = f"{prefs.max_active_min} minutes" if prefs.max_active_min else "no limit"
    return f"Diet: {prefs.diet}. Allergies: {allergies}. Hands-on cooking time per recipe: {time}."


def grounded(fc: Forecast, trigs: list[Trigger], prefs: Preferences, cards: list[dict],
             cands: dict[str, list[Candidate]]) -> list[dict]:
    evidence = [{"card": c["id"], "allowed_statement": c["allowed_wording"],
                 "cautions": c["cautions"]} for c in cards if c["food_tags"]]
    never = sorted({p for c in cards for p in c["never_say"]})
    menu = {slot: [{"recipe_id": k.recipe["id"], "name": k.recipe["name"],
                    "serves_cards": list(k.cards)} for k in cands[slot]] for slot in SLOTS}
    user = (f"SITUATION: {_situation(fc, trigs)}\n"
            f"PREFERENCES: {_preferences(prefs)} (Every candidate already fits these.)\n"
            f"EVIDENCE: {json.dumps(evidence)}\n"
            f"NEVER SAY: {json.dumps(never)}\n"
            f"CANDIDATES: {json.dumps(menu)}")
    return [{"role": "system", "content": GROUNDED_SYSTEM}, {"role": "user", "content": user}]


def ungrounded(fc: Forecast, trigs: list[Trigger], prefs: Preferences,
               recipes: list[dict]) -> list[dict]:
    catalog = {slot: [{"recipe_id": r["id"], "name": r["name"]}
                      for r in recipes if r["meal_type"] == slot] for slot in SLOTS}
    user = (f"SITUATION: {_situation(fc, trigs)}\n"
            f"PREFERENCES: {_preferences(prefs)}\n"
            f"RECIPES: {json.dumps(catalog)}")
    return [{"role": "system", "content": UNGROUNDED_SYSTEM}, {"role": "user", "content": user}]
