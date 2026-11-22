# Step 2: next-day forecasting results (frozen Nov 22, 2026)

Owner: Madhav. Real mcPHASES Interval 1 (2022), 42 participants. Every number here comes from
`make model` and `make shap` and sits in `results/step2_*_real.csv` (aggregates only).
Rerun with `make cgm features model shap`; synthetic versions: add `SYNTHETIC=1`.

## Question and targets

Can signals available by the end of day t forecast day t+1?

- **Unstable glucose:** day t+1's glucose CV in the person's own top third of valid CGM days
  (≥ 70% of 288 readings). 41 participants (one has no valid days). Prevalence 0.34.
- **Symptoms:** day t+1's diary score ≥ 3 ("Moderate") for fatigue (prevalence 0.56),
  cramps (0.16), bloating (0.30), and cravings (0.35).

## Method

**Features** (`src/mealguide/models/configs.py`). Everything is known by the end of day t.

| Group | Columns | Notes |
|---|---|---|
| history | today's four diary scores; the person's past rate of the target | Symptom targets only. The past rate uses a fixed 0.5 prior, so no other participant's labels enter (inside LOSO those would include the held-out person) |
| watch | resting HR, night HR, HRV, skin temperature, sleep time, sleep efficiency, steps | Each as today minus the person's own mean over the previous 28 days |
| phase | Ava's calendar phase, projected one day ahead | Past-only (`phases/calendar.py`); Unknown on 67% of days because it needs one completed cycle |
| glucose | today's CV, time in 70–140, and CV, mean, and MAGE vs the person's past 28 days | Valid CGM days only |
| lh (comparison only) | hormone-confirmed phase of day t+1 | Uses future cycle boundaries, so it is a best case, never deployable |

The glucose target gets no history group: a past rate of high-CV days would leak, because
each label's threshold uses all of a person's days.

**Configurations:** history, watch, watch+phase, watch+phase+glucose. Each config
includes the ones before it, and every symptom config starts from history.
**Models:** logistic regression (median imputation, scaling) and LightGBM (200 trees,
15 leaves, ≥ 40 rows per leaf). Settings are fixed, not tuned, because nested LOSO tuning
on 42 people mostly fits noise.

**Evaluation:** leave-one-subject-out; 95% CIs from 1,000 participant bootstrap resamples.
Two AUROCs:
- **Pooled AUROC** ranks all participant-days together, so it mostly measures who has more
  symptom days. That's why the person's own past rate alone scores 0.79–0.86.
- **Within-person AUROC** is computed per participant (those with both outcomes) and then
  averaged. It asks whether a forecast tracks one person's day-to-day changes, which is the
  forecasting question.

Why both: in the Week 4 watch-only LR, pooled AUROC fell to 0.35 for fatigue although no
feature was below 0.5. With weak features the score is mostly the training intercept, which
is lowest exactly when the held-out person has the most symptom days. Within-person AUROC
can't be fooled this way.

**Headline rule** (fixed in `models/step2.py` before the grid was run): among the
configurations that need no CGM (watch, watch+phase), take the best mean within-person AUROC
over the four symptoms. Prefer LR if it is within 0.01 of the best.

## Results

### Full grid (LR; LightGBM in the CSV)

AUROC [95% CI] / within-person AUROC. **Bold** = headline.

| Target | Persistence | Base rate | LR history | **LR watch** | LR watch+phase | LR watch+phase+glucose |
|---|---|---|---|---|---|---|
| Fatigue | 0.790 / 0.626 | 0.812 / 0.519 | 0.837 / 0.616 | **0.836 [0.786, 0.873] / 0.617** | 0.834 / 0.616 | 0.832 / 0.614 |
| Cramps | 0.846 / 0.714 | 0.790 / 0.435 | 0.858 / 0.691 | **0.868 [0.802, 0.909] / 0.745** | 0.867 / 0.751 | 0.865 / 0.746 |
| Bloating | 0.858 / 0.673 | 0.860 / 0.482 | 0.888 / 0.651 | **0.888 [0.843, 0.920] / 0.655** | 0.887 / 0.651 | 0.886 / 0.660 |
| Cravings | 0.801 / 0.635 | 0.818 / 0.489 | 0.845 / 0.625 | **0.845 [0.801, 0.884] / 0.628** | 0.844 / 0.626 | 0.844 / 0.624 |
| Unstable glucose | 0.568 / 0.580 | 0.463 / 0.435 | n/a | 0.477 / 0.485 | 0.494 / 0.500 | **0.595 [0.568, 0.621] / 0.589** |

n = 3,279 days / 42 people for symptoms and 2,849 / 41 for glucose. Persistence needs
today's value, so it scores fewer days (3,084 and 2,688).

### Findings

1. **Symptoms are forecastable, but mostly from the person's own diary.** Every symptom
   model beats both baselines on pooled AUROC (by 0.02–0.03 over the best baseline). Almost
   all of that comes from the history group: in SHAP, the past rate and today's score rank
   first and second for every symptom.
