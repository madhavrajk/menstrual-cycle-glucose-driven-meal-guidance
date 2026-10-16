# Roadmap, Oct 16 – Dec 11

The Oct 7–14 week was extended to Oct 15, so Weeks 3–7 start one day later than in the
proposal. Week 8 ends the day before Thanksgiving (Nov 26), and the Week 9 buffer and the
Dec 11 deadline don't move.

## Weekly plans

| Week | Dates | Plan |
|---|---|---|
| 2 | Oct 7–15 | [Week Plan, Oct 7–14 (PDF)](Week%20Plan%2C%20Oct%207%E2%80%9314%20Sensing-Driven%20Meal%20Guidance.pdf), deadline extended to Oct 15 |
| 3 | Oct 16–22 | [week03_oct16-22.md](week03_oct16-22.md) |

New weeks are added here as they're written.

## By week and owner

| Week | Ava (Step 1: data and phases) | Madhav (Step 2: forecasting) | Sneha (Step 3: meal guidance) |
|---|---|---|---|
| **3** · Oct 16–22 | Widen LH phase coverage beyond 31%; calendar-estimated phase; Step 1 glucose-by-phase replication | Real-data run of CGM metrics, targets, Fitbit features, baselines; start nighttime HR, HRV, skin temperature | Close Week 2 carry-overs: lit review, LLM options, evidence table and cards, recipe schema, 15 recipes, FDC check |
| **4–5** · Oct 23–Nov 5 | Finish Step 1 (variability metrics by phase, figures); per-day coverage rules written up | Full feature set with past-only baselines; LR + LightGBM for both targets × 3 configs (watch / +phase / +glucose), hormone vs. calendar phase | Preference form spec; Mifflin–St Jeor portion calculator; recipes to ~50; retrieval index |
| **6** · Nov 6–12 | Mediation analysis (does glucose variability explain part of phase → symptoms); Step 1 report figures | Sensor-modality ablation; wear-gap analysis; SHAP; headline deployable config (watch + calendar phase) | Restriction checker; structured output schema; prompt drafts |
| **7** · Nov 13–19 | 20 synthetic user profiles; dashboard skeleton | Forecast API `get_forecast(id, day)` + trigger logic (proactive / phase fallback / reactive) | LLM pipeline end to end: retrieval → LLM → FDC nutrition → code checks |
| **8** · Nov 20–25 | Dashboard integration | Freeze Step 2 numbers; results tables; forecast panel | LLM evaluation: rule-based vs. ungrounded vs. grounded |
| **9** · Nov 26–Dec 2 | Buffer (Thanksgiving). Synthetic demo data; report: data + Step 1 | Report: Step 2 | Report: Step 3 |
| **10** · Dec 3–11 | Final report, slides, release review (no data anywhere in git history), then public repo or tagged release | same | same |

## Critical path

1. **Phase labels → Step 2 "+phase" models (Week 4).** Calendar-estimated phase is needed by Oct 23, and hormone-confirmed phase coverage limits how many days the best-case model sees.
2. **CGM metrics → Step 1 replication and model 3.** The code exists. Each person runs `make cgm` on their own copy.
3. **Forecast API (Week 7) → LLM pipeline and evaluation (Weeks 7–8).** Sneha can build against synthetic forecasts until then.
4. **LLM setup decision → any real participant day in Step 3.** Needs instructor sign-off. This is the riskiest external dependency.

## Risks

| Risk | Signal | Fallback |
|---|---|---|
| LH phase coverage stays low (31% today) | Ava's Week 3 numbers | Calendar phase is the primary deployable config anyway; report hormone-confirmed as a best case on the covered subset |
| Too few valid CGM days | `make cgm` counts | Loosen to 60–65% coverage and report N |
| Rare symptom targets (e.g. cramps ≥ Moderate) | prevalence column in `make baselines` | Person-relative threshold, or pool to "any symptom ≥ Moderate" |
| LLM / DUA approval slow | No instructor answer by Nov 6 | Local model, or send only coarse derived state (phase + risk level) |
| Thanksgiving week | n/a | Week 8 ends Nov 25; Week 9 is a buffer by design |
