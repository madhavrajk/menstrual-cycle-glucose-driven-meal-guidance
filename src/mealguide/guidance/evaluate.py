"""RQ3: does grounding cut unsupported health claims and restriction violations?

    make evaluate                       # all 20 profiles x 5 scenarios x 3 modes (300 plans)
    make evaluate LIMIT=4               # first 4 profiles only, for a quick check
    make rescore                        # re-run only the claims audit on saved plans

Runs Ava's 20 synthetic profiles (notebooks/synthetic_profiles.json) through every
forecast scenario with each planner, then writes:
- results/llm_eval_synthetic.csv           one row per plan
- results/llm_eval_summary_synthetic.csv   one row per mode
- results/llm_outputs_synthetic.jsonl      every plan as returned, for the hand review
All of it is synthetic (invented people and forecasts), so it is safe to commit.

The LLM modes need Ollama running (see guidance/llm.py). A full run makes 200 LLM calls;
on a laptop that's roughly 1-2 hours, so start with LIMIT=4.
"""

import argparse
import csv
import json
import shutil
import time

from mealguide.guidance.claims import AUDIT_VERSION, audit, n_unsupported
from mealguide.guidance.forecast import SCENARIOS, synthetic_forecast
from mealguide.guidance.plan import MODES, Knowledge, load_profiles, make_plan
from mealguide.paths import RESULTS

SUMMARY_COLS = ["mode", "plans", "valid_json_pct", "shown_pct", "restriction_violation_pct",
                "off_menu_pct", "any_unsupported_claim_pct", "unsupported_per_plan",
                "strong_claims", "dose_mentions", "never_say_hits", "mean_attempts"]


def row(r, scenario: str, seconds: float) -> dict:
    claims = r.claims or {}
    return {
        "mode": r.mode, "profile": r.person, "scenario": scenario,
        "valid_json": r.plan is not None, "shown": r.shown,
        "restriction_violations": len(r.restriction_problems), "off_menu": len(r.off_menu),
        "unsupported_claims": r.unsupported,
        "strong": len(claims.get("strong", [])), "dose": len(claims.get("dose", [])),
        "never_say": len(claims.get("never_say", [])),
        "attempts": r.attempts, "seconds": round(seconds, 1),
        "problems": " | ".join(r.format_problems + r.restriction_problems),
    }


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    for mode in MODES:
        rs = [x for x in rows if x["mode"] == mode]
        if not rs:
            continue
        n, valid = len(rs), [x for x in rs if x["valid_json"]]
        pct = lambda k, among=rs: round(100 * sum(1 for x in among if x[k]) / max(len(among), 1), 1)  # noqa: E731
        out.append({
            "mode": mode, "plans": n,
            "valid_json_pct": pct("valid_json"), "shown_pct": pct("shown"),
            "restriction_violation_pct": pct("restriction_violations", valid),
            "off_menu_pct": pct("off_menu", valid),
            "any_unsupported_claim_pct": pct("unsupported_claims", valid),
            "unsupported_per_plan": round(sum(x["unsupported_claims"] for x in valid)
                                          / max(len(valid), 1), 2),
            "strong_claims": sum(x["strong"] for x in valid),
            "dose_mentions": sum(x["dose"] for x in valid),
            "never_say_hits": sum(x["never_say"] for x in valid),
            "mean_attempts": round(sum(x["attempts"] for x in rs) / n, 2),
        })
    return out


