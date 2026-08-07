from sentinel.config import settings
from sentinel.protocols.a2a_client import call_a2a_json
from sentinel.protocols.schemas import KnowledgeAgentResponse
from sentinel.state import IncidentState


async def remote_knowledge_agent_node(state: IncidentState) -> IncidentState:
    payload = {
        "query": state["query"],
        "retry_reason": state.get("retry_reason", ""),
    }

    try:
        raw = await call_a2a_json(settings.a2a_knowledge_agent_url, payload)
        result = KnowledgeAgentResponse.model_validate(raw)

        return {
            "knowledge_evidence": result.knowledge_evidence,
            "agent_trace": [
                "Knowledge Agent (A2A): delegated retrieval to independent remote specialist"
            ],
            "protocol_trace": [
                {
                    "protocol": "A2A 1.0 / JSON-RPC",
                    "target": settings.a2a_knowledge_agent_url,
                    "agent": "DataOps Sentinel Knowledge Agent",
                    "retrieval": result.retrieval_method,
                }
            ],
            "service_events": [
                {
                    "service": "knowledge_agent",
                    "status": "available",
                    "detail": "A2A hybrid retrieval completed",
                }
            ],
        }

    except Exception as exc:
        return {
            "knowledge_evidence": [],
            "agent_trace": [
                "Knowledge Agent (A2A): unavailable; continuing with remaining evidence"
            ],
            "protocol_trace": [
                {
                    "protocol": "A2A 1.0 / JSON-RPC",
                    "target": settings.a2a_knowledge_agent_url,
                    "agent": "DataOps Sentinel Knowledge Agent",
                    "status": "failed",
                    "error_type": type(exc).__name__,
                }
            ],
            "service_events": [
                {
                    "service": "knowledge_agent",
                    "status": "degraded",
                    "detail": f"{type(exc).__name__}: RAG evidence unavailable",
                }
            ],
        }
