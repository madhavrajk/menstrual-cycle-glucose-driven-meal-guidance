"""Step 1 replication. All real outputs stay under MCPHASES_HOME/data/processed."""
import argparse
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import norm

from mealguide import INTERVAL_1, KEYS, paths
from mealguide.cgm.daily_metrics import MIN_COVERAGE, daily_cgm_metrics
from mealguide.data.io import read_daily_table, read_table
from mealguide.phases.calendar import calendar_phases

PHASES = ["Menstrual", "Follicular", "Fertility", "Luteal"]
METRICS = {"glucose_median": "Median glucose (mg/dL)", "glucose_cv": "Glucose CV (%)",
           "mage": "Simplified MAGE (mg/dL)", "tir_70_180": "TIR 70–180 mg/dL (%)",
           "tir_70_140": "TIR 70–140 mg/dL (%)"}


def validate_keys(df):
    if df[KEYS].isna().any().any() or df.duplicated(KEYS).any():
        raise ValueError("Expected unique, nonmissing participant/interval/day keys")


def build_analysis(daily, cgm, threshold=MIN_COVERAGE):
    validate_keys(daily)
    validate_keys(cgm)
    if not 0 < threshold <= 1:
        raise ValueError("Coverage threshold must be in (0, 1]")
    for col in ["lh_phase", "mira_phase"]:
        if not daily[col].dropna().isin(PHASES).all():
            raise ValueError(f"Unexpected {col} labels")
    daily = daily[daily.study_interval.eq(INTERVAL_1)].copy()
    out = daily.merge(cgm, on=KEYS, how="outer", validate="one_to_one", indicator=True)
    out = out[out.study_interval.eq(INTERVAL_1)].copy()
    out["analysis_eligible"] = out.cgm_coverage.ge(threshold)
    out["phase_provenance"] = "Retrospective complete-cycle provisional LH rule"
    # Exploratory peri-ovulatory proxy, not the entire Follicular category.
    relative = out.day_in_study - (out.lh_peak_day + 1)
    reliable = out.phase_quality.eq("provisional_lh_peak") & out.lh_phase.notna()
    out["late_follicular_proxy"] = (reliable & relative.between(-5, -1)
                                    & ~out.lh_phase.eq("Menstrual"))
    out["exploratory_phase"] = out.lh_phase
    out.loc[out.late_follicular_proxy & ~out.lh_phase.eq("Menstrual"),
            "exploratory_phase"] = "LateFollicularProxy"
    return out


def fit_metric(table, metric, phase="lh_phase", threshold=MIN_COVERAGE, high=False):
    """ML random-intercept fit; Wald contrasts are unadjusted for multiplicity."""
    cols = [metric, phase, "id", "cgm_coverage"]
    data = (table.loc[table.cgm_coverage.ge(threshold)]
            .replace([np.inf, -np.inf], np.nan).dropna(subset=cols).copy())
    if high:
        data = data[data.phase_quality.eq("provisional_lh_peak")]
    levels = [p for p in PHASES + ["LateFollicularProxy"] if p in set(data[phase])]
    ref = "LateFollicularProxy" if phase == "exploratory_phase" else "Follicular"
    info = dict(metric=metric, phase=phase, threshold=threshold, high_confidence=high,
                n_days=len(data), n_participants=data.id.nunique(), reference=ref,
                status="insufficient", warnings="", contrasts=[])
    # Pragmatic fit guard, not a power calculation.
    counts = data.groupby(phase).id.nunique()
    if (ref not in levels or len(levels) < 2 or data.id.nunique() < 3
            or len(data) <= len(levels) + 3 or counts.min() < 2):
        return info
    data["phase_model"] = pd.Categorical(data[phase], categories=levels)
    formula = f"{metric} ~ C(phase_model, Treatment(reference='{ref}'))"
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = smf.mixedlm(formula, data, groups=data.id)
            result = model.fit(reml=False, method=["lbfgs", "powell"], disp=False)
        info["warnings"] = " | ".join(str(w.message) for w in caught)
        cov = result.cov_params().loc[result.fe_params.index, result.fe_params.index]
        unstable = (not result.converged or result.cov_re.iloc[0, 0] < 1e-6
                    or not np.isfinite(cov.to_numpy()).all()
                    or np.linalg.eigvalsh(cov.to_numpy()).min() <= 0
                    or "Hessian" in info["warnings"])
        if not np.isfinite(result.fe_params.to_numpy()).all() or not np.isfinite(
                cov.to_numpy()).all():
            raise ValueError("Nonfinite fixed estimates or covariance")
        if (np.diag(cov) < 0).any():
            raise ValueError("Negative fixed-effect variance")
        info["status"] = "unstable" if unstable else "ok"
        info["converged"] = bool(result.converged)
        info["random_intercept_variance"] = float(result.cov_re.iloc[0, 0])
        for term, estimate in result.fe_params.items():
            se = float(np.sqrt(cov.loc[term, term]))
            info["contrasts"].append(dict(term=term, estimate=float(estimate), se=se,
                                         ci_low=float(estimate - 1.96 * se),
                                         ci_high=float(estimate + 1.96 * se),
                                         p_value=float(2 * norm.sf(abs(estimate / se)))
                                         if se > 0 else None))
    except Exception as exc:
        info.update(status="failed", warnings=f"{type(exc).__name__}: {exc}", contrasts=[])
    return info


