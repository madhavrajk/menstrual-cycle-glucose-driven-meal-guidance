# Run from the repo root with the venv active (see README).
#   make baselines              real data under MCPHASES_HOME
#   make baselines SYNTHETIC=1  synthetic data in data/synthetic/

PY ?= python

ifdef SYNTHETIC
FLAG := --synthetic
DATA_DEP := data/synthetic/glucose.csv
endif

# Folder holding data/raw/<zip>; Ava's Step 1 scripts run from there.
STEP1_HOME = $(shell $(PY) -c "from mealguide import paths; print(paths.HOME)")
STEP1 = "$(CURDIR)/scripts/step1_data"

.PHONY: setup data synthetic step1 cgm features baselines model shap forecast fdc nutrition coverage plan evaluate rescore test lint

setup:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .
	pre-commit install

# One-time: verify the PhysioNet download and install it under MCPHASES_HOME.
data:
	@test -n "$(SRC)" || (echo 'Usage: make data SRC=<path to download (zip or folder)>' && exit 1)
	$(PY) -m mealguide.setup_data "$(SRC)"

synthetic data/synthetic/glucose.csv:
	$(PY) -m mealguide.synthetic

# Step 1 (Ava): raw zip -> data/processed/daily_master_labeled.csv
step1:
	cd "$(STEP1_HOME)" && \
	$(PY) $(STEP1)/build_dictionary.py && \
	$(PY) $(STEP1)/build_daily_table.py && \
	$(PY) $(STEP1)/coverage_report.py && \
	$(PY) $(STEP1)/inspect_cycles.py && \
	$(PY) $(STEP1)/label_phases.py && \
	$(PY) $(STEP1)/validate_output.py

# Step 2 (Madhav)
cgm: $(DATA_DEP)
	$(PY) -m mealguide.pipeline cgm $(FLAG)

features: $(DATA_DEP)
	$(PY) -m mealguide.pipeline features $(FLAG)

baselines: cgm features
	$(PY) -m mealguide.pipeline baselines $(FLAG)

# Full grid: LR + LightGBM x {history, watch, watch+phase, watch+phase+glucose} x 5 targets,
# calendar vs LH phase, headline choice, risk thresholds (results/step2_*)
model: cgm features
	$(PY) -m mealguide.pipeline model $(FLAG)

# SHAP for the headline model (run `make model` first)
shap:
	$(PY) -m mealguide.pipeline shap $(FLAG)

# One forecast for Step 3: make forecast ID=3 DAY=40 SYNTHETIC=1
ID ?= 1
DAY ?= 30
forecast:
	$(PY) -m mealguide.models.forecast_api --id $(ID) --day $(DAY) $(FLAG)

# Step 3 (Sneha): fill missing FoodData Central IDs in knowledge/recipes/ (needs FDC_API_KEY)
fdc:
	$(PY) -m mealguide.guidance.fdc resolve

# Step 3 (Sneha): per-serving nutrients for the 3 starter recipes (or RECIPES="id1 id2")
nutrition:
	$(PY) -m mealguide.guidance.nutrition $(RECIPES)

# Step 3 (Sneha): nutrition for all recipes, tag audit, and coverage by card, diet, and meal
coverage:
	$(PY) -m mealguide.guidance.coverage $(if $(FIX),--fix)

# Step 3 (Sneha): one day's plan for a synthetic profile. MODE=rule needs no LLM;
# grounded/ungrounded need Ollama running (see src/mealguide/guidance/llm.py)
PROFILE ?= synthetic-01
SCENARIO ?= menstrual_cramps
MODE ?= grounded
plan:
	$(PY) -m mealguide.guidance.plan --profile $(PROFILE) --scenario $(SCENARIO) --mode $(MODE)

# Step 3 (Sneha): RQ3 evaluation, rule vs ungrounded vs grounded (LIMIT=4 for a quick run)
evaluate:
	$(PY) -m mealguide.guidance.evaluate $(if $(LIMIT),--limit $(LIMIT)) $(if $(MODES),--modes $(MODES))
rescore:
	$(PY) -m mealguide.guidance.evaluate --rescore

test:
	$(PY) -m pytest -q

lint:
	ruff check .

# Step 1: regenerate labels and run all replication analyses locally.
.PHONY: step1-replication
step1-replication: $(if $(SYNTHETIC),synthetic,step1)
	$(PY) -m mealguide.phases.replication $(FLAG)
