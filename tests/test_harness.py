import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from mealguide.models.harness import evaluate, loso_predict


def _frame(n_ids=6, n=30, seed=1):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n_ids * n)
    return pd.DataFrame({"id": np.repeat(np.arange(n_ids), n), "x": x,
                         "y": (x + rng.normal(0, 0.5, n_ids * n) > 0).astype(float)})


def test_evaluate_perfect_and_ci_bounds():
    df = _frame()
    res = evaluate(df.assign(score=df["y"]), "y", "score", n_boot=200)
    assert res["auroc"] == 1.0 and res["auprc"] == 1.0
    assert res["n_participants"] == 6
    df["score"] = df["x"]
    res = evaluate(df, "y", "score", n_boot=200)
    assert res["auroc_lo"] <= res["auroc"] <= res["auroc_hi"]


def test_evaluate_single_class_returns_nan():
    df = pd.DataFrame({"id": [1, 2], "y": [1.0, 1.0], "score": [0.2, 0.9]})
    assert np.isnan(evaluate(df, "y", "score")["auroc"])


def test_loso_predicts_every_row_out_of_fold():
    df = _frame()
    pred = loso_predict(df, ["x"], "y", lambda: LogisticRegression())
    assert pred.notna().all()
    assert evaluate(df.assign(p=pred), "y", "p", n_boot=50)["auroc"] > 0.8