2. **The watch adds day-to-day signal for cramps only.** Within-person AUROC goes from 0.691
   (history) to 0.745 (watch), and resting HR above the person's usual is the third-largest
   SHAP feature. For fatigue, bloating, and cravings the watch changes within-person AUROC
   by under 0.005. The CIs above are not paired, so the cramps gain needs a paired
   test before the report claims it as significant.
3. **Calendar phase adds nothing measurable**: ≤ 0.006 within-person on every symptom, and
   0.485 → 0.500 for glucose, which is still chance. It's
   Unknown on 67% of forecast days, and where both are known it agrees with the LH phase on
   70% of days.
4. **Hormone-confirmed phase helps cramps a little, as a best case.** On the 1,653 forecast
   days with an LH label (33 people), within-person AUROC for cramps is 0.743 (watch),
   0.733 (watch + calendar), and 0.778 (watch + LH). Other targets differ by ≤ 0.02.
   (`results/step2_phase_comparison_real.csv`)
5. **Without a CGM, nothing forecasts unstable glucose.** Watch and watch+phase are at
   chance: 0.477–0.494 pooled, 0.485–0.500 within-person. Today's CGM gets to 0.595 [0.568,
   0.621], slightly above persistence (0.568 [0.548, 0.589]). The SHAP leaders are all CGM
   features: mean glucose vs usual (lower → higher risk), CV vs usual, and time in 70–140.
6. **LightGBM is no better than LR.** It's slightly better within-person for fatigue (0.641
   vs 0.617) and worse for cramps, bloating, and glucose (`step2_models_real.csv`), so the
   headline is LR.

### Headline deployable model

**LR, watch configuration** for the four symptoms (mean within-person AUROC 0.661; watch+phase
0.661, LightGBM 0.646). **LR watch+phase+glucose** for unstable glucose, used only when
today's CGM day is valid. The roadmap expected "watch + calendar phase". The rule picked
watch alone because phase added nothing (finding 3). `get_forecast` still reports the
calendar phase, which Step 3's phase-fallback trigger uses.

### Calibration and the Step 3 risk threshold

LOSO probabilities are calibrated on average: the mean prediction equals prevalence to
within 0.002 for every target. Brier scores are 0.08–0.16 for symptoms and 0.22 for glucose.
At Step 3's `RISK_THRESHOLD = 0.5` (`results/step2_thresholds_real.csv`):

| Target | Days that fire | Sensitivity | PPV (prevalence) |
|---|---|---|---|
| Fatigue | 59% | 0.81 | 0.78 (0.56) |
| Cramps | 10% | 0.49 | 0.75 (0.16) |
| Bloating | 27% | 0.67 | 0.77 (0.30) |
| Cravings | 30% | 0.63 | 0.73 (0.35) |
| Unstable glucose | 5% | 0.08 | 0.58 (0.34) |

**Recommendation: keep 0.5.** About three in four symptom alerts are right, against base
rates of 16–56%. The exception is fatigue, which fires on 59% of days. That's a target
problem, not a threshold problem: a score of 3 or more happens on 56% of days. This
supports the open decision to use ≥ 4 for fatigue. Glucose alerts are rare (5% of days) but
1.7× the base rate.

## Forecast API

`mealguide.models.forecast_api.get_forecast(id, day)` returns Sneha's `Forecast`:

- `day` is the day the forecast is for, made from the row for `day - 1`;
- `risks` holds the four symptoms, plus `unstable_glucose` only if `day - 1` was a valid CGM
  day (77% of forecasts);
- `phase` is the projected calendar phase;
- `logged` holds the symptoms rated ≥ 3 on `day - 1`, for the reactive trigger.

Each participant's forecast comes from models trained without that participant. On real data,
529 sampled forecasts (every 7th participant-day) all built and passed `triggers()`. They
fired 1.2 logged, 0.28 forecast, and 0.05 phase triggers per forecast.
`make forecast ID=3 DAY=40 SYNTHETIC=1` prints one. Real forecasts are restricted data:
local model only.

## Data checks done for this run

- Sleep timestamps are HH:MM:SS clock times (0% unparseable); the main-sleep window median
  (472 min) equals Fitbit's `timeinbed` median.
- HRV: 82% of readings fall 22:00–08:00 and 5.4% after noon, so the noon split is right.
- Skin temperature is in °C (median 33.9, range 25.7–36.4).
- Glucose persistence now uses valid CGM days only, so its n is 2,688 rather than 2,832 in
  `baselines_real.csv` (0.568 vs 0.565 AUROC).

## Limitations

- 42 healthy participants and one interval; LOSO estimates are noisy (see CI widths).
- Symptom labels are self-reported, and "≥ 3" for fatigue is common enough to blur the target.
- The calendar phase is conservative (Unknown until a completed cycle), which limits what
  phase can add. A longer history would help.
- The LH comparison uses retrospective labels and only the 33 people with LH-labeled cycles.
- No paired significance tests between configurations yet; CIs are per configuration.
- Not done (cut per the catch-up plan): sensor-modality ablation and wear-gap analysis.
