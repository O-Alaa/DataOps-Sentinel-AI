from sentinel.state import IncidentState
from sentinel.tools.database import get_latest_kpi_summary

def data_agent_node(state: IncidentState) -> IncidentState:
    evidence = get_latest_kpi_summary()

    trace = list(state.get("agent_trace", []))
    trace.append(
        "Data Agent: queried DuckDB and compared latest vs previous pipeline loads"
    )

    return {
        "data_evidence": evidence,
        "agent_trace": trace,
    }
