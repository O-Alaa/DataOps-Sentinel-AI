from typing import Any
from pydantic import BaseModel, Field

class DataAgentResponse(BaseModel):
    data_evidence: dict[str, Any]
    log_evidence: dict[str, Any]
    mcp_tools_used: list[str] = Field(default_factory=list)

class KnowledgeAgentResponse(BaseModel):
    knowledge_evidence: list[dict[str, Any]]
    retrieval_method: str
