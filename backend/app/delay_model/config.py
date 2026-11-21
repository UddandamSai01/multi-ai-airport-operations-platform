"""Settings for the delay model package (inference only).

Always import as:  from app.delay_model.config import ...
so it never collides with the backend's own app/config.py.
"""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
MODEL_DIR = PACKAGE_DIR / "models"

REQUIRED_MODEL_FILES = ["clf.joblib", "reg.joblib", "calibrator.joblib", "meta.joblib"]

YEAR = 2023
AIRPORTS = ["ATL", "ORD", "DFW", "DEN", "JFK", "LAX", "SFO", "SEA", "MIA", "BOS"]
DELAY_THRESHOLD_MIN = 15

# Calibrated-probability cutoffs for the risk level
RISK_LOW_MAX = 0.15
RISK_HIGH_MIN = 0.30

WEATHER_VARS = ["temperature_2m", "precipitation", "cloud_cover",
                "wind_speed_10m", "wind_gusts_10m", "weather_code"]
WEATHER_FEATURES = [f"{p}{v}" for p in ("o_", "d_") for v in WEATHER_VARS]

CAT_FEATURES = ["airline", "origin", "dest"]
HISTORY_FEATURES = ["airline_delay_rate", "origin_delay_rate",
                    "dest_delay_rate", "route_delay_rate"]
NUM_FEATURES = (["month", "day_of_week", "dep_hour", "is_holiday", "distance",
                 "sched_duration", "origin_dep_count"]
                + WEATHER_FEATURES + HISTORY_FEATURES)
ALL_FEATURES = CAT_FEATURES + NUM_FEATURES


def missing_model_files() -> list:
    """Names of required model files that are not on disk."""
    return [name for name in REQUIRED_MODEL_FILES if not (MODEL_DIR / name).exists()]


def model_files_available() -> bool:
    return not missing_model_files()