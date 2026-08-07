from sentinel.nlp import analyze_incident_text
from sentinel.state import IncidentState

def intake_node(state: IncidentState) -> IncidentState:
    result = analyze_incident_text(state["query"])

    if result["intent"] == "out_of_scope":
        reason = (
            "The request does not contain enough DataOps/BI incident signals "
            "for the investigation workflow."
        )
    else:
        reason = ""

    return {
        "intent": result["intent"],
        "severity": result["severity"],
        "entities": result["entities"],
        "nlp_features": result["features"],
        "out_of_scope_reason": reason,
        "agent_trace": [
            "NLP Intake Agent: spaCy + rules classified intent, severity, and technical entities"
        ],
    }
