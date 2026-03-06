"""
Phase 4 — Backend API: POST /chat with PII check and orchestration.
Response: { "answer", "source_url", "refused" }. No logging or storage of PII.
"""
import os
import time
import uuid
from pathlib import Path
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
except ImportError:
    pass
# Use certifi's CA bundle for SSL (fixes CERTIFICATE_VERIFY_FAILED on macOS)
try:
    import ssl
    import certifi
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
except Exception:
    pass
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .pii_check import contains_pii
from .chat import handle_chat
from .audit_log import log_request

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = _REPO_ROOT / "Phase5_Frontend"

app = FastAPI(
    title="MF FAQ Assistant API",
    description="Facts-only FAQ for mutual fund schemes. No investment advice.",
    version="1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    context_fund: Optional[str] = Field(None, max_length=500, description="Fund from previous message for follow-up (e.g. 'Expense ratio')")


class ChatResponse(BaseModel):
    answer: str
    source_url: str
    refused: bool
    context_fund: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Answer a factual question about mutual fund schemes, or refuse with education link for advice queries.
    Personal information (PAN, Aadhaar, account numbers, OTP, email, phone) is not accepted.
    Send context_fund when the user is asking a follow-up about the same fund (e.g. "Expense ratio" after "ICICI ELSS").
    """
    query = (request.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")

    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    # PII check — reject before any processing
    has_pii, reason = contains_pii(query)
    if has_pii:
        log_request("pii_rejected", request_id=request_id, method="POST", http_path="/chat")
        raise HTTPException(
            status_code=400,
            detail="Personal information is not accepted. Please do not send PAN, Aadhaar, account numbers, OTPs, email, phone, folio or CIN.",
        )

    try:
        result = handle_chat(query, context_fund=request.context_fund)
        audit_path = result.pop("audit_path", "unknown")
        latency_ms = (time.perf_counter() - start_time) * 1000
        log_request(audit_path, request_id=request_id, latency_ms=latency_ms, method="POST", http_path="/chat")
        return ChatResponse(
            answer=result["answer"],
            source_url=result["source_url"],
            refused=result["refused"],
            context_fund=result.get("context_fund"),
        )
    except Exception:
        latency_ms = (time.perf_counter() - start_time) * 1000
        log_request("error", request_id=request_id, latency_ms=latency_ms, method="POST", http_path="/chat")
        return ChatResponse(
            answer="Something went wrong while answering. Please try again or check fund details on the AMC website.",
            source_url="https://www.icicipruamc.com",
            refused=False,
        )


@app.get("/health")
def health():
    """Health check: Gemini key, vector DB reachable, funds.json present. No PII."""
    gemini_configured = bool(os.environ.get("GOOGLE_API_KEY", "").strip())
    funds_json = _REPO_ROOT / "Phase1_Corpus_and_Scope" / "data" / "funds.json"
    funds_json_ok = funds_json.is_file()
    vector_db_ok = False
    try:
        from Phase2_RAG_Pipeline.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
        import chromadb
        from chromadb.config import Settings
        client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR), settings=Settings(anonymized_telemetry=False))
        coll = client.get_collection(name=CHROMA_COLLECTION_NAME)
        _ = coll.count()
        vector_db_ok = True
    except Exception:
        pass
    status = "ok" if (funds_json_ok and vector_db_ok) else "degraded"
    return {
        "status": status,
        "gemini_configured": gemini_configured,
        "vector_db_ok": vector_db_ok,
        "funds_json_ok": funds_json_ok,
    }


_SOURCES_CSV = _REPO_ROOT / "Phase1_Corpus_and_Scope" / "sources.csv"
_FUNDS_JSON = _REPO_ROOT / "Phase1_Corpus_and_Scope" / "data" / "funds.json"

# URL path segment -> display label for fund type (Resources page)
_FUND_TYPE_LABELS = {
    "equity-funds": "Equity",
    "hybrid-funds": "Hybrid",
    "index-funds": "Index",
}
_FUND_TYPE_ORDER = ("Equity", "Hybrid", "Index")

# Fixed resource links shown first on the Resources page (ICICI AMC, INDmoney, KIM/SID)
_RESOURCE_LINKS = [
    {
        "url": "https://www.icicipruamc.com",
        "scheme_name": "ICICI Prudential AMC",
        "page_type": "AMC",
        "amc": "Official AMC website",
    },
    {
        "url": "https://www.indmoney.com/mutual-funds",
        "scheme_name": "INDmoney – Mutual Funds",
        "page_type": "Distributor",
        "amc": "Fund discovery & distributor",
    },
    {
        "url": "https://www.icicipruamc.com/media-center/downloads",
        "scheme_name": "KIM & SID Documents",
        "page_type": "Downloads",
        "amc": "Key Information Memorandum & Scheme Information Document",
    },
]


@app.get("/api/sources")
def get_sources():
    """Return list of source links for Resources page: ICICI AMC, INDmoney, KIM/SID first, then sources.csv."""
    import csv
    out = list(_RESOURCE_LINKS)
    if _SOURCES_CSV.exists():
        with open(_SOURCES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = (row.get("url") or "").strip()
                if not url:
                    continue
                scheme_name = (row.get("scheme_name") or "").strip()
                page_type = (row.get("page_type") or "").strip()
                amc = (row.get("amc") or "").strip()
                # Skip if duplicate of a resource link we already have
                if url in {x["url"] for x in _RESOURCE_LINKS}:
                    continue
                out.append({
                    "url": url,
                    "scheme_name": scheme_name or url,
                    "page_type": page_type,
                    "amc": amc,
                })
    return out


@app.get("/api/funds-by-type")
def get_funds_by_type():
    """Return supported funds grouped by fund type (Equity, Hybrid, Index) for Resources page."""
    import json
    if not _FUNDS_JSON.exists():
        return {"by_type": {}}
    with open(_FUNDS_JSON, "r", encoding="utf-8") as f:
        funds = json.load(f)
    by_type = {}
    for fund in funds:
        name = (fund.get("fund_name") or "").strip()
        url = (fund.get("scheme_page_url") or fund.get("source_url") or "").strip()
        if not name:
            continue
        # Derive type from scheme_page_url path (e.g. .../equity-funds/... -> Equity)
        label = "Equity"  # default
        if isinstance(url, str) and "/mutual-fund/" in url:
            for segment, display in _FUND_TYPE_LABELS.items():
                if "/" + segment + "/" in url:
                    label = display
                    break
        if label not in by_type:
            by_type[label] = []
        factsheet_url = (fund.get("source_url") or "").strip() or None
        by_type[label].append({
            "fund_name": name,
            "scheme_page_url": url or None,
            "factsheet_url": factsheet_url,
        })
    # Order keys and sort funds by name within each type
    out = {}
    for label in _FUND_TYPE_ORDER:
        if label in by_type:
            out[label] = sorted(by_type[label], key=lambda x: (x["fund_name"].lower(),))
    for label, items in by_type.items():
        if label not in out:
            out[label] = sorted(items, key=lambda x: (x["fund_name"].lower(),))
    return {"by_type": out}


# Serve frontend from same server so one command runs everything (no "backend not reachable")
if _FRONTEND_DIR.exists():
    app.mount("/Phase5_Frontend", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")

    @app.get("/")
    def root():
        return RedirectResponse(url="/Phase5_Frontend/", status_code=302)
