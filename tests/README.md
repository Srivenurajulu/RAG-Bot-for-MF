# Tests for MF FAQ RAG Bot

## Offline tests (no server, no API key)

Run from repo root:

```bash
python tests/test_rag_offline.py
```

- Classifier: factual vs advice queries
- Refusal response (AMFI/SEBI URL)
- If ChromaDB index exists and `GOOGLE_API_KEY` is set: retrieval returns chunks

## API tests (backend must be running)

1. Start backend: `./run_backend.sh`
2. From repo root:

```bash
# Fast only (health + PII rejection) — ~10–20 s
python tests/test_rag_chat.py

# Full RAG tests (factual + advice) — 1–2 min (calls Gemini)
python tests/test_rag_chat.py --slow
```

- **Health**: `GET /health` → 200, `status: ok`
- **PII**: query with PAN → 400
- **Factual**: expense ratio, exit load, SIP, ELSS, benchmark, statement → non-empty answer, `refused: false`
- **Advice**: "Should I invest..." → `refused: true`

## 20 test cases (in-process, no server)

```bash
.venv/bin/python3 tests/test_rag_20.py
```

Covers: fast lookup (expense ratio, exit load, SIP, lock-in, riskometer, benchmark, statement), advice refusal, and source URL from scraped data. All 20 must pass.

## 20 complex test cases (in-process, no server)

```bash
.venv/bin/python3 tests/test_complex_20.py
```

Covers: empty/whitespace (refused), advice refusal, fast lookup for multiple funds/fields, "do you have info about" (known + unknown fund), list funds, "list all information on [fund]", fund manager, CAGR, statement download, response shape, and that answer body does not contain "Source: https" or "Last updated from sources". All 20 must pass.

## 50 additional complex test cases (in-process, no server)

```bash
.venv/bin/python3 tests/test_complex_50.py
.venv/bin/python3 tests/test_complex_50.py --show-answers   # print each Q&A
.venv/bin/python3 tests/test_complex_50.py --write-qa      # write tests/COMPLEX_50_QA.md
```

50 new cases (no overlap with test_complex_20): exit load, min SIP, lock-in, riskometer, benchmark, fund manager, CAGR, “is there info”, “have info” (known/unknown), list/which schemes, “everything on”, full/complete details, advice refusal (invest, good to buy, compare, help choose, which better, recommend, worth investing), other-AMC (HDFC/SBI) → out-of-DB, statement download, “what do you know about”. All 50 must pass. Questions and bot answers are in **tests/COMPLEX_50_QA.md** (generate with `--write-qa`).

## PII (stronger) tests (in-process, no server)

```bash
.venv/bin/python3 tests/test_pii_strong.py
```

Covers: PAN, Aadhaar, long account numbers, "my folio number", "folio 12345678", "account number 987654321", CIN, email, phone; and ensures normal queries (expense ratio, statement download, list of funds) are not rejected.

## Manual one-query check

```bash
# From repo root (backend running)
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the expense ratio of ICICI Prudential Large Cap Fund?"}' | python -m json.tool
```

Expect: `{ "answer": "...", "source_url": "...", "refused": false }`. Answer should mention expense ratio (e.g. 0.86% or "index not built" if index missing).
