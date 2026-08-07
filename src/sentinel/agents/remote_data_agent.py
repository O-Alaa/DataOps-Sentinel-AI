from sentinel.config import settings
from sentinel.protocols.a2a_client import call_a2a_json
from sentinel.protocols.schemas import DataAgentResponse
from sentinel.state import IncidentState


async def remote_data_agent_node(state: IncidentState) -> IncidentState:
    payload = {
        "query": state["query"],
        "retry_reason": state.get("retry_reason", ""),
    }

    try:
        raw = await call_a2a_json(settings.a2a_data_agent_url, payload)
        result = DataAgentResponse.model_validate(raw)

        return {
            "data_evidence": result.data_evidence,
            "log_evidence": result.log_evidence,
            "agent_trace": [
                "Data Agent (A2A): delegated investigation to independent remote specialist"
            ],
            "protocol_trace": [
                {
                    "protocol": "A2A 1.0 / JSON-RPC",
                    "target": settings.a2a_data_agent_url,
                    "agent": "DataOps Sentinel Data Agent",
                    "nested_protocol": "MCP v2",
                    "tools": result.mcp_tools_used,
                }
            ],
            "service_events": [
                {
                    "service": "data_agent",
                    "status": "available",
                    "detail": "A2A data investigation completed",
                }
            ],
        }

    except Exception as exc:
        return {
            "data_evidence": {},
            "log_evidence": {},
            "agent_trace": [
                "Data Agent (A2A): unavailable; continuing with remaining evidence"
            ],
            "protocol_trace": [
                {
                    "protocol": "A2A 1.0 / JSON-RPC",
                    "target": settings.a2a_data_agent_url,
                    "agent": "DataOps Sentinel Data Agent",
                    "status": "failed",
                    "error_type": type(exc).__name__,
                }
            ],
            "service_events": [
                {
                    "service": "data_agent",
                    "status": "degraded",
                    "detail": f"{type(exc).__name__}: remote data evidence unavailable",
                }
            ],
        }
