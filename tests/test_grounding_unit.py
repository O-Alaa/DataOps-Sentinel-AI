from sentinel.agents.root_cause import _ground_critical_facts


def test_grounding_restores_verified_rejected_count():
    state = {
        "data_evidence": {
            "latest_rejected_rows": 3678,
            "rejected_reason": "employee_id is NULL after mapping",
        },
        "log_evidence": {
            "contains_null_employee_id": True,
            "contains_rejected_rows": True,
        },
    }

    output = _ground_critical_facts(
        "employee_id became NULL during transformation.",
        state,
    )

    assert "3678" in output.replace(",", "")
    assert "employee_id" in output
