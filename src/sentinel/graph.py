from __future__ import annotations

import time
import uuid

from langgraph.graph import StateGraph, START, END

from sentinel.config import settings
from sentinel.state import IncidentState
from sentinel.security import prepare_input
from sentinel.observability import traced_node

from sentinel.agents.intake import intake_node
from sentinel.agents.out_of_scope import out_of_scope_node
from sentinel.agents.supervisor import supervisor_node
from sentinel.agents.remote_data_agent import remote_data_agent_node
from sentinel.agents.remote_knowledge_agent import remote_knowledge_agent_node
from sentinel.agents.root_cause import root_cause_node
from sentinel.agents.validator import validator_node
from sentinel.agents.retry_context import retry_context_node


def route_after_intake(state: IncidentState):
    if state.get("intent") == "investigate_data_incident":
        return "supervisor"
    return "out_of_scope"


def route_after_validation(state: IncidentState):
    if state.get("validation_passed"):
        return END
    if int(state.get("retry_count", 0)) < settings.validation_max_retries:
        return "retry_context"
    return END


def build_graph():
    builder = StateGraph(IncidentState)

    builder.add_node("intake", traced_node("intake", intake_node))
    builder.add_node("out_of_scope", traced_node("out_of_scope", out_of_scope_node))
    builder.add_node("supervisor", traced_node("supervisor", supervisor_node))
    builder.add_node("data_agent", traced_node("data_agent_a2a_mcp", remote_data_agent_node))
    builder.add_node("knowledge_agent", traced_node("knowledge_agent_a2a_rag", remote_knowledge_agent_node))
    builder.add_node("root_cause", traced_node("root_cause_qwen3", root_cause_node))
    builder.add_node("validator", traced_node("validator", validator_node))
    builder.add_node("retry_context", traced_node("retry_context", retry_context_node))

    builder.add_edge(START, "intake")

    # Phase 4 scope guard prevents irrelevant requests from reaching remote agents/LLM.
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "supervisor": "supervisor",
            "out_of_scope": "out_of_scope",
        },
    )
    builder.add_edge("out_of_scope", END)

    # Parallel A2A fan-out.
    builder.add_edge("supervisor", "data_agent")
    builder.add_edge("supervisor", "knowledge_agent")

    # Fan-in.
    builder.add_edge("data_agent", "root_cause")
    builder.add_edge("knowledge_agent", "root_cause")

    builder.add_edge("root_cause", "validator")
    builder.add_conditional_edges("validator", route_after_validation)
    builder.add_edge("retry_context", "supervisor")

    return builder.compile()


incident_graph = build_graph()


async def investigate(
    query: str,
    input_channel: str = "text",
) -> IncidentState:
    """
    Important security boundary:
    raw text is filtered/anonymized BEFORE entering graph state.
    """
    overall_started = time.perf_counter()
    trace_id = str(uuid.uuid4())

    prepared = prepare_input(query)

    result = await incident_graph.ainvoke(
        {
            "query": prepared.safe_text,
            "input_channel": input_channel,
            "pii_detected_count": prepared.pii_detected_count,
            "pii_entities": prepared.pii_entities,
            "security_flags": prepared.security_flags,
            "retry_count": 0,
            "retry_reason": "",
            "trace_id": trace_id,
            "agent_trace": [],
            "protocol_trace": [],
            "timing_trace": [],
        },
        {"recursion_limit": 20},
    )

    result["total_latency_ms"] = round(
        (time.perf_counter() - overall_started) * 1000,
        2,
    )
    return result
