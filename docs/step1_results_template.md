# Step 1 — Glucose-by-Menstrual-Phase Replication

## 1. Research question
Does glucose vary across menstrual phases in mcPHASES?

## 2. Dataset and inclusion criteria
2022; unique participant/interval/day; primary CGM coverage ≥70% of 288 readings. See quality.json for missingness and model_results.json for each model's sample size.

## 3. Phase-labeling method
Retrospective provisional LH phases; original Mira sensitivity. Late follicular proxy: days −5 to −1 before LH peak+1, excluding bleeding. Exploratory proxy; exact published contrast cannot be established.

## 4. Statistical methods
ML random intercept; Follicular reference; Wald 95% confidence intervals and uncorrected p-values in model_results.json. Unstable fits are unreliable. Intercept is reference estimate, other terms are phase differences. No causal interpretation. Figures are raw equal-person means with participant bootstrap CIs, not model-adjusted estimates.

## 5. Results for glucose level and variability
- glucose_median: ok; 33 people, 1495 days. Luteal−Follicular 2.22 (95% CI 0.86 to 3.59; p=0.00142).
- glucose_cv: ok; 33 people, 1495 days. Luteal−Follicular -0.67 (95% CI -1.16 to -0.18; p=0.00743).
- mage: ok; 33 people, 1495 days. Luteal−Follicular -0.08 (95% CI -1.20 to 1.05; p=0.894).
- tir_70_180: ok; 33 people, 1495 days. Luteal−Follicular 0.54 (95% CI -0.24 to 1.33; p=0.175).
- tir_70_140: ok; 33 people, 1495 days. Luteal−Follicular -0.61 (95% CI -1.95 to 0.74; p=0.376).

## 6. Sensitivity analyses
The median glucose difference stayed positive with Mira labels (+2.50 mg/dL, 95% CI 1.49–3.50), Mira restricted to qualifying cycles (+2.65, 1.25–4.06), 60% CGM coverage (+2.06, 0.70–3.43), and 80% coverage (+1.98, 0.61–3.36). The primary LH analysis already requires qualifying peaks. The CV estimate remained negative, but its confidence interval included zero when using Mira labels across all eligible days.

## 7. Whether the hypothesized glucose pattern replicated
Inconclusive: exact published late-follicular contrast is not established. Exploratory luteal-minus-proxy contrast supports higher luteal glucose: 3.64 mg/dL (95% CI 2.14 to 5.14).

## 8. Limitations
Selection from complete cycles and missingness; provisional LH timing; serial dependence beyond random intercept is unmodeled; no power guarantee. Gaussian TIR models are exploratory because outcomes are bounded and may be at ceiling. Simplified turning-point MAGE. Agreement with Mira is not accuracy.

## 9. Implications for Step 2 symptom prediction
Use calendar_phase and confidence from reported history only. Current-day bleeding must be available by prediction time. LH and Mira labels are retrospective comparators, not prediction features.
