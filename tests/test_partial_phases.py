import pandas as pd

from mealguide.phases.partial import extend_lh_phases


def test_partial_labels_keep_primary_and_require_peak():
    data = pd.DataFrame({
        "id": 1, "study_interval": 2022, "day_in_study": range(1, 42),
        "lh": 2.0, "lh_phase": None, "flow_volume": None,
    })
    data.loc[0, "lh_phase"] = "Luteal"
    data.loc[data.day_in_study.eq(22), "lh"] = 15.0
    starts = data.loc[data.day_in_study.eq(10)]
    out = extend_lh_phases(data, starts)
    pd.testing.assert_series_equal(out.lh_phase, data.lh_phase)
    assert out.loc[0, "lh_phase_expanded"] == "Luteal"
    assert out.loc[21, "lh_expansion_source"] == "start_only"
    assert out.loc[23, "lh_phase_expanded"] == "Luteal"
    assert pd.isna(out.loc[40, "lh_phase_expanded"])
    assert extend_lh_phases(data.assign(lh=2), starts).lh_phase_expanded.notna().sum() == 1
