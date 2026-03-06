# Phase 4 — Backend API (MF FAQ Assistant)

Single chat endpoint that ties Phase 2 (RAG) and Phase 3 (LLM), with PII rejection and concise responses.

## API

- **POST /chat**
  - **Body:** `{ "query": "user message" }`
  - **Response:** `{ "answer": "...", "source_url": "https://...", "refused": false }`  
    For advice queries: `refused: true` and `source_url` is the investor-education link.
  - **400** if the query contains PII (PAN, Aadhaar, account numbers, OTP, email, phone): *"Personal information is not accepted. Please do not send PAN, Aadhaar, account numbers, OTPs, email, or phone numbers."*

- **GET /health** — `{ "status": "ok" }`

## Flow

1. **Validate:** Reject if `query` contains PII → 400.
2. **Classify:** If advice → return refusal + education link; skip RAG and LLM.
3. **RAG:** `get_relevant_context(query)` (Phase 2). Uses scrape_date from chosen chunk.
4. **LLM:** `answer_query(...)` (Phase 3). Enforces one citation URL and "Last updated from sources".
5. **Respond:** JSON with `answer`, `source_url`, `refused`.

No logging or storage of PII. Responses are concise (≤3 sentences for factual answers).

## Where to add the API key

**Add `GOOGLE_API_KEY` before starting the server** (or before the first request):

- **Advice queries** (e.g. “Should I buy this fund?”) do **not** use the key — they return a fixed refusal + education link.
- **Factual queries** (e.g. “What is the expense ratio?”) use the key twice:
  1. **Phase 2 (RAG):** Gemini embedding API to find relevant chunks.
  2. **Phase 3 (LLM):** Gemini to generate the answer.

If the key is missing, the server can start, but **POST /chat** for a factual question will fail with an error about `GOOGLE_API_KEY`. So set it before running:

```bash
export GOOGLE_API_KEY=your_key   # Get one at https://aistudio.google.com/apikey
PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --reload --port 8000
```

### Optional: Gemini polish for fast_lookup / all_info answers

- **Default:** Answers from `funds.json` (fast_lookup, all_info) are returned as-is (template text). No extra Gemini call.
- **Enable:** Set `USE_GEMINI_POLISH_FAST_ANSWERS=1` (or `true`/`yes`) so those answers are rewritten by Gemini for a friendlier tone; facts and numbers stay the same. Adds latency and API usage.
- **Revert:** Unset the variable or set it to `0`/`false`: `unset USE_GEMINI_POLISH_FAST_ANSWERS` or `export USE_GEMINI_POLISH_FAST_ANSWERS=0`. No code change needed.

## Setup

From the **repo root** (parent of Phase4_Backend_API):

```bash
pip install -r Phase4_Backend_API/requirements.txt
# Phase 2 and Phase 3 deps (if not already installed)
pip install -r Phase2_RAG_Pipeline/requirements.txt
pip install -r Phase3_LLM_Prompts/requirements.txt
export GOOGLE_API_KEY=your_key
```

Ensure Phase 2 index is built (`python -m Phase2_RAG_Pipeline.build_index`) and ChromaDB path is correct.

## Run

From the **repo root**:

```bash
PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --reload --host 0.0.0.0 --port 8000
```

Or run the script (from repo root):

```bash
chmod +x Phase4_Backend_API/run_server.sh
./Phase4_Backend_API/run_server.sh
```

## Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the expense ratio of ICICI Prudential Large Cap Fund?"}'
```
