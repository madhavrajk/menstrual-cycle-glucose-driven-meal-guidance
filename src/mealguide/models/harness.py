"""Leave-one-subject-out evaluation with participant-level bootstrap CIs.

Every model and baseline produces one out-of-fold score per row. `evaluate` pools them and
reports AUROC and AUPRC. CIs resample participants, not days, because days from the same
person are correlated.

It also reports **within-person AUROC**: AUROC computed separately for each participant who
has both outcomes, then averaged with equal weight per person. Pooled AUROC mostly ranks
people against each other (who has more symptom days); within-person AUROC asks whether the
score tracks one person's day-to-day changes, which is what a next-day forecast is for.
It's also immune to a LOSO artifact: with weak features a model's score is mostly its
training intercept, which is lowest exactly when the held-out person has the highest rate,
so pooled AUROC can fall well below 0.5 even when no feature is anti-predictive.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut

METRICS = {"auroc": roc_auc_score, "auprc": average_precision_score}


def _bootstrap(y, score, groups, n_boot, seed):
    rng = np.random.default_rng(seed)
    ids = np.unique(groups)
    rows_by_id = {g: np.flatnonzero(groups == g) for g in ids}
    draws = {name: [] for name in METRICS}
    for _ in range(n_boot):
        rows = np.concatenate([rows_by_id[g] for g in rng.choice(ids, size=len(ids))])
        if len(np.unique(y[rows])) < 2:
            continue
        for name, fn in METRICS.items():
            draws[name].append(fn(y[rows], score[rows]))
    return {name: np.percentile(v, [2.5, 97.5]) if v else (np.nan, np.nan)
            for name, v in draws.items()}


def within_person_auroc(y, score, groups) -> np.ndarray:
    """One AUROC per participant who has both outcomes."""
    out = []
    for g in np.unique(groups):
        rows = groups == g
        if len(np.unique(y[rows])) == 2:
            out.append(roc_auc_score(y[rows], score[rows]))
    return np.array(out)


def _within(y, score, groups, n_boot, seed) -> dict:
    per_person = within_person_auroc(y, score, groups)
    if not len(per_person):
        return {"auroc_within": np.nan, "auroc_within_lo": np.nan,
                "auroc_within_hi": np.nan, "n_within": 0}
    rng = np.random.default_rng(seed)
    boot = rng.choice(per_person, (n_boot, len(per_person))).mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"auroc_within": per_person.mean(), "auroc_within_lo": lo,
            "auroc_within_hi": hi, "n_within": len(per_person)}


def evaluate(df: pd.DataFrame, y_col: str, score_col: str, group_col: str = "id",
             n_boot: int = 1000, seed: int = 6998) -> dict:
    d = df.dropna(subset=[y_col, score_col])
    y = d[y_col].to_numpy(int)
    score = d[score_col].to_numpy(float)
    groups = d[group_col].to_numpy()
    out = {"n_days": len(d), "n_participants": len(np.unique(groups)),
           "prevalence": y.mean() if len(y) else np.nan}
    if len(np.unique(y)) < 2:
        return out | {f"{m}{s}": np.nan for m in METRICS for s in ("", "_lo", "_hi")}
    cis = _bootstrap(y, score, groups, n_boot, seed)
    for name, fn in METRICS.items():
        out[name] = fn(y, score)
        out[f"{name}_lo"], out[f"{name}_hi"] = cis[name]
    out |= _within(y, score, groups, n_boot, seed)
    if ((score >= 0) & (score <= 1)).all():  # probabilities only, not raw scores
        out["brier"] = brier_score_loss(y, score)
        out["mean_pred"] = score.mean()
    return out


def loso_predict(df: pd.DataFrame, feature_cols: list[str], y_col: str,
                 make_model: Callable, group_col: str = "id") -> pd.Series:
    """Out-of-fold P(y=1) for each row, training on all other participants."""
    d = df.dropna(subset=[y_col])
    pred = pd.Series(np.nan, index=df.index)
    for train, test in LeaveOneGroupOut().split(d, groups=d[group_col]):
        tr, te = d.iloc[train], d.iloc[test]
        if tr[y_col].nunique() < 2:
            continue
        model = make_model().fit(tr[feature_cols], tr[y_col].astype(int))
        pred.loc[te.index] = model.predict_proba(te[feature_cols])[:, 1]
    return pred
