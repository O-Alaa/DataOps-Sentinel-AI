from sentinel.agents.validator import validator_node


def good_state():
    return {
        "data_evidence": {
            "latest_rejected_rows": 3678,
            "rejected_reason": "employee_id is NULL after mapping",
        },
        "log_evidence": {
            "contains_null_employee_id": True,
            "contains_rejected_rows": True,
        },
        "knowledge_evidence": [
            {"source": "pipeline_runbook.md"},
        ],
        "root_cause": (
            "The pipeline rejected 3,678 rows because employee_id became NULL."
        ),
        "citations": ["pipeline_runbook.md"],
    }


def test_validator_accepts_fully_grounded_answer():
    result = validator_node(good_state())
    assert result["validation_passed"] is True
    assert result["confidence"] == 1.0


def test_critical_fact_failure_cannot_pass_on_average():
    state = good_state()
    state["root_cause"] = "employee_id became NULL."
    result = validator_node(state)
    assert result["validation_passed"] is False
