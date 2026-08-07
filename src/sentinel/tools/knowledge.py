from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"

def keyword_search_knowledge(query: str, limit: int = 3) -> list[dict]:
    # Temporary deterministic retrieval. Replaced by Qdrant + BGE + BM25 in Phase 2.
    terms = {
        token.strip(".,:;!?()[]{}").lower()
        for token in query.split()
        if len(token) >= 4
    }

    scored = []
    for path in KNOWLEDGE_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        score = sum(lower.count(term) for term in terms)

        if "employee_id" in lower:
            score += 5
        if "rejected" in lower:
            score += 3

        scored.append((score, path, text))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "source": path.name,
            "score": score,
            "excerpt": " ".join(text.split())[:500],
        }
        for score, path, text in scored[:limit]
        if score > 0
    ]
