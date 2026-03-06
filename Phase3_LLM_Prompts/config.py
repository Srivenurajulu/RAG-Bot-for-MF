"""
Phase 3 — LLM and prompts config.
Gemini model, refusal message, and investor-education URLs.
"""
import os
from pathlib import Path

PHASE_DIR = Path(__file__).resolve().parent

# Gemini model for answer generation (2.5 Flash / 3 Flash / 3.5 Flash)
# Use gemini-2.0-flash, gemini-1.5-flash, or gemini-2.5-flash when available
GEMINI_MODEL = os.environ.get("GEMINI_LLM_MODEL", "gemini-2.0-flash")
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"

# Refusal (advice queries only): facts-only, no investment advice; link to investor education
AMFI_INVESTOR_EDUCATION_URL = "https://www.amfiindia.com/investor-corner"
SEBI_INVESTOR_EDUCATION_URL = "https://www.sebi.gov.in/sebiweb/investor/InvestorHome.jsp"
DEFAULT_EDUCATION_URL = AMFI_INVESTOR_EDUCATION_URL  # used only for advice refusals

# Factual answers: when RAG returns no citation, point to AMC (your corpus source), not AMFI
AMC_WEBSITE_URL = "https://www.icicipruamc.com"

# KIM / SID downloads — point users to official downloads page
KIM_SID_DOWNLOADS_URL = "https://www.icicipruamc.com/media-center/downloads"

# When user asks about a scheme not in our database (no good RAG match or "do you have info about X?")
OUT_OF_DATABASE_ANSWER = (
    "We only have information on selected ICICI Prudential AMC schemes "
    "(e.g. Balanced Advantage, ELSS Tax Saver, Large Cap, Midcap, Multi Asset, and others). "
    "The scheme you asked about is not in our current database. "
    "For other schemes, please check the ICICI AMC website."
)

# Shown for buy/sell/recommendation queries — strict no-advice message
REFUSAL_MESSAGE = (
    "We do not recommend any buy or sell. We only provide factual information. "
    "For investor education, see: "
)

# Unrelated / out-of-scope queries (not about mutual funds at all)
OUT_OF_SCOPE_MESSAGE = (
    "I am only trained to answer queries related to certain mutual funds and not general queries. "
    "Please ask about ICICI Prudential schemes (e.g. expense ratio, SIP, ELSS lock-in, benchmark, riskometer). "
    "For other topics, please use appropriate resources."
)

# Optional: use Gemini to polish/expand fast_lookup and all_info answers (slower, more API usage).
# Set USE_GEMINI_POLISH_FAST_ANSWERS=1 to enable. Leave unset or 0 to keep original template answers.
_polish_val = (os.environ.get("USE_GEMINI_POLISH_FAST_ANSWERS") or "").strip().lower()
USE_GEMINI_POLISH_FAST_ANSWERS = _polish_val in ("1", "true", "yes")
