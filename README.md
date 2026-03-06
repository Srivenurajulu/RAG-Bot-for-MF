# MF FAQ Assistant

Facts-only FAQ for ICICI Prudential mutual fund schemes. No investment advice.

- **Scope:** 10 ICICI Prudential schemes (Large Cap, MidCap, ELSS Tax Saver, Multi Asset, Smallcap, Balanced Advantage, Energy Opportunities, Multicap, US Bluechip Equity, NASDAQ 100 Index). Answers on expense ratio, exit load, SIP, NAV, benchmark, riskometer, lock-in, statements, etc.
- **Buy/sell:** We do not recommend any buy or sell; we only provide factual information. Queries like "Can I buy ELSS fund?" or "Recommend a fund?" get a fixed refusal and a link to investor education (AMFI/SEBI).
- **Resources:** The app’s Resources page lists fixed links (AMC, INDmoney, KIM & SID) and **supported funds by type** (Equity, Hybrid, Index) with a scheme-page link and a **Factsheet** (PDF) link for each fund.

---

## Quick run (after first-time setup)

**Easiest (one server, no “backend not reachable”):** From the project folder run:
```bash
./run_server.sh
```
Then open **http://localhost:8000/** in your browser. The chat UI and API run on the same server.

Other options: `./run_app.sh` (backend + frontend on two ports) or two terminals: `./run_backend.sh` then `./run_frontend.sh`.

**First time?** Put `GOOGLE_API_KEY=...` in `.env`, then run `./run_scrape_and_build_index.sh` once (see **RUN.md**).

---

**Full instructions (prerequisites, first-time setup, troubleshooting):** **[RUN.md](RUN.md)**  
**Tech stack, libraries, dependencies, and setup for Mac/Windows:** **[SETUP_AND_DEPENDENCIES.md](SETUP_AND_DEPENDENCIES.md)**
