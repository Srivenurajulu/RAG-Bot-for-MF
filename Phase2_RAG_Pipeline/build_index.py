#!/usr/bin/env python3
"""
Phase 2 — Build the RAG index (run after Phase 1).
Loads Phase 1 corpus, chunks, embeds with Gemini, indexes in ChromaDB.
"""
from pathlib import Path
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent  # repo root (parent of Phase2_RAG_Pipeline)
    load_dotenv(_root / ".env")
except ImportError:
    pass
# Use certifi's CA bundle for SSL (fixes CERTIFICATE_VERIFY_FAILED on macOS for Gemini gRPC)
try:
    import ssl
    import certifi
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
except Exception:
    pass
from .config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR
from .index_build import build_index

if __name__ == "__main__":
    print("Loading Phase 1 corpus, chunking, embedding with Gemini, indexing in ChromaDB...")
    name = build_index()
    print(f"Index built: collection '{name}' at {CHROMA_PERSIST_DIR}")
