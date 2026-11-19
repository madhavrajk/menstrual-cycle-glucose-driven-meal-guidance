"""Step 3 pipeline: triggers, retrieval, schema, claims audit, planners, and the RQ3 harness.

No test calls a real model: FakeBackend returns scripted replies, good and deliberately bad.
"""

import json
import re

import pytest

from mealguide.guidance import evaluate
from mealguide.guidance.checks import Preferences
from mealguide.guidance.claims import audit, n_unsupported
from mealguide.guidance.forecast import Forecast, synthetic_forecast, triggers
from mealguide.guidance.llm import FakeBackend
from mealguide.guidance.plan import Knowledge, load_profiles, make_plan
from mealguide.guidance.retrieval import SLOTS, candidates, fired_cards
from mealguide.guidance.schema import parse_plan

KB = Knowledge.load()
PROFILES = load_profiles()
P1 = PROFILES[0]


def _picker(messages, schema):
    """A well-behaved fake model: first listed recipe per slot (CANDIDATES or RECIPES)."""
    user = messages[1]["content"]
    menu = json.loads(re.search(r"(?:CANDIDATES|RECIPES): (.*)$", user, re.M).group(1))
    return json.dumps({"meals": [{"slot": s, "recipe_id": menu[s][0]["recipe_id"],
                                  "why": "This fits your preferences."} for s in SLOTS],
                       "summary": "Some studies suggest ginger may ease period cramps."})


def _bad_plan(recipe_ids):
    return json.dumps({"meals": [{"slot": s, "recipe_id": rid, "why": "Ginger cures cramps."}
                                 for s, rid in zip(SLOTS, recipe_ids, strict=True)],
                       "summary": "Take a 500 mg magnesium supplement to stop your cramps."})


# ---------------------------------------------------------------- triggers
def test_logged_then_forecast_then_phase():
    fc = Forecast("x", 1, "Menstrual", {"cramps": 0.8, "fatigue": 0.6, "bloating": 0.2},
                  logged=("fatigue",))
    assert [(t.target, t.reason) for t in triggers(fc)] == [("fatigue", "logged"),
                                                           ("cramps", "forecast")]


def test_phase_fallback_only_when_nothing_else_fires():
    quiet = Forecast("x", 1, "Menstrual", {"cramps": 0.2})
    assert [(t.target, t.reason) for t in triggers(quiet)] == [("menses", "phase")]
    assert triggers(Forecast("x", 1, "Follicular", {"cramps": 0.2})) == []


def test_forecast_validation():
    with pytest.raises(ValueError):
        Forecast("x", 1, "Ovulation")
    with pytest.raises(ValueError):
        Forecast("x", 1, "Luteal", {"cramps": 1.5})


def test_synthetic_forecasts_are_reproducible():
    a = synthetic_forecast("s1", "menstrual_cramps")
    assert a == synthetic_forecast("s1", "menstrual_cramps")
    assert a != synthetic_forecast("s2", "menstrual_cramps")


# ---------------------------------------------------------------- retrieval
def test_cards_capped_and_strongest_first():
    fc = Forecast("x", 1, "Menstrual", {"cramps": 0.9})
    cards = fired_cards(triggers(fc), KB.cards)
    assert len(cards) == 2 and all(c["strength"] == "low" for c in cards)


def test_candidates_respect_restrictions():
    prefs = Preferences("vegan", frozenset({"soy", "tree_nuts"}), 15)
    cards = fired_cards(triggers(synthetic_forecast("x", "menstrual_cramps")), KB.cards)
    for slot, cands in candidates(KB.recipes, prefs, cards, KB.nutrition).items():
        assert cands, slot
        for c in cands:
            r = c.recipe
            assert "vegan" in r["diets"] and not {"soy", "tree_nuts"} & set(r["allergens"])
            assert r["active_time_min"] <= 15 and r["meal_type"] == slot


def test_bloating_days_prefer_lower_fiber():
    prefs = Preferences("omnivore")
    cards = fired_cards(triggers(Forecast("x", 1, "Luteal", {"bloating": 0.9})), KB.cards)
    ranked = candidates(KB.recipes, prefs, cards, KB.nutrition, bloating=True)
    for cands in ranked.values():
        same_score = [c for c in cands if c.score == cands[0].score]
        fibers = [KB.nutrition[c.recipe["id"]]["fiber_g"] for c in same_score]
        assert fibers == sorted(fibers)


# ---------------------------------------------------------------- schema and claims
def test_schema_rejects_bad_output():
    assert parse_plan("not json")[0] is None
    assert parse_plan(json.dumps({"meals": [], "summary": "x"}))[0] is None
    good = {"meals": [{"slot": s, "recipe_id": "a", "why": "b"} for s in SLOTS], "summary": "c"}
    assert parse_plan(json.dumps(good))[0] == good


def test_every_allowed_wording_passes_the_audit():
    """The cards' own approved sentences must never count as unsupported claims."""
    for c in KB.cards:
        assert n_unsupported(audit(c["allowed_wording"], KB.cards)) == 0, c["id"]


def test_audit_catches_strong_claims_doses_and_never_say():
    found = audit("Ginger treats cramps. Take 200 mg magnesium. Calcium stops cravings.",
                  KB.cards)
    assert "treats" in found["strong"] and "200 mg" in found["dose"]
    assert "calcium stops cravings" in found["never_say"]


