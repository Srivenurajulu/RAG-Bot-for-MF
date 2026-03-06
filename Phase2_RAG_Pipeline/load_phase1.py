"""
Phase 2 — Load scraped content and manifest from Phase 1.
Parses data/raw/*.txt (JSON metadata + --- + body text).
Also loads structured funds from data/funds.json when present (for RAG from structured facts).
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import PHASE1_MANIFEST_PATH, PHASE1_FUNDS_PATH


def parse_raw_file(file_path: Path) -> Dict[str, Any]:
    """
    Parse a Phase 1 raw .txt file: JSON block then '---' then text.
    Returns { "url", "scrape_date", "page_type", "scheme_name", "amc", "text" }.
    """
    content = file_path.read_text(encoding="utf-8", errors="replace")
    parts = content.split("\n---\n", 1)
    meta = {}
    if parts[0].strip():
        try:
            meta = json.loads(parts[0].strip())
        except json.JSONDecodeError:
            pass
    text = parts[1].strip() if len(parts) > 1 else ""
    return {
        "url": meta.get("url", ""),
        "scrape_date": meta.get("scrape_date", ""),
        "page_type": meta.get("page_type", ""),
        "scheme_name": meta.get("scheme_name", ""),
        "amc": meta.get("amc", ""),
        "text": text,
    }


def load_phase1_corpus() -> List[Dict[str, Any]]:
    """
    Load all documents from Phase 1 using manifest.
    Returns list of { "url", "scrape_date", "page_type", "scheme_name", "amc", "text" }.
    """
    if not PHASE1_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Phase 1 manifest not found: {PHASE1_MANIFEST_PATH}. Run Phase 1 scraper first."
        )
    manifest = json.loads(PHASE1_MANIFEST_PATH.read_text(encoding="utf-8"))
    # file_path in manifest is relative to Phase 1 root (e.g. data/raw/xxx.txt)
    base = PHASE1_MANIFEST_PATH.parent.parent
    docs = []
    for url, entry in manifest.items():
        rel_path = entry.get("file_path", "")
        file_path = base / rel_path
        if not file_path.exists():
            continue
        doc = parse_raw_file(file_path)
        if not doc.get("url"):
            doc["url"] = url
        if not doc.get("scrape_date"):
            doc["scrape_date"] = entry.get("scrape_date", "")
        if not doc.get("page_type"):
            doc["page_type"] = entry.get("page_type", "")
        if not doc.get("scheme_name"):
            doc["scheme_name"] = entry.get("scheme_name", "")
        docs.append(doc)
    return docs


def _fund_to_searchable_text(fund: Dict[str, Any]) -> str:
    """Convert one fund record to a single text block for embedding and retrieval."""
    parts = [f"Fund: {fund.get('fund_name', '')}"]
    if fund.get("expense_ratio"):
        er = fund["expense_ratio"]
        parts.append(f"Expense ratio: {er.get('display', er.get('value', ''))}")
    if fund.get("exit_load"):
        el = fund["exit_load"]
        parts.append(f"Exit load: {el.get('display', el.get('value', ''))}")
    if fund.get("minimum_sip"):
        ms = fund["minimum_sip"]
        parts.append(f"Minimum SIP: {ms.get('display', ms.get('value', ''))}")
    if fund.get("lock_in"):
        li = fund["lock_in"]
        parts.append(f"Lock-in: {li.get('display', li.get('value', ''))}")
    if fund.get("riskometer"):
        rm = fund["riskometer"]
        parts.append(f"Riskometer: {rm.get('display', rm.get('value', ''))}")
    if fund.get("benchmark"):
        bm = fund["benchmark"]
        parts.append(f"Benchmark: {bm.get('display', bm.get('value', ''))}")
    if fund.get("statement_download", {}).get("display"):
        parts.append(f"Statement download: {fund['statement_download']['display']}")
    if fund.get("fund_managers"):
        fm = fund["fund_managers"]
        parts.append(f"Fund manager(s): {fm.get('display', ', '.join(fm.get('value', [])))}")
    cagr = fund.get("cagr")
    if cagr and isinstance(cagr, dict):
        cparts = []
        for k, label in (("cagr_1y", "1Y"), ("cagr_3y", "3Y"), ("cagr_5y", "5Y"), ("cagr_since_inception", "Since inception")):
            if cagr.get(k) is not None:
                cparts.append(f"CAGR {label}: {cagr[k]}%")
        if cparts:
            parts.append("CAGR: " + "; ".join(cparts))
    return "\n".join(parts)


def load_funds_corpus() -> List[Dict[str, Any]]:
    """
    Load structured funds from Phase 1 data/funds.json.
    Returns list of docs: { "text", "url", "scrape_date", "page_type", "scheme_name" }
    for indexing. One doc per fund; text is searchable summary of structured fields.
    """
    if not PHASE1_FUNDS_PATH.exists():
        raise FileNotFoundError(
            f"Funds file not found: {PHASE1_FUNDS_PATH}. Run Phase 1 scraper then: python -m Phase1_Corpus_and_Scope.extract_structured"
        )
    funds = json.loads(PHASE1_FUNDS_PATH.read_text(encoding="utf-8"))
    docs = []
    for f in funds:
        docs.append({
            "text": _fund_to_searchable_text(f),
            "url": f.get("source_url", ""),
            "scrape_date": f.get("scrape_date", ""),
            "page_type": "structured_fund",
            "scheme_name": f.get("fund_name", ""),
            "amc": "ICICI Prudential AMC",
        })
    return docs


def load_phase1_corpus_prefer_funds() -> List[Dict[str, Any]]:
    """
    Prefer structured funds (funds.json) for RAG when present; otherwise fall back to raw corpus.
    """
    if PHASE1_FUNDS_PATH.exists():
        return load_funds_corpus()
    return load_phase1_corpus()
