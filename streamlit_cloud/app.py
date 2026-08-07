import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
        if value is not None:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


API_BASE_URL = _setting("API_BASE_URL").rstrip("/")
API_KEY = _setting("API_KEY")
API_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

st.set_page_config(
    page_title="DataOps Sentinel AI",
    page_icon="🛰️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; max-width: 1500px;}
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.22);
        padding: .7rem 1rem;
        border-radius: .65rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛰️ DataOps Sentinel AI")
st.caption(
    "Cloud multi-agent Data & BI incident investigation • "
    "LangGraph • A2A • MCP • Hybrid RAG • Managed Qwen inference"
)

if not API_BASE_URL:
    st.error(
        "Backend is not configured. Add API_BASE_URL and API_KEY in "
        "Streamlit Community Cloud → App settings → Secrets."
    )
    st.stop()


def api_get(path: str, timeout: int = 8):
    return requests.get(
        f"{API_BASE_URL}{path}",
        headers=API_HEADERS,
        timeout=timeout,
    )


def api_post(path: str, *, json_body=None, files=None, timeout: int = 360):
    return requests.post(
        f"{API_BASE_URL}{path}",
        headers=API_HEADERS,
        json=json_body,
        files=files,
        timeout=timeout,
    )


def get_dependency_status():
    try:
        response = api_get("/health/dependencies", timeout=8)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {"ready": False, "services": []}


with st.sidebar:
    st.subheader("Cloud System Status")
    health = get_dependency_status()

    if health.get("services"):
        for service in health["services"]:
            symbol = "🟢" if service["status"] == "healthy" else "🔴"
            st.write(f"{symbol} **{service['service']}**")
    else:
        st.warning("Backend/dependency health unavailable")

    st.divider()
    st.subheader("Architecture")
    st.caption(
        "Streamlit Cloud → FastAPI → LangGraph → A2A specialists → "
        "MCP/RAG → Groq-hosted Qwen → deterministic validator"
    )


tab_investigate, tab_eval, tab_ops = st.tabs(
    ["Investigation", "Evaluation", "Cloud Operations"]
)


