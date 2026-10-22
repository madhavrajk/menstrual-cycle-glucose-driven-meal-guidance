# Run Step 1 on a Mac (Terminal; no VS Code needed)

Open Terminal and enter the repository folder. Use the existing project setup once:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
make setup
cp .env.example .env
```

The example sets `MCPHASES_HOME=~/mcphases`. Install your own authorized download with
`make data SRC="/absolute/path/to/download.zip"`. Never place data in this Git checkout
or upload participant rows to chat. The existing legacy phase scripts require a ZIP;
if you installed an extracted folder, retain/install your authorized ZIP for `make step1`.
No code downloads the restricted data.

After setup, one command runs labeling, calendar features, metrics, models, sensitivities,
figures and the results note:

```sh
make step1-replication
```

Outputs: `~/mcphases/data/processed/step1_replication/` (or your configured home):

- `analysis_table.csv`: outer join on `id, study_interval, day_in_study`, 2022 only.
  Rejects duplicates/missing keys on both inputs. `_merge` records unmatched sources.
  Keeps low-coverage days but `analysis_eligible` flags ≥70%; models filter coverage themselves.
- `model_results.json`: all 35 fits, coefficients in original outcome units, Wald SEs,
  CIs and uncorrected p-values; sample sizes; convergence, random-effect variance, warnings.
  `ok`, `unstable`, `failed`, and `insufficient` remain visible. Intercept is the reference
  phase estimate; each other coefficient is a difference versus the reference.
- `sensitivity.csv`: changes in coefficients and signs relative to primary models.
- `quality.json`, `phase_coverage.csv`: join accounting, column missingness, phase coverage,
  and rerun totals alongside previous **unverified** exploratory totals (not acceptance criteria).
  Audit is across both intervals; model cohorts are 2022 only. Agreement denominator includes
  only days with both labels. Missing glucose/phase days never become zero-valued outcomes.
- Five PNG/PDF figure pairs: raw participant phase means and equal-person means with
  percentile participant-bootstrap CIs (2,000 resamples; deterministic seed). Not adjusted
  model estimates. Figures with fewer than two people cannot show a meaningful CI.
- `results_note.md`: generated concise results note. Inspect fit warnings before interpretation.

All outputs, including participant dots in figures, remain local and restricted. No automatic
publication or upload. `make step1-replication SYNTHETIC=1` exercises the same analysis with
public fake records. Existing synthetic data lack cycle provenance; qualifying-cycle and
late-follicular tests will correctly be unavailable in that demo.

## Methods and interpretation

Primary: daily metric ~ four-category LH phase + participant random intercept; ML estimation,
Follicular reference. Metrics come directly from `daily_cgm_metrics`: median, CV, simplified
MAGE, TIR 70–180 and 70–140 mg/dL (inclusive boundaries; TIR in percentage points).
70% is the team's chosen per-day rule (≥202 of 288 deduplicated readings), not a clinical
validation of daily completeness. Sensitivities: Mira at 70%, qualifying peaks for each
scheme at 70%, LH at 60% and 80%. LH primary already excludes nonqualifying cycles.
No fallback silently replaces LH with Mira. Changes can reflect cohort selection.

No established late-follicular operational definition was found in the inspected project
text documentation. An additional exploratory model separates nonbleeding days −5 through
−1 relative to peak+1 from the four phases and uses that proxy as its reference.
This overlaps the original Fertility window; it is not the entire Follicular phase and
is not clinically validated. The exact published contrast remains untested without a
validated mapping. Positive/negative/inconclusive proxy evidence is reported separately.
The luteal-minus-Follicular coefficient addresses the broad four-phase hypothesis only.

Models require ≥3 participants and ≥2 participants per observed phase, and more observations
than fixed parameters plus three. These are computation guards, not evidence of adequate
power. Missing outcome or phase is excluded per model; every model has its own N.
A boundary random-effect variance (<1e-6), invalid covariance, Hessian warning or failed
convergence marks the fit unstable. Gaussian TIR fits are exploratory; ceiling effects
and predictions outside 0–100 are possible. Serial correlation and cycle effects beyond
a participant intercept are not modeled. No multiplicity correction or causal claims.

## Calendar handoff to Madhav

`mealguide.phases.calendar.calendar_phases(daily)` adds `calendar_phase`,
`calendar_confidence`, `calendar_cycle_length`, `calendar_day`. `make step1` now includes
these in `daily_master_labeled.csv`; the existing Step 2 daily-table loader preserves them.
No changes to Step 2 targets or estimators.

Starts require adjacent observed nonbleeding then bleeding reports (spotting excluded).
Missing previous reports or beginning the record while bleeding do not establish onset.
Use median of last three completed plausible 18–45-day inter-onset intervals known by day t;
no qualifying history → Unknown. Five menstrual days, ovulation at predicted length−14,
fertility ovulation−5 through ovulation, luteal afterward. Estimates are low confidence;
when estimated length is exceeded return Unknown rather than silently wrapping a cycle.
Gaps may miss onsets; these features are deliberately conservative. No hormones, glucose,
future onset, future completed length, or retrospective cycle IDs enter the feature.
Current-day flow must be reported before prediction; for a morning prediction use only
history available then (e.g. shift end-of-day features). LH rules use future cycle boundaries
and are for retrospective Step 1 comparisons only.

## Verification

`make test` includes synthetic key/coverage tests, known-effect random-intercept estimation,
calendar prefix-invariance tests, missing-history handling, strict JSON output and an
end-to-end figure/report run. Tests do not require mcPHASES. Run `make lint` as well.
Previous 70/59/11 cycle totals, 1,746 labeled days and ~88% agreement are only compared
when authorized local data are present. Agreement does not measure glucose replication,
clinical phase accuracy or predictive accuracy.
