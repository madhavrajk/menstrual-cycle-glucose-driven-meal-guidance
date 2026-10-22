# Step 1 — Glucose-by-Menstrual-Phase Replication

## 1. Research question
Do daily glucose level and variability differ by menstrual phase in mcPHASES?
## 2. Dataset and inclusion criteria
NOT RUN ON REAL DATA. 2022; ≥70% daily CGM coverage; {{participants}} people,
{{eligible_days}} days. Missingness: {{quality.json}}.
## 3. Phase-labeling method
Retrospective provisional LH labels; Mira sensitivity. Late-follicular proxy is exploratory.
## 4. Statistical methods
Five participant random-intercept models; Follicular reference; phase differences with
Wald 95% CIs and uncorrected p-values. Per-model Ns and fit diagnostics: {{model_results.json}}.
## 5. Results for glucose level and variability
{{median, CV, MAGE, both TIR effects and CIs — awaiting authorized local data run}}
## 6. Sensitivity analyses
{{Mira, qualifying cycles, 60%/80% coverage differences — awaiting local run}}
## 7. Whether the hypothesized glucose pattern replicated
Undetermined. No actual glucose results obtained. The exact published late-follicular
contrast cannot be established from a provisional timing proxy.
## 8. Limitations
Missingness, cycle selection, exploratory phases/MAGE, repeated-day dependence, bounded
TIR and multiple testing. Association is not causation; Mira agreement is not accuracy.
## 9. Implications for Step 2 symptom prediction
Use past-only calendar_phase with confidence; do not use retrospective LH boundaries
as if available at prediction time. Run `make step1-replication` to generate the populated note.
