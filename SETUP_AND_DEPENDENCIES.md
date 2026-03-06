# Setup & Dependencies — MF FAQ Assistant

This document lists the **tech stack**, **libraries**, **software**, and **dependencies** required to run the project, plus **step-by-step setup for macOS** and **Windows**.

---

## 1. Tech stack overview

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.9+ |
| **Scraping** | Playwright, `requests`; PDF via `pypdf` |
| **Structured data** | Phase 1 → `funds.json` (fast lookup) |
| **NAV** | MFapi.in (HTTP API, no auth); `apscheduler` for daily fetch |
| **Embeddings** | Google Gemini `text-embedding-004` |
| **Vector DB** | ChromaDB (persistent, local) |
| **LLM** | Google Gemini (generation, refusal, optional polish) |
| **Backend** | FastAPI, Uvicorn; CORS; static frontend mount |
| **Frontend** | Static HTML/JS (Phase5_Frontend), served by backend or `python -m http.server`; Resources page with sources and supported funds (scheme page + Factsheet link per fund) |
| **SSL (macOS)** | `certifi` for Gemini/HTTPS certificate verification |

**Behaviour (config):** Buy/sell and recommendation queries get a strict refusal: *"We do not recommend any buy or sell. We only provide factual information. For investor education, see: [AMFI link]."* (Set in `Phase3_LLM_Prompts/config.py` as `REFUSAL_MESSAGE`.) The classifier treats phrases like "can I buy", "should I invest", "recommend" as advice and returns this message without calling RAG or the LLM.

---

## 2. Software requirements

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.9 or higher | Runtime for all phases |
| **pip** | (bundled with Python) | Install Python packages |
| **venv** | (stdlib) | Virtual environment |
| **Git** | (optional) | Clone repo / version control |
| **Browser** | Any modern browser | Chat UI at http://localhost:8000 |

**External API (no install):**

- **Google AI (Gemini):** Embedding + text generation. You need a **GOOGLE_API_KEY** from https://aistudio.google.com/apikey
- **MFapi.in:** NAV data (public HTTP, no key)

**No Node.js/npm required** — the frontend is static and served by the backend or Python’s built-in HTTP server.

---

## 3. Python libraries and dependencies

All packages are installed via `pip` from the project’s `requirements.txt` files (or the combined install below).

### 3.1 By phase (source files)

| Phase | File | Main packages |
|-------|------|----------------|
| **Phase 1** | `Phase1_Corpus_and_Scope/requirements.txt` | `playwright`, `pypdf`, `requests`, `apscheduler` |
| **Phase 2** | `Phase2_RAG_Pipeline/requirements.txt` | `google-generativeai`, `chromadb` |
| **Phase 3** | `Phase3_LLM_Prompts/requirements.txt` | `google-generativeai` |
| **Phase 4** | `Phase4_Backend_API/requirements.txt` | `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv` |

### 3.2 Combined dependency list (for one-command install)

```
# Phase 1
playwright>=1.40.0
pypdf>=4.0.0
requests>=2.28.0
apscheduler>=3.10.0

# Phase 2
google-generativeai>=0.8.0
chromadb>=0.4.0

# Phase 3
google-generativeai>=0.8.0

# Phase 4
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.0.0
python-dotenv>=1.0.0

# Recommended (SSL on macOS / Gemini gRPC)
certifi
```

### 3.3 Playwright browser (Phase 1 scraping only)

After installing Python deps, install the Chromium browser for Playwright:

```bash
playwright install chromium
```

---

## 4. Setup instructions — macOS

### 4.1 Prerequisites

1. **Install Python 3.9+** (if not already installed):
   ```bash
   # Check version
   python3 --version
   ```
   If needed: install from https://www.python.org/downloads/ or via Homebrew: `brew install python@3.11`

2. **Get a Google API key**  
   Create `.env` in the **project root** with:
   ```bash
   GOOGLE_API_KEY=your_key_here
   ```
   Get a key: https://aistudio.google.com/apikey

