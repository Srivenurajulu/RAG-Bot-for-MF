# Phase 1 — Corpus and Scope (MF FAQ Assistant)

**AMC:** ICICI Prudential Asset Management Company  
**Distributor (reference):** INDmoney  
**Schemes:** 10 — Large Cap, MidCap, ELSS Tax Saver, Multi Asset, Smallcap, Balanced Advantage, Energy Opportunities, Multicap, US Bluechip Equity, NASDAQ 100 Index

## Contents

- **sources.csv** — Source list (50 URLs): AMC scheme pages, INDmoney pages, factsheets (PDF), KIM (PDF), SID (PDF).
- **sources.md** — Same list in markdown with a short scope note.
- **scraper.py** — Scraper: reads `sources.csv`, visits each URL (requests or Playwright), extracts text (HTML or PDF), saves to `data/raw/`, writes **data/manifest.json**.
- **extract_structured.py** — Reads `data/raw/` and manifest, groups by scheme, extracts **structured fund data** (expense_ratio, exit_load, minimum_sip, lock_in, riskometer, benchmark, statement_download), writes **data/funds.json**. RAG uses this for facts-only answers.

## Setup

```bash
cd Phase1_Corpus_and_Scope
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Run scraper

```bash
python scraper.py
```

- **Input:** `sources.csv`
- **Output:**
  - `data/raw/<slug>.txt` — Each file: JSON metadata then `---` then extracted text.
  - `data/manifest.json` — Map of URL → `{ "file_path", "scrape_date", "scheme_name", "page_type", "amc" }`.

**After scraping, extract structured fund data (for RAG):**

```bash
# From repo root
python -m Phase1_Corpus_and_Scope.extract_structured
```

- **Input:** `data/manifest.json` and `data/raw/*.txt`
- **Output:** `data/funds.json` — Array of fund objects: `fund_name`, `source_url`, `expense_ratio`, `exit_load`, `minimum_sip`, `lock_in`, `rating`, `riskometer`, `benchmark`, `statement_download`. Phase 2 indexes this so user questions are answered from these facts.

## NAV (live prices)

Latest NAV for the 10 schemes is fetched from **MFapi.in** (AMFI data) and merged into `data/funds.json`. The RAG bot answers “What is the NAV of X?” from this data.

**One-time fetch (from repo root):**
```bash
./run_fetch_nav.sh
# or
python -m Phase1_Corpus_and_Scope.fetch_nav
```

**Scheduled daily fetch (e.g. after NAV is published):**
```bash
pip install apscheduler   # or use Phase1 requirements.txt
python -m Phase1_Corpus_and_Scope.run_nav_scheduler
```
Runs fetch once at startup, then daily at 7:30 PM local time. Set `NAV_SCHEDULE_HOUR` and `NAV_SCHEDULE_MINUTE` to override.

- **Config:** `nav_scheme_codes.py` — maps `fund_name` (as in funds.json) to AMFI scheme code (Direct Plan - Growth).
- **Output:** Each fund in `funds.json` gets a `nav` field: `{ "value", "date", "display" }`.

## Behaviour

- **HTML:** Playwright loads the page, extracts body text (scripts/styles/nav/footer stripped), saves as `.txt`.
- **PDF:** Playwright fetches the PDF, `pypdf` extracts text; saved as `.txt`. Image-only PDFs will yield little or no text.
- **Delays:** 1.5 s between requests; 8 s page timeout.
- **Public only:** No auth; no PII. Uses a polite User-Agent.

## Known limits

- PDFs that are scanned or image-based will not yield usable text (would need OCR).
- Some AMC/INDmoney pages may be heavily dynamic; extraction is best-effort.
- INDmoney pages are distributor content; for RAG, prefer AMC factsheets/KIM/SID as primary sources.
