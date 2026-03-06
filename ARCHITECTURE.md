# FAQ Assistant for Mutual Fund Schemes — Architecture & Phase-by-Phase Implementation

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USER (Browser)                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (Phase 5 — Tiny UI)                                                     │
│  • Welcome line, 3 example questions, "Facts-only. No investment advice."          │
│  • Chat input → POST /chat (optional context_fund for follow-ups)                   │
│  • Render answer + single citation link + "Last updated from sources: <date>"     │
│  • Resources page from GET /api/sources                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  BACKEND (Phase 4 — FastAPI)                                                       │
│  • POST /chat: query + optional context_fund → answer, source_url, refused,       │
│    context_fund. PII check → 400. Structured audit: request_id, path, latency_ms  │
│  • Flow: out_of_scope → advice_refused → fast paths (other_amc, KIM/SID,           │
│    unknown_fund, all_info, list_funds, fast_lookup) → icici_unknown_fund → RAG →   │
│    Gemini. Optional polish for fast_lookup/all_info (USE_GEMINI_POLISH_FAST_ANSWERS)│
│  • GET /health: status, gemini_configured, vector_db_ok, funds_json_ok             │
│  • GET /api/sources: ICICI AMC, INDmoney, KIM/SID first, then sources.csv          │
│  • GET /api/funds-by-type: funds grouped by type (Equity, Hybrid, Index)           │
└─────────────────────────────────────────────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┬───────────────────┐
    ▼               ▼               ▼                   ▼
┌───────────┐  ┌───────────┐  ┌───────────────┐  ┌───────────────────────┐
│ funds.json│  │ ChromaDB  │  │ LLM (Gemini)   │  │ Phase 1 corpus         │
│ (Phase 1  │  │ vector DB │  │ answer +       │  │ data/raw/ + manifest   │
│ extract_  │  │ hybrid    │  │ refusal        │  │ 50 URLs, 10 schemes   │
│ structured)│  │ search +  │  │               │  │ ICICI Prudential AMC   │
│ Fast path │  │ RRF+re-rank│  │               │  │                        │
└───────────┘  └───────────┘  └───────────────┘  └───────────────────────┘
                                        ▲
