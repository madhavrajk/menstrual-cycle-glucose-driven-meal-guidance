# notebooks/

Exploration only. Anything reusable moves into `src/mealguide/`.

Outputs are stripped on commit (nbstripout via pre-commit), because a printed dataframe is
participant data. Name notebooks `<initials>_<topic>.ipynb`, e.g. `mr_cgm_coverage.ipynb`.

- `synthetic_profiles.json`: 20 invented evaluation profiles with diet, allergy,
  cooking-time, and portion-calculator inputs. These are not dataset participants.
- `synthetic_forecast_demo.ipynb`: single-person walkthrough with a fixed forecast
  fixture and a catalog recipe checked by the project's restriction rules. Use the
  installed project Python environment. Replace the fixture once the forecast API lands.
