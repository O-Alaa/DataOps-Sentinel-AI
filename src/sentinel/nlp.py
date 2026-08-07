from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import spacy

from sentinel.config import settings


ERROR_CODE_RE = re.compile(r"\b(?:ERR(?:OR)?[-_]?\d{2,8}|[A-Z]{2,10}[-_]\d{2,8})\b")
TECH_IDENTIFIER_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
PIPELINE_RE = re.compile(r"\b[a-z0-9_]*(?:etl|pipeline)[a-z0-9_]*\b", re.IGNORECASE)

INCIDENT_TERMS = {
    "drop",
    "dropped",
    "dropping",
    "down",
    "decline",
    "declined",
    "declining",
    "fall",
    "fell",
    "fallen",
    "falling",
    "decrease",
    "decreased",
    "decreasing",
    "failed",
    "failure",
    "incident",
    "error",
    "issue",
    "broken",
    "missing",
    "rejected",
    "investigate",
    "anomaly",
    "outage",
    "wrong",
    "incorrect",
    "spike",
}

TECH_TERMS = {
    "dashboard", "kpi", "etl", "pipeline", "warehouse", "database", "table",
    "data", "metric", "report", "refresh", "rows", "records", "sql",
}

HIGH_SEVERITY_TERMS = {
    "executive", "production", "failed", "outage", "critical", "significant",
    "major", "severe",
}


@lru_cache(maxsize=1)
def get_nlp():
    return spacy.load(settings.spacy_model)


def analyze_incident_text(text: str) -> dict[str, Any]:
    doc = get_nlp()(text)
    lower_tokens = {token.lemma_.lower() for token in doc if not token.is_space}
    lower_text = text.lower()

    incident_hits = sorted(term for term in INCIDENT_TERMS if term in lower_tokens or term in lower_text)
    tech_hits = sorted(term for term in TECH_TERMS if term in lower_tokens or term in lower_text)
    high_hits = sorted(term for term in HIGH_SEVERITY_TERMS if term in lower_tokens or term in lower_text)

    error_codes = sorted(set(ERROR_CODE_RE.findall(text)))
    technical_identifiers = sorted(set(TECH_IDENTIFIER_RE.findall(text)))
    pipelines = sorted(set(PIPELINE_RE.findall(text)))

    named_entities = [
        {
            "text": ent.text,
            "label": ent.label_,
        }
        for ent in doc.ents
        if ent.label_ in {"ORG", "PRODUCT", "DATE", "TIME", "EVENT"}
    ]

    is_incident = bool(incident_hits and (tech_hits or technical_identifiers or pipelines))

    if is_incident:
        intent = "investigate_data_incident"
    else:
        intent = "out_of_scope"

    severity = "high" if len(high_hits) >= 1 and is_incident else ("medium" if is_incident else "none")

    system = "Unknown"
    if "sales" in lower_text and ("dashboard" in lower_text or "kpi" in lower_text):
        system = "Sales KPI Dashboard"

    metric = "Sales KPI" if "sales" in lower_text and "kpi" in lower_text else "Unknown"

    return {
        "intent": intent,
        "severity": severity,
        "entities": {
            "system": system,
            "metric": metric,
            "time_reference": "latest" if any(x in lower_text for x in ["today", "latest", "current"]) else "unspecified",
            "error_codes": error_codes,
            "pipeline_identifiers": pipelines,
            "technical_identifiers": technical_identifiers,
            "named_entities": named_entities,
        },
        "features": {
            "incident_terms": incident_hits,
            "technical_terms": tech_hits,
            "high_severity_terms": high_hits,
        },
    }
