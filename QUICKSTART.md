# Quick start — MF FAQ Assistant

## First time only

1. **API key**  
   Open the `.env` file in this folder and set your key:
   ```bash
   GOOGLE_API_KEY=paste_your_key_here
   ```
   Get a key: https://aistudio.google.com/apikey

2. **Get real search results (one command)** — run once from the project folder in **your own terminal** (e.g. Terminal.app, not inside Cursor’s run):
   ```bash
   ./run_scrape_and_build_index.sh
   ```
   This runs Phase 1 (scrape data, 2–5 min) then Phase 2 (build RAG index, a few min). Uses your `.env` API key for Phase 2.

   **If you already have Phase 1 data** (e.g. `Phase1_Corpus_and_Scope/data/manifest.json` exists), you can skip scraping and only build the index:
   ```bash
   ./run_scrape_and_build_index.sh --skip-scrape
   ```
   Or run Phase 1 and Phase 2 separately:
   ```bash
   cd Phase1_Corpus_and_Scope && ../.venv/bin/python scraper.py && cd ..
   ./run_build_index.sh
   ```
   **Note:** If the index build fails with `CERTIFICATE_VERIFY_FAILED` (common on macOS), run `./run_build_index.sh` in your system terminal (e.g. Terminal.app) so SSL can use your system certificates.

---

## Every time you want to use the site

**Terminal 1 — start backend**
```bash
./run_backend.sh
```
Leave this open. Wait until you see “Uvicorn running on …”.

**Terminal 2 — start frontend**
```bash
./run_frontend.sh
```
Leave this open.

**Browser**  
Open: **http://localhost:3000/Phase5_Frontend/**

---

## If scripts don’t run

Make them executable once:
```bash
chmod +x run_backend.sh run_frontend.sh run_build_index.sh run_scrape_and_build_index.sh
```

Run everything from the project folder:  
`/Users/srivenurajulu/Documents/RAG Bot for MF`
