from sentinel.state import IncidentState
from sentinel.tools.logs import inspect_latest_pipeline_log

def log_agent_node(state: IncidentState) -> IncidentState:
    evidence = inspect_latest_pipeline_log()

    trace = list(state.get("agent_trace", []))
    trace.append("Log Agent: inspected pipeline warnings and rejected-row evidence")

    return {
        "log_evidence": evidence,
        "agent_trace": trace,
    }
