"""Tool 1 — Document search/retrieval over policies, SOPs, agreements, product docs."""
import os
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_store")

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _collection = _client.get_collection("parcelpilot_docs", embedding_function=embed_fn)
    return _collection


TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": (
            "Search ParcelPilot's policy documents, SOPs, product docs, and signed "
            "customer agreements. Returns chunks ranked with reliability metadata "
            "(tier, status, scope). ALWAYS check 'status' and 'scope' on results: "
            "prefer account-scoped signed agreements over general policy, and NEVER "
            "treat a DEPRECATED document as current authority. Call this for any "
            "question about policy, SLAs, cancellation rules, service credits, "
            "product behavior, or known issues."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query."},
                "account_id": {
                    "type": ["string", "null"],
                    "description": "Optional. If the question concerns a specific account, "
                                    "pass its account_id (e.g. ACCT-001) to prioritize that "
                                    "account's signed agreement. Pass null if not applicable.",
                },
            },
            "required": ["query"],
        },
    },
}


def search_documents(query: str, account_id: str = None, n_results: int = 4):
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=n_results)

    hits = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        hits.append({
            "content": doc,
            "source": meta["label"],
            "status": meta["status"],
            "tier": meta["tier"],
            "scope": meta["scope"],
            "relevance": round(1 - dist, 3),
        })

    # Boost the caller's own account-scoped agreement to the top when relevant,
    # and always flag deprecated docs explicitly rather than silently dropping them
    # (the model should be ABLE to see "this exists but is deprecated" to reason about it).
    if account_id:
        scope_key = f"account:{account_id}"
        hits.sort(key=lambda h: (h["scope"] != scope_key, h["tier"]))
    else:
        hits.sort(key=lambda h: h["tier"])

    return {
        "query": query,
        "results": hits,
        "precedence_reminder": (
            "Precedence when sources conflict: signed customer agreement (tier 1) "
            "> current policy/SOP (tier 2) > product docs (tier 3) > deprecated docs "
            "(never authoritative, tier 99). Historical ticket resolutions are not "
            "returned by this tool and must never be treated as policy."
        ),
    }