@pytest.mark.parametrize("text", [
    # Sentences from the Nov 18 full run that copy or respect the cards' wording.
    "Please note that these foods may not treat or cure these conditions.",
    "No specific claim is made about preventing sugar crashes or stabilizing hormones.",
    "Ginger-cinnamon overnight oats may help ease period pain, according to some small studies "
    "that used supplements, not food amounts.",
    "These meals incorporate ingredients that may help alleviate menstrual cramps and fatigue.",
    "These foods do not replace medical treatment.",
])
def test_audit_allows_card_style_wording(text):
    assert n_unsupported(audit(text, KB.cards)) == 0


@pytest.mark.parametrize("text", [
    "Ginger and cinnamon help alleviate menstrual cramps and fatigue.",
    "These ingredients can help alleviate bloating.",
    "It includes options to help stabilize blood sugar levels throughout the day.",
    "Eat these alongside any recommended iron supplements.",
    "Not tired yet? Ginger treats cramps.",
])
def test_audit_flags_full_run_overstatements(text):
    assert n_unsupported(audit(text, KB.cards)) >= 1


def test_audit_pilot_cases():
    """Cases from the Nov 18 pilot run."""
    ok = audit("They are quick to prepare and do not require any supplements.", KB.cards)
    assert n_unsupported(ok) == 0
    assert audit("Try a magnesium supplement.", KB.cards)["dose"] == ["supplement"]
    bad = audit("These meals alleviate cramps and help stabilize blood sugar levels.", KB.cards)
    assert len(bad["strong"]) == 2


# ---------------------------------------------------------------- planners
def test_rule_plans_are_always_clean():
    for scenario in ("menstrual_cramps", "luteal_cravings_bloating", "menstrual_quiet"):
        r = make_plan(P1, synthetic_forecast("synthetic-01", scenario), "rule", kb=KB)
        assert r.shown and r.unsupported == 0 and len(r.plan["meals"]) == 4


def test_grounded_plan_with_good_model():
    fc = synthetic_forecast("synthetic-01", "menstrual_cramps")
    r = make_plan(P1, fc, "grounded", _picker, KB)
    assert r.shown and not r.off_menu and r.attempts == 1
    assert all(m["servings"] >= 0.5 for m in r.plan["meals"])
    assert r.totals["energy_kcal"] > 0


def test_retry_once_on_bad_json():
    fc = synthetic_forecast("synthetic-01", "menstrual_cramps")
    good = make_plan(P1, fc, "grounded", _picker, KB).plan
    fake = FakeBackend("{oops", json.dumps(good))
    r = make_plan(P1, fc, "grounded", fake, KB)
    assert r.attempts == 2 and r.plan is not None
    assert "problems" in fake.calls[1][-1]["content"]


def test_two_bad_replies_give_no_plan():
    fc = synthetic_forecast("synthetic-01", "menstrual_cramps")
    r = make_plan(P1, fc, "grounded", FakeBackend("nope"), KB)
    assert r.plan is None and not r.shown and r.format_problems


def test_violations_and_claims_are_caught():
    milk_free_vegetarian = next(p for p in PROFILES if p["diet"] == "vegetarian"
                                and "milk" in p["allergies"])
    ids = ["spinach-feta-scramble-toast", "made-up-salad", "ginger-garlic-salmon",
           "ginger-lemon-tea"]
    fc = synthetic_forecast(milk_free_vegetarian["profile_id"], "menstrual_cramps")
    r = make_plan(milk_free_vegetarian, fc, "grounded", FakeBackend(_bad_plan(ids)), KB)
    assert not r.shown
    problems = " ".join(r.restriction_problems)
    assert "contains milk" in problems and "not in the curated" in problems
    assert "not vegetarian" in problems
    assert set(r.off_menu) >= {"spinach-feta-scramble-toast", "made-up-salad"}
    assert r.claims["strong"] and r.claims["dose"]


def test_ungrounded_prompt_has_catalog_but_no_evidence():
    fake = FakeBackend(_bad_plan(["ginger-lemon-tea"] * 4))
    make_plan(P1, synthetic_forecast("synthetic-01", "menstrual_cramps"), "ungrounded",
              fake, KB)
    user = fake.calls[0][1]["content"]
    assert "RECIPES" in user and "EVIDENCE" not in user and "CANDIDATES" not in user


# ---------------------------------------------------------------- RQ3 harness
def test_evaluation_harness(tmp_path):
    rows = evaluate.run(limit=2, backend=_picker, kb=KB, out_dir=tmp_path, tag="test")
    assert len(rows) == 2 * 5 * 3
    summary = {s["mode"]: s for s in evaluate.summarize(rows)}
    assert set(summary) == {"rule", "ungrounded", "grounded"}
    assert summary["rule"]["shown_pct"] == 100.0
    assert (tmp_path / "llm_eval_summary_test.csv").exists()
    assert len((tmp_path / "llm_outputs_test.jsonl").read_text().splitlines()) == 30


def test_rescore_keeps_plans_and_old_summary(tmp_path):
    fake = FakeBackend(json.dumps({"meals": [{"slot": s, "recipe_id": "ginger-lemon-tea",
                                              "why": "May help alleviate cramps."} for s in SLOTS],
                                   "summary": "Ginger cures cramps."}))
    before = evaluate.run(modes=("rule", "ungrounded"), limit=1, backend=fake, kb=KB,
                          out_dir=tmp_path, tag="t")
    after = evaluate.rescore(out_dir=tmp_path, tag="t", kb=KB)
    assert [r["restriction_violations"] for r in after] == \
        [r["restriction_violations"] for r in before]
    ung = [r for r in after if r["mode"] == "ungrounded"]
    assert all(r["unsupported_claims"] == 1 for r in ung)  # "cures" only; hedged alleviate ok
    assert (tmp_path / "llm_eval_summary_t_audit_v1.csv").exists()
