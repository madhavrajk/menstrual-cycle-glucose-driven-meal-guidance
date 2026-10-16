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

.PHONY: setup synthetic step1 cgm features baselines test lint

setup:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .
	pre-commit install

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

test:
	$(PY) -m pytest -q

lint:
	ruff check .
