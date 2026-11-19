"""Step 3 end to end: forecast -> triggers -> retrieval -> planner -> code checks -> portions.

    make plan                                  # synthetic-01, menstrual_cramps, grounded
    make plan PROFILE=synthetic-07 SCENARIO=luteal_cravings_bloating MODE=ungrounded
    make plan MODE=rule                        # no LLM needed

Three planners share everything except the middle step (RQ3 compares them):
- rule: no LLM; top candidate per slot, card wording as written
- ungrounded: an LLM with the full catalog and no evidence
- grounded: an LLM with pre-checked candidates and the fired evidence cards

Whatever a planner returns, code then checks it (recipe exists, fits the restrictions) and
sets portions and nutrition. In an app a plan with any violation is rejected, never shown.
"""

import argparse
import json
from dataclasses import dataclass, field

from mealguide.guidance import prompts
from mealguide.guidance.checks import Preferences, check_plan
from mealguide.guidance.claims import audit, n_unsupported
from mealguide.guidance.forecast import SCENARIOS, Forecast, synthetic_forecast, triggers
from mealguide.guidance.knowledge import load_cards, load_recipes
from mealguide.guidance.portions import daily_target, meal_targets, scale_factor
from mealguide.guidance.retrieval import SLOTS, candidates, fired_cards, load_nutrition
from mealguide.guidance.schema import PLAN_SCHEMA, parse_plan, plan_text
from mealguide.paths import REPO_ROOT

MODES = ("rule", "ungrounded", "grounded")
PROFILES_FILE = REPO_ROOT / "notebooks" / "synthetic_profiles.json"
LUTEAL_UPPER = False  # team decision pending (docs/decisions.md); see luteal-portions card
TOTALS = ("energy_kcal", "protein_g", "fiber_g", "sodium_mg", "calcium_mg", "iron_mg")


@dataclass
class Knowledge:
    recipes: list
    cards: list
    nutrition: dict

    @classmethod
    def load(cls) -> "Knowledge":
        return cls(load_recipes(), load_cards(), load_nutrition())


@dataclass
class PlanResult:
    mode: str
    person: str
    triggers: list
    cards: list
    plan: dict | None                     # None if the planner never produced valid JSON
    format_problems: list = field(default_factory=list)
    restriction_problems: list = field(default_factory=list)
    off_menu: list = field(default_factory=list)  # grounded only: valid recipe, not a candidate
    claims: dict = field(default_factory=dict)
    energy: dict = field(default_factory=dict)
    totals: dict = field(default_factory=dict)
    attempts: int = 0

    @property
    def shown(self) -> bool:
        """Would an app show this plan? Only if it parsed and broke no restriction."""
        return self.plan is not None and not self.restriction_problems

    @property
    def unsupported(self) -> int:
        return n_unsupported(self.claims) if self.claims else 0


def load_profiles(path=PROFILES_FILE) -> list[dict]:
    return json.loads(path.read_text())


def preferences(profile: dict) -> Preferences:
    return Preferences(profile["diet"], frozenset(profile["allergies"]),
                       profile.get("max_active_min"))


def _rule_plan(cards: list[dict], cands: dict, prefs: Preferences) -> dict:
    wording = {c["id"]: c["allowed_wording"] for c in cards}
    meals, used_cards = [], []
    for slot in SLOTS:
        if not cands[slot]:
            continue
        top = cands[slot][0]
        fresh = [c for c in top.cards if c not in used_cards] or list(top.cards)
        if fresh:
            used_cards.append(fresh[0])
            why = wording[fresh[0]]
        else:
            why = (f"Fits your {prefs.diet} diet and takes {top.recipe['active_time_min']} "
                   f"minutes hands-on.")
        meals.append({"slot": slot, "recipe_id": top.recipe["id"], "why": why})
    used = [wording[c["id"]] for c in cards if c["food_tags"]][:2]
    summary = " ".join(used) or "A balanced day of meals that fits your diet and cooking time."
    return {"meals": meals, "summary": summary}


def _ask(backend, messages: list[dict]) -> tuple[dict | None, list[str], int]:
    """One retry: if the reply isn't a valid plan, show the model its problems once."""
    reply = backend(messages, PLAN_SCHEMA)
    plan, problems = parse_plan(reply)
    if plan is not None:
        return plan, [], 1
    retry = messages + [{"role": "assistant", "content": reply},
                        {"role": "user", "content": "That reply had problems: "
                         + "; ".join(problems) + ". Reply again with corrected JSON only."}]
    plan, problems2 = parse_plan(backend(retry, PLAN_SCHEMA))
    return plan, ([] if plan is not None else problems2), 2


