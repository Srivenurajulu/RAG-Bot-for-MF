#!/usr/bin/env python3
"""
Test joint (multi-fund) queries: e.g. "ELSS fund and Small Cap fund - NAV, SIP, ..."
should return data for both funds, not just one.
Run from repo root: .venv/bin/python3 tests/test_joint_query.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.chat import handle_chat


def run(query: str, expect_fund_names: list) -> tuple:
    """Return (passed: bool, message: str)."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e!r}"
    answer = (out.get("answer") or "").strip()
    audit_path = out.get("audit_path", "")

    if audit_path != "fast_lookup":
        return False, f"expected audit_path=fast_lookup, got {audit_path!r}"
    if not answer:
        return False, "empty answer"
    for name in expect_fund_names:
        if name not in answer:
            return False, f"answer should contain fund name {name!r}, got answer length {len(answer)}"
    return True, "OK"


def main():
    # Joint query: ELSS and Small Cap with multiple fields
    query = (
        "List out ICICI ELSS fund and ICICI Small Cap fund - NAV, Min SIP, Expense ratio, "
        "Exit Load, CAGR, Benchmark, Riskometer, Fund manager, Top 5 stock holdings and Top 5 sector holdings"
    )
    ok, msg = run(query, ["ICICI Prudential ELSS Tax Saver Fund", "ICICI Prudential Smallcap Fund"])
    if not ok:
        print("FAILED:", msg)
        sys.exit(1)
    print("OK: joint query returns both ELSS and Smallcap data.")
    # Single-fund still works
    ok2, msg2 = run("What is the NAV and expense ratio of Large Cap Fund?", ["ICICI Prudential Large Cap Fund"])
    if not ok2:
        print("FAILED (single-fund):", msg2)
        sys.exit(1)
    print("OK: single-fund query still works.")
    print("All joint-query tests passed.")


if __name__ == "__main__":
    main()
