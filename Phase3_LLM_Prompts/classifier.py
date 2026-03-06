"""
Phase 3 — Query classifier: label as "factual", "advice", or "out_of_scope".
For "advice", return fixed refusal + education URL.
For "out_of_scope", return message that we only answer MF-related questions.
"""
import re
from pathlib import Path
from typing import List, Literal, Tuple

from .config import REFUSAL_MESSAGE, DEFAULT_EDUCATION_URL, OUT_OF_SCOPE_MESSAGE, AMC_WEBSITE_URL

_PHASE_DIR = Path(__file__).resolve().parent
_OUT_OF_SCOPE_PHRASES_FILE = _PHASE_DIR / "out_of_scope_phrases.txt"

# Phrases that indicate advice/opinion requests (should be refused)
ADVICE_PATTERNS = [
    r"\bshould\s+i\s+(buy|sell|invest)\b",
    r"\bshould\s+we\s+(buy|sell|invest)\b",
    r"\bcan\s+i\s+(buy|sell|invest)\b",
    r"\bcan\s+we\s+(buy|sell|invest)\b",
    r"\bmay\s+i\s+(buy|sell|invest)\b",
    r"\bis\s+it\s+(ok|safe|good)\s+to\s+(buy|sell|invest)\b",
    r"\b(is|are)\s+(this|these)\s+(good|bad|better|best)\b",
    r"\bwhat\s+should\s+i\s+invest\b",
    r"\bwhich\s+(scheme|fund)\s+to\s+(buy|choose|invest)\b",
    r"\brecommend\b",
    r"\badvice\s+(on|for)\s+investing\b",
    r"\bgood\s+(to\s+)?(buy|invest)\b",
    r"\bworth\s+investing\b",
    r"\bwill\s+(it|this)\s+(go\s+up|perform)\b",
    r"\bcompare\s+(returns|performance)\b",
    r"\bwhich\s+is\s+better\b",
    r"\bhelp\s+me\s+(choose|decide)\b",
]
ADVICE_REGEX = re.compile("|".join(f"({p})" for p in ADVICE_PATTERNS), re.IGNORECASE)

# Terms that indicate the query is about mutual funds / schemes (if present, not out-of-scope)
# Note: "index" omitted so "UV index", "air quality index" stay out-of-scope; "index fund" still in-scope via "fund"
MF_KEYWORDS = {
    "fund", "funds", "scheme", "schemes", "sip", "elss", "expense", "nav", "amc", "mutual",
    "ratio", "benchmark", "riskometer", "lock-in", "folio", "statement", "load", "invest",
    "large cap", "midcap", "smallcap", "tax saver", "balanced", "multicap",
    "icici", "prudential", "amfi", "sebi", "factsheet", "kim", "sid", "returns", "aum",
}

# Patterns for clearly unrelated topics (currency, weather, sports, etc.)
UNRELATED_PATTERNS = [
    r"\b(us\s+)?dollar\s*(price|rate|value)?\b",
    r"\bcurrency\s*(rate|price|exchange)\b",
    r"\bweather\b",
    r"\bcricket\b",
    r"\bfootball\b",
    r"\brecipe\b",
    r"\bstock\s+price\b",
    r"\bgold\s+price\b",
    r"\bpetrol\s+(price|rate)\b",
    r"\belection\s+(result|date)\b",
    r"\bwho\s+won\b",
    r"\bcurrent\s+time\b",
    r"\btoday\s*[\'']?s\s+news\b",
]
UNRELATED_REGEX = re.compile("|".join(f"({p})" for p in UNRELATED_PATTERNS), re.IGNORECASE)


def _load_out_of_scope_phrases() -> List[str]:
    """Load trigger phrases from out_of_scope_phrases.txt (one per line, skip # and empty)."""
    if not _OUT_OF_SCOPE_PHRASES_FILE.exists():
        return []
    phrases = []
    with open(_OUT_OF_SCOPE_PHRASES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                phrases.append(line.lower())
    return phrases


# Cached list of out-of-scope trigger phrases (lazy load)
_out_of_scope_phrases: List[str] = []


def _get_out_of_scope_phrases() -> List[str]:
    global _out_of_scope_phrases
    if not _out_of_scope_phrases and _OUT_OF_SCOPE_PHRASES_FILE.exists():
        _out_of_scope_phrases = _load_out_of_scope_phrases()
    return _out_of_scope_phrases


def _has_mf_keyword(query: str) -> bool:
    """True if query contains any term that suggests mutual-fund-related question (as whole word)."""
    if not query:
        return False
    q = query.lower().strip()
    for kw in MF_KEYWORDS:
        # Word boundary so "outlook" does not match "load", "index fund" still matches "fund"
        if re.search(r"\b" + re.escape(kw) + r"\b", q):
            return True
    return False


def is_out_of_scope(query: str) -> bool:
    """
    True if the query is not clearly about mutual funds → show "only trained for certain mutual funds" message.
    In-scope only when the query contains at least one MF-related keyword (fund, scheme, sip, expense, nav,
    icici, prudential, benchmark, riskometer, etc.). Any other query is treated as out-of-scope so that
    general questions (passport, weather, recipe, or any unseen topic) get the same polite refusal.
    """
    if not (query or "").strip():
        return False
    q = (query or "").strip().lower()
    if _has_mf_keyword(q):
        return False
    # No MF keyword → treat as out-of-scope (general query)
    return True


def classify_query(query: str) -> Literal["factual", "advice"]:
    """
    Rule-based classifier: "advice" if query matches advice-seeking patterns.
    Otherwise "factual".
    """
    if not (query or "").strip():
        return "factual"
    return "advice" if ADVICE_REGEX.search(query) else "factual"


def get_refusal_response() -> Tuple[str, str]:
    """
    Return (answer_text, source_url) for advice queries.
    Do not call RAG or LLM; use fixed message + education URL.
    """
    answer_text = REFUSAL_MESSAGE + DEFAULT_EDUCATION_URL
    source_url = DEFAULT_EDUCATION_URL
    return (answer_text, source_url)


def get_out_of_scope_response() -> Tuple[str, str]:
    """
    Return (answer_text, source_url) for unrelated / out-of-scope queries.
    Do not call RAG or LLM; use fixed message and point to AMC for MF questions.
    """
    return (OUT_OF_SCOPE_MESSAGE, AMC_WEBSITE_URL)
