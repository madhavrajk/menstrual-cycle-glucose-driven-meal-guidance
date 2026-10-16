# Decisions

Newest first. "Provisional" means the code uses it now, but the group hasn't confirmed it.

| Date | Decision | Status | Why / notes |
|---|---|---|---|
| Oct 15 | **Interval scope:** Interval 1 (2022) is primary for all models. | Settled by data | Interval 2 has no CGM, almost no diary entries, and no flow data (Ava's coverage report). Interval 2 is used only for wearable-only sensitivity checks, if at all. |
| Oct 15 | **CGM day validity:** ≥ 70% of 288 readings (≥ 202). | Set; confirm with real counts | The consensus statements give a *period-level* rule: about 14 days with ≥ 70% of possible readings (Danne et al. 2017; Battelino et al. 2019, *Diabetes Care* 42(8):1593, the TIR consensus). Neither defines a per-day rule, so we apply the same 70% to each day, because our unit is the day. If `make cgm` shows too few valid days, drop to 60% and report N for both. Add Battelino 2019 to the references. |
| Oct 15 | **Glucose target:** high-variability day = CV in the participant's own top third of valid days. Need ≥ 10 valid days. | Per proposal | The threshold uses all of a person's days. Fine for a label, never a feature. |
| Oct 15 | **Time in range:** report both 70–180 and 70–140 mg/dL. | Settled | Healthy participants sit near 100% in 70–180. |
| Oct 15 | **Symptom target:** next-day score ≥ 3 ("Moderate") on the 0–5 diary scale. | Provisional | Revisit after seeing prevalence per symptom. A person-relative threshold is the alternative. |
| Oct 15 | **Leakage rule:** features and baselines at day t use only days ≤ t, and labels known by t (≤ t−1 for next-day labels). Splits are leave-one-subject-out. | Settled | Covered by `tests/test_leakage.py`. |
| Oct 15 | **Repo:** one private repo; Ava's `mira-cycle-analysis` imported (her authorship kept) so it can be deleted. | Done | Public release review in Week 10. |
| Oct 8 → open | **Primary phase scheme:** LH-anchored (ours) vs. shipped Mira labels. | Open | Suggested: LH-anchored primary, Mira as cross-check. LH labels cover only 31% of days today (1,746 / 5,659), so coverage must improve first. |
| Oct 8 → open | **LLM setup for Step 3:** local model vs. zero-retention API vs. sending only derived state. | Open | Sneha's options page, then instructor confirmation before any real participant day reaches a hosted model. |
