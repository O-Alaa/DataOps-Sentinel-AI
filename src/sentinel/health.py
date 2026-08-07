from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx

from sentinel.config import settings


async def _http_status(name: str, url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(url)
        ok = 200 <= response.status_code < 400
        return {
            "service": name,
            "status": "healthy" if ok else "unhealthy",
            "detail": f"HTTP {response.status_code}",
        }
    except Exception as exc:
        return {
            "service": name,
            "status": "unavailable",
            "detail": f"{type(exc).__name__}: {exc}",
        }


async def _tcp_status(name: str, url: str) -> dict:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=2.5,
        )
        writer.close()
        await writer.wait_closed()
        return {
            "service": name,
            "status": "healthy",
            "detail": f"TCP {host}:{port}",
        }
    except Exception as exc:
        return {
            "service": name,
            "status": "unavailable",
            "detail": f"{type(exc).__name__}: {exc}",
        }


async def dependency_health() -> dict:
    checks = await asyncio.gather(
        _http_status(
            "ollama",
            settings.ollama_base_url.rstrip("/") + "/api/tags",
        ),
        _http_status(
            "qdrant",
            (
                settings.qdrant_url.rstrip("/") + "/readyz"
                if settings.qdrant_url
                else "http://127.0.0.1:6333/readyz"
            ),
        ),
        _http_status(
            "data_agent",
            settings.a2a_data_agent_url.rstrip("/") + "/health",
        ),
        _http_status(
            "knowledge_agent",
            settings.a2a_knowledge_agent_url.rstrip("/") + "/health",
        ),
        _tcp_status("mcp", settings.mcp_server_url),
    )

    ready = all(item["status"] == "healthy" for item in checks)

    return {
        "ready": ready,
        "services": checks,
    }
