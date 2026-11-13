"""Exploratory retrospective LH labels for the edges of observed cycles."""
import pandas as pd

from mealguide.phases.calendar import BLEEDING


def extend_lh_phases(daily, starts):
    """Keep primary labels intact and extend only before the first/after the last onset."""
    out = daily.copy()
    out["lh_phase_expanded"] = out["lh_phase"].copy()
    out["lh_expansion_source"] = "unclassified"
    out.loc[out.lh_phase.notna(), "lh_expansion_source"] = "complete_cycle"
    for (pid, interval), group in out.groupby(["id", "study_interval"]):
        onsets = starts.loc[starts.id.eq(pid) & starts.study_interval.eq(interval),
                            "day_in_study"]
        if onsets.empty:
            continue
        first, last = onsets.min(), onsets.max()
        edges = [
            (group[group.day_in_study.between(first - 45, first - 1)],
             first - 25, first - 8, "end_only"),
            (group[group.day_in_study.between(last, last + 44)],
             last + 5, last + 30, "start_only"),
        ]
        for segment, lower, upper, source in edges:
            candidates = segment[segment.day_in_study.between(lower, upper)].dropna(
                subset=["lh"])
            if len(candidates) < 3:
                continue
            peak = candidates.loc[candidates.lh.idxmax()]
            baseline = candidates.lh.median()
            if baseline <= 0 or peak.lh < 10 or peak.lh / baseline < 2.5:
                continue
            # Limit the end-only window to peri-ovulatory and subsequent days.
            start = peak.day_in_study - 4 if source == "end_only" else last
            end = peak.day_in_study + 16 if source == "start_only" else first - 1
            segment = segment[segment.day_in_study.between(start, end)
                              & segment.lh_phase.isna()]
            phase = pd.Series("Fertility", index=segment.index)
            phase.loc[segment.day_in_study < peak.day_in_study - 4] = "Follicular"
            phase.loc[segment.day_in_study > peak.day_in_study + 1] = "Luteal"
            phase.loc[segment.flow_volume.isin(BLEEDING)] = "Menstrual"
            out.loc[segment.index, "lh_phase_expanded"] = phase
            out.loc[segment.index, "lh_expansion_source"] = source
    return out
