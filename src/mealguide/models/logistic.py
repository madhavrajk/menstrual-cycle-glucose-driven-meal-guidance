"""Step 2 model factories: logistic regression and LightGBM.

Each call returns a fresh, unfitted model; `loso_predict` calls it once per fold, so the
imputer and scaler are refit on the training participants every time and the held-out
person's data never shapes them.

Both use fixed, conservative settings rather than tuning: with 41-42 participants, nested
LOSO tuning would cost hours and mostly fit noise. The LR fills missing values with the
training median. An earlier version also added missingness indicators, on the idea that
wearing the watch could be informative; on real data it wasn't (AUROC 0.50 for the share of
missing watch features), and the indicators made next-day glucose slightly worse.
LightGBM handles missing values natively.
"""

from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Kept for the Week 4 watch-only model; Step 2 configs live in models/configs.py.
WATCH_FEATURES = [
    "resting_hr_dev", "night_hr_dev", "hrv_rmssd_dev", "skin_temp_dev",
    "sleep_minutes_dev", "sleep_efficiency_dev", "steps_dev",
]


def make_lr(C: float = 1.0):
    return make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=C, max_iter=1000),
    )


def make_lgbm(seed: int = 0):
    return LGBMClassifier(
        n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=40,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
        random_state=seed, verbose=-1,
    )


MODELS = {"lr": make_lr, "lgbm": make_lgbm}
