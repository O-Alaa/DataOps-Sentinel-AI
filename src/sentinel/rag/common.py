from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from sentinel.config import PROJECT_ROOT, settings

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def load_markdown_chunks(max_chars: int = 700, overlap_chars: int = 120) -> list[dict]:
    """Lightweight paragraph-aware chunker."""
    chunks: list[dict] = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        current = ""
        chunk_index = 0

        for paragraph in paragraphs:
            candidate = paragraph if not current else current + "\n\n" + paragraph

            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                chunks.append({
                    "chunk_id": f"{path.stem}-{chunk_index}",
                    "source": path.name,
                    "text": current,
                })
                chunk_index += 1
                overlap = current[-overlap_chars:] if overlap_chars else ""
                current = (overlap + "\n\n" + paragraph).strip()
            else:
                chunks.append({
                    "chunk_id": f"{path.stem}-{chunk_index}",
                    "source": path.name,
                    "text": paragraph[:max_chars],
                })
                chunk_index += 1
                current = paragraph[max_chars - overlap_chars :]

        if current:
            chunks.append({
                "chunk_id": f"{path.stem}-{chunk_index}",
                "source": path.name,
                "text": current,
            })

    return chunks


def _normalize(array: np.ndarray) -> np.ndarray:
    if array.ndim == 1:
        norm = float(np.linalg.norm(array))
        return array if norm == 0 else array / norm

    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return array / norms


class FastEmbedAdapter:
    """Compatibility adapter exposing the encode() API used by the retriever."""

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=model_name)
        self._dimension: int | None = None

    def encode(
        self,
        texts: str | list[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        del show_progress_bar
        single = isinstance(texts, str)
        batch = [texts] if single else list(texts)
        vectors = np.asarray(list(self.model.embed(batch)), dtype=np.float32)

        if normalize_embeddings:
            vectors = _normalize(vectors)

        if self._dimension is None and len(vectors):
            self._dimension = int(vectors.shape[-1])

        return vectors[0] if single else vectors

    def get_sentence_embedding_dimension(self) -> int:
        if self._dimension is None:
            probe = self.encode("dimension probe", normalize_embeddings=True)
            self._dimension = int(probe.shape[-1])
        return self._dimension


@lru_cache(maxsize=1)
def get_embedding_model() -> Any:
    backend = settings.embedding_backend.strip().lower()

    if backend == "sentence_transformers":
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(settings.embedding_model)

    if backend == "fastembed":
        return FastEmbedAdapter(settings.embedding_model)

    raise ValueError(
        f"Unsupported EMBEDDING_BACKEND={settings.embedding_backend!r}. "
        "Supported backends: sentence_transformers, fastembed."
    )
