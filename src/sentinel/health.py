from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx

from sentinel.config import settings


async def _http_status(name: str, url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
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
            timeout=3.5,
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


async def _llm_status() -> dict:
    provider = settings.llm_provider.strip().lower()

    if provider == "ollama":
        return await _http_status(
            "llm_ollama",
            settings.ollama_base_url.rstrip("/") + "/api/tags",
        )

    if provider == "groq":
        configured = bool(settings.groq_api_key.strip())
        return {
            "service": "llm_groq",
            "status": "healthy" if configured else "unavailable",
            "detail": "managed provider configured" if configured else "provider key missing",
        }

    return {
        "service": f"llm_{provider or 'unknown'}",
        "status": "unavailable",
        "detail": f"Unsupported LLM provider: {provider}",
    }


async def _qdrant_status() -> dict:
    if not settings.qdrant_url.strip():
        return await _http_status("qdrant", "http://127.0.0.1:6333/readyz")

    try:
        from sentinel.rag.qdrant_store import create_qdrant_client

        client = create_qdrant_client()
        client.get_collections()
        client.close()
        return {
            "service": "qdrant",
            "status": "healthy",
            "detail": "Qdrant API reachable",
        }
    except Exception as exc:
        return {
            "service": "qdrant",
            "status": "unavailable",
            "detail": f"{type(exc).__name__}: {exc}",
        }


async def dependency_health() -> dict:
    checks = await asyncio.gather(
        _llm_status(),
        _qdrant_status(),
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
    return {"ready": ready, "services": checks}
