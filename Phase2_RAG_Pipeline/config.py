"""
Phase 2 — RAG pipeline config.
Phase 1 data path, chunking, embedding, and ChromaDB settings.
"""
import os
from pathlib import Path

# Path to Phase 1 output (manifest + data/raw/)
PHASE_DIR = Path(__file__).resolve().parent
PHASE1_DIR = PHASE_DIR.parent / "Phase1_Corpus_and_Scope"
PHASE1_DATA_DIR = os.environ.get("PHASE1_DATA_DIR", str(PHASE1_DIR))
PHASE1_RAW_DIR = Path(PHASE1_DATA_DIR) / "data" / "raw"
PHASE1_MANIFEST_PATH = Path(PHASE1_DATA_DIR) / "data" / "manifest.json"
PHASE1_FUNDS_PATH = Path(PHASE1_DATA_DIR) / "data" / "funds.json"

# Chunking: sentence and paragraph boundaries so tables/lists are not split awkwardly.
# Order: paragraph (\n\n), line (\n), sentence (". "), then word (" ").
CHUNK_SIZE_CHARS = 1800   # ~450 tokens
CHUNK_OVERLAP_CHARS = 200  # ~50 tokens
SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", " "]  # sentence-boundary before mid-sentence break

# Gemini embedding
# Use a widely supported Gemini embedding model ID.
GEMINI_EMBEDDING_MODEL = "models/embedding-001"
EMBED_BATCH_SIZE = 50  # batch for API calls
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"

# ChromaDB
CHROMA_PERSIST_DIR = PHASE_DIR / "data" / "chroma"
CHROMA_COLLECTION_NAME = "mf_faq_corpus"

# Retrieval (final number of chunks passed to LLM after hybrid + re-rank)
DEFAULT_TOP_K = 5
