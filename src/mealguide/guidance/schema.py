"""The JSON every planner (rule-based, ungrounded LLM, grounded LLM) must return.

The LLM chooses recipes and writes the words. It never sets portions or nutrition: code
adds those afterwards, so a number in the plan always comes from code.
"""

import json

from mealguide.guidance.retrieval import SLOTS

MAX_WHY_CHARS = 300
MAX_SUMMARY_CHARS = 600

# JSON Schema, passed to Ollama's `format` so the model can only emit this shape.
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "meals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "slot": {"type": "string", "enum": list(SLOTS)},
                    "recipe_id": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["slot", "recipe_id", "why"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["meals", "summary"],
}


def parse_plan(text: str) -> tuple[dict | None, list[str]]:
    """Parse and validate model output. Returns (plan, problems); plan is None if unusable."""
    try:
        plan = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        return None, [f"not valid JSON: {e}"]
    problems = validate_plan(plan)
    return (plan if not problems else None), problems


def validate_plan(plan) -> list[str]:
    if not isinstance(plan, dict):
        return ["plan must be a JSON object"]
    problems = []
    if not isinstance(plan.get("summary"), str) or not plan["summary"].strip():
        problems.append("summary must be a non-empty string")
    elif len(plan["summary"]) > MAX_SUMMARY_CHARS:
        problems.append(f"summary longer than {MAX_SUMMARY_CHARS} characters")
    meals = plan.get("meals")
    if not isinstance(meals, list):
        return problems + ["meals must be a list"]
    slots = []
    for i, m in enumerate(meals):
        if not isinstance(m, dict):
            problems.append(f"meal {i} must be an object")
            continue
        for key in ("slot", "recipe_id", "why"):
            if not isinstance(m.get(key), str):
                problems.append(f"meal {i}: {key} must be a string")
        if m.get("slot") not in SLOTS:
            problems.append(f"meal {i}: slot must be one of {SLOTS}")
        if isinstance(m.get("why"), str) and len(m["why"]) > MAX_WHY_CHARS:
            problems.append(f"meal {i}: why longer than {MAX_WHY_CHARS} characters")
        slots.append(m.get("slot"))
    if sorted(s for s in slots if s in SLOTS) != sorted(SLOTS) or len(slots) != len(SLOTS):
        problems.append(f"need exactly one meal per slot {SLOTS}, got {slots}")
    return problems


def plan_text(plan: dict) -> str:
    """All the words a plan shows the user, for the claims audit."""
    return " ".join([plan.get("summary", "")] + [m.get("why", "") for m in plan.get("meals", [])])
