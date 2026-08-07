import operator
from typing import Any, Annotated, TypedDict

class IncidentState(TypedDict, total=False):
    query: str
    input_channel: str

    pii_detected_count: int
    pii_entities: list[str]
    security_flags: list[str]

    intent: str
    entities: dict[str, Any]
    severity: str
    nlp_features: dict[str, Any]
    out_of_scope_reason: str

    investigation_plan: list[str]

    data_evidence: dict[str, Any]
    log_evidence: dict[str, Any]
    knowledge_evidence: list[dict[str, Any]]

    root_cause: str
    impact: str
    recommendations: list[str]
    evidence_summary: list[str]
    citations: list[str]
    synthesis_mode: str

    confidence: float
    validation_passed: bool
    validation_notes: list[str]
    retry_count: int
    retry_reason: str

    trace_id: str
    total_latency_ms: float

    agent_trace: Annotated[list[str], operator.add]
    protocol_trace: Annotated[list[dict[str, Any]], operator.add]
    timing_trace: Annotated[list[dict[str, Any]], operator.add]
    service_events: Annotated[list[dict[str, Any]], operator.add]
