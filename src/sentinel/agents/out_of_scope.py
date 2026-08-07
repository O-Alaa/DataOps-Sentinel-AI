from sentinel.state import IncidentState

def out_of_scope_node(state: IncidentState) -> IncidentState:
    return {
        "root_cause": (
            "No DataOps incident investigation was started because the request "
            "was classified as outside this system's scope."
        ),
        "impact": "Not applicable.",
        "recommendations": [
            "Provide a data, ETL, dashboard, KPI, pipeline, warehouse, or reporting incident to investigate."
        ],
        "evidence_summary": [],
        "citations": [],
        "synthesis_mode": "scope_guard",
        "confidence": 0.0,
        "validation_passed": False,
        "validation_notes": ["scope_guard: PASS"],
        "agent_trace": [
            "Scope Guard: stopped the workflow before remote agents or the LLM were called"
        ],
    }
