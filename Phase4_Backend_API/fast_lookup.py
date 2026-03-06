"""
Phase 4 — Fast lookup: answer directly from funds.json by keyword (no RAG, no LLM).
Uses scraped data only. Returns immediately for queries like "expense ratio of Large Cap Fund".
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
FUNDS_JSON = _REPO_ROOT / "Phase1_Corpus_and_Scope" / "data" / "funds.json"

def _scheme_page_url_for_fund(fund_name: str) -> str:
    """Return AMC scheme page URL for NAV answers when not in funds.json."""
    try:
        from Phase1_Corpus_and_Scope.nav_scheme_codes import FUND_SCHEME_PAGE_URLS
        return FUND_SCHEME_PAGE_URLS.get(fund_name or "", "") or ""
    except Exception:
        return ""

# Field keys in funds.json -> query keywords (lowercase). Prefer longer phrases to avoid false hits (e.g. "ter" in "riskometer")
FIELD_KEYWORDS = {
    "expense_ratio": ["expense ratio", "total expense ratio"],
    "exit_load": ["exit load"],
    "minimum_sip": ["minimum sip", "min sip", "sip amount", "sip minimum", "minimum investment"],
    "lock_in": ["lock-in", "lock in", "lockin", "elss lock"],
    "nav": ["nav", "net asset value", "current price", "latest nav", "today's nav", "nav today"],
    "riskometer": ["riskometer", "risk meter", "risk level"],
    "benchmark": ["benchmark", "bench mark"],
    "statement_download": [
        "download statement",
        "download my statement",
        "download mutual fund statement",
        "download my mutual fund statement",
        "capital gains statement",
        "account statement",
        "how to download statement",
        "statement download",
    ],
    "fund_managers": ["fund manager", "fund managers", "who manages", "manager of"],
    "cagr": ["cagr", "1 year return", "3 year return", "5 year return", "since inception", "returns 1y", "returns 3y", "returns 5y"],
    "top_5_stock_holdings": ["top 5 stock holdings", "top 5 stocks", "stock holdings", "top stock holding", "stock holding"],
    "top_5_sector_holdings": ["top 5 sector holdings", "top 5 sectors", "sector holdings", "top sector holding", "sector holding"],
}

# When user enters an ICICI fund we don't have — exact message requested (instant reply, no RAG)
ICICI_UNKNOWN_FUND_MESSAGE = "Currently we are limited with funds. For more funds check official websites."

# Short names / keywords -> substring to match in fund_name (lowercase)
FUND_MATCH_KEYWORDS = [
    "balanced advantage", "elss", "tax saver", "energy", "energy opportunities", "large cap",
    "midcap", "mid cap", "multi asset", "multicap", "multi cap", "nasdaq", "smallcap",
    "small cap", "us bluechip", "bluechip",
]


def _load_funds() -> List[Dict[str, Any]]:
    if not FUNDS_JSON.exists():
        return []
    with open(FUNDS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _find_fund_for_query(query_norm: str, funds: List[Dict]) -> Optional[Dict]:
    """Return first fund whose name is in query or whose distinctive keyword matches query and name."""
    # Prefer: query contains full fund name
    for fund in funds:
        name_norm = _normalize(fund.get("fund_name", ""))
        if name_norm and len(name_norm) > 10 and name_norm in query_norm:
            return fund
    # Else: keyword in query and in fund name (e.g. "large cap" -> Large Cap Fund)
    # Treat "small cap" / "smallcap", "mid cap" / "midcap" etc. as equivalent
    for kw in FUND_MATCH_KEYWORDS:
        if kw not in query_norm:
            continue
        kw_compact = kw.replace(" ", "")
        for fund in funds:
            name_norm = _normalize(fund.get("fund_name", ""))
            if kw in name_norm or (kw_compact and kw_compact in name_norm):
                return fund
    return None


def _find_funds_from_query(query_norm: str, funds: List[Dict]) -> List[Dict[str, Any]]:
    """
    Detect multi-fund queries (e.g. "ELSS fund and Small Cap fund") and return list of matching funds.
    Splits on " and ", ", ", " & "; each segment is matched to a fund. Dedupes by fund_name.
    Returns 0, 1, or 2+ funds. Used so we can return combined data for all requested funds.
    """
    # Split on " and " / ", " / " & " (allow comma or "and" as separator)
    parts = re.split(r"\s+and\s+|\s*,\s*|\s+&\s+", query_norm)
    seen_names: set = set()
    result: List[Dict[str, Any]] = []
    for part in parts:
        segment = part.strip()
        if len(segment) < 3:
            continue
        fund = _find_fund_for_query(segment, funds)
        if fund:
            name = fund.get("fund_name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                result.append(fund)
    return result


def _which_field(query_norm: str) -> Optional[str]:
    # Prefer longest matching keyword to avoid "ter" matching inside "riskometer"
    best_field, best_len = None, 0
    for field, keywords in FIELD_KEYWORDS.items():
        for kw in keywords:
            if kw in query_norm and len(kw) > best_len:
                best_field, best_len = field, len(kw)
    return best_field


def _query_contains_keyword(query_norm: str, kw: str) -> bool:
    """True if query contains keyword; treat 'bench mark' same as 'benchmark' (space-insensitive)."""
    if kw in query_norm:
        return True
    kw_compact = kw.replace(" ", "")
    if not kw_compact:
        return False
    return kw_compact in query_norm.replace(" ", "")


def query_looks_like_followup(query: str) -> bool:
    """
    True only if the query looks like a short follow-up about a fund (e.g. "expense ratio", "benchmark").
    Unrelated queries (e.g. "Whats the weather", "Why are you hallucinating") return False so we
    treat them as new and search RAG instead of sticking to the previous fund.
    """
    if not query or len(query.strip()) > 80:
        return False
    q = _normalize(query)
    for _field, keywords in FIELD_KEYWORDS.items():
        for kw in keywords:
            if _query_contains_keyword(q, kw):
                return True
    return False

def _which_fields(query_norm: str) -> List[str]:
    """Return all fields whose keywords appear in query, in order of first keyword occurrence (any combination)."""
    # (first_index, field) for each matching field; then sort by index and dedupe by field
    order: List[Tuple[int, str]] = []
    query_compact = query_norm.replace(" ", "")
    for field, keywords in FIELD_KEYWORDS.items():
        first_idx = len(query_norm)
        for kw in keywords:
            if not _query_contains_keyword(query_norm, kw):
                continue
            # Index in original query for ordering (prefer first occurrence of compact form)
            kw_compact = kw.replace(" ", "")
            idx = query_compact.find(kw_compact) if kw_compact else query_norm.find(kw)
            if idx < 0:
                idx = query_norm.find(kw)
            if idx < first_idx:
                first_idx = idx
        if first_idx < len(query_norm):
            order.append((first_idx, field))
    order.sort(key=lambda x: x[0])
    seen = set()
    result = []
    for _, field in order:
        if field not in seen:
            seen.add(field)
            result.append(field)
    return result


def _format_value(fund: Optional[Dict], field: str) -> Optional[Tuple[str, str]]:
    """Return (display_text, source_url) or None if fund is missing."""
    if fund is None:
        return None
    url = fund.get("source_url", "")
    name = fund.get("fund_name", "")
    val = fund.get(field)
    if val is None:
        return f"{name}: {field.replace('_', ' ').title()} is not available in the indexed data.", url
    if field == "cagr" and isinstance(val, dict):
        parts = []
        for k in ("cagr_1y", "cagr_3y", "cagr_5y", "cagr_since_inception"):
            v = val.get(k)
            if v is not None:
                label = "1Y" if k == "cagr_1y" else "3Y" if k == "cagr_3y" else "5Y" if k == "cagr_5y" else "Since inception"
                parts.append(f"{label}: {v}%")
        display = "; ".join(parts) if parts else "not available"
        return f"{name}: CAGR (compounded annual growth rate) — {display}.", url
    # Top 5 stock/sector holdings: format as bullet points
    if field in ("top_5_stock_holdings", "top_5_sector_holdings") and isinstance(val, dict):
        items = val.get("value")
        if isinstance(items, list) and items:
            label = field.replace("_", " ").title()
            bullets = "\n".join(f"• {e.get('name', '')} ({e.get('pct', '')}%)" for e in items[:5] if isinstance(e, dict))
            return f"{name}: {label}:\n{bullets}", url
    if isinstance(val, dict):
        display = val.get("display") or val.get("value") or str(val)
    else:
        display = str(val)
    return f"{name}: {field.replace('_', ' ').title()} is {display}.", url


# Base examples for "What would you like to know?" — we add holdings only if the fund has them
_FUND_NAME_ONLY_BASE = (
    "NAV, expense ratio, benchmark, riskometer, lock-in, fund manager, minimum SIP"
)


def _fund_name_only_prompt(fund: Dict[str, Any]) -> str:
    """Build prompt listing only topics this fund actually has (e.g. don't promise top 5 sector holdings for NASDAQ 100 if we don't have that data)."""
    name = fund.get("fund_name", "")
    parts = [_FUND_NAME_ONLY_BASE]
    if fund.get("top_5_stock_holdings"):
        parts.append("top 5 stock holdings")
    if fund.get("top_5_sector_holdings"):
        parts.append("top 5 sector holdings")
    examples = ", ".join(parts) + "."
    return f"We have information on {name}. What would you like to know? (e.g. {examples})"


def fast_lookup(query: str) -> Optional[Dict[str, Any]]:
    """
    If query clearly asks for one or more funds' known fields, return answer from funds.json.
    Supports joint queries (e.g. "ELSS fund and Small Cap fund - NAV, SIP, expense ratio").
    If query is just a fund name we have (no field asked), return a prompt asking what they want.
    Returns None if we should fall back to RAG.
    """
    query = (query or "").strip()
    if len(query) < 5:
        return None
    query_norm = _normalize(query)
    funds = _load_funds()
    if not funds:
        return None
    fields = _which_fields(query_norm)
    # Try multi-fund first when user asks for specific fields (e.g. "list X and Y - NAV, SIP")
    multi_funds = _find_funds_from_query(query_norm, funds) if fields else []
    fund = _find_fund_for_query(query_norm, funds) if not multi_funds else None
    if not multi_funds and fund:
        multi_funds = [fund]

    # Generic statement-download questions should not be tied to a specific fund.
    # If the user didn't mention a fund name, return a generic instruction + AMC link.
    if "statement_download" in fields and not multi_funds:
        try:
            from Phase3_LLM_Prompts.config import AMC_WEBSITE_URL
            url = AMC_WEBSITE_URL
        except Exception:
            url = "https://www.icicipruamc.com"
        return {
            "answer": (
                "You can download your mutual fund statement from the official AMC website or the registrar portal. "
                "Please check the official site for the latest steps."
            ),
            "source_url": url,
            "refused": False,
            "context_fund": "",
        }

    # User gave only a fund name we have (no fields) → single-fund prompt
    if not fields and fund:
        return {
            "answer": _fund_name_only_prompt(fund),
            "source_url": fund.get("source_url", ""),
            "refused": False,
            "context_fund": fund.get("fund_name", ""),
        }
    if not fields:
        return None
    if not multi_funds:
        return None

    # Build answer for one or more funds and requested fields
    parts = []
    source_url = ""
    for i, f in enumerate(multi_funds):
        name = f.get("fund_name", "").strip()
        section = [f"——— {name} ———"]
        # Prefer scheme page for NAV; otherwise source_url from fund
        fund_url = f.get("scheme_page_url") or _scheme_page_url_for_fund(name) or f.get("source_url", "")
        if "nav" in fields:
            if fund_url and not source_url:
                source_url = fund_url
        elif not source_url:
            source_url = fund_url or f.get("source_url", "")
        for field in fields:
            formatted = _format_value(f, field)
            if formatted:
                section.append(formatted[0])
        # When multiple funds, include each fund's reference so user gets per-fund sources
        if len(multi_funds) > 1 and fund_url:
            section.append(f"Source: {fund_url}")
        if len(section) > 1:
            parts.append("\n\n".join(section))
    if not parts:
        return None
    answer_text = "\n\n".join(parts)
    return {
        "answer": answer_text,
        "source_url": source_url or (multi_funds[0].get("source_url", "") if multi_funds else ""),
        "refused": False,
        "context_fund": multi_funds[0].get("fund_name", "") if len(multi_funds) == 1 else "",
    }


# "List all the information you have on [fund]" / "all information about [fund]" / "what do you know about [fund]"
_ALL_INFO_PATTERNS = [
    re.compile(r"\b(?:list\s+)?(?:all\s+)?(?:the\s+)?information\s+(?:you\s+have\s+)?(?:on|about)\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\ball\s+(?:the\s+)?information\s+(?:you\s+have\s+)?(?:on|about)\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\beverything\s+(?:you\s+have\s+)?(?:on|about)\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(?:full|complete)\s+details\s+(?:of|on|about)\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bdetails\s+(?:of|on|about)\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(?:tell\s+me\s+)?(?:all\s+)?(?:the\s+)?details\s+(?:you\s+have\s+)?(?:on|about)\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bwhat\s+(?:do\s+you\s+)?know\s+(?:about|on)\s+(.+)$", re.IGNORECASE | re.DOTALL),
]
# Fields to include in "all information" summary (order preserved)
_ALL_INFO_FIELDS = [
    "nav", "expense_ratio", "exit_load", "minimum_sip", "lock_in", "riskometer",
    "benchmark", "fund_managers", "cagr", "statement_download",
    "top_5_stock_holdings", "top_5_sector_holdings",
]


def _format_all_info(fund: Dict[str, Any]) -> Tuple[str, str]:
    """Build a single summary string of all available fields for the fund. Returns (answer_text, source_url)."""
    # Prefer scheme page URL when we have NAV (so Source link is the fund page)
    url = fund.get("scheme_page_url") or _scheme_page_url_for_fund(fund.get("fund_name", "")) or fund.get("source_url", "")
    name = fund.get("fund_name", "").strip()
    lines = [f"{name} — summary of what we have:"]
    for field in _ALL_INFO_FIELDS:
        formatted = _format_value(fund, field)
        if formatted:
            text, _ = formatted
            # Drop repeated fund name from each line (e.g. "Fund: Expense ratio is X" -> "Expense ratio: X")
            if name and text.startswith(name + ":"):
                text = text[len(name) + 1 :].strip()
            elif name and text.startswith(name + " —"):
                text = text[len(name) + 3 :].strip()
            lines.append(f"• {text}")
    return "\n\n".join(lines), url


def all_info_for_fund_if_asked(query: str) -> Optional[Dict[str, Any]]:
    """
    If the user asks for all information / list all info / everything about a fund,
    find the fund and return a full summary from funds.json (no RAG, no Gemini).
    """
    query = (query or "").strip()
    if len(query) < 15:
        return None
    q_norm = _normalize(query)
    topic = None
    for pat in _ALL_INFO_PATTERNS:
        m = pat.search(query)
        if m:
            topic = (m.group(1) or "").strip()
            break
    if not topic or len(topic) < 2:
        return None
    topic_norm = _normalize(topic)
    # Don't match when user asks about another AMC's fund (e.g. SBI, HDFC)
    _OTHER_AMC = ("sbi ", "hdfc ", "axis ", "nippon ", "kotak ", "mirae ", "uti ", "idfc ", "dsp ", "icici prudential infrastructure", "icici transport")
    if any(topic_norm.startswith(p) or p in topic_norm for p in _OTHER_AMC):
        return None
    funds = _load_funds()
    if not funds:
        return None
    fund = _find_fund_for_query(topic_norm, funds)
    if not fund:
        return None
    answer_text, source_url = _format_all_info(fund)
    return {"answer": answer_text, "source_url": source_url, "refused": False, "context_fund": fund.get("fund_name", "")}


# Pattern: "do you have information/details about X" / "do you have details of X" / "is there info on X"
_HAVE_INFO_ABOUT_PATTERN = re.compile(
    r"\b(?:do\s+you\s+have|is\s+there|have\s+you\s+got)\s+(?:any\s+)?(?:information|info|details)\s+(?:about|of|on)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def reply_unknown_fund_if_asked(query: str) -> Optional[Dict[str, Any]]:
    """
    If the user asks "do you have information about [X]?", first check if we have
    that fund in our database. If yes, reply instantly with a friendly yes and what
    they can ask. If we don't have it, call Gemini to suggest visiting official sites.
    """
    if not query or len(query) < 10:
        return None
    match = _HAVE_INFO_ABOUT_PATTERN.search(query)
    if not match:
        return None
    topic = (match.group(1) or "").strip()
    if not topic or len(topic) < 3:
        return None
    # If user clearly asks about another AMC's fund (e.g. SBI, HDFC), don't match our ICICI funds
    topic_norm = _normalize(topic)
    _OTHER_AMC_PREFIXES = ("sbi ", "hdfc ", "axis ", "nippon ", "kotak ", "mirae ", "uti ", "idfc ", "dsp ")
    if any(topic_norm.startswith(p) or p in topic_norm for p in _OTHER_AMC_PREFIXES):
        funds = _load_funds()
        if not funds:
            return None
        try:
            from Phase3_LLM_Prompts.config import AMC_WEBSITE_URL
            url = AMC_WEBSITE_URL
        except Exception:
            url = "https://www.icicipruamc.com"
        return {
            "answer": "We don't have that scheme in our data. Please visit the official site to explore more mutual funds.",
            "source_url": url,
            "refused": False,
        }
    funds = _load_funds()
    if not funds:
        return None
    query_norm = topic_norm
    fund = _find_fund_for_query(query_norm, funds)
    try:
        url = "https://www.icicipruamc.com"
        from Phase3_LLM_Prompts.config import AMC_WEBSITE_URL
        url = AMC_WEBSITE_URL
    except Exception:
        pass
    if fund:
        name = fund.get("fund_name", "").strip() or "this scheme"
        er = fund.get("expense_ratio")
        er_display = (er.get("display") or f"{er.get('value', '')}% p.a.") if isinstance(er, dict) else ""
        extra = f" (e.g. expense ratio: {er_display})" if er_display else ""
        answer = (
            f"Yes, we have information on {name}. "
            f"You can ask me about its expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, fund manager, CAGR, top 5 stock/sector holdings, or how to download your statement.{extra}"
        )
        return {"answer": answer, "source_url": url, "refused": False, "context_fund": name}
    # We don't have this scheme — return immediately (no Gemini call) so we never timeout
    # Use the same message for ICICI unknown funds as when user types the fund name directly
    answer = ICICI_UNKNOWN_FUND_MESSAGE if ("icici" in topic_norm or "prudential" in topic_norm) else "We don't have that scheme in our data. Please visit the official site to explore more mutual funds."
    return {"answer": answer, "source_url": url, "refused": False}


# Queries about other AMCs (SBI, HDFC, etc.) — return immediately without RAG/Gemini to avoid timeout
_OTHER_AMC_NAMES = (
    "sbi", "hdfc", "axis", "nippon", "kotak", "mirae", "uti", "idfc", "dsp",
    "tata ", "l&t", "sundaram", "edelweiss", "mahindra", "quant", "parag parikh",
)


def other_amc_query_fast_reply(query: str) -> Optional[Dict[str, Any]]:
    """
    If the query is clearly about another AMC (e.g. "SBI mutual fund", "HDFC fund"),
    return a short reply immediately without calling RAG or Gemini. Avoids slow timeouts.
    """
    if not query or len(query.strip()) > 80:
        return None
    q = _normalize(query)
    if "icici" in q or "prudential" in q:
        return None
    if not any(amc in q for amc in _OTHER_AMC_NAMES):
        return None
    try:
        from Phase3_LLM_Prompts.config import AMC_WEBSITE_URL
        url = AMC_WEBSITE_URL
    except Exception:
        url = "https://www.icicipruamc.com"
    return {
        "answer": "We only have information on ICICI Prudential AMC schemes. For SBI, HDFC, or other AMCs, please visit their official websites.",
        "source_url": url,
        "refused": False,
    }


# KIM / SID — point users to ICICI official downloads page
_KIM_SID_KEYWORDS = (
    "kim", "key information memorandum", "sid", "scheme information document",
    "download kim", "download sid", "where can i get kim", "where can i get sid",
)


def kim_sid_download_reply(query: str) -> Optional[Dict[str, Any]]:
    """
    If the user asks for KIM or SID (Key Information Memorandum / Scheme Information Document),
    point them to the ICICI Prudential AMC official downloads page. No RAG/Gemini.
    """
    if not query or len(query.strip()) < 3:
        return None
    q = _normalize(query)
    if not any(kw in q for kw in _KIM_SID_KEYWORDS):
        return None
    try:
        from Phase3_LLM_Prompts.config import KIM_SID_DOWNLOADS_URL
        url = KIM_SID_DOWNLOADS_URL
    except Exception:
        url = "https://www.icicipruamc.com/media-center/downloads"
    answer = (
        "You can download KIM (Key Information Memorandum) and SID (Scheme Information Document) "
        "for ICICI Prudential schemes from the official downloads page: "
    ) + url
    return {"answer": answer, "source_url": url, "refused": False}


# When user enters an ICICI fund name we don't have (e.g. "ICICI transport and opporti fund") — instant reply, no RAG
def _query_looks_like_icici_fund_name(query_norm: str) -> bool:
    """True if query looks like a fund name (not a generic question). Avoids triggering on 'what is ICICI' etc."""
    if "fund" in query_norm or "scheme" in query_norm:
        return True
    words = query_norm.split()
    if len(words) < 2:
        return False
    question_starters = ("what", "how", "when", "who", "which", "why", "is there", "tell me", "can you")
    if any(query_norm.startswith(w) or query_norm.startswith(w + " ") for w in question_starters):
        return False
    # e.g. "icici transport and opporti" (no "fund") — still name-like if 3+ words
    return len(words) >= 3


def icici_unknown_fund_instant_reply(query: str) -> Optional[Dict[str, Any]]:
    """
    When user enters an ICICI fund name we don't have, return the limited-funds message instantly (no RAG/Gemini).
    Prevents timeout: e.g. "ICICI transport and opporti fund" → immediate reply.
    """
    if not query or len(query.strip()) < 5:
        return None
    q = _normalize(query)
    if "icici" not in q and "prudential" not in q:
        return None
    if not _query_looks_like_icici_fund_name(q):
        return None
    funds = _load_funds()
    if not funds:
        return None
    if _find_fund_for_query(q, funds) is not None:
        return None  # we have this fund; fast_lookup would have answered
    try:
        from Phase3_LLM_Prompts.config import AMC_WEBSITE_URL
        url = AMC_WEBSITE_URL
    except Exception:
        url = "https://www.icicipruamc.com"
    return {
        "answer": ICICI_UNKNOWN_FUND_MESSAGE,
        "source_url": url,
        "refused": False,
    }


# "What funds do you have?" / "List of schemes" → instant list from funds.json (no RAG/Gemini)
_LIST_FUNDS_PATTERNS = [
    r"what\s+(?:are\s+)?(?:the\s+)?(?:funds?|schemes?)",
    r"what\s+(?:funds?|schemes?)\s+(?:do\s+you\s+have|(?:does\s+)?(?:the\s+)?bot\s+have)",
    r"(?:list|name)\s+(?:of\s+)?(?:the\s+)?(?:funds?|schemes?)",
    r"list\s+all\s+funds",
    r"list\s+all\s+schemes",
    r"list\s+all\s+mutual\s+funds?",
    r"list\s+all\s+icici\s+prudential\s+(?:funds?|schemes?)",
    r"(?:funds?|schemes?)\s+available",
    r"(?:funds?|schemes?)\s+(?:that\s+)?you\s+have",
    r"(?:mutual\s+funds?)\s+(?:that\s+)?you\s+have",
    # e.g. "Which ICICI Prudential schemes do you have information on?"
    r"which\s+.*\b(?:funds?|schemes?)\b",
    r"funds?\s+(?:that\s+)?(?:your\s+)?(?:bot\s+)?(?:has\s+)?information\s+on",
    r"schemes?\s+(?:you\s+)?(?:have\s+)?(?:information\s+)?(?:on|about)",
    r"information\s+on\s+which\s+funds",
]


def list_funds_if_asked(query: str) -> Optional[Dict[str, Any]]:
    """
    If the user asks what funds/schemes the bot has information on, return the list from funds.json
    immediately (no RAG, no Gemini). Avoids timeout on this common question.
    """
    if not query or len(query) < 10:
        return None
    q = _normalize(query)
    if not any(re.search(p, q) for p in _LIST_FUNDS_PATTERNS):
        return None
    funds = _load_funds()
    if not funds:
        return None
    try:
        from Phase3_LLM_Prompts.config import AMC_WEBSITE_URL
        url = AMC_WEBSITE_URL
    except Exception:
        url = "https://www.icicipruamc.com"
    names = [f.get("fund_name", "").strip() for f in funds if f.get("fund_name")]
    if not names:
        return None
    bullet_list = "\n".join(f"• {n}" for n in names)
    answer = (
        f"The following ICICI Prudential AMC schemes ({len(names)} schemes):\n\n"
        f"{bullet_list}\n\n"
        f"You can ask about expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, fund manager, CAGR, or statement download for any of these."
    )
    return {"answer": answer, "source_url": url, "refused": False}
