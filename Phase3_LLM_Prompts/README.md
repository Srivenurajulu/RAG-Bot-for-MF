# Phase 3 — LLM & Prompts (MF FAQ Assistant)

Produces short, factual answers from retrieved context using Gemini, or a fixed refusal for advice-style queries.

## Components

| Module | Role |
|--------|------|
| **config.py** | Gemini model name, `GOOGLE_API_KEY`, refusal message, AMFI/SEBI education URLs |
| **classifier.py** | `classify_query(query)` → `"factual"` or `"advice"`; `get_refusal_response()` → (answer_text, source_url) |
| **prompts.py** | System prompt (facts-only, one citation, ≤3 sentences, no PII, "Last updated from sources"); `build_user_prompt(...)` |
| **answer.py** | `answer_query(user_query, retrieved_chunks, citation_url, scrape_date)` → `{ answer_text, source_url, refused }` |

## Flow

1. **Advice query** (e.g. "Should I buy this fund?"): classifier returns `"advice"` → return fixed refusal + education URL; **no RAG, no LLM** on context.
2. **Factual query**: build system + user prompt from retrieved chunks, citation URL, scrape date; call Gemini; normalize reply (one source link, "Last updated from sources"); return answer + citation_url.

## Setup

```bash
cd Phase3_LLM_Prompts
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key
```

## Usage (e.g. from Phase 4)

From repo root (so that `Phase3_LLM_Prompts` is a package):

```python
from Phase3_LLM_Prompts.classifier import classify_query, get_refusal_response
from Phase3_LLM_Prompts.answer import answer_query

# If advice, skip RAG and use refusal
if classify_query("Should I invest in this scheme?") == "advice":
    answer_text, source_url = get_refusal_response()
    # return answer_text, source_url, refused=True

# Factual: pass RAG output into answer_query
result = answer_query(
    user_query="What is the expense ratio of ICICI Prudential Large Cap Fund?",
    retrieved_chunks=["...chunk 1...", "...chunk 2..."],
    citation_url="https://www.icicipruamc.com/.../factsheet.pdf",
    scrape_date="2025-01-15",
)
# result["answer_text"], result["source_url"], result["refused"]
```

## Config

- **GEMINI_LLM_MODEL**: `gemini-2.0-flash`, `gemini-1.5-flash`, or `gemini-2.5-flash` (when available).
- **Refusal**: Message + AMFI/SEBI investor-education URL; no LLM call for advice queries.

## Reply normalization

- Exactly one "Source: [URL]" using the provided citation URL (hallucinated URLs replaced).
- Line "Last updated from sources: [scrape_date]" appended or corrected.
- No PII; no returns comparison; ≤3 sentences encouraged by system prompt.
