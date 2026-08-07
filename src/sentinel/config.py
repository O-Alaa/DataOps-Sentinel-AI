from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "DataOps Sentinel AI"
    service_host: str = "0.0.0.0"

    # LLM provider profile.
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_num_ctx: int = 4096
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    # Retrieval.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_backend: str = "sentence_transformers"
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_local_path: str = "qdrant_storage"
    qdrant_collection: str = "sentinel_knowledge"
    rag_top_k: int = 3
    rag_auto_ingest: bool = False
    rag_recreate_on_start: bool = False

    # Protocol endpoints.
    mcp_server_url: str = "http://127.0.0.1:8100/mcp"
    a2a_data_agent_url: str = "http://127.0.0.1:8201"
    a2a_knowledge_agent_url: str = "http://127.0.0.1:8202"
    validation_max_retries: int = 1

    # Security / NLP.
    spacy_model: str = "en_core_web_sm"
    pii_score_threshold: float = 0.35
    api_auth_key: str = ""

    # Speech-to-text provider profile.
    stt_provider: str = "local"
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 1
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # Observability / presentation.
    otel_service_name: str = "dataops-sentinel-ai"
    api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
    )

    @property
    def qdrant_path(self) -> Path:
        path = Path(self.qdrant_local_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path


settings = Settings()
