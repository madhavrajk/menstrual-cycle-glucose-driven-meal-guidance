"""All records in this module are synthetic, never research results."""
import json

import numpy as np
import pandas as pd
import pytest

from mealguide.phases.calendar import calendar_phases
from mealguide.phases.replication import PHASES, build_analysis, fit_metric, run


def fixture():
    rng = np.random.default_rng(12)
    rows = []
    for pid in range(8):
        person = rng.normal(0, 8)
        for day in range(40):
            phase = PHASES[day % 4]
            rows.append(dict(id=pid, study_interval=2022, day_in_study=day,
                             lh_phase=phase, mira_phase=phase, cycle_id=f"{pid}_1",
                             lh_peak_day=15, phase_quality="provisional_lh_peak",
                             glucose_median=100 + person + (4 if phase == "Luteal" else 0)
                             + rng.normal(0, 2), glucose_cv=10+rng.normal(),
                             mage=20+rng.normal(), tir_70_180=95+rng.normal(),
                             tir_70_140=80+rng.normal(), cgm_coverage=.9,
                             n_readings=260, cgm_valid=True))
    df = pd.DataFrame(rows)
    metrics = ["glucose_median", "glucose_cv", "mage", "tir_70_180", "tir_70_140",
               "cgm_coverage", "n_readings", "cgm_valid"]
    return df.drop(columns=metrics), df[["id", "study_interval", "day_in_study"] + metrics]


def test_join_and_coverage():
    daily, cgm = fixture()
    cgm.loc[0, "cgm_coverage"] = .69
    table = build_analysis(daily, cgm)
    assert len(table) == len(daily)
    assert not table.analysis_eligible.iloc[0]
    assert table.analysis_eligible.sum() == len(table)-1
    with pytest.raises(ValueError):
        build_analysis(pd.concat([daily, daily.iloc[:1]]), cgm)
    with pytest.raises(ValueError):
        build_analysis(daily, pd.concat([cgm, cgm.iloc[:1]]))
    cgm.loc[0, "id"] = np.nan
    with pytest.raises(ValueError):
        build_analysis(daily, cgm)


def test_missing_and_interval():
    daily, cgm = fixture()
    daily.loc[0, "study_interval"] = 2024
    daily.loc[1, "lh_phase"] = None
    table = build_analysis(daily, cgm.iloc[1:])
    assert table.study_interval.eq(2022).all()
    assert len(table) == len(daily)-1
    assert table.lh_phase.isna().sum() == 1
    assert PHASES == ["Menstrual", "Follicular", "Fertility", "Luteal"]


def test_mixed_model_recovers_known_synthetic_difference():
    daily, cgm = fixture()
    result = fit_metric(build_analysis(daily, cgm), "glucose_median")
    assert result["status"] == "ok"
    assert result["n_days"] == 320 and result["n_participants"] == 8
    effect = next(c for c in result["contrasts"] if "[T.Luteal]" in c["term"])
    assert 3 < effect["estimate"] < 5
    assert effect["ci_low"] < effect["estimate"] < effect["ci_high"]
    json.dumps(result, allow_nan=False)
    assert fit_metric(build_analysis(daily.iloc[:1], cgm.iloc[:1]),
                      "glucose_median")["status"] == "insufficient"


def history():
    return pd.DataFrame({"id": 1, "study_interval": 2022, "day_in_study": range(65),
                         "flow_volume": ["Moderate" if d % 28 in (1, 2, 3) else "None"
                                         for d in range(65)]})


def test_calendar_past_only_and_unknown():
    df = history()
    original = calendar_phases(df)
    assert original.loc[original.day_in_study < 29, "calendar_phase"].eq("Unknown").all()
    assert original.loc[29, "calendar_phase"] == "Menstrual"
    changed = df.copy()
    changed.loc[changed.day_in_study > 40, "flow_volume"] = "Heavy"
    pd.testing.assert_frame_equal(original.loc[:40], calendar_phases(changed).loc[:40])
    pd.testing.assert_frame_equal(original.loc[:40], calendar_phases(df.iloc[:41]))
    df["lh"] = 999
    df["glucose_median"] = -50
    pd.testing.assert_series_equal(original.calendar_phase, calendar_phases(df).calendar_phase)


def test_missing_flow_is_not_onset():
    df = history()
    df.loc[28, "flow_volume"] = None
    assert calendar_phases(df).loc[29, "calendar_phase"] == "Unknown"


def test_end_to_end(tmp_path):
    daily, cgm = fixture()
    models = run(daily, cgm, tmp_path, synthetic=True)
    assert len(models) == 35
    assert len(list(tmp_path.glob("*.png"))) == 5
    assert len(list(tmp_path.glob("*.pdf"))) == 5
    assert "SYNTHETIC" in (tmp_path / "results_note.md").read_text()
    assert len(json.loads((tmp_path / "model_results.json").read_text())) == 35


def test_fit_failure_is_visible(monkeypatch):
    from mealguide.phases import replication
    daily, cgm = fixture()

    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError("synthetic singularity")

    monkeypatch.setattr(replication.smf, "mixedlm", fail)
    result = fit_metric(build_analysis(daily, cgm), "glucose_median")
    assert result["status"] == "failed"
    assert "synthetic singularity" in result["warnings"]
    assert result["contrasts"] == []


def test_legacy_step1_small_cohort_and_no_cycles(tmp_path):
    """No hardcoded historical cohort totals; zero-cycle output remains readable."""
    import os
    import subprocess
    import sys
    import zipfile
    from pathlib import Path

    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    diary = pd.DataFrame({"id": [1, 1], "study_interval": [2022, 2024],
                          "day_in_study": [1, 1], "phase": ["Follicular"] * 2,
                          "lh": [1, 1], "estrogen": [1, 1], "pdg": [None, None],
                          "flow_volume": [None, None], "fatigue": ["Low"] * 2,
                          "cramps": ["Low"] * 2, "bloating": ["Low"] * 2,
                          "foodcravings": ["Low"] * 2})
    keys = ["id", "study_interval", "day_in_study"]
    with zipfile.ZipFile(raw / "synthetic.zip", "w") as archive:
        archive.writestr("fake/hormones_and_selfreport.csv", diary.to_csv(index=False))
        archive.writestr("fake/glucose.csv", diary[keys].to_csv(index=False))
        archive.writestr("fake/steps.csv", diary[keys].to_csv(index=False))
    repo = Path(__file__).resolve().parents[1]
    env = {**os.environ, "MCPHASES_HOME": str(tmp_path), "PYTHONPATH": str(repo / "src")}
    result = subprocess.run(["make", "step1", f"PY={sys.executable}"],
                            cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    daily = pd.read_csv(tmp_path / "data/processed/daily_master_labeled.csv")
    assert len(daily) == 2
    assert daily.calendar_phase.eq("Unknown").all()
    assert pd.read_csv(tmp_path / "data/processed/cycle_summary.csv").empty
