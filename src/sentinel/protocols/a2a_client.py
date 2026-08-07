from __future__ import annotations

import json
from typing import Any

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_stream_response_text, new_text_message
from a2a.types import Role, SendMessageRequest


async def call_a2a_json(agent_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Discover an A2A agent from its Agent Card, send one JSON payload as text,
    and parse the single message response as JSON.
    """
    client = await create_client(
        agent=agent_url,
        client_config=ClientConfig(streaming=False),
    )

    try:
        message = new_text_message(
            text=json.dumps(payload),
            role=Role.ROLE_USER,
        )
        request = SendMessageRequest(message=message)

        response_text = ""
        async for chunk in client.send_message(request):
            text = get_stream_response_text(chunk)
            if text:
                response_text = text

        if not response_text:
            raise RuntimeError(f"A2A agent at {agent_url} returned no text response.")

        parsed = json.loads(response_text)
        if not isinstance(parsed, dict):
            raise RuntimeError("A2A response must be a JSON object.")
        return parsed
    finally:
        await client.close()
