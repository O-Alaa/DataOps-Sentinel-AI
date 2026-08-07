from __future__ import annotations

import inspect
import os
import time
from functools import wraps
from typing import Callable, Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from sentinel.config import settings


def _configure_tracer() -> None:
    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        return

    provider = TracerProvider(
        resource=Resource.create({
            "service.name": settings.otel_service_name,
        })
    )

    # Optional exporter. This is compatible with Langfuse's OTLP endpoint
    # once OTEL_EXPORTER_OTLP_* environment variables are configured.
    if (
        os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    ):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)


_configure_tracer()
tracer = trace.get_tracer("sentinel.langgraph")


def traced_node(name: str, fn: Callable[..., Any]):
    if inspect.iscoroutinefunction(fn):
        @wraps(fn)
        async def async_wrapper(state):
            started = time.perf_counter()
            with tracer.start_as_current_span(name) as span:
                span.set_attribute("sentinel.node", name)
                span.set_attribute("sentinel.trace_id", state.get("trace_id", ""))
                span.set_attribute("sentinel.retry_count", int(state.get("retry_count", 0)))
                try:
                    output = await fn(state)
                    return {
                        **output,
                        "timing_trace": [{
                            "node": name,
                            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                            "status": "ok",
                            "retry": int(state.get("retry_count", 0)),
                        }],
                    }
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_attribute("sentinel.status", "error")
                    raise
        return async_wrapper

    @wraps(fn)
    def sync_wrapper(state):
        started = time.perf_counter()
        with tracer.start_as_current_span(name) as span:
            span.set_attribute("sentinel.node", name)
            span.set_attribute("sentinel.trace_id", state.get("trace_id", ""))
            span.set_attribute("sentinel.retry_count", int(state.get("retry_count", 0)))
            try:
                output = fn(state)
                return {
                    **output,
                    "timing_trace": [{
                        "node": name,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                        "status": "ok",
                        "retry": int(state.get("retry_count", 0)),
                    }],
                }
            except Exception as exc:
                span.record_exception(exc)
                span.set_attribute("sentinel.status", "error")
                raise

    return sync_wrapper