def run(modes=MODES, limit: int | None = None, backend=None, kb: Knowledge | None = None,
        out_dir=RESULTS, tag: str = "synthetic") -> list[dict]:
    kb = kb or Knowledge.load()
    profiles = load_profiles()[:limit]
    rows = []
    out_dir.mkdir(exist_ok=True)
    total = len(profiles) * len(SCENARIOS) * len(modes)
    with open(out_dir / f"llm_outputs_{tag}.jsonl", "w") as raw:
        for p in profiles:
            for scenario in SCENARIOS:
                fc = synthetic_forecast(p["profile_id"], scenario)
                for mode in modes:
                    start = time.time()
                    r = make_plan(p, fc, mode, None if mode == "rule" else backend, kb)
                    rows.append(row(r, scenario, time.time() - start))
                    raw.write(json.dumps({"mode": mode, "profile": r.person,
                                          "scenario": scenario, "cards": r.cards,
                                          "plan": r.plan, "claims": r.claims,
                                          "problems": r.format_problems
                                          + r.restriction_problems}) + "\n")
                    print(f"  [{len(rows)}/{total}] {p['profile_id']} {scenario} {mode}: "
                          f"{'shown' if r.shown else 'REJECTED'}, "
                          f"{r.unsupported} unsupported", flush=True)
    for name, data, cols in [(f"llm_eval_{tag}.csv", rows, list(rows[0])),
                             (f"llm_eval_summary_{tag}.csv", summarize(rows), SUMMARY_COLS)]:
        with open(out_dir / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(data)
    return rows


INT_COLS = ("restriction_violations", "off_menu", "unsupported_claims", "strong", "dose",
            "never_say", "attempts")


def rescore(out_dir=RESULTS, tag: str = "synthetic", kb: Knowledge | None = None) -> list[dict]:
    """Re-run the claims audit on saved plans; no LLM needed. Plans, restriction checks and
    attempts are unchanged. Keeps the previous summary as llm_eval_summary_<tag>_audit_v<N>.csv
    so both audit versions can be reported."""
    from mealguide.guidance.schema import plan_text
    kb = kb or Knowledge.load()
    per_plan, raw_file = out_dir / f"llm_eval_{tag}.csv", out_dir / f"llm_outputs_{tag}.jsonl"
    summary = out_dir / f"llm_eval_summary_{tag}.csv"
    with open(per_plan) as f:
        rows = list(csv.DictReader(f))
    raws = [json.loads(line) for line in raw_file.read_text().splitlines()]
    if len(rows) != len(raws):
        raise SystemExit(f"{per_plan.name} and {raw_file.name} have different plan counts")
    old = out_dir / f"llm_eval_summary_{tag}_audit_v{AUDIT_VERSION - 1}.csv"
    if summary.exists() and not old.exists():
        shutil.copy(summary, old)
    for row, raw in zip(rows, raws, strict=True):
        if (row["mode"], row["profile"], row["scenario"]) != (raw["mode"], raw["profile"],
                                                                raw["scenario"]):
            raise SystemExit("per-plan CSV and outputs file are out of order")
        row["valid_json"] = row["valid_json"] == "True"
        row["shown"] = row["shown"] == "True"
        for k in INT_COLS:
            row[k] = int(row[k])
        claims = audit(plan_text(raw["plan"]), kb.cards) if raw["plan"] else {}
        raw["claims"] = claims
        row["unsupported_claims"] = n_unsupported(claims) if claims else 0
        for k in ("strong", "dose", "never_say"):
            row[k] = len(claims.get(k, []))
    raw_file.write_text("".join(json.dumps(r) + "\n" for r in raws))
    for name, data, cols in [(per_plan.name, rows, list(rows[0])),
                             (summary.name, summarize(rows), SUMMARY_COLS)]:
        with open(out_dir / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(data)
    return rows


def _print_summary(rows: list[dict]) -> None:
    print(f"\nRQ3 summary, claims audit v{AUDIT_VERSION} "
          "(percentages of valid plans unless noted):")
    for s in summarize(rows):
        print(f"  {s['mode']:<11} plans {s['plans']:>3} · valid JSON {s['valid_json_pct']}% · "
              f"shown {s['shown_pct']}% · restriction violations "
              f"{s['restriction_violation_pct']}% · any unsupported claim "
              f"{s['any_unsupported_claim_pct']}% ({s['unsupported_per_plan']} per plan)")


def main() -> None:
    parser = argparse.ArgumentParser(description="RQ3 evaluation on synthetic profiles")
    parser.add_argument("--limit", type=int, default=None, help="first N profiles only")
    parser.add_argument("--modes", nargs="+", default=list(MODES), choices=MODES)
    parser.add_argument("--rescore", action="store_true",
                        help="re-run only the claims audit on saved plans (no LLM)")
    args = parser.parse_args()
    if args.rescore:
        _print_summary(rescore())
        print("\nUpdated results/llm_eval_synthetic.csv, results/llm_eval_summary_synthetic.csv, "
              "results/llm_outputs_synthetic.jsonl (previous summary kept as *_audit_v1.csv)")
        return
    from dotenv import load_dotenv

    from mealguide.guidance.llm import OllamaBackend
    from mealguide.paths import REPO_ROOT
    load_dotenv(REPO_ROOT / ".env")
    backend = OllamaBackend() if set(args.modes) - {"rule"} else None
    print(f"Evaluating {args.modes} with {backend or 'no LLM'}")
    rows = run(args.modes, args.limit, backend)
    _print_summary(rows)
    print("\nWrote results/llm_eval_synthetic.csv, results/llm_eval_summary_synthetic.csv, "
          "results/llm_outputs_synthetic.jsonl")


if __name__ == "__main__":
    main()
