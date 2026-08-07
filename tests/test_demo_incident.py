import asyncio

import pytest

from sentinel.graph import investigate


@pytest.mark.integration
def test_demo_incident_is_validated():
    result = asyncio.run(
        investigate(
            "The Sales KPI dashboard dropped today. "
            "Investigate the incident."
        )
    )

    assert result["intent"] == "investigate_data_incident"

    assert result["validation_passed"] is True

    assert "employee_id" in result["root_cause"].lower()

    assert "3678" in result["root_cause"].replace(",", "")

    assert result["confidence"] >= 0.80

    assert len(result.get("citations", [])) > 0