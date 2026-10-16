"""Step 2 pipeline: CGM metrics -> Fitbit features -> targets -> baselines.

    python -m mealguide.pipeline cgm        [--synthetic]
    python -m mealguide.pipeline features   [--synthetic]
    python -m mealguide.pipeline baselines  [--synthetic]

Real-data outputs go to $MCPHASES_HOME/data/processed/ (never committed). Synthetic outputs
go to data/synthetic/. The baselines step also writes aggregate metrics only to results/.
"""

import argparse
from pathlib import Path

import pandas as pd

from mealguide import INTERVAL_1, KEYS, paths
from mealguide.cgm.daily_metrics import MIN_COVERAGE, daily_cgm_metrics
from mealguide.cgm.targets import add_next_day, label_high_cv, symptom_high
from mealguide.data.io import read_daily_table, read_table
from mealguide.features.fitbit_daily import fitbit_daily
from mealguide.models.baselines import persistence, person_base_rate
from mealguide.models.harness import evaluate

SYMPTOMS = ["fatigue", "cramps", "bloating", "cravings"]


def _out_dir(synthetic: bool) -> Path:
    d = paths.SYNTHETIC if synthetic else paths.PROCESSED
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_cgm(synthetic: bool) -> pd.DataFrame:
    glucose = read_table("glucose", synthetic,
                         usecols=KEYS + ["timestamp", "glucose_value"])
    daily = label_high_cv(daily_cgm_metrics(glucose))
    daily.to_csv(_out_dir(synthetic) / "cgm_daily.csv", index=False)

    valid = daily[daily["cgm_valid"]]
    per_person = valid.groupby("id")["high_cv"].agg(["count", "sum"])
    print(f"CGM: {len(daily):,} participant-days, {len(valid):,} valid "
          f"(>= {100 * MIN_COVERAGE:.0f}% of 288 readings), {daily['id'].nunique()} participants")
    print(f"  valid days per participant: min {per_person['count'].min()}, "
          f"median {per_person['count'].median():.0f}; "
          f"high-CV days per participant: median {per_person['sum'].median():.0f}")
    return daily


def run_features(synthetic: bool) -> pd.DataFrame:
    feats = fitbit_daily(synthetic)
    feats.to_csv(_out_dir(synthetic) / "fitbit_daily.csv", index=False)
    print(f"Fitbit: {len(feats):,} participant-days; median wear "
          f"{feats['wear_pct'].median():.0f}% of minutes")
    return feats


def _load_or_run(name: str, synthetic: bool, runner) -> pd.DataFrame:
    path = _out_dir(synthetic) / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else runner(synthetic)


def build_model_table(synthetic: bool) -> pd.DataFrame:
    """One row per Interval 1 participant-day with today's signals and tomorrow's targets."""
    daily = read_daily_table(synthetic)
    cgm = _load_or_run("cgm_daily", synthetic, run_cgm)
    feats = _load_or_run("fitbit_daily", synthetic, run_features)

    df = (daily[daily["study_interval"] == INTERVAL_1]
          .merge(cgm, on=KEYS, how="left")
          .merge(feats, on=KEYS, how="left"))
    df = df.drop_duplicates(KEYS).sort_values(KEYS).reset_index(drop=True)

    df = add_next_day(df, "high_cv")
    for s in SYMPTOMS:
        df[f"{s}_high"] = symptom_high(df, s)
        df = add_next_day(df, f"{s}_high")
    return df


def run_baselines(synthetic: bool) -> pd.DataFrame:
    df = build_model_table(synthetic)
    tasks = [("high_cv", "glucose_cv")] + [(f"{s}_high", f"{s}_score") for s in SYMPTOMS]

    rows = []
    for target, today_signal in tasks:
        y = f"{target}_next"
        df["score_persistence"] = persistence(df, today_signal)
        df["score_base_rate"] = person_base_rate(df, y)
        for baseline in ("persistence", "base_rate"):
            rows.append({"target": f"next-day {target}", "baseline": baseline,
                         **evaluate(df, y, f"score_{baseline}")})
    results = pd.DataFrame(rows)

    source = "synthetic" if synthetic else "real"
    paths.RESULTS.mkdir(exist_ok=True)
    results.round(4).to_csv(paths.RESULTS / f"baselines_{source}.csv", index=False)

    print(f"\nBaselines on {source} Interval 1 data (LOSO, 95% participant-bootstrap CI)")
    for r in results.itertuples():
        print(f"  {r.target:<22} {r.baseline:<12} "
              f"AUROC {r.auroc:.3f} [{r.auroc_lo:.3f}, {r.auroc_hi:.3f}]  "
              f"AUPRC {r.auprc:.3f} [{r.auprc_lo:.3f}, {r.auprc_hi:.3f}]  "
              f"prev {r.prevalence:.2f}  n={r.n_days} days / {r.n_participants} ppl")
    return results


def main():
    parser = argparse.ArgumentParser(description="Step 2 forecasting pipeline")
    parser.add_argument("step", choices=["cgm", "features", "baselines"])
    parser.add_argument("--synthetic", action="store_true", help="use data/synthetic/")
    args = parser.parse_args()
    {"cgm": run_cgm, "features": run_features, "baselines": run_baselines}[args.step](
        args.synthetic)


if __name__ == "__main__":
    main()
