from qdrant_client import QdrantClient

from sentinel.config import settings


def create_qdrant_client() -> QdrantClient:
    """
    Production: connect to a standalone Qdrant service.
    Local fallback: persistent embedded Qdrant storage.
    """
    if settings.qdrant_url.strip():
        return QdrantClient(url=settings.qdrant_url.strip())

    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.qdrant_path))
