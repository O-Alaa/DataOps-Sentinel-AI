import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a.helpers import get_message_text, new_text_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Role,
)

from sentinel.config import settings
from sentinel.protocols.mcp_client import collect_dataops_evidence


async def health(request):
    return JSONResponse({"status": "ok", "service": "data-agent"})


class DataInvestigationExecutor(AgentExecutor):
    async def execute(self, context, event_queue) -> None:
        _ = get_message_text(context.message) if context.message else ""
        result = await collect_dataops_evidence()

        await event_queue.enqueue_event(
            new_text_message(
                text=json.dumps(result),
                role=Role.ROLE_AGENT,
            )
        )

    async def cancel(self, context, event_queue) -> None:
        raise RuntimeError("This short read-only investigation does not support cancellation.")


skill = AgentSkill(
    id="data_pipeline_investigation",
    name="Data and Pipeline Investigation",
    description="Investigates KPI row counts and ETL logs through MCP.",
    tags=["dataops", "sql", "pipeline", "mcp"],
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    examples=["Investigate why the Sales KPI dashboard dropped today."],
)

agent_card = AgentCard(
    name="DataOps Sentinel Data Agent",
    description="Independent A2A specialist for database and pipeline-log evidence.",
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            protocol_version="1.0",
            url=settings.a2a_data_agent_url,
        )
    ],
    version="0.5.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=DataInvestigationExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

routes = [Route("/health", health, methods=["GET"])]
routes.extend(create_agent_card_routes(agent_card))
routes.extend(create_jsonrpc_routes(handler, "/"))
app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.service_host, port=8201)