def figures(table, output, synthetic=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = table[table.analysis_eligible & table.lh_phase.notna()]
    rng = np.random.default_rng(42)
    for metric, label in METRICS.items():
        fig, ax = plt.subplots(figsize=(7.5, 4.5), layout="constrained")
        labels = []
        for i, phase in enumerate(PHASES):
            sub = valid[valid.lh_phase.eq(phase)].dropna(subset=[metric])
            means = sub.groupby("id")[metric].mean().to_numpy()
            labels.append(f"{phase}\n{sub.id.nunique()} people / {len(sub)} days")
            if len(means):
                ax.scatter(i + rng.uniform(-.12, .12, len(means)), means,
                           s=12, alpha=.4, color="#247584")
                if len(means) >= 2:
                    boot = rng.choice(means, (2000, len(means)), replace=True).mean(axis=1)
                    lo, hi = np.quantile(boot, [.025, .975])
                    ax.errorbar(i, means.mean(), yerr=[[means.mean()-lo], [hi-means.mean()]],
                                fmt="o", color="black", capsize=5)
        ax.set_xticks(range(4), labels, fontsize=8)
        ax.set_ylabel(label)
        ax.set_title(("SYNTHETIC — " if synthetic else "") + "LH phases: descriptive means")
        fig.supxlabel("Dots: participant phase means; black: equal-person mean, 95% bootstrap CI",
                      fontsize=8)
        fig.savefig(output / f"{metric}.png", dpi=300)
        fig.savefig(output / f"{metric}.pdf")
        plt.close(fig)


def audit(daily):
    cycles = daily.dropna(subset=["cycle_id"]).drop_duplicates("cycle_id")
    both = daily.dropna(subset=["lh_phase", "mira_phase"])
    return {"cycles": len(cycles),
            "qualifying": int(cycles.phase_quality.eq("provisional_lh_peak").sum()),
            "nonqualifying": int(cycles.phase_quality.eq("no_valid_lh_peak").sum()),
            "labeled_days": int(daily.lh_phase.notna().sum()),
            "agreement": float(both.lh_phase.eq(both.mira_phase).mean()) if len(both) else None,
            "previous_unverified": {"cycles": 70, "qualifying": 59, "nonqualifying": 11,
                                    "labeled_days": 1746, "agreement": 1536/1746}}


def result_line(model):
    """Human-readable estimate, preserving failed/insufficient status."""
    prefix = (f"- {model['metric']}: {model['status']}; "
              f"{model['n_participants']} people, {model['n_days']} days.")
    contrast = next((c for c in model["contrasts"] if "[T.Luteal]" in c["term"]), None)
    if contrast:
        p = contrast["p_value"]
        p_text = "unavailable" if p is None else f"{p:.3g}" if p else "<1e-300"
        prefix += (f" Luteal−Follicular {contrast['estimate']:.2f} "
                   f"(95% CI {contrast['ci_low']:.2f} to {contrast['ci_high']:.2f}; "
                   f"p={p_text}).")
    return prefix


def write_note(output, models, quality, synthetic=False):
    primary = [m for m in models if m["metric"] == "glucose_median"
               and m["phase"] == "exploratory_phase"]
    conclusion = "Inconclusive: exact published late-follicular contrast is not established."
    proxy = "Exploratory proxy contrast unavailable or unstable."
    if primary and primary[0]["status"] == "ok":
        contrast = next((c for c in primary[0]["contrasts"] if "[T.Luteal]" in c["term"]), None)
        if contrast:
            direction = ("supports" if contrast["ci_low"] > 0 else
                         "contradicts" if contrast["ci_high"] < 0 else "is inconclusive for")
            proxy = (f"Exploratory luteal-minus-proxy contrast {direction} higher luteal glucose: "
                     f"{contrast['estimate']:.2f} mg/dL (95% CI "
                     f"{contrast['ci_low']:.2f} to {contrast['ci_high']:.2f}).")
    sections = [
        ("Research question", "Does glucose vary across menstrual phases in mcPHASES?"),
        ("Dataset and inclusion criteria", f"{'SYNTHETIC TEST ONLY. ' if synthetic else ''}"
         "2022; unique participant/interval/day; primary CGM coverage ≥70% of 288 readings. "
         "See quality.json for missingness and model_results.json for each model's sample size."),
        ("Phase-labeling method", "Retrospective provisional LH phases; original Mira sensitivity. "
         "Late follicular proxy: days −5 to −1 before LH peak+1, excluding bleeding. "
         "Exploratory proxy; exact published contrast cannot be established."),
        ("Statistical methods", "ML random intercept; Follicular reference; Wald 95% CIs "
         "Uncorrected p-values in model_results.json. Unstable fits are unreliable. "
         "Intercept is reference estimate, other "
         "terms are phase differences. No causal interpretation. Figures are raw equal-person "
         "means with participant bootstrap CIs, not model-adjusted estimates."),
        ("Results for glucose level and variability", "\n".join(
            result_line(m)
            for m in models[:5])),
        ("Sensitivity analyses", "Original Mira, qualifying cycles for both schemes, 60% and 80% "
         "coverage: all fits and contrasts in model_results.json; differences from primary in "
         "sensitivity.csv. Qualifying-peak restriction is redundant for primary LH labels."),
        ("Whether the hypothesized glucose pattern replicated",
         ("No real research conclusions from synthetic tests." if synthetic
          else conclusion + " " + proxy)),
        ("Limitations", "Selection from complete cycles and missingness; provisional LH timing; "
         "serial dependence beyond random intercept is unmodeled; no power guarantee. "
         "Gaussian TIR models are exploratory because outcomes are bounded and may be at ceiling. "
         "Simplified turning-point MAGE. Agreement with Mira is not accuracy."),
        ("Implications for Step 2 symptom prediction", "Use calendar_phase and confidence from "
         "reported history only. Current-day bleeding must be available by prediction time. "
         "LH and Mira labels are retrospective comparators, not prediction features.")]
    text = "# Step 1 — Glucose-by-Menstrual-Phase Replication\n\n"
    text += "\n\n".join(f"## {i}. {title}\n{body}" for i, (title, body) in enumerate(sections, 1))
    (output / "results_note.md").write_text(text + "\n")


def run(daily, cgm, output, synthetic=False):
    output.mkdir(parents=True, exist_ok=True)
    table = build_analysis(daily, cgm)
    table.to_csv(output / "analysis_table.csv", index=False)
    specs = [("lh_phase", .7, False), ("mira_phase", .7, False),
             ("lh_phase", .7, True), ("mira_phase", .7, True),
             ("lh_phase", .6, False), ("lh_phase", .8, False),
             ("exploratory_phase", .7, False)]
    models = [fit_metric(table, metric, phase, threshold, high)
              for phase, threshold, high in specs for metric in METRICS]
    (output / "model_results.json").write_text(json.dumps(models, indent=2, allow_nan=False))
    changes = []
    for m in models[5:]:
        base = next(b for b in models[:5] if b["metric"] == m["metric"])
        for c in m["contrasts"]:
            b = next((x for x in base["contrasts"] if x["term"] == c["term"]), None)
            if b and c["term"] != "Intercept":
                changes.append({**{k: m[k] for k in ["metric", "phase", "threshold",
                                                    "high_confidence", "status"]},
                                "term": c["term"], "estimate": c["estimate"],
                                "primary_estimate": b["estimate"],
                                "difference": c["estimate"] - b["estimate"],
                                "direction_changed": c["estimate"] * b["estimate"] < 0})
    pd.DataFrame(changes).to_csv(output / "sensitivity.csv", index=False)
    quality = {"rows": len(table), "eligible_days": int(table.analysis_eligible.sum()),
               "missing_by_column": table.isna().sum().to_dict(),
               "join": table._merge.value_counts().to_dict(), "previous_work": audit(daily)}
    (output / "quality.json").write_text(json.dumps(quality, indent=2))
    table.groupby(["lh_phase"], dropna=False).agg(
        days=("id", "size"), people=("id", "nunique"),
        eligible=("analysis_eligible", "sum")).to_csv(output / "phase_coverage.csv")
    figures(table, output, synthetic)
    write_note(output, models, quality, synthetic)
    return models


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    daily = calendar_phases(read_daily_table(args.synthetic))
    if args.synthetic:
        # Existing public generator has no cycle provenance; never claim qualifying peaks.
        for col in ["cycle_id", "lh_peak_day"]:
            if col not in daily:
                daily[col] = np.nan
        daily["phase_quality"] = "synthetic_unverified"
    cgm = daily_cgm_metrics(read_table("glucose", args.synthetic))
    root = paths.SYNTHETIC if args.synthetic else paths.PROCESSED
    daily.to_csv(root / "daily_master_labeled.csv", index=False)
    run(daily, cgm, root / "step1_replication", args.synthetic)
    print("Step 1 outputs saved locally under", root / "step1_replication")


if __name__ == "__main__":
    main()
