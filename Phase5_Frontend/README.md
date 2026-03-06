# Phase 5 — Frontend (MF FAQ Assistant)

Minimal chat UI in **bright gold and red**: welcome line, 3 example questions, disclaimer, and display of answer + one source link.

## Scope

- **AMC:** ICICI Prudential AMC  
- **Topics:** Expense ratio, exit load, SIP, ELSS lock-in, riskometer, benchmark, statements (factual only).

## UI

- **Welcome:** Ask factual questions about ICICI Prudential AMC schemes (expense ratio, exit load, SIP, ELSS lock-in, riskometer, benchmark, statements).
- **Disclaimer:** "Facts-only. No investment advice."
- **3 example questions:** Expense ratio (Large Cap), ELSS lock-in, download capital gains statement.
- **Input:** Text box + Send. No collection of PII (PAN, Aadhaar, account, OTP, email, phone).
- **Output:** Answer text, one "Source:" link (`source_url`), and "Last updated from sources" when present. If `refused=true`, the refusal message and education link are shown; no performance comparisons or advice.

## Setup

1. **Backend (Phase 4)** must be running, e.g.:
   ```bash
   PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --reload --port 8000
   ```

2. **API URL:** The frontend calls `http://localhost:8000` by default. To change it, edit `config.js` and set `window.MF_FAQ_API_BASE` before the app loads, or serve the page and set it in the HTML.

3. **CORS:** Phase 4 backend allows cross-origin requests so the frontend can call `/chat` from another port or origin.

## Run

**Option A — Static server (recommended):**  
From the repo root:
```bash
python -m http.server 3000
```
Then open: http://localhost:3000/Phase5_Frontend/

**Option B — Open file:**  
Opening `index.html` directly (file://) may fail to call the API due to browser security. Use a local server (Option A).

## Files

- **index.html** — Structure: header, examples, input, output.
- **styles.css** — Bright gold and red theme.
- **config.js** — `MF_FAQ_API_BASE` (default `http://localhost:8000`).
- **app.js** — POST /chat, display answer, source link, refused state, loading and error.

## Known limits

- Single backend URL; no auth.
- No PII collected or displayed; no returns comparison or advice.
- Best used with Phase 2 index built and Phase 4 server running.
