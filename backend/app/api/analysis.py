"""Delay estimate endpoints (PRD Section 6.3). Any logged-in role can read estimates."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.analysis_agent import (
    LIMITATIONS_TEXT,
    lookup_flight_by_number,
    run_analysis,
)
from app.agents.analysis_tools import model_available, run_delay_tool
from app.agents.flight_mapper import map_flight_row
from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection

log = logging.getLogger("analysis_api")

router = APIRouter(tags=["Delay estimates"])

MODEL_UNAVAILABLE_MESSAGE = (
    "The delay model is unavailable (model files are missing or cannot be loaded). "
    "The rest of the application is not affected."
)


class DelayEstimatesRequest(BaseModel):
    flight_numbers: list[str] = Field(min_length=1, max_length=10)


def _find_flight(flight_id: str):
    """Find a flight by database id (digits) or by flight number. Returns a dict or None."""
    flight_id = flight_id.strip()
    if flight_id.isdigit():
        connection = get_db_connection()
        try:
            cursor = connection.execute(
                "SELECT * FROM flights WHERE id = ?", (int(flight_id),)
            )
            found = cursor.fetchone()
            if found is not None:
                columns = [c[0] for c in cursor.description]
                return dict(zip(columns, tuple(found)))
        finally:
            connection.close()
    return lookup_flight_by_number(flight_id)


@router.get("/api/flights/{flight_id}/delayestimate")
def get_flight_delay_estimate(
    flight_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not model_available():
        raise HTTPException(status_code=503, detail=MODEL_UNAVAILABLE_MESSAGE)

    row = _find_flight(flight_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Flight not found")

    mapped = map_flight_row(row)
    if not mapped["ok"]:
        raise HTTPException(
            status_code=422,
            detail=f"This flight cannot be converted for the delay model: {mapped['error']}",
        )

    tool = run_delay_tool(mapped["model_input"], row.get("flight_number", flight_id))
    if tool["status"] != "ok":
        if tool.get("error_type") == "model_unavailable":
            raise HTTPException(status_code=503, detail=MODEL_UNAVAILABLE_MESSAGE)
        if tool.get("error_type") == "invalid_input":
            raise HTTPException(status_code=422, detail=tool["error"])
        raise HTTPException(status_code=500, detail=f"Estimate failed: {tool['error']}")

    result = {k: v for k, v in tool.items() if k not in ("status", "error", "error_type")}
    result["warnings"] = list(tool.get("warnings", [])) + list(mapped["notes"])
    result["flight_number"] = row.get("flight_number")
    result["route"] = f"{row.get('origin_code')}-{row.get('destination_code')}"
    result["limitations"] = LIMITATIONS_TEXT
    return result


@router.post("/api/analysis/delay-estimates")
def post_delay_estimates(
    request: DelayEstimatesRequest,
    current_user: dict = Depends(get_current_user),
):
    if not model_available():
        raise HTTPException(status_code=503, detail=MODEL_UNAVAILABLE_MESSAGE)

    result = run_analysis(request.flight_numbers)
    result["limitations"] = LIMITATIONS_TEXT
    return result