from sentinel.state import IncidentState


def retry_context_node(state: IncidentState) -> IncidentState:
    failed = [
        note for note in state.get("validation_notes", [])
        if note.endswith("FAIL")
    ]
    reason = "; ".join(failed) if failed else "Validator requested additional evidence."
    next_retry = int(state.get("retry_count", 0)) + 1

    return {
        "retry_count": next_retry,
        "retry_reason": reason,
        "agent_trace": [
            f"Validation Loop: retry {next_retry} requested because evidence checks failed"
        ],
        "protocol_trace": [
            {
                "protocol": "LangGraph conditional loop",
                "action": "retry_investigation",
                "retry": next_retry,
                "reason": reason,
            }
        ],
    }
