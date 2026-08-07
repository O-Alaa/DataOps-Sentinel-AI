from functools import lru_cache
from langchain_ollama import ChatOllama

from sentinel.config import settings

@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    """
    Local open-source LLM through Ollama.

    reasoning=False is intentional for the demo:
    - lower latency
    - cleaner structured output
    - the system's reliability comes from external evidence + validation,
      not hidden reasoning text.
    """
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        reasoning=False,
        num_ctx=settings.ollama_num_ctx,
    )
