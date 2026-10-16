# Week 3 plan, Oct 16–22: Sensing-Driven Meal Guidance

## This week at a glance

By Thursday, Oct 22, the team should have:
- Step 2 baselines running on real Interval 1 data.
- Wider phase coverage, with a calendar-estimated phase for the Week 4 models.
- A first Step 1 replication result.
- The Week 2 meal-guidance groundwork finished: evidence table, cards, 15 recipes, and nutrition computed in code.

The shared repo exists now. Work happens on branches with small PRs (see `docs/CONTRIBUTING.md`).

| Person | Track | Due Oct 22 |
|---|---|---|
| Ava | Phases and Step 1 replication | Phase coverage report; calendar phase column; mixed-effects glucose-by-phase results |
| Madhav | Step 2 forecasting | `make baselines` on real data; first extra wearable features |
| Sneha | Step 3 groundwork | Evidence table + cards; recipe schema + 15 recipes; nutrition for 3 recipes from code; LLM options page |

## Carry-overs from Oct 7–15

Status of the [Oct 7–14 PDF plan](week02_oct07-14.pdf):

- **Ava, done** (now in the repo under `scripts/step1_data/` and `docs/`):
  - Done: data dictionary, symptom check, loader, coverage report, per-day table, LH-anchored phases, and the Mira cross-tab (88% agreement where both exist).
  - Open: the one-page phase-rules note.
- **Madhav, mostly done in code; needs a real-data run:**
  - Done: repo, synthetic dataset, daily CGM metrics, coverage rule, glucose target, LOSO harness with bootstrap CIs, persistence and base-rate baselines, and first Fitbit features. All are tested on synthetic data.
  - Done Oct 15: PhysioNet access, verified download, and the real-data run (`results/baselines_real.csv`). Found and fixed mixed glucose units (see `docs/decisions.md`).
- **Sneha, not started:** lit review, reference 2 fix, LLM options page, evidence table, card template, recipe schema, 15 recipes, and the FoodData Central check all carry into this week.
- **Kickoff decisions:**
  - Interval scope is settled by the data: Interval 1.
  - Phase scheme and LLM setup are still open (see `docs/decisions.md`).

What Ava's Week 2 output changes:
- **Join on three keys:** `id, study_interval, day_in_study`, not two.
- **31% LH phase coverage:** only 1,746 of 5,659 days get an LH phase, because labeling needs two observed period starts.
- **Interval 2 is thin:** almost no diary entries, no flow, and no CGM.
- **The Fitbit coverage flag counts steps records, not wear time.** Madhav's code now computes real wear time from heart-rate minutes.

## First steps for everyone (Thu Oct 15 – Fri Oct 16)

- [ ] Accept the GitHub invite. Clone the repo **outside OneDrive** if you like (`~/code/...`); only Madhav's copy lives in OneDrive.
- [ ] Follow the README setup: venv outside OneDrive, `make setup`, then copy `.env.example` to `.env`.
- [ ] Put your own mcPHASES zip in `~/mcphases/data/raw/` and set `MCPHASES_HOME=~/mcphases`.
- [ ] Run `make test` and `make baselines SYNTHETIC=1` to confirm your setup works.
- [ ] Run `make step1`, then `make baselines`. You now have every shared table locally; nobody sends files.
- [ ] Ava: confirm your files in the team repo, then delete or archive `mira-cycle-analysis`.

## Ava: phases and Step 1 replication

Ava owns phase labels, which every "+phase" model reads. The Week 4 models need the calendar phase by Oct 23.

- [ ] **Fri, coverage diagnosis.** Break the 3,913 unlabeled days down by reason: no second period start, cycle length outside 18–45 days, no qualifying LH peak, Interval 2.
- [ ] **Fri–Mon, widen LH-anchored coverage.** Label single-boundary cycles: count forward from an observed period start to the LH peak, or backward from the peak using a typical ~14-day luteal phase. Flag these as `lh_partial`.
- [ ] **Mon, calendar-estimated phase.** Use period start dates only, as a period-tracking app would, with no hormones. New column `calendar_phase`. This is the phase in the headline deployable model.
- [ ] **Mon, Mira fallback (sensitivity only).** A documented rule for when the Mira label is used.
- [ ] **Tue–Wed, Step 1 replication.**
  - Run `make cgm` locally for daily CGM metrics.
  - Fit mixed-effects models of glucose median, CV, MAGE, and TIR by phase, with a random intercept per participant (statsmodels `mixedlm`).
  - Compare the result with Lin et al. 2023: highest in luteal, lowest in late follicular.
- [ ] **Wed, `docs/phase_rules.md`.** Phase rules, exclusions, and a coverage table for each labeling scheme.

**Done when** `daily_master_labeled.csv` has `calendar_phase` on most Interval 1 days and the replication table is in `results/` (aggregates only).

## Madhav: Step 2 forecasting

Madhav owns the forecasting pipeline and the repo. The scaffold is built and tested on synthetic data. This week moves it to real data and starts the Week 4 features early.

