"""
Phase 2 — Build ChromaDB index from Phase 1 corpus.
Chunk documents, embed with Gemini, store in ChromaDB with metadata.
"""
import hashlib
import json
from pathlib import Path

from .config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
from .load_phase1 import load_phase1_corpus_prefer_funds
from .chunking import chunk_document
from .embeddings import embed_texts
import chromadb
from chromadb.config import Settings


def build_index(collection_name: str = None, persist_dir: Path = None) -> str:
    """
    Load Phase 1 corpus, chunk, embed, and index in ChromaDB.
    Returns the collection name.
    """
    collection_name = collection_name or CHROMA_COLLECTION_NAME
    persist_dir = persist_dir or CHROMA_PERSIST_DIR
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Prefer structured funds (funds.json) when present so RAG answers from structured facts
    docs = load_phase1_corpus_prefer_funds()
    all_chunks = []
    for doc in docs:
        # For structured fund docs, one doc = one chunk (no splitting)
        if doc.get("page_type") == "structured_fund":
            all_chunks.append({
                "text": doc["text"],
                "source_url": doc["url"],
                "scrape_date": doc.get("scrape_date", ""),
                "page_type": doc.get("page_type", ""),
                "scheme_name": doc.get("scheme_name", ""),
            })
            continue
        chunks = chunk_document(
            text=doc["text"],
            source_url=doc["url"],
            scrape_date=doc.get("scrape_date", ""),
            page_type=doc.get("page_type", ""),
            scheme_name=doc.get("scheme_name", ""),
        )
        all_chunks.extend(chunks)

    if not all_chunks:
        raise RuntimeError("No chunks produced from Phase 1 corpus. Check Phase 1 data.")

    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)

    # ChromaDB metadata values must be str, int, float, or bool
    metadatas = []
    ids = []
    for i, c in enumerate(all_chunks):
        metadatas.append({
            "source_url": c["source_url"],
            "scrape_date": c["scrape_date"],
            "page_type": c["page_type"],
            "scheme_name": c["scheme_name"],
        })
        # Stable id from content + index
        id_str = hashlib.sha256((c["text"] + c["source_url"] + str(i)).encode()).hexdigest()[:24]
        ids.append(id_str)

    client = chromadb.PersistentClient(path=str(persist_dir), settings=Settings(anonymized_telemetry=False))
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": "MF FAQ corpus from Phase 1"},
    )
    # Add in batches to avoid huge payloads
    batch_size = 100
    for j in range(0, len(ids), batch_size):
        end = min(j + batch_size, len(ids))
        collection.add(
            ids=ids[j:end],
            embeddings=embeddings[j:end],
            documents=texts[j:end],
            metadatas=metadatas[j:end],
        )
    return collection_name
