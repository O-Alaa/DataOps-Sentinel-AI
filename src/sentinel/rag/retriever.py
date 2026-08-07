from __future__ import annotations

from collections import defaultdict
from rank_bm25 import BM25Okapi

from sentinel.config import settings
from sentinel.rag.common import (
    get_embedding_model,
    load_markdown_chunks,
    tokenize,
)
from sentinel.rag.qdrant_store import create_qdrant_client

RRF_K = 60


def _rrf_add(
    scores: dict[str, float],
    ranked_ids: list[str],
    weight: float,
) -> None:
    for rank, chunk_id in enumerate(ranked_ids, start=1):
        scores[chunk_id] += weight * (1.0 / (RRF_K + rank))


def hybrid_search(query: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or settings.rag_top_k
    candidate_k = max(top_k * 3, 8)

    chunks = load_markdown_chunks()
    if not chunks:
        return []

    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}

    model = get_embedding_model()
    query_vector = model.encode(query, normalize_embeddings=True).tolist()

    client = create_qdrant_client()

    if not client.collection_exists(settings.qdrant_collection):
        client.close()
        raise RuntimeError(
            "Qdrant knowledge index does not exist. "
            "Run: python scripts/ingest_knowledge.py"
        )

    dense_points = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=candidate_k,
        with_payload=True,
    ).points
    client.close()

    dense_ranked = []
    dense_raw = {}
    for point in dense_points:
        payload = point.payload or {}
        chunk_id = payload.get("chunk_id")
        if chunk_id:
            dense_ranked.append(chunk_id)
            dense_raw[chunk_id] = float(point.score)

    tokenized_corpus = [tokenize(chunk["text"]) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(tokenize(query))

    bm25_order = sorted(
        range(len(chunks)),
        key=lambda i: float(bm25_scores[i]),
        reverse=True,
    )[:candidate_k]

    bm25_ranked = [chunks[i]["chunk_id"] for i in bm25_order]
    bm25_raw = {
        chunks[i]["chunk_id"]: float(bm25_scores[i])
        for i in bm25_order
    }

    fused: dict[str, float] = defaultdict(float)
    _rrf_add(fused, dense_ranked, weight=0.65)
    _rrf_add(fused, bm25_ranked, weight=0.35)

    ranked = sorted(
        fused.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]

    results = []
    for chunk_id, fused_score in ranked:
        chunk = chunk_by_id[chunk_id]
        results.append({
            "chunk_id": chunk_id,
            "source": chunk["source"],
            "text": chunk["text"],
            "retrieval_method": "BGE dense + BM25 + weighted RRF",
            "fused_score": round(fused_score, 6),
            "dense_score": round(dense_raw.get(chunk_id, 0.0), 4),
            "bm25_score": round(bm25_raw.get(chunk_id, 0.0), 4),
        })

    return results