- [x] **Thu Oct 15, data access (carry-over).** Create a PhysioNet account with your Columbia email, sign the mcPHASES data use agreement, and download the ZIP to `~/mcphases/data/raw/`. Tell the group the same day if the page asks for anything beyond the agreement.
- [ ] **Thu Oct 15, repo live.** Push, invite Ava and Sneha, and walk the team through it at the check-in.
- [x] **Fri, real-data shakedown.**
  - Run `make step1 && make cgm && make features`.
  - Check the **timestamp format** in `glucose.csv` and `heart_rate.csv`. `time_of_day()` assumes clock times like `HH:MM:SS`.
  - Check that the join on the 3-part key loses no rows.
- [x] **Fri, coverage rule.**
  - Check the 70% floor against Danne et al. 2017.
  - Look at how many valid days and participants survive, and loosen the floor if needed.
  - Record the result in `docs/decisions.md`.
- [x] **Mon, target sanity.**
  - Count high-CV labels per participant (every participant should have ≥ 10 valid days).
  - Check symptom prevalence at the ≥ 3 threshold.
  - If a symptom is rarer than ~5%, propose a person-relative threshold.
- [ ] **Mon, hand off to Ava.** Confirm `make cgm` works on her machine for the Step 1 replication.
- [x] **Tue, real baselines.** `make baselines` prints AUROC/AUPRC with CIs for all 5 targets. Commit `results/baselines_real.csv`, which holds aggregates only.
- [ ] **Tue–Thu, Week 4 features early.** Add each one with a `_dev` past-baseline column (`features/rolling.py`):
  - Nighttime HR from minute-level heart rate, during the main sleep window.
  - HRV (`heart_rate_variability_details.rmssd`, nightly).
  - Skin-temperature deviation (`computed_temperature.nightly_temperature` or `wrist_temperature`).
- [ ] **Thu, first model.** Logistic regression with `loso_predict` on watch-only features for next-day high CV, run against the baselines.

**Done when** `make baselines` runs on real Interval 1 data and the three new features are in `fitbit_daily.csv`.

## Sneha: meal-guidance groundwork

Sneha builds the evidence base Step 3 depends on. This week clears the Week 2 list, which pulls recipe curation forward and protects Weeks 7–8.

- [ ] **Fri, finalize the literature review.**
  - Add the dataset authors' 2024 wrist-temperature paper (npj Women's Health).
  - Fix reference 2's author list to match the journal page.
  - Check that every reference resolves by DOI or URL.
- [ ] **Fri, LLM data-handling options.**
  - One page comparing a local model, a zero-retention API, and sending only derived state.
  - Bring a recommendation to the Mon update, then email the instructor.
- [ ] **Fri–Mon, evidence table.**
  - Cover the four symptoms, glucose-aware planning, and iron during menses.
  - Give each the claim, best source, study type, and strength.
  - Mark weak or unsupported claims.
- [ ] **Mon, evidence-card template + first 5 cards** in `knowledge/evidence_cards/`, as YAML.
- [ ] **Mon, recipe schema.** Ingredients in grams with FDC IDs, dietary-pattern tags, allergens, cooking time, and meal type. Add a small validator test in `tests/`.
- [ ] **Tue, first 15 recipes** in `knowledge/recipes/`, split across omnivore, vegetarian, and vegan.
- [ ] **Tue–Wed, nutrition from code.** Get an FDC API key (into `.env`) and write `src/mealguide/guidance/nutrition.py`. Compute nutrients for 3 recipes.

**Done when** every planned guidance rule traces to a source or is marked unsupported, and nutrition for 3 recipes computes from code.

## Schedule and check-ins

- **Thu Oct 15, repo walkthrough (30 min).** Everyone clones, runs `make test`, and records the open decisions.
- **Mon Oct 19, async update.** Done, blocked, and numbers so far: Ava's coverage, Madhav's valid CGM days, Sneha's LLM recommendation.
- **Wed Oct 21, week review (30 min).** Ava shows the replication, Madhav shows the real baselines, Sneha shows the evidence table and recipes. Then the group plans Weeks 4–5.

## Decisions and risks

Decisions for the Mon or Wed check-in:
1. **Primary phase scheme.** LH-anchored if Ava's widened coverage is good enough; calendar phase is primary for the deployable model either way.
2. **Symptom target threshold.** ≥ 3 ("Moderate") vs. a person-relative threshold, based on Madhav's prevalence numbers.
3. **LLM setup.** Sneha's recommendation, then instructor confirmation.

| Risk this week | How you'll know | Fallback |
|---|---|---|
| Timestamp format differs from `HH:MM:SS` | `make cgm` errors or reports odd counts on Fri | Adjust `data/io.py::time_of_day` (one function) |
| Few valid CGM days at 70% | `make cgm` output | Loosen the floor; report N |
| Calendar phase slips past Oct 23 | Mon update | Madhav starts the Week 4 models with the Mira label as a temporary phase |
| Sneha overloaded by carry-overs | Mon update | Push recipes 11–15 to Week 4; evidence table and LLM options take priority |
