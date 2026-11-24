import json
import logging

from app.agents.llm import get_llm
from app.agents.prompts import PLANNING_AGENT_PROMPT
from app.agents.schemas import PlanningResult

log = logging.getLogger("planning_agent")


def _fallback_planning_result(
    workflow_id: str,
    airport: str,
    disruption: str,
    affected_flights: list[str],
    gate_information: dict | None,
) -> PlanningResult:
    gate_text = (
        "Gate availability has not been checked because no gate request was supplied."
        if not gate_information
        else f"Gate availability data is supplied: {json.dumps(gate_information)}"
    )

    return PlanningResult(
        workflow_id=workflow_id,
        airport=airport,
        planning_objective=(
            f"Investigate and verify the reported disruption at {airport} "
            f"before any operational decision is made."
        ),
        research_requirements=[
            f"Verify the reported disruption: {disruption}",
            "Verify current weather measurements and forecast data.",
            "Verify current operational status for each affected flight.",
            "Identify missing or conflicting operational evidence.",
        ],
        analysis_requirements=[
            f"Review delay and operational risk for: {', '.join(affected_flights)}.",
            "Identify possible cascading delays and resource conflicts.",
            "Confirm whether the supplied disruption has been validated.",
        ],
        resource_requirements=[
            "Verify gate availability and alternative gate assignments.",
            "Verify runway status and staff availability.",
        ],
        proposed_steps=[
            "Review the disruption report and confirm the source.",
            "Verify weather, flight, runway, gate, and staff information.",
            "Compare validated evidence with the Rule Engine findings.",
            "Review the Analysis Agent estimates without treating them as facts.",
            "Submit the findings to an authorized operator for final review.",
        ],
        status="planning_completed_template_fallback_pending_review",
    )

def run_planning_agent(
    workflow_id: str,
    airport: str,
    disruption: str,
    affected_flights: list[str],
    gate_information: dict | None = None,
    operational_information: dict | None = None,
) -> PlanningResult:

    if not workflow_id.strip():
        raise ValueError("Workflow ID cannot be empty.")

    airport = airport.strip().upper()

    if not 3 <= len(airport) <= 4:
        raise ValueError(
            "Airport code must contain 3 or 4 characters."
        )

    if not disruption.strip():
        raise ValueError(
            "Disruption description cannot be empty."
        )

    if not affected_flights:
        raise ValueError(
            "At least one affected flight must be provided."
        )

    gate_data = (
        gate_information
        if gate_information is not None
        else {
            "status": "not_checked",
            "reason": "No gate request was provided",
        }
    )

    operational_data = (
        operational_information
        if operational_information is not None
        else {
            "status": "not_available",
            "reason": (
                "Operational rule evaluation "
                "has not been provided."
            ),
        }
    )

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(
            PlanningResult,
            method="function_calling"
        )
        planning_chain = PLANNING_AGENT_PROMPT | structured_llm
        result = planning_chain.invoke(
            {
                "workflow_id": workflow_id,
                "airport": airport,
                "disruption": disruption,
                "affected_flights": ", ".join(affected_flights),
                "gate_information": json.dumps(gate_data, indent=2),
                "operational_information": json.dumps(operational_data, indent=2),
            }
        )
    except Exception as exc:
        log.warning(
            "Planning LLM unavailable for workflow %s; using template fallback: %s",
            workflow_id,
            exc,
        )
        return _fallback_planning_result(
            workflow_id,
            airport,
            disruption,
            affected_flights,
            gate_data,
        )

    if not isinstance(result, PlanningResult):
        raise TypeError(
            "Planning Agent did not return "
            "a valid PlanningResult."
        )

    return result