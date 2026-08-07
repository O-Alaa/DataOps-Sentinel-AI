from __future__ import annotations

import json

from pydantic import BaseModel, Field

from sentinel.config import settings
from sentinel.llm import get_llm
from sentinel.state import IncidentState


class RootCauseReport(BaseModel):
    root_cause: str = Field(
        description=(
            "Evidence-grounded root cause. Preserve exact critical facts and "
            "numbers from the supplied evidence."
        )
    )
    impact: str = Field(
        description="Quantified business/data impact using only supplied evidence."
    )
    recommendations: list[str] = Field(
        description="3 to 5 concrete remediation or prevention actions."
    )
    evidence_summary: list[str] = Field(
        description="Short factual bullets showing which evidence supports the conclusion."
    )
    citations: list[str] = Field(
        description="Only filenames from the retrieved knowledge evidence."
    )


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fallback_report(state: IncidentState) -> dict:
    data = state.get("data_evidence", {})
    logs = state.get("log_evidence", {})
    knowledge = state.get("knowledge_evidence", [])

    rejected = _safe_int(data.get("latest_rejected_rows"))
    previous_loaded = _safe_int(data.get("previous_loaded_rows"))
    latest_loaded = _safe_int(data.get("latest_loaded_rows"))
    expected_loaded = _safe_int(data.get("latest_expected_rows"))
    reason = str(data.get("rejected_reason", "unknown"))
    change = data.get("loaded_rows_change_pct")

    if rejected and "employee_id" in reason and logs.get("contains_null_employee_id"):
        root_cause = (
            f"The latest Sales KPI pipeline rejected {rejected:,} rows because "
            f"`employee_id` became NULL during the employee mapping transformation. "
            "The warehouse therefore loaded fewer records, causing the dashboard decline."
        )
    else:
        root_cause = (
            "The available live evidence is incomplete, so the system cannot establish "
            "a fully validated root cause."
        )

    if previous_loaded and latest_loaded and change is not None:
        impact = (
            f"Loaded-row volume changed by {change}% versus the previous run "
            f"({previous_loaded:,} -> {latest_loaded:,})."
        )
    else:
        impact = "Impact could not be fully quantified because live data evidence was unavailable."

    evidence_summary = []
    if rejected:
        evidence_summary.append(f"Database reports {rejected:,} rejected rows.")
    if reason != "unknown":
        evidence_summary.append(f"Database rejected reason: {reason}.")
    if logs.get("contains_null_employee_id"):
        evidence_summary.append("Pipeline logs independently report NULL employee_id values.")
    if knowledge:
        evidence_summary.append(f"Retrieved {len(knowledge)} runbook/history chunks.")

    recommendations = []
    if "employee_id" in reason:
        recommendations.append(
            "Inspect and repair missing employee identifiers in the employee mapping source."
        )
    if rejected:
        recommendations.append(
            f"Reprocess the {rejected:,} rejected records after the mapping fix passes quality checks."
        )
    if expected_loaded and latest_loaded:
        recommendations.append(
            f"Verify loaded rows return to the expected {expected_loaded:,} before accepting the rerun."
        )
    recommendations.append(
        "Refresh the downstream Sales KPI dashboard only after row-count and quality validation pass."
    )

    return {
        "root_cause": root_cause,
        "impact": impact,
        "recommendations": recommendations,
        "evidence_summary": evidence_summary,
        "citations": list(dict.fromkeys(
            item["source"] for item in knowledge if item.get("source")
        )),
        "synthesis_mode": "deterministic_fallback",
    }


def _ground_critical_facts(generated_root_cause: str, state: IncidentState) -> str:
    data = state.get("data_evidence", {})
    logs = state.get("log_evidence", {})

    rejected_rows = _safe_int(data.get("latest_rejected_rows"))
    rejected_reason = str(data.get("rejected_reason", ""))
    normalized = generated_root_cause.lower()
    numeric = generated_root_cause.replace(",", "")

    employee_supported = (
        "employee_id" in rejected_reason
        and bool(logs.get("contains_null_employee_id"))
    )
    count_supported = (
        rejected_rows > 0
        and bool(logs.get("contains_rejected_rows"))
    )

    employee_present = "employee_id" in normalized and "null" in normalized
    count_present = rejected_rows > 0 and str(rejected_rows) in numeric

    if (
        (not employee_supported or employee_present)
        and (not count_supported or count_present)
    ):
        return generated_root_cause.strip()

    parts = []
    if count_supported:
        parts.append(f"The latest Sales KPI pipeline rejected {rejected_rows:,} rows")
    else:
        parts.append("The latest Sales KPI pipeline rejected rows")

    if employee_supported:
        parts.append(
            "because `employee_id` became NULL during the employee mapping transformation"
        )

    verified = " ".join(parts).strip()
    if not verified.endswith("."):
        verified += "."

    return f"{verified} {generated_root_cause.strip()}".strip()


