from __future__ import annotations

import uuid
from qdrant_client import models

from sentinel.config import settings
from sentinel.rag.common import get_embedding_model, load_markdown_chunks
from sentinel.rag.qdrant_store import create_qdrant_client


def build_index(recreate: bool = True) -> dict:
    chunks = load_markdown_chunks()
    if not chunks:
        raise RuntimeError(
            "No knowledge documents found. Run scripts/generate_demo_data.py first."
        )

    model = get_embedding_model()
    dimension = model.get_sentence_embedding_dimension()

    client = create_qdrant_client()
    exists = client.collection_exists(settings.qdrant_collection)

    if exists and recreate:
        client.delete_collection(settings.qdrant_collection)
        exists = False

    if not exists:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
            ),
        )

    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    points = []
    for chunk, vector in zip(chunks, embeddings):
        point_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"dataops-sentinel/{chunk['chunk_id']}",
        ))
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload=chunk,
            )
        )

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
        wait=True,
    )
    client.close()

    return {
        "collection": settings.qdrant_collection,
        "chunks_indexed": len(chunks),
        "embedding_model": settings.embedding_model,
        "dimension": dimension,
        "storage": settings.qdrant_url or str(settings.qdrant_path),
    }
