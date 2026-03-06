#!/usr/bin/env python3
"""
End-to-end tests: when user asks about a fund not in our database (e.g. "Do you have
details of ICICI transport and Logistic fund"), the bot must reply instantly and
politely without calling RAG/Gemini (audit_path=reply_unknown_fund). No "Sending your
question..." hang.
Run from repo root: .venv/bin/python3 tests/test_unknown_fund.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.chat import handle_chat


def run_unknown(query: str) -> tuple:
    """Assert query about an unknown ICICI fund gets instant reply with limited-funds message. Return (passed, msg)."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e!r}"
    audit = out.get("audit_path", "")
    answer = (out.get("answer") or "").strip()
    if audit not in ("reply_unknown_fund", "icici_unknown_fund"):
        return False, f"expected audit_path reply_unknown_fund or icici_unknown_fund (instant reply, no RAG), got {audit!r}"
    if not answer:
        return False, "empty answer"
    if "limited with funds" not in answer.lower() and "don't have" not in answer.lower():
        return False, f"answer should say we are limited with funds or don't have that scheme: {answer[:150]!r}"
    if "official" not in answer.lower() and "visit" not in answer.lower():
        return False, f"answer should point to official site: {answer[:150]!r}"
    return True, "OK"


def run_known(query: str) -> tuple:
    """Assert query about a known fund gets 'Yes, we have information on...'. Return (passed, msg)."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e!r}"
    audit = out.get("audit_path", "")
    answer = (out.get("answer") or "").strip()
    if audit != "reply_unknown_fund":
        return False, f"expected audit_path=reply_unknown_fund for 'have info' flow, got {audit!r}"
    if "yes" not in answer.lower() or "have information" not in answer.lower():
        return False, f"expected 'Yes, we have information on...': {answer[:180]!r}"
    return True, "OK"


def main():
    failed = []
    # Unknown fund — "details of" (was missing, caused RAG hang)
    ok, msg = run_unknown("Do you have details of ICICI transport and Logistic fund")
    if not ok:
        failed.append(f"  'Do you have details of ICICI transport and Logistic fund' -> {msg}")
    else:
        print("  OK: Do you have details of ICICI transport and Logistic fund -> instant polite reply")
    # Unknown fund — "information about"
    ok, msg = run_unknown("Do you have information about ICICI infrastructure fund?")
    if not ok:
        failed.append(f"  'Do you have information about ICICI infrastructure fund?' -> {msg}")
    else:
        print("  OK: Do you have information about ICICI infrastructure fund -> instant polite reply")
    # Known fund — should get "Yes, we have information on [fund]"
    ok, msg = run_known("Do you have information about ICICI Prudential ELSS fund?")
    if not ok:
        failed.append(f"  'Do you have information about ELSS?' -> {msg}")
    else:
        print("  OK: Do you have information about ELSS -> Yes we have information")
    if failed:
        print("FAILED:")
        for f in failed:
            print(f)
        sys.exit(1)
    print("All unknown-fund (and known-fund) tests passed.")


if __name__ == "__main__":
    main()
