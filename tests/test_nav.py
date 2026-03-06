#!/usr/bin/env python3
"""
Test NAV answers: bot returns Regular Plan NAV and scheme page URL as Source.
NAV values change daily; we assert format (Rs., as of date) and correct scheme page link.
Run from repo root: .venv/bin/python3 tests/test_nav.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.chat import handle_chat

# fund_name -> expected scheme page URL (must be used as source for NAV answers)
EXPECTED_SCHEME_PAGES = {
    "ICICI Prudential Large Cap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-bluechip-fund/211",
    "ICICI Prudential MidCap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-midcap-fund/15",
    "ICICI Prudential ELSS Tax Saver Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-elss-tax-saver-fund/2",
    "ICICI Prudential Multi Asset Fund": "https://www.icicipruamc.com/mutual-fund/hybrid-funds/icici-prudential-multi-asset-fund/55",
    "ICICI Prudential Balanced Advantage Fund": "https://www.icicipruamc.com/mutual-fund/hybrid-funds/icici-prudential-balanced-advantage-fund/202",
    "ICICI Prudential Energy Opportunities Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-energy-opportunities-fund/1878",
    "ICICI Prudential Multicap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-multicap-fund/22",
    "ICICI Prudential US Bluechip Equity Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-us-bluechip-equity-fund/437",
    "ICICI Prudential NASDAQ 100 Index Fund": "https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nasdaq-100-index-fund/1827",
    "ICICI Prudential Smallcap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-smallcap-fund/168",
}


def run_nav_test(query: str, expected_scheme_url: str) -> tuple:
    """Return (passed: bool, message: str)."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e!r}"
    answer = (out.get("answer") or "").strip()
    source = (out.get("source_url") or "").strip()
    audit_path = out.get("audit_path", "")

    if audit_path != "fast_lookup":
        return False, f"expected audit_path=fast_lookup, got {audit_path!r}"
    if not answer:
        return False, "empty answer"
    if "Rs." not in answer:
        return False, f"answer should contain 'Rs.' (NAV value), got: {answer[:150]!r}"
    if "as of" not in answer.lower():
        return False, f"answer should contain 'as of' (date), got: {answer[:150]!r}"
    if source != expected_scheme_url:
        return False, f"source_url should be scheme page {expected_scheme_url!r}, got {source!r}"
    return True, "OK"


def main():
    # Query pattern -> (expected scheme URL key in EXPECTED_SCHEME_PAGES)
    cases = [
        ("What is the NAV of ICICI Prudential Large Cap Fund?", "ICICI Prudential Large Cap Fund"),
        ("NAV of MidCap Fund?", "ICICI Prudential MidCap Fund"),
        ("Latest NAV for ELSS Tax Saver Fund?", "ICICI Prudential ELSS Tax Saver Fund"),
        ("What is the NAV of Multi Asset Fund?", "ICICI Prudential Multi Asset Fund"),
        ("NAV Balanced Advantage Fund?", "ICICI Prudential Balanced Advantage Fund"),
        ("Current NAV of Energy Opportunities Fund?", "ICICI Prudential Energy Opportunities Fund"),
        ("NAV of Multicap Fund?", "ICICI Prudential Multicap Fund"),
        ("What is the NAV of US Bluechip Equity Fund?", "ICICI Prudential US Bluechip Equity Fund"),
        ("NASDAQ 100 Index Fund NAV?", "ICICI Prudential NASDAQ 100 Index Fund"),
        ("NAV of Smallcap Fund?", "ICICI Prudential Smallcap Fund"),
    ]
    failed = []
    for query, fund_key in cases:
        expected_url = EXPECTED_SCHEME_PAGES.get(fund_key, "")
        if not expected_url:
            failed.append(f"  No scheme URL for {fund_key!r}")
            continue
        ok, msg = run_nav_test(query, expected_url)
        if not ok:
            failed.append(f"  {query!r} -> {msg}")
        else:
            print(f"  OK: {query[:50]}...")
    if failed:
        print("FAILED:")
        for f in failed:
            print(f)
        sys.exit(1)
    print("All NAV tests passed (Regular Plan, scheme page as Source).")


if __name__ == "__main__":
    main()
