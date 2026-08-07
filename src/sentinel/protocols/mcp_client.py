from __future__ import annotations

from typing import Any
from mcp import Client

from sentinel.config import settings


def _tool_error_text(result: Any) -> str:
    parts = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return " | ".join(parts) or "Unknown MCP tool error"


async def call_mcp_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call one remote MCP v2 tool and require structured output."""
    async with Client(settings.mcp_server_url) as client:
        result = await client.call_tool(name, arguments or {})

    if getattr(result, "is_error", False):
        raise RuntimeError(f"MCP tool {name!r} failed: {_tool_error_text(result)}")

    structured = getattr(result, "structured_content", None)
    if not isinstance(structured, dict):
        raise RuntimeError(
            f"MCP tool {name!r} did not return structured JSON data."
        )

    return structured


async def collect_dataops_evidence() -> dict[str, Any]:
    """
    The A2A Data Agent uses this MCP client rather than importing DB/log tools.
    This creates a real protocol boundary between the agent and enterprise tools.
    """
    data = await call_mcp_tool("get_latest_kpi_summary")
    logs = await call_mcp_tool("inspect_latest_pipeline_log")
    return {
        "data_evidence": data,
        "log_evidence": logs,
        "mcp_tools_used": [
            "get_latest_kpi_summary",
            "inspect_latest_pipeline_log",
        ],
    }
