from __future__ import annotations

import re
from pathlib import Path
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from sentinel.config import PROJECT_ROOT, settings

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"

def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())

def load_markdown_chunks(max_chars: int = 700, overlap_chars: int = 120) -> list[dict]:
    """
    Lightweight paragraph-aware chunker.

    We deliberately keep chunking transparent for interview discussion instead
    of hiding it behind a framework abstraction.
    """
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
                current = paragraph[max_chars-overlap_chars:]

        if current:
            chunks.append({
                "chunk_id": f"{path.stem}-{chunk_index}",
                "source": path.name,
                "text": current,
            })

    return chunks

@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)
