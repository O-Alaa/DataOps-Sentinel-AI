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
from sentinel.rag.retriever import hybrid_search


async def health(request):
    return JSONResponse({"status": "ok", "service": "knowledge-agent"})


class KnowledgeInvestigationExecutor(AgentExecutor):
    async def execute(self, context, event_queue) -> None:
        raw = get_message_text(context.message) if context.message else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"query": raw}

        query = str(payload.get("query", ""))
        retry_reason = str(payload.get("retry_reason", ""))

        augmented = (
            query
            + " employee_id rejected rows ETL pipeline quality gate recovery procedure "
            + "historical incident "
            + retry_reason
        )

        results = hybrid_search(augmented)
        evidence = [
            {
                "source": item["source"],
                "chunk_id": item["chunk_id"],
                "retrieval_method": item["retrieval_method"],
                "fused_score": item["fused_score"],
                "dense_score": item["dense_score"],
                "bm25_score": item["bm25_score"],
                "excerpt": " ".join(item["text"].split())[:650],
            }
            for item in results
        ]

        await event_queue.enqueue_event(
            new_text_message(
                text=json.dumps({
                    "knowledge_evidence": evidence,
                    "retrieval_method": "BGE dense + Qdrant + BM25 + weighted RRF",
                }),
                role=Role.ROLE_AGENT,
            )
        )

    async def cancel(self, context, event_queue) -> None:
        raise RuntimeError("This short read-only investigation does not support cancellation.")


skill = AgentSkill(
    id="knowledge_investigation",
    name="Runbook and Historical Incident Retrieval",
    description="Retrieves evidence using hybrid RAG.",
    tags=["rag", "qdrant", "bm25", "bge", "knowledge"],
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    examples=["Find runbook evidence related to NULL employee_id rows."],
)

agent_card = AgentCard(
    name="DataOps Sentinel Knowledge Agent",
    description="Independent A2A specialist for enterprise hybrid retrieval.",
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            protocol_version="1.0",
            url=settings.a2a_knowledge_agent_url,
        )
    ],
    version="0.5.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=KnowledgeInvestigationExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

routes = [Route("/health", health, methods=["GET"])]
routes.extend(create_agent_card_routes(agent_card))
routes.extend(create_jsonrpc_routes(handler, "/"))
app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.service_host, port=8202)
