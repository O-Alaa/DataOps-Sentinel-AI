from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "DataOps Sentinel AI"
    service_host: str = "0.0.0.0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_num_ctx: int = 4096

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    qdrant_url: str = ""
    qdrant_local_path: str = "qdrant_storage"
    qdrant_collection: str = "sentinel_knowledge"
    rag_top_k: int = 3

    mcp_server_url: str = "http://127.0.0.1:8100/mcp"
    a2a_data_agent_url: str = "http://127.0.0.1:8201"
    a2a_knowledge_agent_url: str = "http://127.0.0.1:8202"
    validation_max_retries: int = 1

    spacy_model: str = "en_core_web_sm"
    pii_score_threshold: float = 0.35

    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 1

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
