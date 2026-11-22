"""Analysis agent: delay estimates for a list of flights (PRD Section 6.2).

run_analysis() never raises. Every number comes from the delay model, never from an LLM.
"""
import logging

from app.agents.analysis_tools import model_available, run_delay_tool
from app.agents.flight_mapper import map_flight_row
from app.database.connection import get_db_connection

log = logging.getLogger("analysis_agent")

MAX_FLIGHTS = 10

DISCLAIMER = ("Estimate for decision support only. Based on historical patterns and forecast "
              "weather; a person makes the final decision.")

LIMITATIONS_TEXT = (
    "Delay estimates come from a model trained on one year (2023) of flights between 10 US "
    "airports (ATL, ORD, DFW, DEN, JFK, LAX, SFO, SEA, MIA, BOS). Estimates for other airports "
    "or airlines are less reliable. Forecast weather is less accurate than historical weather, "
    "and the model's accuracy is moderate. Use it as decision support, not as a certainty."
)


def lookup_flight_by_number(flight_number):
    """Return the flights table row for this flight number as a dict, or None.

    If the flight number exists on several dates, the latest scheduled departure is used.
    """
    connection = get_db_connection()
    try:
        cursor = connection.execute(
            "SELECT * FROM flights WHERE flight_number = ? COLLATE NOCASE "
            "ORDER BY scheduled_departure DESC LIMIT 1",
            (flight_number,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [c[0] for c in cursor.description]
        return dict(zip(columns, tuple(row)))
    finally:
        connection.close()


def _failed(flight_id, route, error, error_type="prediction_failed"):
    return {
        "flight_id": flight_id, "route": route, "status": "failed",
        "delay_probability": None, "expected_delay_minutes": None, "risk_level": None,
        "top_factors": [], "warnings": [], "weather_source": None,
        "error": error, "error_type": error_type, "estimate": True,
    }


def assess_flight(flight_number):
    """One flight: look it up, convert it, call the model. Always returns an assessment dict."""
    try:
        row = lookup_flight_by_number(flight_number)
    except Exception as e:
        log.exception("Database lookup failed for %s", flight_number)
        return _failed(flight_number, None, f"Could not read the flight from the database: {e}",
                       "lookup_failed")
    if row is None:
        return _failed(flight_number, None, "Flight not found in the database", "not_found")

    route = f"{row.get('origin_code')}-{row.get('destination_code')}"

    mapped = map_flight_row(row)
    if not mapped["ok"]:
        return _failed(flight_number, route, mapped["error"], "invalid_input")

    tool = run_delay_tool(mapped["model_input"], flight_number)
    if tool["status"] != "ok":
        return _failed(flight_number, route, tool["error"], tool.get("error_type", "prediction_failed"))

    return {
        "flight_id": flight_number,
        "route": route,
        "status": "ok",
        "delay_probability": tool["delay_probability"],
        "expected_delay_minutes": tool["expected_delay_minutes"],
        "risk_level": tool["risk_level"],
        "top_factors": tool["top_factors"],
        "warnings": list(tool.get("warnings", [])) + list(mapped["notes"]),
        "weather_source": tool["weather_source"],
        "in_training_scope": tool.get("in_training_scope"),
        "error": None,
        "estimate": True,
    }


def _build_notes(assessments, extra_notes):
    notes = []
    failed = [a for a in assessments if a["status"] == "failed"]
    if failed and all(a.get("error_type") == "model_unavailable" for a in failed) \
            and len(failed) == len(assessments):
        notes.append("The delay model is unavailable, so no estimates could be produced.")
    else:
        for a in failed:
            notes.append(f"{a['flight_id']}: could not be assessed. {a['error']}")
    for a in assessments:
        if a["status"] != "ok":
            continue
        if a["weather_source"] != "forecast":
            notes.append(f"{a['flight_id']}: weather forecast was unavailable, so the "
                         "estimate uses historical patterns without weather.")
        if a.get("in_training_scope") is False:
            notes.append(f"{a['flight_id']}: outside the model's training data, so the "
                         "estimate is less reliable.")
    notes.extend(extra_notes or [])
    return notes


def _template_summary(counts, ranked, total):
    ok = counts["High"] + counts["Medium"] + counts["Low"]
    if ok == 0:
        return (f"No delay estimates could be produced for the {total} flight(s) requested. "
                "See the notes for the reasons. These are estimates only.")
    text = (f"Estimated delay risk for {ok} of {total} flight(s): {counts['High']} high, "
            f"{counts['Medium']} medium, {counts['Low']} low")
    if counts["failed"]:
        text += f", {counts['failed']} could not be assessed"
    text += "."
    if ranked:
        top = ", ".join(f"{a['flight_id']} ({round(a['delay_probability'] * 100)}%)"
                        for a in ranked[:3])
        text += f" Highest predicted delay risk: {top}."
    return text + " These are estimates, not certainties."


def run_analysis(flight_numbers, extra_notes=None, summary_writer=None):
    """Analyse up to 10 flights and return the Section 6.2 result.

    summary_writer: optional function(result_dict) -> str, for an LLM-written summary.
    extra_notes: optional list of strings added to the notes (for example rule findings).
    """
    try:
        requested, seen = [], set()
        for fn in flight_numbers or []:
            fn = str(fn).strip().upper()
            if fn and fn not in seen:
                seen.add(fn)
                requested.append(fn)

        extra = list(extra_notes or [])
        if len(requested) > MAX_FLIGHTS:
            dropped = requested[MAX_FLIGHTS:]
            requested = requested[:MAX_FLIGHTS]
            extra.append(f"Only the first {MAX_FLIGHTS} flights were analysed. Not analysed: "
                         f"{', '.join(dropped)}.")
        if not requested:
            extra.append("No flights were given to analyse.")

        assessments = [assess_flight(fn) for fn in requested]

        ok = [a for a in assessments if a["status"] == "ok"]
        counts = {"High": 0, "Medium": 0, "Low": 0,
                  "failed": len(assessments) - len(ok)}
        for a in ok:
            counts[a["risk_level"]] += 1
        ranked = sorted(ok, key=lambda a: a["delay_probability"], reverse=True)
        average = round(sum(a["delay_probability"] for a in ok) / len(ok), 3) if ok else None

        result = {
            "flights_analysed": len(assessments),
            "assessments": assessments,
            "counts": counts,
            "average_delay_probability": average,
            "highest_risk": [a["flight_id"] for a in ranked[:3]],
            "notes": _build_notes(assessments, extra),
            "summary": _template_summary(counts, ranked, len(assessments)),
            "summary_source": "template",
            "estimate": True,
            "disclaimer": DISCLAIMER,
        }

        if summary_writer is not None:
            try:
                written = summary_writer(result)
                if isinstance(written, str) and written.strip():
                    result["summary"] = written.strip()
                    result["summary_source"] = "llm"
            except Exception as e:
                log.warning("Summary writer failed, keeping the template summary: %s", e)
        return result

    except Exception as e:  # last safety net: never fail the workflow
        log.exception("Analysis agent failed")
        return {
            "flights_analysed": 0, "assessments": [],
            "counts": {"High": 0, "Medium": 0, "Low": 0, "failed": 0},
            "average_delay_probability": None, "highest_risk": [],
            "notes": [f"The analysis could not be completed: {e}"],
            "summary": "The delay analysis could not be completed. These are estimates only.",
            "summary_source": "template", "estimate": True, "disclaimer": DISCLAIMER,
        }