┌─────────────────────────────────────────────────────────────────────────────────┐
│  CORPUS BUILD (Phase 1 — Offline)                                                 │
│  • sources.csv → scraper.py → data/raw/*.txt + manifest.json; extract_structured    │
│    → data/funds.json. NAV: fetch_nav.py (MFapi.in) merges NAV into funds.json;     │
│    run_nav_scheduler runs fetch daily (default 7:30 PM). Phase 2: chunk → embed →  │
│    ChromaDB.                                                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase Overview

| Phase | Name | Purpose | When you provide “training” / corpus for RAG |
|-------|------|---------|---------------------------------------------|
| **P1** | Corpus & scope | sources.csv (50 URLs), scraper → data/raw + manifest; extract_structured → funds.json | **Yes — RAG corpus + structured data for fast lookup** |
| **P2** | RAG pipeline | Chunk (sentence/table-aware), embed (Gemini), ChromaDB; hybrid retrieval (vector + keyword, RRF, re-rank) + citation | **Yes — index from P1 corpus** |
| **P3** | LLM & prompts | Classifier, refusal, answer_query (Gemini); factual answer + citation | No (prompt-only) |
| **P4** | Backend API | FastAPI: /chat (query, context_fund), /health (vector DB + funds.json), /api/sources; PII check; audit log | No |
| **P5** | Frontend + integration | Tiny UI, example questions, Resources from /api/sources, disclaimer | No |

**When do you provide “training information” for the chatbot?**  
→ **Phase 1 and Phase 2.** In P1 you **collect** the training/corpus data (scraped pages). In P2 you **use** that data to build the RAG index (embeddings in ChromaDB/Pinecone). There is no separate “training” step; the model is zero-shot/few-shot with RAG retrieval. All factual knowledge comes from the indexed public pages.

---

## 3. Phase 1 — Corpus & Scope (Data Collection)

**Goal:** One AMC, multiple schemes, public URLs; scrape, store raw content, and extract structured fund data.

### 3.1 Scope (current)

- **AMC:** ICICI Prudential Asset Management Company.
- **Schemes (10):** Large Cap, MidCap, ELSS Tax Saver, Multi Asset, Smallcap, Balanced Advantage, Energy Opportunities, Multicap, US Bluechip Equity, NASDAQ 100 Index.
- **Source list:** `sources.csv` — 50 URLs (AMC scheme pages, factsheets, KIM/SID PDFs, etc.).

### 3.2 Deliverables

- **sources.csv:** url, amc, scheme_name, page_type (and optional columns).
- **Scraper:** `scraper.py` reads sources.csv, visits each URL (Playwright/requests), extracts text or PDF content, saves `data/raw/<slug>.txt` (JSON metadata + `---` + text), writes **data/manifest.json** (url → file_path, scrape_date, scheme_name, page_type, amc).
- **Structured data:** `extract_structured.py` reads data/raw and manifest, groups by scheme, extracts fields (expense_ratio, exit_load, minimum_sip, lock_in, riskometer, benchmark, statement_download), writes **data/funds.json** — used for fast lookup and as fallback context. **NAV** is then kept up to date by `fetch_nav.py` (MFapi.in) and the NAV scheduler (see §3.4).

### 3.3 Implementation outline

1. **sources.csv** — columns: url, amc, scheme_name, page_type, etc.
2. **scraper.py** — for each URL: navigate, extract main content (no nav/ads), save data/raw with metadata; output manifest.json.
3. **extract_structured.py** — from raw + manifest → funds.json (per-scheme structured fields). No PII; public pages only.

### 3.4 NAV fetch and scheduler

**Goal:** Keep NAV (Net Asset Value) in `funds.json` up to date so the bot can answer “What is the NAV of …?” from live data.

- **Config:** `nav_scheme_codes.py` — maps each `fund_name` (as in funds.json) to an AMFI scheme code (Regular Plan - Growth) and to the AMC scheme page URL. **Funds fetched for NAV (10):** ICICI Prudential Large Cap Fund, MidCap Fund, ELSS Tax Saver Fund, Multi Asset Fund, Balanced Advantage Fund, Energy Opportunities Fund, Multicap Fund, US Bluechip Equity Fund, NASDAQ 100 Index Fund, Smallcap Fund.
- **API:** MFapi.in (`https://api.mfapi.in/mf/{scheme_code}/latest`) — no auth; returns latest NAV and date.
- **Script:** `fetch_nav.py` — reads `data/funds.json`, for each fund in `NAV_SCHEME_CODES` calls the API, merges `nav: { value, date, display }` and `scheme_page_url` into the corresponding fund record, writes `funds.json` back. Run once: `python -m Phase1_Corpus_and_Scope.fetch_nav` or `./run_fetch_nav.sh` from repo root.
- **Scheduler:** `run_nav_scheduler.py` — runs the fetch once at startup, then **daily at 7:30 PM local time** (configurable: `NAV_SCHEDULE_HOUR`, `NAV_SCHEDULE_MINUTE`; default 19:30). Uses `apscheduler` (BlockingScheduler + CronTrigger). Run: `python -m Phase1_Corpus_and_Scope.run_nav_scheduler` (Ctrl+C to stop). Ensures NAV is refreshed after market hours when NAV is published.

### 3.5 Phase 1 prompt (for implementation)

```
You are implementing Phase 1: Corpus and scope for an MF FAQ assistant.

Tasks:
1. Create a source list (CSV or MD) with 15–25 public URLs for one AMC and 3–5 schemes (e.g. one large-cap, one flexi-cap, one ELSS). Include: factsheets, KIM/SID, scheme FAQs, fee/charges, riskometer/benchmark, statement/tax-doc guides from AMC and SEBI/AMFI.
2. Implement a Playwright scraper that:
   - Reads the source list and visits each URL.
   - Waits for main content to load; extracts main text (no nav/footer/ads).
   - Saves raw content (HTML or cleaned text) with metadata: url, scrape_date, page_type.
   - Uses polite delays and respects robots.txt; public pages only, no auth.
3. Output: source list file + scraped files in data/raw/ and a manifest (e.g. data/manifest.json) mapping url → file path and date.
```

---

## 4. Phase 2 — RAG Pipeline (Indexing & Retrieval)

**Goal:** Chunk scraped content, embed with the same embedding model you’ll use at query time, index in ChromaDB; hybrid retrieval (vector + keyword, RRF, re-rank) that returns relevant chunks + one source URL for citation.

**This is the phase where the “training information” is consumed:** the scraped pages from P1 (and funds.json in P4 for fast path). No model fine-tuning; knowledge is in the vector index and funds.json.

### 4.1 Design choices

- **Embeddings:** Gemini `text-embedding-004`; same model at index and query time.
- **Vector DB:** ChromaDB (persistent, local). Store: id, embedding, document text, metadata: `source_url`, `page_type`, `scrape_date`, `scheme_name`.
- **Chunking:** Sentence/paragraph boundaries (`\n\n`, `\n`, `. `, `? `, `! `, ` `); ~1800 chars, 200 overlap. Table-aware grouping so tables/lists are not split mid-row.

### 4.2 Pipeline steps

1. **Load:** Read scraped files from P1 via manifest.
2. **Chunk:** Recursive split by SEPARATORS; table heuristics keep table blocks together.
3. **Embed:** Gemini embedding API per chunk (batch where supported).
4. **Index:** Upsert to ChromaDB with metadata (source_url, page_type, scrape_date, scheme_name).
5. **Retrieve (hybrid):** Vector: top 15 candidates. Keyword: term-overlap score, top 15 ids. RRF merge → re-rank by keyword score → top k (5). Returns (chunk_texts, source_urls, chosen_citation_url, scrape_date, distances).

### 4.3 Citation rule

- **One link per answer:** Pick the **single** most relevant chunk (e.g. by score or by “fact type”: preferred page type: factsheet, KIM, SID). Return that chunk’s `source_url` in the answer.

### 4.4 Phase 2 prompt (for implementation)

```
You are implementing Phase 2: RAG pipeline for the MF FAQ assistant.

Input: Scraped content and manifest from Phase 1 (data/raw/ + manifest).

Tasks:
1. Chunking: Split each document into overlapping segments (e.g. 300–600 tokens, 50–100 overlap). Keep tables intact (e.g. one chunk per table or table + heading). Attach metadata: source_url, scrape_date, page_type, scheme_name.
2. Embeddings: Use Gemini embedding API (or the project’s chosen embedder) for each chunk. Batch requests where the API allows.
3. Vector DB: Index chunks in ChromaDB (or Pinecone). Store: id, embedding, text, source_url, page_type, scrape_date. Ensure query-time embedding uses the same model.
4. Retrieval: Given a query, embed it, run top-k (e.g. k=3–5), return chunks and their source_url. Implement a rule to choose ONE source_url per answer (e.g. highest score or first among fact-type matches).
5. Output: A retrieval function get_relevant_context(query, k=5) -> (list of chunk texts, list of source_urls, chosen_citation_url). No PII; no content from outside the indexed corpus.
```

---

## 5. Phase 3 — LLM & Prompts (Answer Generation & Refusal)

**Goal:** With retrieved context and citation URL, use Gemini to produce short, factual answers or polite refusals; never give investment advice.

### 5.1 Query classification and out-of-scope

- **Out-of-scope (checked first):** If the query contains **no** mutual-fund-related keyword (fund, scheme, sip, elss, expense, nav, benchmark, riskometer, icici, prudential, etc.), the query is treated as **out-of-scope**. The bot returns a fixed message (configured in “config.py” as “OUT_OF_SCOPE_MESSAGE”). No RAG or LLM call.
- **Advice/opinion:** Queries such as “Should I buy/sell?”, “Can I buy ELSS fund?”, “May I invest?”, “Recommend a fund?”, “Is this scheme good?” → **Refuse** with the fixed message: “We do not recommend any buy or sell. We only provide factual information. For investor education, see: [AMFI link].” (Configured in config.py as REFUSAL_MESSAGE.) The classifier uses rule-based patterns (e.g. should/can/may I buy|sell|invest, recommend, good to invest) so no RAG or LLM call.
- **Factual (in-scope):** expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, how to download statements, NAV, etc. → **Answer from context + citation** (or from fast_lookup when served from funds.json).
- **Optional:** “USE_GEMINI_POLISH_FAST_ANSWERS=1” enables a Gemini step to polish fast_lookup and all_info answers; default off.

### 5.2 System prompt (Gemini)

```
You are a facts-only FAQ assistant for mutual fund schemes. You answer only from the provided context from official AMC/SEBI/AMFI public pages.

Rules:
- Answer in at most 3 sentences. Be precise: numbers, dates, and terms exactly as in the context.
- Every answer must include exactly one source link, in the format: "Source: [URL]". Use the citation URL provided to you.
- If the context does not contain the answer, say "This information was not found in the provided sources." and still give the citation URL if any was provided, or a generic AMFI/SEBI link.
- Do not give investment advice, recommendations, or opinions. If the user asks whether to buy, sell, or what to invest in, respond only with: "We do not recommend any buy or sell. We only provide factual information. For investor education, see: [AMFI/SEBI investor education URL]."
- Do not use or request PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.
- Do not compute or compare returns; if asked about performance, direct the user to the official factsheet link.
- End with: "Last updated from sources: [date]" using the scrape date from the context.
```

### 5.3 User prompt template (per query)

```
Context from official sources (use only this to answer):

---
[Chunk 1 text]
Source URL: [url1]
---
[Chunk 2 text]
Source URL: [url2]
---
...

Citation URL to use in the answer (use this exact URL as the single source link): [chosen_citation_url]
Scrape date for "Last updated from sources": [scrape_date]

User question: {user_query}

Answer in at most 3 sentences, with the one source link and "Last updated from sources" as specified. If the question asks for advice or opinion, refuse politely and give the education link only.
```

### 5.4 Phase 3 prompt (for implementation)

```
You are implementing Phase 3: LLM and prompts for the MF FAQ assistant.

Tasks:
1. Query classifier: Implement a simple classifier (keyword/rule or a tiny Gemini call) that labels the user query as "factual" or "advice". For "advice", do not call RAG; return a fixed refusal message and AMFI/SEBI investor-education URL.
2. System prompt: Use the provided system prompt that enforces facts-only, one citation link, ≤3 sentences, no PII, no returns comparison, and "Last updated from sources".
3. User prompt: Build the user prompt from retrieved chunks, chosen citation URL, scrape date, and user query.
4. LLM: Call Gemini (2.5 Flash / 3 Flash / 3.5 Flash) with system + user prompt. Parse the reply and ensure it contains exactly one source link and the disclaimer line. If the model hallucinates a URL, replace it with the citation URL you passed in.
5. Output: A function answer_query(user_query, retrieved_chunks, citation_url, scrape_date) -> { answer_text, source_url }. Handle refusals without calling the LLM on retrieved context.
```

---

## 6. Phase 4 — Backend API (Chat Service)

**Goal:** FastAPI app: chat endpoint (with optional context_fund), health check, sources API; PII validation; structured audit log; static frontend served from same server.

### 6.1 API contract (current)

- **POST /chat** — Body: `{ "query", "context_fund" (optional) }`. Response: `{ "answer", "source_url", "refused", "context_fund" (optional) }`. PII → 400.
- **GET /health** — `{ "status": "ok"|"degraded", "gemini_configured", "vector_db_ok", "funds_json_ok" }`.
- **GET /api/sources** — Fixed resource links first (ICICI Prudential AMC, INDmoney – Mutual Funds, KIM & SID Documents), then source list from sources.csv. Used by the Resources page.
- **GET /api/funds-by-type** — Returns supported funds from funds.json grouped by type (Equity, Hybrid, Index). Each fund includes `fund_name`, `scheme_page_url`, and `factsheet_url` (PDF). The Resources page shows each fund with a scheme-page link and a "Factsheet" link.

### 6.2 Backend flow

1. **Validate:** PII check; reject 400. Generate request_id; record start time for latency.
2. **Out-of-scope:** If the query has no MF-related keyword → return fixed out-of-scope message (no source link); audit_path `out_of_scope`.
3. **Advice:** If classify_query → advice → refusal + education link; audit_path `advice_refused`.
4. **Fast paths (funds.json):** other_amc, KIM/SID, reply_unknown_fund ("do you have info about X?"), all_info, list_funds; then fast_lookup(query) or fast_lookup(context_fund + query) for follow-ups. Optional Gemini polish when `USE_GEMINI_POLISH_FAST_ANSWERS=1`.
5. **ICICI unknown fund:** If the query looks like an ICICI fund name we don't have → instant reply: *"Currently we are limited with funds. For more funds check official websites."*; audit_path `icici_unknown_fund`.
6. **RAG:** get_relevant_context(query, k=3); if index not built or no match (distance threshold) → friendly message; else build context from chunks.
7. **LLM:** answer_query with chunks, citation URL, scrape_date; enforce one source link and Last updated from sources; audit_path `rag_answer`.
8. **Respond:** Return answer, source_url, refused, context_fund. **Audit:** log_request(audit_path, request_id, latency_ms). No PII in logs.

**Multi-fund NAV:** When the user asks for NAV of multiple funds, the answer includes each fund's block with its own **Source:** URL (scheme page) so each fund has a reference.

### 6.3 Phase 4 prompt (for implementation)

```
You are implementing Phase 4: Backend API for the MF FAQ assistant.

Tasks:
1. Expose POST /chat: body { "query": "..." }, response { "answer", "source_url", "refused" }.
2. PII check: Before processing, detect and reject PAN, Aadhaar, account numbers, OTPs, emails, phone numbers. Return 400 with a message that personal information is not accepted.
3. Orchestration: (1) Classify query → if advice, return refusal + education link. (2) Else: RAG retrieval (Phase 2) → build LLM prompt (Phase 3) → call Gemini → parse answer and force citation URL and "Last updated from sources" if missing. (3) Return answer and source_url.
4. Use the retrieval and LLM functions from Phase 2 and Phase 3. No logging or storage of PII. Keep responses concise.
```

---

## 7. Phase 5 — Frontend & Integration (Tiny UI)

**Goal:** Minimal chat UI: welcome, 3 example questions, disclaimer, and display of answer + one link.

### 7.1 UI elements

- **Welcome line:** e.g. “Ask factual questions about [AMC] mutual fund schemes (expense ratio, exit load, SIP, ELSS lock-in, riskometer, benchmark, statements).”
- **3 example questions:** Clickable; e.g. “What is the expense ratio of [Scheme X]?”, “What is the ELSS lock-in period?”, “How can I download my capital gains statement?”
- **Disclaimer:** Shown on every launch; user must click “I understand” (no persistence).
- **Input:** Text box + Send (+ Stop while request in flight).
- **Output:** Answer text; below it, one “Source:” link (clickable); then “Last updated from sources: …”. For multi-fund NAV answers, each fund's block in the answer includes its own Source URL.
- **Resources page:** Loads GET /api/sources (ICICI AMC, INDmoney, KIM/SID, then sources.csv) and GET /api/funds-by-type; shows “Supported funds by type” (Equity, Hybrid, Index) with fund names and scheme page links.

### 7.2 Flow

- User clicks an example or types a question → POST /chat → show answer, source link, and date. If `refused`, show the refusal and the education link.

### 7.3 Phase 5 prompt (for implementation)

```
You are implementing Phase 5: Frontend and integration for the MF FAQ assistant.

Tasks:
1. Build a chat UI should be in Bright GOLD and RED color and give a  welcome line (scope: [AMC] schemes, factual topics), 3 example questions (expense ratio, ELSS lock-in, download statements), and a note "Facts-only. No investment advice."
2. Chat input sends the query to POST /chat; display the returned answer. Always show one "Source:" link (the source_url from the response) and "Last updated from sources" if present in the answer.
3. If the response has refused=true, show the answer as the refusal message and still show the source link (education link).
4. No collection or display of PII (no PAN, Aadhaar, account, OTP, email, phone). Do not show performance comparisons or advice.
5. Optional: demo video (≤3 min) or link to running app; README with setup steps, scope (AMC + schemes), and known limits.
```

---

## 8. Operations and quality

- **Health check:** GET /health verifies Gemini key (gemini_configured), ChromaDB reachable (vector_db_ok), and presence of Phase 1 data/funds.json (funds_json_ok). status is "ok" when vector_db_ok and funds_json_ok are true; otherwise "degraded".
- **CI:** GitHub Actions (`.github/workflows/tests.yml`) runs on push/PR: installs Phase 1–4 deps, runs test_fund_context_followup, test_holdings_and_multi_questions, test_complex_20. Set GOOGLE_API_KEY secret for full RAG tests.
- **Structured logs:** Audit log (Phase4_Backend_API/logs/audit.log): one JSON line per request with timestamp, path (audit_path), request_id, latency_ms, method, http_path. No PII or query text.

---

## 9. Summary: Where RAG "Training" Fits

- **Phase 1:** You **provide** the training/corpus data by **collecting** source URLs (sources.csv), scraping (scraper.py → data/raw + manifest), and extracting structured data (extract_structured.py → funds.json).
- **Phase 2:** You **use** that data to **build the RAG index** (chunk → embed → ChromaDB). Hybrid retrieval (vector + keyword, RRF, re-rank) pulls from this index at runtime. No separate model training.
- **Phases 3–5:** Prompts and API/UI only; no new corpus. Optional: add more URLs in P1 and re-run P2 to refresh the index.

---

## 10. Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Scraping | Playwright, requests; PDF via pypdf |
| Structured data | Phase 1 extract_structured → funds.json (fast lookup) |
| NAV | MFapi.in (no auth); fetch_nav.py merges into funds.json; run_nav_scheduler (apscheduler, daily default 19:30) |
| NAV config | Phase1 nav_scheme_codes.py: fund_name → AMFI scheme_code + scheme_page_url (10 funds) |
| Embeddings | Gemini text-embedding-004 (index + query) |
| Vector DB | ChromaDB (persistent, local) |
| LLM | Gemini (generation + refusal; optional polish for fast answers) |
| Backend | FastAPI; CORS; static frontend mount; certifi for SSL; /api/sources, /api/funds-by-type |
| Frontend | Static (Phase5_Frontend); Resources (sources + supported funds by type); disclaimer on launch |
| Operations | GitHub Actions CI (test suites on push/PR); audit log (request_id, path, latency_ms, no PII) |

---

## 11. Recent / notable changes

- **NAV scheduler:** `fetch_nav.py` pulls latest NAV from MFapi.in for the 10 schemes in `nav_scheme_codes.py` and merges `nav` + `scheme_page_url` into `funds.json`. `run_nav_scheduler.py` runs the fetch once at startup and daily at 7:30 PM (configurable). One-off run: `./run_fetch_nav.sh` or `python -m Phase1_Corpus_and_Scope.fetch_nav`.
- **Out-of-scope:** Queries with no MF-related keyword return a fixed message (no RAG); message text in `Phase3_LLM_Prompts/config.py` (`OUT_OF_SCOPE_MESSAGE`). Checked before advice refusal.
- **ICICI unknown fund:** If the user asks about an ICICI fund not in the supported list, instant reply: "Currently we are limited with funds. For more funds check official websites." (no RAG); implemented in `fast_lookup.py`, invoked from `chat.py`.
- **Multi-fund NAV:** When NAV is asked for multiple funds, the answer includes a per-fund Source URL (scheme page) in the text; the API still returns one `source_url` for compatibility.
- **Resources page:** Fixed links first (ICICI Prudential AMC, INDmoney – Mutual Funds, KIM & SID Documents) from the backend; then entries from sources.csv. **Supported funds by type:** GET `/api/funds-by-type` returns funds with `scheme_page_url` and `factsheet_url`; the Resources page shows each fund with a scheme-page link and a Factsheet (PDF) link.
- **Advice refusal:** Buy/sell/recommendation queries (e.g. "Can I buy ELSS fund?", "Should I invest?") get the strict message: "We do not recommend any buy or sell. We only provide factual information. For investor education, see: [AMFI link]." Message in `config.py` (`REFUSAL_MESSAGE`); classifier patterns include can/may/should I buy|sell|invest, recommend, etc.
- **Optional Gemini polish:** Env `USE_GEMINI_POLISH_FAST_ANSWERS=1` enables Gemini to polish fast_lookup and all_info answers; default off.
- **Frontend:** Disclaimer shown on every launch ("I understand"); Stop button while a request is in flight; Resources page uses both `/api/sources` and `/api/funds-by-type`.

---

## 12. Deliverables Checklist (from your spec)

- [ ] Working prototype (app or notebook) or ≤3-min demo video  
- [ ] Source list (CSV/MD) of 15–25 URLs  
- [ ] README: setup, scope (AMC + schemes), known limits  
- [ ] Sample Q&A file (5–10 queries with answers + links)  
- [ ] UI disclaimer: “Facts-only. No investment advice.”

This architecture gives you a phase-by-phase plan and concrete prompts for each phase; RAG “training” is done by building the corpus in Phase 1 and the index in Phase 2.