def _message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return str(content).strip()


def _invoke_groq_json_report(prompt: str) -> RootCauseReport:
    """
    Qwen 3.6 on Groq supports JSON Object Mode, not Groq's native JSON-schema
    constrained output mode. Ask for valid JSON, then enforce our Pydantic schema
    application-side. A bounded second attempt handles occasional schema drift.
    """
    schema_text = json.dumps(RootCauseReport.model_json_schema(), indent=2)
    base_prompt = (
        prompt
        + "\n\nThe JSON object MUST satisfy this application schema exactly:\n"
        + schema_text
        + "\nReturn JSON only. Do not use Markdown fences or explanatory text."
    )

    llm = get_llm().bind(response_format={"type": "json_object"})
    last_error: Exception | None = None

    for attempt in range(2):
        attempt_prompt = base_prompt
        if last_error is not None:
            attempt_prompt += (
                "\n\nThe previous response failed application validation. "
                f"Correct the schema error and return a complete JSON object: {last_error}"
            )

        message = llm.invoke(attempt_prompt)
        raw_text = _message_text(message)

        try:
            parsed = json.loads(raw_text)
            return RootCauseReport.model_validate(parsed)
        except Exception as exc:
            last_error = exc

    assert last_error is not None
    raise last_error


def _invoke_report(prompt: str) -> RootCauseReport:
    provider = settings.llm_provider.strip().lower()

    if provider == "groq":
        return _invoke_groq_json_report(prompt)

    structured_llm = get_llm().with_structured_output(
        RootCauseReport,
        method="json_schema",
    )
    return structured_llm.invoke(prompt)


def root_cause_node(state: IncidentState) -> IncidentState:
    data = state.get("data_evidence", {})
    logs = state.get("log_evidence", {})
    knowledge = state.get("knowledge_evidence", [])

    context = {
        "user_incident": state.get("query"),
        "database_evidence": data,
        "pipeline_log_evidence": logs,
        "retrieved_knowledge": knowledge,
        "validation_retry_reason": state.get("retry_reason", ""),
        "service_events": state.get("service_events", []),
    }

    prompt = f"""
You are the Root Cause Analysis Agent in an enterprise DataOps incident system.

Use ONLY the supplied evidence.

Rules:
1. Separate observations from causation.
2. Cross-check database evidence against pipeline logs.
3. Runbooks/history are supporting documentation, not live system facts.
4. Preserve all evidence-critical numbers exactly.
5. Explicitly preserve the rejected-row count when supplied.
6. Explicitly mention employee_id becoming NULL only if supported by live evidence.
7. Quantify loaded-row impact when supplied.
8. Never invent systems, tables, errors, people, dates, numbers, root causes, or fixes.
9. Citations may contain ONLY filenames present in retrieved_knowledge.
10. If a service is unavailable, explicitly avoid treating its missing evidence as proof.
11. If validation_retry_reason is non-empty, correct the failed point using supplied evidence.

Return ONLY a valid JSON object with exactly these fields:
- root_cause: string
- impact: string
- recommendations: array of strings
- evidence_summary: array of strings
- citations: array of strings

Evidence:
{json.dumps(context, indent=2)}
"""

    try:
        provider = settings.llm_provider.strip().lower()
        report = _invoke_report(prompt)

        allowed_sources = {
            item.get("source") for item in knowledge if item.get("source")
        }
        safe_citations = [
            source for source in report.citations if source in allowed_sources
        ]
        if not safe_citations and allowed_sources:
            safe_citations = list(dict.fromkeys(
                item["source"] for item in knowledge if item.get("source")
            ))

        grounded_root_cause = _ground_critical_facts(
            generated_root_cause=report.root_cause,
            state=state,
        )

        synthesis_mode = (
            "qwen3_structured_output"
            if provider == "ollama"
            else "groq_qwen_json_output"
        )
        provider_label = (
            f"Ollama/{settings.ollama_model}"
            if provider == "ollama"
            else f"Groq/{settings.groq_model}"
        )

        return {
            "root_cause": grounded_root_cause,
            "impact": report.impact,
            "recommendations": report.recommendations,
            "evidence_summary": report.evidence_summary,
            "citations": safe_citations,
            "synthesis_mode": synthesis_mode,
            "agent_trace": [
                "Root Cause Agent: "
                f"{provider_label} synthesized the report and evidence invariants were verified"
            ],
        }

    except Exception as exc:
        fallback = _fallback_report(state)
        fallback["agent_trace"] = [
            "Root Cause Agent: configured LLM unavailable/invalid; used "
            f"deterministic fallback ({type(exc).__name__})"
        ]
        return fallback