### 4.2 One-time project setup

Run these from the **project root** (the folder that contains `Phase1_Corpus_and_Scope`, `Phase4_Backend_API`, etc.):

```bash
# 1. Go to project folder
cd "/Users/srivenurajulu/Documents/RAG Bot for MF"
# (or your actual path, e.g. cd ~/Documents/RAG\ Bot\ for\ MF)

# 2. Create virtual environment
python3 -m venv .venv

# 3. Activate it
source .venv/bin/activate

# 4. Install all dependencies (all phases + certifi for macOS SSL)
pip install -r Phase4_Backend_API/requirements.txt \
  -r Phase2_RAG_Pipeline/requirements.txt \
  -r Phase3_LLM_Prompts/requirements.txt \
  -r Phase1_Corpus_and_Scope/requirements.txt
pip install certifi

# 5. Install Playwright Chromium (needed for Phase 1 scraping)
playwright install chromium

# 6. Make run scripts executable
chmod +x run_server.sh run_backend.sh run_frontend.sh run_build_index.sh run_scrape_and_build_index.sh run_fetch_nav.sh
```

### 4.3 First-time: scrape data and build RAG index

Do this **once** (or when you want to refresh data):

```bash
# From project root, with .venv activated
./run_scrape_and_build_index.sh
```

- Phase 1: scrapes URLs from `sources.csv` (2–5 min)
- Phase 1b: builds `data/funds.json`
- Phase 2: builds ChromaDB index (uses `GOOGLE_API_KEY`)

If you see **SSL/certificate errors** during index build, run that script in **Terminal.app** (not inside Cursor) so it can use system/certifi certificates.

### 4.4 Run the app (every time)

**Recommended — single server (backend + frontend on port 8000):**

```bash
cd "/Users/srivenurajulu/Documents/RAG Bot for MF"
source .venv/bin/activate
./run_server.sh
```

Then open **http://localhost:8000/** (or http://localhost:8000/Phase5_Frontend/) in your browser.

**Optional — backend and frontend on two ports:**

- Terminal 1: `./run_backend.sh` (port 8000)
- Terminal 2: `./run_frontend.sh` (port 3000)
- Browser: http://localhost:3000/Phase5_Frontend/

### 4.5 Optional: update NAV daily

To refresh NAV in `funds.json` (e.g. after market hours):

```bash
# One-off
./run_fetch_nav.sh

# Or run scheduler (daily at 7:30 PM by default)
python -m Phase1_Corpus_and_Scope.run_nav_scheduler
```

---

## 5. Setup instructions — Windows

### 5.1 Prerequisites

1. **Install Python 3.9+**  
   Download from https://www.python.org/downloads/ and ensure **“Add Python to PATH”** is checked.

2. **Verify in Command Prompt or PowerShell:**
   ```cmd
   py --version
   ```
   or
   ```cmd
   python --version
   ```

3. **Create `.env`** in the **project root** with:
   ```
   GOOGLE_API_KEY=your_key_here
   ```
   Get a key: https://aistudio.google.com/apikey

### 5.2 One-time project setup

Run from **Command Prompt** or **PowerShell**, in the **project root**:

```cmd
REM 1. Go to project folder (adjust path to your location)
cd "C:\Users\YourName\Documents\RAG Bot for MF"

REM 2. Create virtual environment
py -m venv .venv
REM or: python -m venv .venv

REM 3. Activate it
.venv\Scripts\activate

REM 4. Install all dependencies
pip install -r Phase4_Backend_API/requirements.txt -r Phase2_RAG_Pipeline/requirements.txt -r Phase3_LLM_Prompts/requirements.txt -r Phase1_Corpus_and_Scope/requirements.txt
pip install certifi

REM 5. Install Playwright Chromium
playwright install chromium
```

**Note:** The `run_*.sh` scripts are for macOS/Linux. On Windows use the equivalent commands below instead of `./run_server.sh`.

