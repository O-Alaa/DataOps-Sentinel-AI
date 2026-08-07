import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.rag.retriever import hybrid_search

query = (
    "What should happen when employee_id is NULL and rows are rejected "
    "from the Sales KPI ETL?"
)

if __name__ == "__main__":
    results = hybrid_search(query, top_k=4)

    print("\n=== HYBRID RAG RESULTS ===")
    for i, item in enumerate(results, start=1):
        print(f"\n#{i} {item['source']} / {item['chunk_id']}")
        print(f"Method: {item['retrieval_method']}")
        print(
            f"RRF={item['fused_score']}  "
            f"Dense={item['dense_score']}  "
            f"BM25={item['bm25_score']}"
        )
        print(" ".join(item["text"].split())[:500])
