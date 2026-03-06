"""
Phase 2 — Retrieval: get_relevant_context(query, k) with hybrid (vector + keyword) and re-ranking.
Uses ChromaDB + Gemini embedding; keyword overlap for exact phrases (e.g. "Nifty 50 TRI", "lock-in").
RRF merges vector and keyword results; then re-ranks by query-term overlap. No PII.
Returns distances so the caller can decide when there is no good match.
"""
import re
from typing import List, Tuple

from .config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, DEFAULT_TOP_K
from .embeddings import embed_query
import chromadb
from chromadb.config import Settings


# Prefer these page types for the single citation (official AMC docs)
PREFERRED_CITATION_PAGE_TYPES = ("factsheet", "kim", "sid")

# Hybrid search: fetch more candidates then re-rank and take top k
RETRIEVE_CANDIDATES = 15   # vector top 15 + keyword top 15 -> RRF -> re-rank -> top k
RRF_K = 60                 # reciprocal rank fusion constant


def _tokenize(text: str) -> List[str]:
    """Lowercase tokenize; keep tokens of length >= 2."""
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in tokens if len(t) >= 2]


def _keyword_score(query_tokens: List[str], document: str) -> float:
    """Score document by number of query terms present (simple BM25-like boost for exact phrases)."""
    if not query_tokens or not document:
        return 0.0
    doc_lower = document.lower()
    return sum(1 for t in query_tokens if t in doc_lower)


def _rrf_merge(
    vector_ids: List[str],
    keyword_ids: List[str],
    k_final: int,
    rrf_k: int = RRF_K,
) -> List[str]:
    """Merge two ranked id lists using reciprocal rank fusion. Returns top k_final ids."""
    rank_v = {vid: i + 1 for i, vid in enumerate(vector_ids)}
    rank_k = {kid: i + 1 for i, kid in enumerate(keyword_ids)}
    candidate_ids = list(set(vector_ids) | set(keyword_ids))
    scores = {}
    for cid in candidate_ids:
        rv = rank_v.get(cid, rrf_k + 1)
        rk = rank_k.get(cid, rrf_k + 1)
        scores[cid] = 1 / (rrf_k + rv) + 1 / (rrf_k + rk)
    ordered = sorted(candidate_ids, key=lambda x: -scores[x])
    return ordered[:k_final]


def get_relevant_context(
    query: str,
    k: int = None,
    collection_name: str = None,
    persist_dir: str = None,
) -> Tuple[List[str], List[str], str, str, List[float]]:
    """
    Hybrid retrieval: vector search + keyword (term overlap) over corpus, RRF merge, then
    re-rank by keyword score. Returns (chunk_texts, source_urls, chosen_citation_url, scrape_date, distances).
    """
    k = k or DEFAULT_TOP_K
    collection_name = collection_name or CHROMA_COLLECTION_NAME
    persist_dir = persist_dir or str(CHROMA_PERSIST_DIR)

    query_embedding = embed_query(query)
    query_tokens = _tokenize(query)
    client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection(name=collection_name)
    n_total = collection.count()
    if n_total == 0:
        return ([], [], "", "", [])

    # 1) Vector search: top RETRIEVE_CANDIDATES with ids
    n_vector = min(RETRIEVE_CANDIDATES, n_total)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_vector,
        include=["documents", "metadatas", "distances", "ids"],
    )
    vector_ids = results.get("ids", [[]])[0] or []
    vector_docs = results["documents"][0] if results["documents"] else []
    vector_metas = results["metadatas"][0] if results["metadatas"] else []
    vector_dists = results["distances"][0] if results.get("distances") else []

    # 2) Keyword retrieval: get all docs (corpus is small), score, take top RETRIEVE_CANDIDATES ids
    all_ids, all_docs, all_metas = [], [], []
    try:
        all_data = collection.get(include=["documents", "metadatas"], limit=500)
        all_ids = all_data.get("ids") or []
        all_docs = all_data.get("documents") or []
        all_metas = all_data.get("metadatas") or []
    except Exception:
        pass

    keyword_ids = []
    if all_ids and all_docs and query_tokens:
        scored = [(all_ids[i], _keyword_score(query_tokens, all_docs[i])) for i in range(len(all_ids))]
        scored.sort(key=lambda x: -x[1])
        keyword_ids = [sid for sid, _ in scored[:RETRIEVE_CANDIDATES]]

    # 3) RRF merge and take top k
    merged_ids = _rrf_merge(vector_ids, keyword_ids, k_final=k, rrf_k=RRF_K)
    if not merged_ids:
        merged_ids = vector_ids[:k]

    # 4) Build id -> doc/meta/dist maps (vector first, then fill from all_data)
    id_to_doc = {vector_ids[i]: vector_docs[i] for i in range(len(vector_ids))}
    id_to_meta = {vector_ids[i]: vector_metas[i] for i in range(len(vector_metas))}
    id_to_dist = {vector_ids[i]: vector_dists[i] for i in range(len(vector_dists))}
    for i, uid in enumerate(all_ids):
        if uid not in id_to_doc:
            id_to_doc[uid] = all_docs[i] if i < len(all_docs) else ""
        if uid not in id_to_meta:
            id_to_meta[uid] = all_metas[i] if i < len(all_metas) else {}
        if uid not in id_to_dist:
            id_to_dist[uid] = 1.0

    # 5) Re-rank merged list by keyword score (exact phrase matches float up)
    def reorder_key(id_list):
        return -_keyword_score(query_tokens, id_to_doc.get(id_list, ""))

    reranked_ids = sorted(merged_ids, key=reorder_key)

    chunk_texts = [id_to_doc.get(uid, "") for uid in reranked_ids if id_to_doc.get(uid)]
    source_urls = [id_to_meta.get(uid, {}).get("source_url", "") for uid in reranked_ids]
    distances = [id_to_dist.get(uid, 1.0) for uid in reranked_ids]

    # Choose ONE citation URL and scrape_date
    metadatas = [id_to_meta.get(uid, {}) for uid in reranked_ids]
    chosen_citation_url = ""
    scrape_date = ""
    for m in metadatas:
        pt = (m.get("page_type") or "").lower()
        if pt in PREFERRED_CITATION_PAGE_TYPES:
            chosen_citation_url = m.get("source_url", "")
            scrape_date = m.get("scrape_date", "")
            break
    if not chosen_citation_url and source_urls:
        chosen_citation_url = source_urls[0] or ""
        if metadatas:
            scrape_date = metadatas[0].get("scrape_date", "")

    return (chunk_texts, source_urls, chosen_citation_url, scrape_date, distances)