### 5.3 First-time: scrape data and build RAG index

**Option A — Using Git Bash (if you have Git for Windows):**  
You can run:

```bash
./run_scrape_and_build_index.sh
```

**Option B — Using Command Prompt / PowerShell:**

```cmd
.venv\Scripts\activate
set PYTHONPATH=.

REM Phase 1: scrape
cd Phase1_Corpus_and_Scope
python scraper.py
cd ..

REM Phase 1b: extract structured data
python -m Phase1_Corpus_and_Scope.extract_structured

REM Phase 2: build index (set GOOGLE_API_KEY in .env or set in this session)
python -m Phase2_RAG_Pipeline.build_index
```

### 5.4 Run the app (every time)

**Single server (backend serves frontend on port 8000):**

```cmd
.venv\Scripts\activate
set PYTHONPATH=.
.venv\Scripts\uvicorn Phase4_Backend_API.app:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000/** or **http://localhost:8000/Phase5_Frontend/** in your browser.

**Two processes (backend + frontend):**

- **Terminal 1 (backend):**
  ```cmd
  .venv\Scripts\activate
  set PYTHONPATH=.
  .venv\Scripts\uvicorn Phase4_Backend_API.app:app --reload --host 0.0.0.0 --port 8000
  ```
- **Terminal 2 (frontend):**
  ```cmd
  cd "C:\Users\YourName\Documents\RAG Bot for MF"
  python -m http.server 3000
  ```
- Browser: http://localhost:3000/Phase5_Frontend/

### 5.5 Optional: update NAV

```cmd
.venv\Scripts\activate
python -m Phase1_Corpus_and_Scope.fetch_nav
```

---

## 6. Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_API_KEY` | Yes (for RAG + LLM) | Gemini API key; put in `.env` in project root |
| `USE_GEMINI_POLISH_FAST_ANSWERS` | No | Set to `1` to polish fast-lookup answers with Gemini (default: off) |
| `NAV_SCHEDULE_HOUR` | No | Hour (0–23) for NAV scheduler (default: 19) |
| `NAV_SCHEDULE_MINUTE` | No | Minute for NAV scheduler (default: 30) |

---

## 7. Quick reference

| Task | macOS / Linux | Windows (CMD/PowerShell) |
|------|----------------|---------------------------|
| Activate venv | `source .venv/bin/activate` | `.venv\Scripts\activate` |
| Install all deps | `pip install -r Phase4_Backend_API/requirements.txt -r Phase2_RAG_Pipeline/requirements.txt -r Phase3_LLM_Prompts/requirements.txt -r Phase1_Corpus_and_Scope/requirements.txt` | Same |
| Run single server | `./run_server.sh` | `set PYTHONPATH=.` then `.venv\Scripts\uvicorn Phase4_Backend_API.app:app --host 0.0.0.0 --port 8000` |
| First-time scrape + index | `./run_scrape_and_build_index.sh` | See §5.3 Option B |
| Fetch NAV once | `./run_fetch_nav.sh` | `python -m Phase1_Corpus_and_Scope.fetch_nav` |

---

## 8. Troubleshooting

| Issue | What to do |
|-------|------------|
| **“Backend not reachable”** | Use single-server mode (run backend; open http://localhost:8000). Backend serves the frontend. |
| **SSL / certificate error (macOS)** | Run `run_build_index.sh` in Terminal.app; ensure `certifi` is installed and scripts set `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`. |
| **Port 8000 in use** | Stop the process using 8000, or run backend on another port: `uvicorn ... --port 8001` and open the corresponding URL. |
| **“No module named …”** | Activate `.venv` and install all phase requirements (see §3.2 / §4.2 / §5.2). |
| **Playwright browser not found** | Run `playwright install chromium` after installing Phase 1 requirements. |
| **Index not built / no answers** | Run first-time scrape + index (see §4.3 or §5.3). |

For more detail, see **[RUN.md](RUN.md)**.
