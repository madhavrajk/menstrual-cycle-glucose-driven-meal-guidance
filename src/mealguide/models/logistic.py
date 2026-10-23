"""First Step 2 model: logistic regression on watch-only features.

Watch-only means signals a Fitbit gives by this morning, with no phase, glucose, or diary
input, which is the cheapest deployable configuration. Each physiological signal enters as
its deviation from the person's own past 28 days (`_dev`), so the model learns "higher than
usual for you" rather than "a high-HR person".

The imputer and scaler sit inside the pipeline, so `loso_predict` refits them on the
training participants in every fold: the held-out person's data never shapes them. Missing
values are filled with the training median and flagged with an indicator column, because
whether the watch was worn can itself be informative.
"""

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

WATCH_FEATURES = [
    "resting_hr_dev", "night_hr_dev", "hrv_rmssd_dev", "skin_temp_dev",
    "sleep_minutes", "sleep_efficiency", "steps",
]


def make_lr(C: float = 1.0):
    """A fresh, unfitted pipeline (loso_predict calls this once per fold)."""
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=C, max_iter=1000),
    )
