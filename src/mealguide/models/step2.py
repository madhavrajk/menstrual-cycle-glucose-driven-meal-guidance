"""Step 2 results: every model x configuration x target, the phase comparison, the headline
choice, risk thresholds for Step 3, and SHAP for the headline model.

    make model      grid + phase comparison + headline + thresholds
    make shap       SHAP for the headline model (needs results/step2_headline_<source>.json)

All outputs in results/ are aggregates (one row per target x model, or per feature). Nothing
with participant-day rows is written to the repo.

Headline rule, fixed before looking at the grid: among the configurations that need no CGM
(watch, watch+phase) and both model families, take the highest mean within-person AUROC
across the four symptom targets. If LR is within 0.01 of the best, take LR, because it's
easier to explain and its probabilities are better calibrated. The glucose target always
uses the same model family with watch+phase+glucose, because without a CGM nothing in the
grid forecasts it (see docs/step2_results.md).
"""

import json

import numpy as np
import pandas as pd

from mealguide import paths
from mealguide.models.baselines import persistence, person_base_rate
from mealguide.models.configs import (
    CONFIGS,
    NO_CGM_CONFIGS,
    SYMPTOMS,
    TARGETS,
    add_model_features,
    config_features,
)
from mealguide.models.harness import evaluate, loso_predict
from mealguide.models.logistic import MODELS

SIGNAL = {"high_cv": "glucose_cv"} | {f"{s}_high": f"{s}_score" for s in SYMPTOMS}
GLUCOSE_CONFIG = "watch+phase+glucose"
THRESHOLDS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]


def _source(synthetic: bool) -> str:
    return "synthetic" if synthetic else "real"


def _save(df: pd.DataFrame, name: str, synthetic: bool) -> None:
    paths.RESULTS.mkdir(exist_ok=True)
    df.round(4).to_csv(paths.RESULTS / f"{name}_{_source(synthetic)}.csv", index=False)


def model_table(synthetic: bool) -> pd.DataFrame:
    from mealguide.pipeline import build_model_table  # avoid a circular import
    return add_model_features(build_model_table(synthetic))


def configs_for(target: str) -> list[str]:
    return [c for c in CONFIGS if not (target == "high_cv" and c == "history")]


def run_grid(df: pd.DataFrame, n_boot: int = 1000) -> tuple[pd.DataFrame, dict]:
    """LOSO scores for baselines and every model x config x target.

    Returns the metrics table and the out-of-fold predictions, keyed (target, model, config).
    """
    rows, preds = [], {}
    for target in TARGETS:
        y = f"{target}_next"
        df["_s"] = persistence(df, SIGNAL[target])
        rows.append({"target": target, "model": "baseline", "config": "persistence",
                     **evaluate(df, y, "_s", n_boot=n_boot)})
        df["_s"] = person_base_rate(df, y)
        rows.append({"target": target, "model": "baseline", "config": "base_rate",
                     **evaluate(df, y, "_s", n_boot=n_boot)})
        for model, make in MODELS.items():
            for config in configs_for(target):
                p = loso_predict(df, config_features(target, config), y, make)
                preds[(target, model, config)] = p
                df["_s"] = p
                rows.append({"target": target, "model": model, "config": config,
                             **evaluate(df, y, "_s", n_boot=n_boot)})
                r = rows[-1]
                print(f"  {target:<14} {model:<5} {config:<20} AUROC {r['auroc']:.3f}  "
                      f"within {r.get('auroc_within', np.nan):.3f}", flush=True)
    df.drop(columns="_s", inplace=True)
    return pd.DataFrame(rows), preds


def choose_headline(grid: pd.DataFrame) -> dict:
    sym = grid[grid["target"].isin([f"{s}_high" for s in SYMPTOMS])
               & grid["config"].isin(NO_CGM_CONFIGS)]
    score = sym.groupby(["model", "config"])["auroc_within"].mean().sort_values()
    best_model, best_config = score.index[-1]
    lr = score.xs("lr", level="model")
    if best_model != "lr" and lr.max() >= score.iloc[-1] - 0.01:
        best_model, best_config = "lr", lr.idxmax()
    return {"model": best_model, "symptom_config": best_config,
            "glucose_config": GLUCOSE_CONFIG,
            "mean_within_auroc_symptoms": round(float(score[(best_model, best_config)]), 4),
            "candidates": {f"{m}:{c}": round(float(v), 4) for (m, c), v in score.items()}}


def headline_config(headline: dict, target: str) -> str:
    return headline["glucose_config"] if target == "high_cv" else headline["symptom_config"]


def phase_comparison(df: pd.DataFrame, model: str = "lr", n_boot: int = 1000) -> pd.DataFrame:
    """Calendar vs hormone-confirmed (LH) phase on the same rows: forecast days with an LH
    label. LH phase uses future cycle boundaries, so it's a best case, not deployable."""
    sub = df[df["lh_phase_next"].notna()].copy()
    rows = []
    for target in TARGETS:
        y = f"{target}_next"
        known = sub.dropna(subset=[y])
        cal_known = (known["phase_next"] != "Unknown").mean()
        both = known[known["phase_next"] != "Unknown"]
        agree = (both["phase_next"] == both["lh_phase_next"]).mean() if len(both) else np.nan
        for config in ("watch", "watch+phase", "watch+lh"):
            sub["_s"] = loso_predict(sub, config_features(target, config), y, MODELS[model])
            rows.append({"target": target, "model": model, "config": config,
                         "calendar_phase_known": cal_known, "calendar_lh_agreement": agree,
                         **evaluate(sub, y, "_s", n_boot=n_boot)})
    return pd.DataFrame(rows)


