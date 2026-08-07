from functools import lru_cache

from sentinel.config import settings


@lru_cache(maxsize=1)
def get_llm():
    """
    Return the configured chat model.

    Local profile:
      Ollama + Qwen on the developer machine.

    Cloud profile:
      Managed Groq inference. The rest of the grounding and deterministic
      validation architecture remains unchanged.
    """
    provider = settings.llm_provider.strip().lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            reasoning=False,
            num_ctx=settings.ollama_num_ctx,
        )

    if provider == "groq":
        if not settings.groq_api_key.strip():
            raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")

        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0,
            max_retries=2,
            model_kwargs={
                "reasoning_effort": "none",
                "reasoning_format": "hidden",
            },
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
        "Supported providers: ollama, groq."
    )
