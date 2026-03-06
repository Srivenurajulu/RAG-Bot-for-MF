# Phase 2 — RAG Pipeline (MF FAQ Assistant)

Builds the retrieval index from Phase 1 corpus and exposes `get_relevant_context(query, k=5)` for the FAQ assistant.

## Input

- **Phase 1 output:** `Phase1_Corpus_and_Scope/data/raw/*.txt` and `data/manifest.json`
- Set `PHASE1_DATA_DIR` if Phase 1 data lives elsewhere (default: `../Phase1_Corpus_and_Scope`).

## Components

| Module | Role |
|--------|------|
| **config.py** | Paths, chunk size/overlap, Gemini model, ChromaDB path, top-k |
| **load_phase1.py** | Load manifest + parse raw `.txt` files (metadata + body) |
| **chunking.py** | Split documents into overlapping segments (~300–600 tokens), keep tables intact; attach source_url, scrape_date, page_type, scheme_name |
| **embeddings.py** | Gemini embedding API (batch for docs, single for query); same model at index and query time |
| **index_build.py** | Chunk → embed → ChromaDB add (id, embedding, text, metadata) |
| **retrieve.py** | `get_relevant_context(query, k=5)` → (chunk texts, source_urls, chosen_citation_url) |

## Citation rule

One source URL per answer: prefer **factsheet**, **kim**, or **sid** from the top-k results; otherwise use the first result’s URL.

## Setup

```bash
cd Phase2_RAG_Pipeline
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key   # from https://aistudio.google.com/apikey
```

## Build index (after Phase 1)

From the **repo root** (parent of Phase2_RAG_Pipeline):

```bash
python -m Phase2_RAG_Pipeline.build_index
```

- Reads Phase 1 manifest and raw files, chunks, embeds with Gemini, writes to `data/chroma/`.
- Requires `GOOGLE_API_KEY` in the environment.

## Use retrieval (e.g. from Phase 3/4)

From repo root (so that `Phase2_RAG_Pipeline` is a package):

```python
from Phase2_RAG_Pipeline.retrieve import get_relevant_context

chunk_texts, source_urls, citation_url, scrape_date = get_relevant_context("What is the expense ratio of ICICI Prudential Large Cap Fund?", k=5)
# Use chunk_texts, citation_url, scrape_date in the LLM prompt.
```

## Config (config.py)

- **Chunking:** `CHUNK_SIZE_CHARS` (~450 tokens), `CHUNK_OVERLAP_CHARS` (~50 tokens).
- **Embedding:** `GEMINI_EMBEDDING_MODEL` (e.g. `models/text-embedding-004` or `models/embedding-001`).
- **ChromaDB:** `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`.
- **Retrieval:** `DEFAULT_TOP_K = 5`.

## Known limits

- Embedding model must match at index and query time.
- ChromaDB is local; for scale consider Pinecone (same interface pattern: embed → query index → return chunks + metadata).
- No PII; content comes only from the indexed Phase 1 corpus.
