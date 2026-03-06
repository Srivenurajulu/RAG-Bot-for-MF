# How to launch the MF FAQ Assistant site

Follow these steps **in order** from the **repo root** (the folder that contains `Phase1_Corpus_and_Scope`, `Phase4_Backend_API`, `Phase5_Frontend`, etc.).

---

## 1. Open the project folder in a terminal

```bash
cd "/Users/srivenurajulu/Documents/RAG Bot for MF"
```

You must be inside this folder for all commands below.

---

## 2. (One-time) Use the project virtual environment

A `.venv` folder in the project contains all dependencies. **Activate it** so you use the right Python and pip:

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

After activation, your prompt may show `(.venv)`. Then use `python` and `pip` as in the steps below.

**If you need to reinstall dependencies** (e.g. no `.venv` yet):
```bash
python3 -m venv .venv
source .venv/bin/activate   # or Windows equivalent
pip install fastapi "uvicorn[standard]" pydantic python-dotenv google-generativeai chromadb pypdf playwright
.venv/bin/playwright install chromium
```

---

## 3. (One-time) Add your API key

You should already have a **`.env`** file in the repo root with:

```
GOOGLE_API_KEY=your_actual_key_here
```

If not, create `.env` in the repo root and add that line. Get a key at: https://aistudio.google.com/apikey

---

## 4. (One-time) Build the RAG index (Phase 1 → Phase 2)

**4a. Scrape the corpus (Phase 1)** — if you haven’t already (with venv activated):

```bash
cd Phase1_Corpus_and_Scope
python scraper.py
cd ..
```

This fills `Phase1_Corpus_and_Scope/data/raw/` and creates `data/manifest.json`.

**4b. Build the vector index (Phase 2):** (from repo root, with venv activated)

```bash
python -m Phase2_RAG_Pipeline.build_index
```

Wait until it finishes. You only need to run this once (or again when you change Phase 1 data).

---

## 5. Start the backend (Phase 4)

In a **first terminal**, from the repo root (with venv activated):

```bash
cd "/Users/srivenurajulu/Documents/RAG Bot for MF"
source .venv/bin/activate
PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --reload --host 0.0.0.0 --port 8000
```

Leave this running. You should see something like:

```
Uvicorn running on http://0.0.0.0:8000
```

---

## 6. Start the frontend (Phase 5)

In a **second terminal**, from the repo root:

```bash
cd "/Users/srivenurajulu/Documents/RAG Bot for MF"
python3 -m http.server 3000
```

Leave this running. You should see:

```
Serving HTTP on 0.0.0.0 port 3000 ...
```

---

## 7. Open the site in your browser

Go to:

**http://localhost:3000/Phase5_Frontend/**

You should see the gold/red MF FAQ Assistant page. Type a question or click one of the three example questions.

---

## Quick reference

| Step | Command | Where |
|------|--------|--------|
| Repo root | `cd "/Users/srivenurajulu/Documents/RAG Bot for MF"` | Any terminal |
| One-time: scrape (Phase 1) | `cd Phase1_Corpus_and_Scope` then `python scraper.py` then `cd ..` | — |
| One-time: build index (Phase 2) | `python -m Phase2_RAG_Pipeline.build_index` | Repo root |
| Start backend | `PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --reload --host 0.0.0.0 --port 8000` | Terminal 1 (repo root) |
| Start frontend server | `python -m http.server 3000` | Terminal 2 (repo root) |
| Open site | **http://localhost:3000/Phase5_Frontend/** | Browser |

---

## If something fails

- **“No module named …”** → Run the install step (step 2) again.
- **“Set GOOGLE_API_KEY”** → Check `.env` in the repo root and that the backend was started **after** the `.env` file was saved.
- **“Phase 1 manifest not found”** → Run Phase 1 scraper first (step 4a).
- **Frontend says “Could not reach the server”** → Start the backend (step 5) and ensure it’s on port 8000.
- **Blank or 404 on frontend** → Use the exact URL: **http://localhost:3000/Phase5_Frontend/** (with the trailing slash and correct port).
