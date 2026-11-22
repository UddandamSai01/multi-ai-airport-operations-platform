"""Convert a flights table row into the delay model's input (PRD Section 6.1).

map_flight_row() never raises. It returns:
  {"ok": True,  "model_input": {...}, "notes": [...], "error": None}
  {"ok": False, "model_input": None,  "notes": [],    "error": "<reason>"}
"""
import csv
import logging
import math
import re
from datetime import datetime
from pathlib import Path

log = logging.getLogger("flight_mapper")

AIRPORTS_CSV = Path(__file__).resolve().parent.parent / "data" / "airports.csv"
EARTH_RADIUS_MILES = 3958.8
CRUISE_MPH = 500.0
EXTRA_MINUTES = 30            # taxi, climb and approach, added to the distance estimate
SAME_ZONE_MAX_LON_DIFF = 7.5  # degrees of longitude: beyond this, assume different time zones

_AIRPORTS = {}


class MappingError(ValueError):
    """The flight row cannot be converted. The message says why."""


def _load_airports():
    """Load airports.csv once: coordinates by IATA code, and an ICAO to IATA map."""
    if _AIRPORTS:
        return _AIRPORTS
    by_iata, icao_to_iata = {}, {}
    with open(AIRPORTS_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            iata = (r.get("iata_code") or "").strip().upper()
            if not iata:
                continue
            try:
                lat, lon = float(r["latitude_deg"]), float(r["longitude_deg"])
            except (KeyError, TypeError, ValueError):
                continue
            scheduled = r.get("scheduled_service") == "yes"
            current = by_iata.get(iata)
            if current is None or (scheduled and not current["scheduled"]):
                by_iata[iata] = {"lat": lat, "lon": lon, "scheduled": scheduled}
            icao = (r.get("icao_code") or "").strip().upper()
            if icao:
                icao_to_iata[icao] = iata
    _AIRPORTS["iata"] = by_iata
    _AIRPORTS["icao"] = icao_to_iata
    return _AIRPORTS


def _to_iata(field, code):
    code = str(code or "").strip().upper()
    if re.fullmatch(r"[A-Z]{3}", code):
        return code
    if re.fullmatch(r"[A-Z0-9]{4}", code):
        iata = _load_airports()["icao"].get(code)
        if iata:
            return iata
        raise MappingError(f"{field} ICAO code {code} was not found in airports.csv")
    raise MappingError(f"{field} must be a 3-letter IATA or 4-letter ICAO code, got {code!r}")


def _carrier_code(flight_number, airline):
    match = re.match(r"^([A-Z0-9]{2})\s*\d", str(flight_number or "").strip().upper())
    if match and any(ch.isalpha() for ch in match.group(1)):
        return match.group(1)
    column = str(airline or "").strip().upper()
    if re.fullmatch(r"[A-Z0-9]{2}", column):
        return column
    raise MappingError(
        f"Cannot find a 2-character carrier code in flight number {flight_number!r} "
        f"or airline {airline!r}")


def _parse_dt(field, value):
    """Return (naive datetime, had_time_zone). The clock time in the text is kept as is."""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value or "").strip()
        if not text:
            raise MappingError(f"{field} is missing")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            raise MappingError(f"{field} is not a valid date and time: {value!r}")
    return dt.replace(tzinfo=None), dt.tzinfo is not None


def _haversine_miles(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def map_flight_row(row):
    """Convert one flights table row (dict or sqlite Row) into model input."""
    try:
        row = dict(row)
        notes = []

        airline = _carrier_code(row.get("flight_number"), row.get("airline"))
        origin = _to_iata("origin_code", row.get("origin_code"))
        dest = _to_iata("destination_code", row.get("destination_code"))
        if origin == dest:
            raise MappingError(f"Origin and destination are the same airport ({origin})")

        airports = _load_airports()["iata"]
        missing = [c for c in (origin, dest) if c not in airports]
        if missing:
            raise MappingError(
                f"Airport {', '.join(missing)} not found in airports.csv, so the distance "
                "cannot be calculated")
        o, d = airports[origin], airports[dest]
        distance = round(_haversine_miles(o["lat"], o["lon"], d["lat"], d["lon"]), 1)

        dep, dep_tz = _parse_dt("scheduled_departure", row.get("scheduled_departure"))
        arr, arr_tz = _parse_dt("scheduled_arrival", row.get("scheduled_arrival"))
        if dep_tz or arr_tz:
            notes.append("Scheduled times carry a time zone offset; the clock times were "
                         "read as local airport times.")

        stated = (arr - dep).total_seconds() / 60.0
        estimated = distance / CRUISE_MPH * 60.0 + EXTRA_MINUTES
        same_zone = abs(o["lon"] - d["lon"]) <= SAME_ZONE_MAX_LON_DIFF
        if same_zone and 0 < stated <= 1440:
            duration = stated
        else:
            duration = estimated
            notes.append("Scheduled duration was estimated from the distance, because the "
                         "airports appear to be in different time zones or the times "
                         "are inconsistent.")

        model_input = {
            "airline": airline,
            "origin": origin,
            "dest": dest,
            "flight_date": dep.date().isoformat(),
            "sched_dep_time": dep.hour * 100 + dep.minute,
            "sched_arr_time": arr.hour * 100 + arr.minute,
            "sched_duration_min": round(duration),
            "distance_miles": distance,
        }
        return {"ok": True, "model_input": model_input, "notes": notes, "error": None}

    except MappingError as e:
        return {"ok": False, "model_input": None, "notes": [], "error": str(e)}
    except Exception as e:
        log.exception("Unexpected error converting flight row")
        return {"ok": False, "model_input": None, "notes": [],
                "error": f"Unexpected error converting flight: {e}"}