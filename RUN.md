# How to run the MF FAQ Assistant

**Project folder:**  
`/Users/srivenurajulu/Documents/RAG Bot for MF`  
Run all commands from this folder unless noted.

**If the chat shows "Cannot reach the backend":** Use the single-server option: run `./run_server.sh` from the project folder, then open **http://localhost:8000/** in your browser. One process serves both the UI and the API, so the error cannot occur.

---

## 1. Prerequisites (one-time)

- **Python 3.9+** with `venv`
- **API key:** Create `.env` in the project folder with:
  ```bash
  GOOGLE_API_KEY=your_key_here
  ```
  Get a key: https://aistudio.google.com/apikey

- **Venv and dependencies** (if not already done):
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate   # Windows: .venv\Scripts\activate
  pip install -r Phase4_Backend_API/requirements.txt -r Phase2_RAG_Pipeline/requirements.txt -r Phase3_LLM_Prompts/requirements.txt -r Phase1_Corpus_and_Scope/requirements.txt
  ```

- **Scripts executable** (if needed):
  ```bash
  chmod +x run_backend.sh run_frontend.sh run_build_index.sh run_scrape_and_build_index.sh
  ```

---

## 2. First-time: get data and build the index

Do this **once** (or when you want to refresh data). Use your **system terminal** (e.g. Terminal.app), not inside Cursor.

**Option A — Full run (scrape + extract + build index):**
```bash
./run_scrape_and_build_index.sh
```
- Phase 1: scrapes URLs from `Phase1_Corpus_and_Scope/sources.csv` (2–5 min)
- Phase 1b: builds `data/funds.json` from scraped data
- Phase 2: builds RAG index with Gemini (a few min)

**Option B — You already have scraped data** (e.g. `Phase1_Corpus_and_Scope/data/manifest.json` exists):
```bash
python -m Phase1_Corpus_and_Scope.extract_structured   # optional: refresh funds.json
./run_build_index.sh
```

**If index build fails with SSL / certificate errors:** run `./run_build_index.sh` in **Terminal.app** (macOS) so it can use system certificates.

**Important:** Until the index is built, the chatbot will say "information not found" and will not use your scraped data. The "Source" link will point to the AMC website (https://www.icicipruamc.com) only when there is no citation from your corpus — we do not use any link you didn’t add (e.g. AMFI) for factual answers. After a successful index build, answers come from your corpus.

**Check setup:** `python scripts/verify_rag_setup.py` — confirms funds.json and Chroma index; tells you to run `./run_build_index.sh` if the index is missing or empty.

---

## 3. Every time: start the app

**Option A — Single server (recommended; no “backend not reachable”)**  
From the project folder run:
```bash
./run_server.sh
```
One process serves both the chat UI and the API on port 8000. Open **http://localhost:8000/** in your browser. No separate frontend server needed.

**Option B — Backend + frontend (two ports)**  
Run `./run_app.sh` — backend on 8000, frontend on 3000. Open http://localhost:3000/Phase5_Frontend/

**Option C — Two terminals**  
If you prefer to run them separately:
- **Terminal 1:** `./run_backend.sh` — wait until you see "Uvicorn running…"
- **Terminal 2:** `./run_frontend.sh`
- **Browser:** http://localhost:3000/Phase5_Frontend/

If the backend is not running, the chatbot will show "Backend not reachable" until you start it.

---

## 4. Speed: fast lookup from scraped data

For questions that clearly ask for one fund’s one fact (expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, statement), the bot answers **directly from funds.json** (no RAG, no Gemini call). That makes those answers fast. Other questions use RAG + LLM when the index is built.

## 5. Play around

- Type questions in the chat, e.g.:
  - *What is the expense ratio of ICICI Prudential Large Cap Fund?*
  - *Exit load for Balanced Advantage Fund?*
  - *Minimum SIP for ELSS Tax Saver Fund?*
  - *What is the lock-in for ELSS?*
  - *Benchmark for NASDAQ 100 Index Fund?*
  - *How to download statement?*
- **Advice-style** questions (e.g. *Should I invest in X?*) get a polite refusal and a link to AMFI/SEBI.
- **PII** (PAN, Aadhaar, phone, etc.) in the query is rejected with 400.

**Test from command line:**
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the expense ratio of ICICI Prudential Large Cap Fund?"}' | python3 -m json.tool
```

---

## 6. Troubleshooting

| Issue | What to do |
|-------|------------|
| **“Failed to fetch” / “Backend not reachable”** | **Do this:** Open a terminal, go to the project folder (`cd "RAG Bot for MF"` or your full path), then run `./run_app.sh`. Keep that terminal open. Open or refresh http://localhost:3000/Phase5_Frontend/ in the browser. If port 8000 was in use, run `./stop_backend.sh` then `./run_app.sh` again. |
| **“Index not built” / no real answers** | Run `./run_build_index.sh` (and Phase 1 scraper first if you have no `data/`). |
| **Port 8000 already in use** | Run `./stop_backend.sh` then `./run_backend.sh` again. |
| **SSL / certificate error when building index** | Run `./run_build_index.sh` in Terminal.app (not Cursor). |
| **Script permission denied** | `chmod +x run_backend.sh run_frontend.sh run_build_index.sh run_scrape_and_build_index.sh` |
| **No module named …** | Activate venv and install deps (see Prerequisites). |

---

## 7. Optional: run tests

- **Offline (no server):**  
  `python tests/test_rag_offline.py`
- **API (backend running):**  
  `python tests/test_rag_chat.py` (fast) or `python tests/test_rag_chat.py --slow` (full).  
  See `tests/README.md` for details.
