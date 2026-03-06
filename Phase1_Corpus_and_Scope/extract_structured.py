"""
Phase 1 — Extract structured fund data from scraped corpus.
Reads data/raw/*.txt and manifest, groups by scheme_name, extracts expense_ratio,
exit_load, minimum_sip, lock_in, riskometer, benchmark; writes data/funds.json.
Used by RAG to answer from structured facts.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Paths (same as scraper)
PHASE_DIR = Path(__file__).resolve().parent
DATA_DIR = PHASE_DIR / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"
FUNDS_JSON_PATH = DATA_DIR / "funds.json"

# Default statement download (AMC/registrar)
DEFAULT_STATEMENT = {
    "available": True,
    "instructions": ["Statements can be downloaded from ICICI Prudential AMC website or registrar portal."],
    "display": "Available - Check ICICI Prudential AMC website or registrar portal",
}


def _first_group(text: str, pattern: str, flags: int = 0) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m and m.lastindex else None


def extract_expense_ratio(text: str) -> Optional[Dict[str, Any]]:
    """Prefer Direct plan TER. Patterns: 'Direct : 0.86% p. a.' or 'Total Expense Ratio' / 'TER'."""
    # Direct : X.XX% p. a.
    direct = _first_group(text, r"Direct\s*:\s*([\d.]+)\s*%\s*(?:p\.?\s*a\.?)?", re.I)
    if direct:
        try:
            v = float(direct)
            return {"value": v, "unit": "%", "display": f"{direct}% p.a."}
        except ValueError:
            pass
    # Generic X.XX% p.a. after "expense" or "TER"
    generic = _first_group(text, r"(?:Total\s+)?(?:Expense\s+Ratio|TER)[\s:]*[\d.]*\s*([\d.]+)\s*%\s*(?:p\.?\s*a\.?)?", re.I)
    if generic:
        try:
            v = float(generic)
            return {"value": v, "unit": "%", "display": f"{generic}% p.a."}
        except ValueError:
            pass
    return None


def extract_exit_load(text: str) -> Optional[Dict[str, Any]]:
    """Exit load: NIL or X% within Y year(s)."""
    # Exit Load is NIL / Exit Load: Nil (check before matching percentages)
    if re.search(r"Exit\s+[Ll]oad\s*(?:is|:)\s*Nil", text, re.I):
        return {"value": 0, "unit": "%", "period": None, "display": "NIL"}
    # NIL - If units ... (any NIL exit condition; avoid matching "30% of the units" as exit load)
    if re.search(r"Exit\s+[Ll]oad[^N]*(?:NIL|Nil)\s*[-–]", text, re.I) or re.search(r"NIL\s*-\s*If units", text, re.I):
        return {"value": 0, "unit": "%", "period": None, "display": "NIL (conditions may apply)"}
    # 1% of the applicable NAV ... within 1 year (must be clearly exit load %, not "30% of the units")
    m = re.search(r"([\d.]+)\s*%\s*of\s+the\s+applicable\s+NAV[^.]*within\s*(\d+)\s*year", text, re.I)
    if m:
        val, yr = float(m.group(1)), m.group(2)
        return {"value": val, "unit": "%", "period": f"{yr} year", "display": f"{val}% within {yr} year"}
    return None


def extract_minimum_sip(text: str) -> Optional[Dict[str, Any]]:
    """Minimum SIP: Rs. 100 or Rs 100/- or Minimum application Rs. 1,000."""
    # SIP ... Rs. 100 / Rs 100/-
    sip = _first_group(text, r"(?:SIP|Monthly\s+SIP)[^.]*?Rs\.?\s*([\d,]+)/?", re.I)
    if sip:
        v = int(sip.replace(",", ""))
        return {"value": v, "unit": "Rs", "display": f"Rs. {v}"}
    # Minimum application amount ... Rs. 1,000
    min_app = _first_group(text, r"Minimum\s+(?:application|subscription)[^.]*?Rs\.?\s*([\d,]+)/?", re.I)
    if min_app:
        v = int(min_app.replace(",", ""))
        return {"value": v, "unit": "Rs", "display": f"Rs. {v}"}
    # Daily, Weekly ... SIP: Rs. 100
    alt = _first_group(text, r"Monthly\s+SIP[^:]*:\s*Rs\.?\s*([\d,]+)", re.I)
    if alt:
        v = int(alt.replace(",", ""))
        return {"value": v, "unit": "Rs", "display": f"Rs. {v}"}
    return None


def extract_lock_in(text: str, scheme_name: str) -> Optional[Dict[str, Any]]:
    """ELSS lock-in 3 years. Only for ELSS schemes."""
    if "ELSS" not in scheme_name.upper() and "Tax Saver" not in scheme_name:
        return None
    if re.search(r"lock\s*[- ]?in\s*(?:of\s*)?3\s*year", text, re.I) or re.search(r"3\s*year\s*lock", text, re.I):
        return {"value": 3, "unit": "years", "display": "3 years (ELSS)"}
    if re.search(r"lock[- ]?in", text, re.I):
        m = re.search(r"(\d+)\s*year", text)
        if m:
            return {"value": int(m.group(1)), "unit": "years", "display": f"{m.group(1)} years"}
    return None


# SEBI riskometer levels (exact display form)
RISKOMETER_LEVELS = [
    "Very High", "High", "Moderately High", "Moderate", "Moderately Low", "Low",
]
# Normalize phrases found in source docs to one of the levels above
_RISK_NORMALIZE = {
    "very high": "Very High",
    "high": "High",
    "moderately high": "Moderately High",
    "moderate": "Moderate",
    "moderately low": "Moderately Low",
    "low": "Low",
    "low to moderate": "Moderate",
}


def extract_riskometer(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract scheme riskometer from factsheet/KIM/SID. Prefer the explicit phrase
    'The risk of the scheme is X' to avoid picking up scale labels (e.g. 'Low' from a legend).
    """
    # 1) Factsheet/KIM: "The risk of the scheme is very high" or "... is moderately high" (before Benchmark text)
    m = re.search(
        r"The\s+risk\s+of\s+the\s+scheme\s+is\s+([a-z]+(?:\s+[a-z]+)*)\s*(?=The\s+risk\s+of\s+the\s+[Bb]enchmark|\.|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        raw = m.group(1).strip().lower()
        raw = re.sub(r"\s+", " ", raw)
        normalized = _RISK_NORMALIZE.get(raw)
        if normalized:
            return {"value": normalized, "display": normalized}
        for key, value in _RISK_NORMALIZE.items():
            if key in raw or raw in key:
                return {"value": value, "display": value}

    # 2) SID: "Riskometer (As on ...)" or "Riskometer (At the time of Launch)" then value on next lines (e.g. "Very High")
    m = re.search(
        r"Riskometer\s*\([^)]+\)\s*\n(?:[^\n]*\n){0,5}?\s*(Very\s+High|Moderately\s+High|Moderately\s+Low|Low\s+to\s+Moderate|High|Moderate|Low)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if m:
        raw = m.group(1).strip().lower()
        raw = re.sub(r"\s+", " ", raw)
        normalized = _RISK_NORMALIZE.get(raw) or (raw.title() if raw in ("high", "low", "moderate") else None)
        if normalized:
            return {"value": normalized, "display": normalized}

    # 3) Standalone line with only a level (e.g. SID table: line 46 "Very High")
    for level in RISKOMETER_LEVELS:
        # Line that is only the level (possibly with whitespace), after Scheme Riskometer or Riskometer
        if re.search(r"(?:Scheme\s+)?Riskometer[\s#]*\s*\n[\s\S]*?^\s*" + re.escape(level) + r"\s*$", text, re.MULTILINE | re.IGNORECASE):
            return {"value": level, "display": level}

    # 4) Fallback: "Scheme Riskometer" or "Riskometer" section then one of the six levels on same or next line (strict)
    for level in RISKOMETER_LEVELS:
        # Require level to appear in same sentence/line as "risk of the scheme" or within 50 chars after "Scheme Riskometer"
        pat = r"(?:Scheme\s+Riskometer|Risk-o-meter)[\s#]*[.\n]{0,50}?\b" + re.escape(level) + r"\b"
        if re.search(pat, text, re.IGNORECASE | re.DOTALL):
            # Avoid matching scale legend: "Low" / "High" alone in a list like "Low\nModerate\nHigh"
            if level == "Low" and re.search(r"(?:High|Medium|Moderate)\s+Low\b", text, re.I):
                continue
            if level == "High" and re.search(r"\bHigh\s+(?:Medium|Moderate|Low)\b", text, re.I):
                continue
            return {"value": level, "display": level}
    return None


def extract_fund_managers(text: str) -> Optional[Dict[str, Any]]:
    """Extract fund manager names from factsheet/KIM. Returns { "value": ["Name1", "Name2"], "display": "Name1, Name2" }."""
    # "Fund Managers** :" or "Fund Managers :" then names on same or next lines (e.g. "Equity : Rajat Chandak")
    names = []
    m = re.search(r"Fund\s+Managers\s*\*?\s*:\s*([\s\S]{10,800})?(?:Indicative|Inception|Notes|Total Expense|CAGR|1 Year)", text, re.I)
    if m:
        block = (m.group(1) or "").strip()
        # Names often appear as "Name (Managing" or "Equity : Name" or "Name1, Name2 and Name3"
        for part in re.split(r"[\n,]", block):
            part = part.strip()
            # "Equity : Rajat Chandak (Managing" or "Rajat Chandak (Managing" or "Debt : Manish Banthia"
            name = _first_group(part, r"(?:Equity|Debt|Hybrid)\s*:\s*([A-Za-z][A-Za-z\s\.\'\-]+?)(?:\s*\(Managing|\s*\(w\.e\.f\.|$)", re.I)
            if not name:
                name = _first_group(part, r"([A-Za-z][A-Za-z\s\.\'\-]{3,40}?)(?:\s*\(Managing|\s*\(w\.e\.f\.|$)")
            if name:
                name = re.sub(r"\s+", " ", name).strip()
                if (
                    len(name) > 2
                    and name not in names
                    and "Scheme" not in name
                    and "p. a." not in name.lower()
                    and "overall" not in name.lower()
                    and "experience" not in name.lower()
                ):
                    names.append(name)
    # Fallback: "managed by X, Y and Z"
    if not names:
        m = re.search(r"(?:scheme\s+is\s+)?(?:currently\s+)?managed\s+by\s+([A-Za-z][^.]+?)(?:\.|Refer|Total)", text, re.I)
        if m:
            raw = m.group(1).strip()
            for sep in [" and ", ", "]:
                for n in raw.split(sep):
                    n = re.sub(r"\s+", " ", n).strip()
                    if 3 < len(n) < 50 and n not in names:
                        names.append(n)
    # Split "Name1 and Name2" into two
    expanded = []
    for n in names:
        if " and " in n:
            for part in n.split(" and "):
                part = part.strip()
                if len(part) > 2 and part not in expanded:
                    expanded.append(part)
        elif n not in expanded:
            expanded.append(n)
    if expanded:
        return {"value": expanded[:10], "display": ", ".join(expanded[:8])}
    return None


def extract_cagr(text: str) -> Optional[Dict[str, Any]]:
    """Extract CAGR 1Y, 3Y, 5Y, since inception from factsheet returns table (Scheme row)."""
    out = {"cagr_1y": None, "cagr_3y": None, "cagr_5y": None, "cagr_since_inception": None}
    # Find returns table: "1 Year" "3 Years" "5 Years" "Since inception" then later "Scheme" row with numbers
    table_start = re.search(r"1\s+Year\s+3\s+Years\s+5\s+Years\s+Since\s+inception", text, re.I)
    if table_start:
        block = text[table_start.start() : table_start.start() + 2500]
    else:
        idx = text.find("Scheme")
        if idx == -1:
            return None
        block = text[idx : idx + 1500]
    # Scheme row: 8 numbers (1Y, val, 3Y, val, 5Y, val, SI, val). Values can be 11221.63 or 77620.00
    line_m = re.search(
        r"(\d{1,2}\.\d{2})\s+[\d.,]+\s+(\d{1,2}\.\d{2})\s+[\d.,]+\s+(\d{1,2}\.\d{2})\s+[\d.,]+\s+(\d{1,2}\.\d{2})\s+[\d.,]+",
        block,
    )
    if line_m:
        try:
            out["cagr_1y"] = float(line_m.group(1))
            out["cagr_3y"] = float(line_m.group(2))
            out["cagr_5y"] = float(line_m.group(3))
            out["cagr_since_inception"] = float(line_m.group(4))
            return out
        except ValueError:
            pass
    # 5Y missing: "25.34 12533.86 35.21 24758.03 - - 17.02 19368.70"
    line_m2 = re.search(
        r"(\d{1,2}\.\d{2})\s+[\d.,]+\s+(\d{1,2}\.\d{2})\s+[\d.,]+\s+-\s+-\s+(\d{1,2}\.\d{2})\s+[\d.,]+",
        block,
    )
    if line_m2:
        try:
            out["cagr_1y"] = float(line_m2.group(1))
            out["cagr_3y"] = float(line_m2.group(2))
            out["cagr_5y"] = None
            out["cagr_since_inception"] = float(line_m2.group(3))
            return out
        except ValueError:
            pass
    return None


def extract_top_5_stock_holdings(text: str) -> Optional[Dict[str, Any]]:
    """Extract Top 5 Stock Holdings from factsheet: 'Top 5 Stock Holdings' followed by lines 'Name X.XX%'."""
    m = re.search(r"Top\s+5\s+Stock\s+Holdings\s*\n(.*?)(?=\n\s*Top\s+5\s+Sector\s+Holdings|\n\s*Equity\s+Shares|\n\n[A-Z]|\Z)", text, re.I | re.DOTALL)
    if not m:
        return None
    block = m.group(1).strip()
    # Each line: "Company Name Ltd. 7.61%" or "Estee Lauder Cos Inc 3.08%"
    entries = []
    for line in block.split("\n"):
        line = re.sub(r"\s+", " ", line.strip())
        # Match "Something 12.34%" at end (allow decimal)
        hit = re.match(r"^(.+?)\s+([\d.]+)\s*%\s*$", line)
        if hit:
            name, pct = hit.group(1).strip(), hit.group(2)
            if len(name) > 1 and len(name) < 80:
                entries.append({"name": name, "pct": pct})
        if len(entries) >= 5:
            break
    if not entries:
        return None
    display = "; ".join(f"{e['name']} ({e['pct']}%)" for e in entries[:5])
    return {"value": entries[:5], "display": display}


def extract_top_5_sector_holdings(text: str) -> Optional[Dict[str, Any]]:
    """Extract Top 5 Sector Holdings from factsheet: 'Top 5 Sector Holdings' followed by lines 'Sector X.XX%'."""
    m = re.search(r"Top\s+5\s+Sector\s+Holdings\s*\n(.*?)(?=\s+Equity\s+Shares|\n\s*-\s*\n|\n\n[A-Z]|\Z)", text, re.I | re.DOTALL)
    if not m:
        return None
    block = m.group(1).strip()
    entries = []
    for line in block.split("\n"):
        line = re.sub(r"\s+", " ", line.strip())
        hit = re.match(r"^(.+?)\s+([\d.]+)\s*%\s*$", line)
        if hit:
            name, pct = hit.group(1).strip(), hit.group(2)
            if len(name) > 1 and len(name) < 80:
                entries.append({"name": name, "pct": pct})
        if len(entries) >= 5:
            break
    if not entries:
        return None
    display = "; ".join(f"{e['name']} ({e['pct']}%)" for e in entries[:5])
    return {"value": entries[:5], "display": display}


def extract_benchmark(text: str) -> Optional[Dict[str, Any]]:
    """Benchmark: e.g. CRISIL Hybrid 50+50, Nifty 50 TRI, NASDAQ-100 TRI."""
    # Scheme\n...Index Name (Benchmark) - capture only the index name line
    m = re.search(r"Scheme\s*\n\s*([A-Za-z0-9][A-Za-z0-9\s+\-®]+?(?:Index|TRI)\s*)\s*\(Benchmark\)", text)
    if m:
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        if len(name) > 4 and "Scheme" not in name:
            return {"value": name, "display": name}
    # (Benchmark) immediately after index name (no leading digits/newlines)
    m = re.search(r"(?<!\d)([A-Za-z][A-Za-z0-9\s+\-®]+(?:Index|TRI)?)\s*\(Benchmark\)", text)
    if m:
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        if 3 < len(name) < 80:
            return {"value": name, "display": name}
    # "Benchmark for the scheme would be X"
    m = re.search(r"Benchmark\s+for\s+the\s+scheme\s+(?:would\s+be|is)\s+([A-Za-z0-9][^.\n]{2,60})", text, re.I)
    if m:
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        return {"value": name, "display": name}
    # "benchmarked to the ... index"
    m = re.search(r"benchmarked\s+to\s+(?:the\s+)?(?:total\s+return\s+variant\s+of\s+)?(?:the\s+)?([A-Za-z0-9][^.\n]{2,60})", text, re.I)
    if m:
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        return {"value": name, "display": name}
    return None


def parse_raw_file(file_path: Path) -> Dict[str, Any]:
    """Parse Phase 1 raw .txt: JSON block then --- then text."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    parts = content.split("\n---\n", 1)
    meta = {}
    if parts[0].strip():
        try:
            meta = json.loads(parts[0].strip())
        except json.JSONDecodeError:
            pass
    text = parts[1].strip() if len(parts) > 1 else ""
    return {"url": meta.get("url", ""), "scrape_date": meta.get("scrape_date", ""), "page_type": meta.get("page_type", ""), "scheme_name": meta.get("scheme_name", ""), "amc": meta.get("amc", ""), "text": text}


def merge_fund_record(
    scheme_name: str,
    docs: List[Dict[str, Any]],
    source_url: str,
    scrape_date: str = "",
) -> Dict[str, Any]:
    """Build one fund record from multiple docs. Prefer factsheet > kim > sid > distributor."""
    record = {
        "fund_name": scheme_name,
        "source_url": source_url,
        "scrape_date": scrape_date,
        "expense_ratio": None,
        "exit_load": None,
        "minimum_sip": None,
        "lock_in": None,
        "rating": None,
        "riskometer": None,
        "benchmark": None,
        "statement_download": DEFAULT_STATEMENT,
        "fund_managers": None,
        "cagr": None,
        "top_5_stock_holdings": None,
        "top_5_sector_holdings": None,
    }
    # Order by preference (factsheet has CAGR and fund managers)
    ordered = sorted(docs, key=lambda d: {"factsheet": 0, "kim": 1, "sid": 2}.get((d.get("page_type") or "").lower(), 3))
    for doc in ordered:
        text = (doc.get("text") or "")[:80_000]
        if not record["expense_ratio"]:
            record["expense_ratio"] = extract_expense_ratio(text)
        if not record["exit_load"]:
            record["exit_load"] = extract_exit_load(text)
        if not record["minimum_sip"]:
            record["minimum_sip"] = extract_minimum_sip(text)
        if not record["lock_in"]:
            record["lock_in"] = extract_lock_in(text, scheme_name)
        if not record["riskometer"]:
            record["riskometer"] = extract_riskometer(text)
        if not record["benchmark"]:
            record["benchmark"] = extract_benchmark(text)
        if not record["fund_managers"]:
            record["fund_managers"] = extract_fund_managers(text)
        if not record["cagr"]:
            record["cagr"] = extract_cagr(text)
        if not record["top_5_stock_holdings"]:
            record["top_5_stock_holdings"] = extract_top_5_stock_holdings(text)
        if not record["top_5_sector_holdings"]:
            record["top_5_sector_holdings"] = extract_top_5_sector_holdings(text)
    return record


def build_funds_json() -> List[Dict[str, Any]]:
    """Load manifest and raw files, group by scheme_name, extract structured data, write funds.json. Returns list of fund records."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}. Run scraper first.")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    base = DATA_DIR  # data/
    raw_dir = base / "raw"
    # Group by scheme_name (normalize: strip)
    by_scheme: Dict[str, List[Dict]] = {}
    for url, entry in manifest.items():
        rel_path = entry.get("file_path", "")
        # file_path in manifest is relative to Phase1 root (e.g. data/raw/xxx.txt)
        file_path = PHASE_DIR / rel_path
        if not file_path.exists():
            file_path = raw_dir / Path(rel_path).name
        if not file_path.exists():
            continue
        doc = parse_raw_file(file_path)
        if not doc.get("scheme_name"):
            doc["scheme_name"] = entry.get("scheme_name", "")
        if not doc.get("url"):
            doc["url"] = url
        key = (doc.get("scheme_name") or "").strip()
        if not key:
            continue
        by_scheme.setdefault(key, []).append(doc)
    funds = []
    for scheme_name, docs in sorted(by_scheme.items()):
        # Prefer factsheet URL as source_url
        factsheet = next((d for d in docs if (d.get("page_type") or "").lower() == "factsheet"), None)
        kim = next((d for d in docs if (d.get("page_type") or "").lower() == "kim"), None)
        sid = next((d for d in docs if (d.get("page_type") or "").lower() == "sid"), None)
        best = factsheet or kim or sid or docs[0]
        source_url = best.get("url", "")
        scrape_date = best.get("scrape_date", "")
        rec = merge_fund_record(scheme_name, docs, source_url, scrape_date)
        funds.append(rec)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FUNDS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(funds, f, ensure_ascii=False, indent=2)
    return funds


if __name__ == "__main__":
    funds = build_funds_json()
    print(f"Written {FUNDS_JSON_PATH} with {len(funds)} funds.")
