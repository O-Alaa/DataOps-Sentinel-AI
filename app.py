import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
PROJECT_ROOT = Path(__file__).resolve().parent

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
    "Production-style multi-agent Data & BI incident investigation • "
    "LangGraph • A2A • MCP • Hybrid RAG • Local Qwen3"
)

def get_dependency_status():
    try:
        response = requests.get(
            f"{API_BASE_URL}/health/dependencies",
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {"ready": False, "services": []}

with st.sidebar:
    st.subheader("System Status")
    health = get_dependency_status()

    if health.get("services"):
        for service in health["services"]:
            symbol = "🟢" if service["status"] == "healthy" else "🔴"
            st.write(f"{symbol} **{service['service']}**")
    else:
        st.warning("API/dependency health unavailable")

    st.divider()
    st.subheader("Architecture")
    st.caption(
        "Text/Voice → Security/NLP → LangGraph → "
        "A2A specialists → MCP/RAG → Qwen3 → Validator"
    )

tab_investigate, tab_eval, tab_ops = st.tabs(
    ["Investigation", "Evaluation", "Operations"]
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
            "Transcribe locally",
            use_container_width=True,
        ):
            with st.spinner("Transcribing with faster-whisper..."):
                response = requests.post(
                    f"{API_BASE_URL}/transcribe",
                    files={
                        "file": (
                            "incident.wav",
                            audio_value.getvalue(),
                            "audio/wav",
                        )
                    },
                    timeout=300,
                )
                response.raise_for_status()
                transcription = response.json()

            st.session_state.incident_query = transcription["safe_preview"]

            a, b, c = st.columns(3)
            a.metric("Language", transcription.get("language", "-").upper())
            b.metric(
                "Language confidence",
                f"{float(transcription.get('language_probability', 0)):.0%}",
            )
            c.metric(
                "STT latency",
                f"{float(transcription.get('transcription_latency_ms', 0))/1000:.2f}s",
            )

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
                response = requests.post(
                    f"{API_BASE_URL}/investigate",
                    json={
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

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Severity", str(result.get("severity", "-")).upper())
            m2.metric("Confidence", f"{float(result.get('confidence', 0)):.0%}")
            m3.metric(
                "Validated",
                "YES" if result.get("validation_passed") else "NO",
            )
            m4.metric(
                "Synthesis",
                "QWEN3"
                if result.get("synthesis_mode") == "qwen3_structured_output"
                else "FALLBACK",
            )
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
                "Investigation request failed. Check the Operations tab for "
                f"dependency health. Details: {exc}"
            )

with tab_eval:
    st.subheader("Latest Regression Evaluation")
    latest_path = PROJECT_ROOT / "evals" / "results" / "latest.json"

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

        st.dataframe(
            pd.DataFrame(report.get("cases", [])),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Run `python scripts/evaluate_phase4.py` to create the report.")

with tab_ops:
    st.subheader("Dependency Health")
    health = get_dependency_status()

    if health.get("services"):
        st.dataframe(
            pd.DataFrame(health["services"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.error("Unable to read dependency health.")

    st.subheader("Runtime")
    st.code(
        "docker compose up -d --build\n"
        "docker compose ps\n"
        "docker compose logs -f api",
        language="bash",
    )

    st.subheader("Useful endpoints")
    st.code(
        "Streamlit: http://localhost:8501\n"
        "FastAPI:   http://localhost:8000/docs\n"
        "Qdrant:    http://localhost:6333/dashboard\n"
        "Data A2A:  http://localhost:8201/.well-known/agent-card.json\n"
        "RAG A2A:   http://localhost:8202/.well-known/agent-card.json",
        language=None,
    )
