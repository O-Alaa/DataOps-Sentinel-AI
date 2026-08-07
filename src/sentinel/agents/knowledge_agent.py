from sentinel.state import IncidentState
from sentinel.rag.retriever import hybrid_search

def knowledge_agent_node(state: IncidentState) -> IncidentState:
    query = (
        state["query"]
        + " employee_id rejected rows ETL pipeline quality gate "
        + "recovery procedure historical incident"
    )

    results = hybrid_search(query)

    evidence = [
        {
            "source": item["source"],
            "chunk_id": item["chunk_id"],
            "retrieval_method": item["retrieval_method"],
            "fused_score": item["fused_score"],
            "dense_score": item["dense_score"],
            "bm25_score": item["bm25_score"],
            "excerpt": " ".join(item["text"].split())[:650],
        }
        for item in results
    ]

    trace = list(state.get("agent_trace", []))
    trace.append(
        f"Knowledge Agent: hybrid RAG retrieved {len(evidence)} evidence chunks "
        "using BGE + Qdrant + BM25/RRF"
    )

    return {
        "knowledge_evidence": evidence,
        "agent_trace": trace,
    }
