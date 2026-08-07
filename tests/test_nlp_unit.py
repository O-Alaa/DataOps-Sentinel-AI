from sentinel.nlp import analyze_incident_text


def test_dataops_incident_routes_correctly():
    result = analyze_incident_text(
        "The executive Sales KPI dashboard dropped today after the ETL pipeline."
    )

    assert result["intent"] == "investigate_data_incident"
    assert result["entities"]["system"] == "Sales KPI Dashboard"


def test_unrelated_request_is_out_of_scope():
    result = analyze_incident_text("Write a poem about the ocean.")
    assert result["intent"] == "out_of_scope"

def test_falling_kpi_is_detected_as_incident():
    result = analyze_incident_text(
        "Why did today's Sales KPI report fall "
        "after the morning ETL run?"
    )

    assert (
        result["intent"]
        == "investigate_data_incident"
    )