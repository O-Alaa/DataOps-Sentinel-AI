from sentinel.state import IncidentState

def supervisor_node(state: IncidentState) -> IncidentState:
    plan = [
        "Inspect latest KPI and row-count changes",
        "Inspect the latest ETL/pipeline logs",
        "Retrieve runbook and historical incident evidence",
        "Synthesize a root-cause hypothesis",
        "Validate the hypothesis against independent evidence",
    ]

    return {
        "investigation_plan": plan,
        "agent_trace": ["Supervisor Agent: created investigation plan"],
    }
