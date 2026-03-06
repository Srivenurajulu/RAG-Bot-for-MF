#!/usr/bin/env python3
"""
50 test cases: when user enters an ICICI fund that is not available, the bot must reply
instantly with: "Currently we are limited with funds. For more funds check official websites."
No RAG, no Gemini — audit_path is icici_unknown_fund or reply_unknown_fund. No timeout.
Run from repo root: python tests/test_icici_unknown_fund_50.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.chat import handle_chat

# Exact message required for ICICI unknown funds
REQUIRED_MESSAGE = "Currently we are limited with funds. For more funds check official websites."
ALLOWED_AUDIT_PATHS = ("icici_unknown_fund", "reply_unknown_fund")


def run_one(query: str, case_id: int, description: str) -> tuple[bool, str]:
    """Run one test. Return (passed, error_msg)."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e!r}"
    audit = out.get("audit_path", "")
    answer = (out.get("answer") or "").strip()
    if audit not in ALLOWED_AUDIT_PATHS:
        return False, f"expected audit_path in {ALLOWED_AUDIT_PATHS}, got {audit!r}"
    if not answer:
        return False, "empty answer"
    if REQUIRED_MESSAGE not in answer:
        return False, f"answer must contain the exact message. Got: {answer[:200]!r}"
    if "official" not in answer.lower():
        return False, f"answer should mention official websites: {answer[:150]!r}"
    return True, "OK"


# 50 test cases: (query, short_description)
TEST_CASES = [
    ("ICICI transport and opporti fund", "direct fund name typo"),
    ("ICICI transport and opportunity fund", "direct fund name full"),
    ("ICICI transport and logistic fund", "direct transport logistic"),
    ("icici transport and opporti fund", "lowercase direct"),
    ("ICICI Prudential Transport and Opportunity Fund", "full AMC + fund name"),
    ("ICICI infrastructure fund", "infrastructure fund"),
    ("ICICI Prudential Infrastructure Fund", "ICICI infra full"),
    ("ICICI banking fund", "banking fund"),
    ("ICICI technology fund", "technology fund"),
    ("ICICI pharma fund", "pharma fund"),
    ("ICICI consumption fund", "consumption fund"),
    ("ICICI gold fund", "gold fund"),
    ("ICICI liquid fund", "liquid fund"),
    ("ICICI overnight fund", "overnight fund"),
    ("ICICI retirement fund", "retirement fund"),
    ("ICICI hybrid fund", "hybrid fund"),
    ("ICICI value fund", "value fund"),
    ("ICICI growth fund", "growth fund"),
    ("ICICI focused fund", "focused fund"),
    ("ICICI dividend fund", "dividend fund"),
    ("ICICI transport and opporti fund?", "with question mark"),
    ("  ICICI transport and opporti fund  ", "with spaces"),
    ("ICICI scheme transport", "scheme keyword"),
    ("Prudential transport fund", "Prudential prefix"),
    ("ICICI fund", "two words fund"),
    ("Do you have information about ICICI transport and Logistic fund", "do you have info"),
    ("Do you have details of ICICI transport and opporti fund", "do you have details"),
    ("Do you have info about ICICI infrastructure fund?", "info about infra"),
    ("Do you have information about ICICI banking fund", "info about banking"),
    ("Do you have details of ICICI technology fund", "details technology"),
    ("Is there info on ICICI transport fund?", "is there info"),
    ("Have you got information about ICICI pharma fund", "have you got"),
    ("Do you have any information about ICICI consumption fund", "any information"),
    ("ICICI XYZ fund", "generic XYZ"),
    ("ICICI abc def fund", "generic abc def"),
    ("ICICI Prudential Some Random Fund", "random fund name"),
    ("icici prudential transport and opportunity fund", "all lowercase"),
    ("ICICI TRANSPORT AND OPPORTI FUND", "all uppercase"),
    ("What is ICICI transport fund?", "what is - still fund name"),
    ("Tell me about ICICI infrastructure scheme", "tell me scheme"),
    ("ICICI opporti fund", "short opporti"),
    ("ICICI trasport fund", "typo trasport"),
    ("ICICI transport and opportuity fund", "typo opportuity"),
    ("ICICI Pru transport fund", "Pru shorthand"),
    ("ICICI Prudential Transport Fund", "no 'and opportunity'"),
    ("ICICI Prudential Infrastructure Growth Fund", "infra growth"),
    ("ICICI Prudential Banking and Financial Services Fund", "sector fund"),
    ("ICICI Prudential Commodities Fund", "commodities"),
    ("ICICI Prudential ESG Fund", "ESG fund"),
    ("ICICI Prudential International Fund", "international"),
]


def main():
    failed = []
    for i, (query, desc) in enumerate(TEST_CASES, start=1):
        ok, msg = run_one(query, i, desc)
        if not ok:
            failed.append(f"  #{i} [{desc}] {query!r} -> {msg}")
        else:
            print(f"  #{i} OK: [{desc}]")
    if failed:
        print("FAILED:", len(failed), "of", len(TEST_CASES))
        for f in failed:
            print(f)
        sys.exit(1)
    print("All 50 ICICI unknown fund tests passed.")


if __name__ == "__main__":
    main()