with tab_investigate:
    input_mode = st.radio(
        "Input mode",
        ["Text", "Voice"],
        horizontal=True,
    )

    if "incident_query" not in st.session_state:
        st.session_state.incident_query = (
            "Our executive Sales KPI dashboard dropped significantly today. "
            "Investigate what happened and recommend what we should do."
        )

    input_channel = "text"

    if input_mode == "Voice":
        input_channel = "voice"
        audio_value = st.audio_input(
            "Record incident",
            sample_rate=16000,
        )

        if audio_value is not None and st.button(
            "Transcribe",
            use_container_width=True,
        ):
            try:
                with st.spinner("Transcribing through cloud Whisper..."):
                    response = api_post(
                        "/transcribe",
                        files={
                            "file": (
                                "incident.wav",
                                audio_value.getvalue(),
                                "audio/wav",
                            )
                        },
                        timeout=180,
                    )
                    response.raise_for_status()
                    transcription = response.json()

                st.session_state.incident_query = transcription["safe_preview"]

                a, b, c = st.columns(3)
                a.metric(
                    "Language",
                    str(transcription.get("language", "-")).upper(),
                )
                probability = float(
                    transcription.get("language_probability", 0) or 0
                )
                b.metric(
                    "Language confidence",
                    f"{probability:.0%}" if probability else "N/A",
                )
                c.metric(
                    "STT latency",
                    f"{float(transcription.get('transcription_latency_ms', 0))/1000:.2f}s",
                )
            except requests.RequestException as exc:
                st.error(f"Transcription failed: {exc}")

    query = st.text_area(
        "Incident description",
        key="incident_query",
        height=125,
    )

    if st.button(
        "Run autonomous investigation",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.status(
                "Investigating across data, logs, and enterprise knowledge...",
                expanded=True,
            ) as status:
                response = api_post(
                    "/investigate",
                    json_body={
                        "query": query,
                        "input_channel": input_channel,
                    },
                    timeout=360,
                )
                response.raise_for_status()
                result = response.json()

                status.update(
                    label="Investigation complete",
                    state="complete",
                )

            degraded = [
                event
                for event in result.get("service_events", [])
                if event.get("status") == "degraded"
            ]

            if degraded:
                st.warning(
                    "Graceful degradation active: "
                    + "; ".join(
                        f"{event['service']} unavailable"
                        for event in degraded
                    )
                )

            synthesis_mode = str(result.get("synthesis_mode", ""))
            if synthesis_mode == "qwen3_structured_output":
                synthesis_label = "QWEN3 / OLLAMA"
            elif synthesis_mode == "groq_qwen_structured_output":
                synthesis_label = "QWEN / GROQ"
            else:
                synthesis_label = "FALLBACK"

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Severity", str(result.get("severity", "-")).upper())
            m2.metric("Confidence", f"{float(result.get('confidence', 0)):.0%}")
            m3.metric(
                "Validated",
                "YES" if result.get("validation_passed") else "NO",
            )
            m4.metric("Synthesis", synthesis_label)
            m5.metric("Retries", int(result.get("retry_count", 0)))
            m6.metric(
                "Latency",
                f"{float(result.get('total_latency_ms', 0))/1000:.2f}s",
            )

            st.caption(f"Trace ID: `{result.get('trace_id', '-')}`")

            if result.get("intent") == "out_of_scope":
                st.info(result.get("root_cause"))
            else:
                st.subheader("Root Cause")
                if result.get("validation_passed"):
                    st.success(result.get("root_cause"))
                else:
                    st.warning(result.get("root_cause"))

                st.subheader("Impact")
                st.write(result.get("impact", "-"))

                left, right = st.columns(2)
                with left:
                    st.subheader("Evidence")
                    for item in result.get("evidence_summary", []):
                        st.write("•", item)
                with right:
                    st.subheader("Recommended Actions")
                    for i, item in enumerate(result.get("recommendations", []), 1):
                        st.write(f"{i}. {item}")

            timings = result.get("timing_trace", [])
            if timings:
                st.subheader("Execution Performance")
                timing_df = pd.DataFrame(timings)
                st.dataframe(
                    timing_df,
                    use_container_width=True,
                    hide_index=True,
                )
                chart_df = timing_df.copy()
                chart_df["invocation"] = [
                    f"{row.node} [retry {row.retry}]"
                    for row in chart_df.itertuples()
                ]
                st.bar_chart(
                    chart_df.set_index("invocation")["duration_ms"]
                )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("Security / NLP")
                st.write("PII redactions:", result.get("pii_detected_count", 0))
                st.write("Security flags:", len(result.get("security_flags", [])))
                with st.expander("NLP details"):
                    st.json({
                        "intent": result.get("intent"),
                        "severity": result.get("severity"),
                        "entities": result.get("entities"),
                        "features": result.get("nlp_features"),
                    })

            with col2:
                st.subheader("Agent / Protocol Trace")
                for item in result.get("agent_trace", []):
                    st.write("✓", item)
                with st.expander("Protocol details"):
                    for item in result.get("protocol_trace", []):
                        st.json(item)

            with col3:
                st.subheader("Validation")
                for item in result.get("validation_notes", []):
                    st.write(
                        "✅" if "PASS" in item and "FAIL" not in item else "❌",
                        item,
                    )
                st.subheader("Citations")
                for source in result.get("citations", []):
                    st.code(source, language=None)

            with st.expander("Raw evidence"):
                st.json({
                    "database": result.get("data_evidence"),
                    "pipeline_logs": result.get("log_evidence"),
                    "rag": result.get("knowledge_evidence"),
                    "services": result.get("service_events"),
                })

        except requests.RequestException as exc:
            st.error(
                "Investigation request failed. Check Cloud Operations for "
                f"dependency health. Details: {exc}"
            )


with tab_eval:
    st.subheader("Validated Local Production Regression")
    latest_path = PROJECT_ROOT / "evals" / "results" / "phase5_latest.json"

    if latest_path.exists():
        report = json.loads(latest_path.read_text(encoding="utf-8"))
        summary = report.get("summary", {})

        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric("Cases", summary.get("cases", 0))
        e2.metric("Routing", f"{summary.get('routing_accuracy', 0):.0%}")
        e3.metric("Fact accuracy", f"{summary.get('fact_accuracy', 0):.0%}")
        e4.metric("PII leak", f"{summary.get('pii_leak_rate', 0):.0%}")
        e5.metric(
            "Avg latency",
            f"{summary.get('avg_latency_ms', 0)/1000:.2f}s",
        )

        st.caption(
            "These metrics are the previously validated Docker/Ollama regression "
            "baseline. Re-evaluate the managed-cloud profile before publishing "
            "cloud metrics."
        )
        st.dataframe(
            pd.DataFrame(report.get("cases", [])),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No committed production evaluation artifact was found.")


with tab_ops:
    st.subheader("Backend Dependency Health")
    health = get_dependency_status()

    if health.get("services"):
        st.dataframe(
            pd.DataFrame(health["services"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.error("Unable to read backend dependency health.")

    st.subheader("Cloud Deployment Profile")
    st.code(
        "Streamlit Community Cloud\n"
        "        ↓ HTTPS + X-API-Key\n"
        "Railway FastAPI\n"
        "        ↓ private Railway network\n"
        "LangGraph → A2A Agents → MCP / Hybrid RAG\n"
        "        ↓                    ↓\n"
        "      DuckDB           Qdrant Cloud\n"
        "        └────── Groq-hosted Qwen ──────┘",
        language=None,
    )
