"""Validated delay-estimate tool for the Analysis agent.

run_delay_tool() never raises. It always returns a dict:
  success: {"status": "ok", "error": None, "error_type": None, ...model output...}
  failure: {"status": "failed", "error": "<reason>", "error_type": <one of below>}

error_type values:
  invalid_input      the flight data cannot be used (the API should answer 422)
  model_unavailable  model files missing or cannot be loaded (the API should answer 503)
  prediction_failed  any other unexpected error
"""
import logging
import re
import time
from datetime import date, datetime

from app.delay_model.config import missing_model_files
from app.delay_model.predictor import ModelUnavailableError, predict_flight

log = logging.getLogger("analysis_tools")

MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 1.0

INVALID_INPUT = "invalid_input"
MODEL_UNAVAILABLE = "model_unavailable"
PREDICTION_FAILED = "prediction_failed"

REQUIRED_FIELDS = ["airline", "origin", "dest", "flight_date", "sched_dep_time",
                   "sched_arr_time", "sched_duration_min", "distance_miles"]


class InvalidFlightInput(ValueError):
    """The flight data is not usable. The message says why."""


def _to_hhmm(name, value):
    try:
        number = int(str(value).strip().replace(":", ""))
    except (TypeError, ValueError):
        raise InvalidFlightInput(f"{name} must be a time like 1530, got {value!r}")
    if not (0 <= number <= 2359 and number % 100 < 60):
        raise InvalidFlightInput(f"{name} must be a valid time (0000 to 2359), got {value!r}")
    return number


def _to_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value).strip()[:10]).isoformat()
    except ValueError:
        raise InvalidFlightInput(f"flight_date must be a date like 2026-11-24, got {value!r}")


def _positive_number(name, value, maximum):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise InvalidFlightInput(f"{name} must be a number, got {value!r}")
    if not (0 < number <= maximum):
        raise InvalidFlightInput(f"{name} must be between 0 and {maximum}, got {value!r}")
    return number


def validate_flight_input(flight):
    """Check and clean one flight's model input. Raises InvalidFlightInput with the reason."""
    if not isinstance(flight, dict):
        raise InvalidFlightInput("Flight input must be a dictionary")
    missing = [k for k in REQUIRED_FIELDS if flight.get(k) in (None, "")]
    if missing:
        raise InvalidFlightInput(f"Missing fields: {', '.join(missing)}")

    airline = str(flight["airline"]).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2}", airline):
        raise InvalidFlightInput(
            f"airline must be a 2-character carrier code like DL, got {flight['airline']!r}")

    origin = str(flight["origin"]).strip().upper()
    dest = str(flight["dest"]).strip().upper()
    for name, code in (("origin", origin), ("dest", dest)):
        if not re.fullmatch(r"[A-Z]{3}", code):
            raise InvalidFlightInput(f"{name} must be a 3-letter IATA code, got {code!r}")

    cleaned = {
        "airline": airline,
        "origin": origin,
        "dest": dest,
        "flight_date": _to_date(flight["flight_date"]),
        "sched_dep_time": _to_hhmm("sched_dep_time", flight["sched_dep_time"]),
        "sched_arr_time": _to_hhmm("sched_arr_time", flight["sched_arr_time"]),
        "sched_duration_min": _positive_number("sched_duration_min", flight["sched_duration_min"], 1440),
        "distance_miles": _positive_number("distance_miles", flight["distance_miles"], 20000),
    }
    if flight.get("origin_dep_count") is not None:
        cleaned["origin_dep_count"] = _positive_number(
            "origin_dep_count", flight["origin_dep_count"], 10000)
    return cleaned


def model_available():
    """True when all model files are on disk."""
    return not missing_model_files()


def _failed(error_type, message):
    return {"status": "failed", "error": message, "error_type": error_type}


def run_delay_tool(flight, label=""):
    """Validate one flight, call the delay model (with one retry), and log the outcome.

    `label` is only used in log messages (for example the flight number).
    """
    missing_files = missing_model_files()
    if missing_files:
        message = f"Delay model is unavailable. Missing files: {', '.join(missing_files)}"
        log.error("delay tool [%s]: %s", label, message)
        return _failed(MODEL_UNAVAILABLE, message)

    try:
        cleaned = validate_flight_input(flight)
    except InvalidFlightInput as e:
        log.warning("delay tool [%s]: invalid input: %s", label, e)
        return _failed(INVALID_INPUT, str(e))

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            started = time.time()
            prediction = predict_flight(cleaned)
            log.info("delay tool [%s]: ok in %.1fs (attempt %d, risk=%s)",
                     label, time.time() - started, attempt, prediction.get("risk_level"))
            return {"status": "ok", "error": None, "error_type": None, **prediction}
        except ModelUnavailableError as e:
            log.error("delay tool [%s]: model unavailable: %s", label, e)
            return _failed(MODEL_UNAVAILABLE, str(e))
        except ValueError as e:
            log.warning("delay tool [%s]: invalid input: %s", label, e)
            return _failed(INVALID_INPUT, str(e))
        except Exception as e:  # unexpected: retry once
            last_error = e
            log.warning("delay tool [%s]: attempt %d failed: %s", label, attempt, e)
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    return _failed(PREDICTION_FAILED, f"Prediction failed after {MAX_ATTEMPTS} attempts: {last_error}")