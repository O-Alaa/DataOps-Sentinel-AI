from sentinel.state import IncidentState


def validator_node(state: IncidentState) -> IncidentState:
    data = state.get("data_evidence", {})
    logs = state.get("log_evidence", {})
    knowledge = state.get("knowledge_evidence", [])
    root_cause = state.get("root_cause", "")
    citations = state.get("citations", [])

    retrieved_sources = {
        item.get("source") for item in knowledge if item.get("source")
    }

    try:
        rejected_rows = int(data.get("latest_rejected_rows", 0))
    except (TypeError, ValueError):
        rejected_rows = 0

    normalized = root_cause.lower()
    numeric = root_cause.replace(",", "")

    checks = {
        "database_has_rejected_rows": rejected_rows > 0,
        "database_names_employee_id":
            "employee_id" in str(data.get("rejected_reason", "")),
        "log_confirms_null_employee_id":
            bool(logs.get("contains_null_employee_id")),
        "log_confirms_rejected_rows":
            bool(logs.get("contains_rejected_rows")),
        "rag_returned_supporting_evidence":
            len(knowledge) > 0,
        "root_cause_preserves_employee_id_fact":
            "employee_id" in normalized and "null" in normalized,
        "root_cause_preserves_rejected_row_count":
            rejected_rows > 0 and str(rejected_rows) in numeric,
        "citations_are_retrieved_sources":
            len(citations) > 0
            and all(source in retrieved_sources for source in citations),
    }

    passed_checks = sum(bool(value) for value in checks.values())
    total_checks = len(checks)
    confidence = round(passed_checks / total_checks, 2)

    critical_checks = [
        "database_has_rejected_rows",
        "database_names_employee_id",
        "log_confirms_null_employee_id",
        "log_confirms_rejected_rows",
        "root_cause_preserves_employee_id_fact",
        "root_cause_preserves_rejected_row_count",
        "citations_are_retrieved_sources",
    ]

    critical_checks_passed = all(checks[name] for name in critical_checks)
    validation_passed = confidence >= 0.80 and critical_checks_passed

    notes = [
        f"{name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in checks.items()
    ]

    failed_critical = [name for name in critical_checks if not checks[name]]
    if failed_critical:
        notes.append("critical_validation: FAIL - " + ", ".join(failed_critical))
    else:
        notes.append("critical_validation: PASS")

    return {
        "confidence": confidence,
        "validation_passed": validation_passed,
        "validation_notes": notes,
        "agent_trace": [
            (
                f"Validator Agent: {passed_checks}/{total_checks} evidence checks passed; "
                f"critical checks={'PASS' if critical_checks_passed else 'FAIL'}"
            )
        ],
    }