def threshold_table(df: pd.DataFrame, preds: dict, headline: dict) -> pd.DataFrame:
    """How often each risk threshold would fire, and how often it would be right."""
    rows = []
    for target in TARGETS:
        y = f"{target}_next"
        p = preds[(target, headline["model"], headline_config(headline, target))]
        d = pd.DataFrame({"y": df[y], "p": p}).dropna()
        for t in THRESHOLDS:
            fire = d["p"] >= t
            tp = (fire & (d["y"] == 1)).sum()
            rows.append({"target": target, "threshold": t, "fire_rate": fire.mean(),
                         "sensitivity": tp / max((d["y"] == 1).sum(), 1),
                         "ppv": tp / fire.sum() if fire.any() else np.nan,
                         "prevalence": d["y"].mean(), "mean_pred": d["p"].mean()})
    return pd.DataFrame(rows)


def _print_grid(grid: pd.DataFrame, source: str) -> None:
    print(f"\nStep 2 models on {source} Interval 1 data "
          "(LOSO; 95% participant-bootstrap CIs; within = mean per-person AUROC)")
    for r in grid.itertuples():
        within = getattr(r, "auroc_within", np.nan)
        print(f"  {r.target:<14} {r.model:<8} {r.config:<20} "
              f"AUROC {r.auroc:.3f} [{r.auroc_lo:.3f}, {r.auroc_hi:.3f}]  "
              f"within {within:.3f}  AUPRC {r.auprc:.3f}  n={r.n_days}/{r.n_participants}")


def run_models(synthetic: bool, n_boot: int = 1000) -> pd.DataFrame:
    df = model_table(synthetic)
    grid, preds = run_grid(df, n_boot)
    _save(grid, "step2_models", synthetic)
    _print_grid(grid, _source(synthetic))

    headline = choose_headline(grid)
    (paths.RESULTS / f"step2_headline_{_source(synthetic)}.json").write_text(
        json.dumps(headline, indent=2) + "\n")
    print(f"\nHeadline: {headline['model']} {headline['symptom_config']} for symptoms, "
          f"{headline['glucose_config']} for glucose")

    _save(threshold_table(df, preds, headline), "step2_thresholds", synthetic)
    comparison = phase_comparison(df, headline["model"], n_boot)
    _save(comparison, "step2_phase_comparison", synthetic)
    print("\nPhase comparison on forecast days with an LH label:")
    for r in comparison.itertuples():
        print(f"  {r.target:<14} {r.config:<12} AUROC {r.auroc:.3f}  "
              f"within {getattr(r, 'auroc_within', np.nan):.3f}  n={r.n_days}  "
              f"calendar known {r.calendar_phase_known:.2f}")
    return grid


def load_headline(synthetic: bool) -> dict:
    path = paths.RESULTS / f"step2_headline_{_source(synthetic)}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `make model` first.")
    return json.loads(path.read_text())


def fit_headline(df: pd.DataFrame, headline: dict, target: str, exclude=None):
    """The headline model for one target, fit on every labeled row (minus one person)."""
    feats = config_features(target, headline_config(headline, target))
    d = df.dropna(subset=[f"{target}_next"])
    if exclude is not None:
        d = d[d["id"] != exclude]
    return MODELS[headline["model"]]().fit(d[feats], d[f"{target}_next"].astype(int)), feats


def shap_importance(df: pd.DataFrame, headline: dict) -> pd.DataFrame:
    """Mean |SHAP| per feature for the headline model fit on all participants.

    `direction` is the correlation between a feature's value and its SHAP value: + means
    higher values push the risk up."""
    import shap

    rows = []
    for target in TARGETS:
        model, feats = fit_headline(df, headline, target)
        X = df.dropna(subset=[f"{target}_next"])[feats]
        if headline["model"] == "lr":
            Xt = model[:-1].transform(X)
            values = shap.LinearExplainer(model[-1], Xt).shap_values(Xt)
        else:
            values = shap.TreeExplainer(model).shap_values(X)
            values = values[1] if isinstance(values, list) else values
        values = np.asarray(values)
        for i, f in enumerate(feats):
            x = X[f].to_numpy(float)
            ok = ~np.isnan(x)
            sd = np.std(x[ok]) * np.std(values[ok, i]) if ok.sum() > 2 else 0
            direction = np.corrcoef(x[ok], values[ok, i])[0, 1] if sd > 0 else np.nan
            rows.append({"target": target, "config": headline_config(headline, target),
                         "feature": f, "mean_abs_shap": np.abs(values[:, i]).mean(),
                         "direction": direction})
    out = pd.DataFrame(rows)
    out["rank"] = out.groupby("target")["mean_abs_shap"].rank(ascending=False).astype(int)
    return out.sort_values(["target", "rank"]).reset_index(drop=True)


def run_shap(synthetic: bool) -> pd.DataFrame:
    df = model_table(synthetic)
    headline = load_headline(synthetic)
    out = shap_importance(df, headline)
    _save(out, "step2_shap", synthetic)
    from mealguide.models.figures import shap_figure
    shap_figure(out, paths.RESULTS / "figures" / f"step2_shap_{_source(synthetic)}.png",
                headline, synthetic)
    print(f"SHAP for {headline['model']} (top 3 per target):")
    for target, g in out.groupby("target"):
        top = ", ".join(f"{r.feature} ({r.mean_abs_shap:.3f})" for r in g.head(3).itertuples())
        print(f"  {target:<14} {top}")
    return out
