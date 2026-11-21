import numpy as np
import pandas as pd
import shap

LABELS = {
    "airline_delay_rate": "Airline's historical delay rate",
    "origin_delay_rate": "Origin airport's historical delay rate",
    "dest_delay_rate": "Destination airport's historical delay rate",
    "route_delay_rate": "Route's historical delay rate",
    "origin_dep_count": "Departures scheduled at origin that hour",
    "dep_hour": "Scheduled departure hour", "day_of_week": "Day of week",
    "month": "Month", "is_holiday": "Holiday", "distance": "Distance",
    "sched_duration": "Scheduled duration", "airline": "Airline",
    "origin": "Origin airport", "dest": "Destination airport",
}
WX_LABELS = {"temperature_2m": "temperature", "precipitation": "precipitation",
             "cloud_cover": "cloud cover", "wind_speed_10m": "wind speed",
             "wind_gusts_10m": "wind gusts", "weather_code": "weather condition"}


def feature_label(name):
    """Readable label for a feature, for example 'Origin wind gusts'."""
    if name in LABELS:
        return LABELS[name]
    side = "Origin" if name.startswith("o_") else "Destination"
    return f"{side} {WX_LABELS.get(name[2:], name[2:])}"


def _positive_class(values):
    """Different SHAP versions return a list per class, a 2D array or a 3D array."""
    if isinstance(values, list):
        values = values[1]
    values = np.asarray(values)
    if values.ndim == 3:
        values = values[..., 1]
    return values


class _Explainer:
    """SHAP values for the classifier. Uses the shap library; if it cannot handle the model,
    uses LightGBM's built-in exact SHAP contributions (the same TreeSHAP algorithm)."""

    def __init__(self, clf):
        self.clf = clf
        self.backend = "shap"
        try:
            self._shap = shap.TreeExplainer(clf)
        except Exception:
            self._shap = None
            self.backend = "lightgbm"

    def shap_values(self, X):
        if self._shap is not None:
            try:
                return _positive_class(self._shap.shap_values(X))
            except Exception:
                self._shap = None
                self.backend = "lightgbm"
        contrib = np.asarray(self.clf.booster_.predict(X, pred_contrib=True))
        return contrib[:, :-1]          # the last column is the bias term


def build_explainer(clf):
    """Return an explainer object with a .shap_values(X) method."""
    return _Explainer(clf)


def top_factors(explainer, X_row, feature_values=None, n=5):
    """Top n features that pushed this flight's prediction up or down.

    `impact` is in the model's raw score units (log-odds), so use it for ranking and direction,
    not as percentage points.
    """
    feature_values = feature_values or {}
    sv = np.asarray(explainer.shap_values(X_row))[0]
    names = list(X_row.columns)
    out = []
    for i in np.argsort(-np.abs(sv))[:n]:
        out.append({"factor": feature_label(names[i]),
                    "value": feature_values.get(names[i]),
                    "effect": "increases delay risk" if sv[i] > 0 else "reduces delay risk",
                    "impact": round(float(sv[i]), 3)})
    return out


def global_importance(explainer, X_sample, feature_names):
    """Mean absolute SHAP value per feature, largest first."""
    sv = np.asarray(explainer.shap_values(X_sample))
    return pd.Series(np.abs(sv).mean(axis=0), index=feature_names).sort_values(ascending=False)