def make_plan(profile: dict, fc: Forecast, mode: str, backend=None,
              kb: Knowledge | None = None) -> PlanResult:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    kb = kb or Knowledge.load()
    prefs = preferences(profile)
    trigs = triggers(fc)
    cards = fired_cards(trigs, kb.cards)
    cands = candidates(kb.recipes, prefs, cards, kb.nutrition,
                       bloating=any(t.target == "bloating" for t in trigs))
    result = PlanResult(mode, profile["profile_id"], [t.__dict__ for t in trigs],
                        [c["id"] for c in cards], None)

    if mode == "rule":
        plan, problems, attempts = _rule_plan(cards, cands, prefs), [], 0
    else:
        if backend is None:
            raise ValueError(f"mode {mode} needs an LLM backend")
        messages = (prompts.grounded(fc, trigs, prefs, cards, cands) if mode == "grounded"
                    else prompts.ungrounded(fc, trigs, prefs, kb.recipes))
        plan, problems, attempts = _ask(backend, messages)
    result.format_problems, result.attempts = problems, attempts
    if plan is None:
        return result

    ids = [m["recipe_id"] for m in plan["meals"]]
    result.plan = plan
    result.restriction_problems = check_plan(ids, kb.recipes, prefs)
    allowed = {k.recipe["id"] for slot in SLOTS for k in cands[slot]}
    result.off_menu = [i for i in ids if i not in allowed] if mode == "grounded" else []
    result.claims = audit(plan_text(plan), kb.cards)

    # Portions and nutrition: code only.
    energy = daily_target(profile["weight_kg"], profile["height_cm"], profile["age"],
                          profile.get("activity", "light"), profile.get("goal", "maintain"),
                          luteal=fc.phase == "Luteal", luteal_upper=LUTEAL_UPPER)
    slots_kcal = meal_targets(energy.target, meals=3, snacks=1)
    result.energy = {"low": energy.low, "target": energy.target, "high": energy.high,
                     "notes": list(energy.notes)}
    totals = dict.fromkeys(TOTALS, 0.0)
    for m in plan["meals"]:
        n = kb.nutrition.get(m["recipe_id"])
        if not n or not n.get("energy_kcal"):
            continue
        kcal_slot = slots_kcal["snack" if m["slot"] == "snack" else "meal"]
        m["servings"] = scale_factor(n["energy_kcal"], kcal_slot)
        for k in TOTALS:
            totals[k] += n[k] * m["servings"]
    result.totals = {k: round(v, 1) for k, v in totals.items()}
    return result


def show(r: PlanResult, kb: Knowledge) -> None:
    names = {x["id"]: x["name"] for x in kb.recipes}
    print(f"\n{r.person} · {r.mode} · triggers: "
          + (", ".join(f"{t['target']} ({t['reason']})" for t in r.triggers) or "none"))
    print(f"Evidence cards: {', '.join(r.cards) or 'none'}")
    if r.plan is None:
        print("No valid plan: " + "; ".join(r.format_problems))
        return
    for m in r.plan["meals"]:
        serv = f" x{m['servings']:g}" if "servings" in m else ""
        print(f"  {m['slot']:<10} {names.get(m['recipe_id'], m['recipe_id'] + ' (UNKNOWN)')}{serv}")
        print(f"             {m['why']}")
    print(f"Summary: {r.plan['summary']}")
    print(f"Energy target {r.energy['target']} kcal (range {r.energy['low']}-{r.energy['high']}); "
          f"plan totals: " + ", ".join(f"{k} {v:g}" for k, v in r.totals.items()))
    status = "SHOWN" if r.shown else "REJECTED"
    print(f"Checks: {status}. Restrictions: {r.restriction_problems or 'ok'}. "
          f"Off-menu: {r.off_menu or 'none'}. Unsupported claims: {r.unsupported} {r.claims}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default="synthetic-01")
    parser.add_argument("--scenario", default="menstrual_cramps", choices=sorted(SCENARIOS))
    parser.add_argument("--mode", default="grounded", choices=MODES)
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
    from mealguide.guidance.llm import OllamaBackend

    profile = next((p for p in load_profiles() if p["profile_id"] == args.profile), None)
    if profile is None:
        raise SystemExit(f"No profile {args.profile} in {PROFILES_FILE}")
    kb = Knowledge.load()
    fc = synthetic_forecast(args.profile, args.scenario)
    backend = None if args.mode == "rule" else OllamaBackend()
    show(make_plan(profile, fc, args.mode, backend, kb), kb)


if __name__ == "__main__":
    main()
