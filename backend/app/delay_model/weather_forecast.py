import numpy as np
import pandas as pd
import requests

from app.delay_model.config import WEATHER_VARS

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_forecast(lat, lon, when, prefix, timeout=10):
    """Open-Meteo forecast for one airport and one local hour.

    Returns (values, ok). `values` holds the six weather variables named prefix + variable
    (for example o_wind_gusts_10m). On any failure the values are NaN and ok is False.
    """
    empty = {f"{prefix}{v}": np.nan for v in WEATHER_VARS}
    try:
        when = pd.Timestamp(when).floor("h")
        day = when.date().isoformat()
        r = requests.get(FORECAST_URL, params={
            "latitude": float(lat), "longitude": float(lon),
            "hourly": ",".join(WEATHER_VARS),
            "start_date": day, "end_date": day, "timezone": "auto"}, timeout=timeout)
        r.raise_for_status()
        hourly = pd.DataFrame(r.json()["hourly"])
        hourly["time"] = pd.to_datetime(hourly["time"])
        hourly[WEATHER_VARS] = hourly[WEATHER_VARS].apply(pd.to_numeric, errors="coerce")
        row = hourly[hourly["time"] == when]
        if row.empty:
            return empty, False
        values = {f"{prefix}{v}": float(row.iloc[0][v]) for v in WEATHER_VARS}
        ok = not any(np.isnan(x) for x in values.values())
        return values, ok
    except Exception:
        return empty, False