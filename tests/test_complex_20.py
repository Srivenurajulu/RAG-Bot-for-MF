#!/usr/bin/env python3
"""
20 complex test cases for the RAG Bot: fast paths, advice refusal, list/all-info,
known/unknown fund, response shape, and edge cases. Runs handle_chat in-process (no server).
Run from repo root (use venv): .venv/bin/python3 tests/test_complex_20.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.chat import handle_chat


def run(
    query: str,
    *,
    expect_refused: bool = None,
    expect_contains: list = None,
    expect_not_contains: list = None,
    expect_source_icici: bool = False,
    allow_index_not_built: bool = False,
):
    """Run handle_chat(query). Return (passed: bool, message: str)."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e!r}"
    answer = (out.get("answer") or "").strip()
    source = (out.get("source_url") or "").strip()
    refused = out.get("refused", False)

    if expect_refused is not None and refused != expect_refused:
        return False, f"refused={refused} expected {expect_refused}"
    if not answer and not allow_index_not_built:
        return False, "empty answer"
    if expect_contains:
        for sub in expect_contains:
            if sub not in answer and sub.lower() not in answer.lower():
                return False, f"answer missing '{sub}'"
    if expect_not_contains:
        for sub in expect_not_contains:
            if sub in answer or sub.lower() in answer.lower():
                return False, f"answer must not contain '{sub}'"
    if expect_source_icici and "icicipruamc.com" not in source:
        return False, f"source_url should contain icicipruamc.com, got {source[:80]!r}"
    if not source and not allow_index_not_built:
        return False, "empty source_url"
    # Answer text must not contain raw source/date (we removed those from body)
    if "Last updated from sources:" in answer or "Source: https://" in answer:
        return False, "answer body must not contain 'Source: https' or 'Last updated from sources'"
    return True, "OK"


def main():
    cases = [
        # 1. Empty query -> refused (source is education URL, not necessarily icici)
        ("", True, ["facts-only", "advice"], None, False, "empty query"),
        # 2. Whitespace-only -> refused
        ("   \n\t  ", True, ["facts-only"], None, False, "whitespace only"),
        # 3. Advice: should I invest -> refused
        ("Should I invest in ICICI Prudential Large Cap Fund?", True, ["facts-only", "advice"], None, False, "advice refusal"),
        # 4. Advice: which fund to buy -> refused
        ("Which fund should I buy for my goals?", True, [], None, False, "advice which fund"),
        # 5. Fast lookup: expense ratio Large Cap
        ("What is the expense ratio of ICICI Prudential Large Cap Fund?", False, ["0.86", "expense"], None, True, "expense ratio Large Cap"),
        # 6. Fast lookup: ELSS lock-in
        ("What is the lock-in period for ICICI Prudential ELSS Tax Saver Fund?", False, ["3", "ELSS"], None, True, "ELSS lock-in"),
        # 7. Fast lookup: Minimum SIP ELSS
        ("Minimum SIP for ELSS Tax Saver Fund?", False, ["500", "SIP"], None, True, "min SIP ELSS"),
        # 8. Fast lookup: Riskometer Smallcap (Very High in data)
        ("Riskometer of Smallcap Fund?", False, ["Riskometer", "Very High"], None, True, "riskometer Smallcap"),
        # 9. Fast lookup: Benchmark NASDAQ
        ("What is the benchmark for NASDAQ 100 Index Fund?", False, ["NASDAQ", "benchmark"], None, True, "benchmark NASDAQ"),
        # 10. Do you have info about [known fund] -> full summary (all_info path) or affirmative
        ("Do you have information about ICICI Prudential ELSS fund?", False, ["ELSS", "expense", "1.08"], None, True, "have info ELSS"),
        # 11. Do you have info about [unknown fund] -> out of DB
        ("Do you have information about ICICI transport and logistic fund?", False, ["don't have", "official site"], None, True, "have info unknown fund"),
        # 12. What funds do you have -> list
        ("What funds do you have?", False, ["schemes", "ICICI Prudential", "expense ratio"], None, True, "list funds"),
        # 13. List all info on ELSS -> full summary
        ("List all the information you have on the ELSS fund", False, ["ELSS", "expense", "1.08"], None, True, "all info ELSS"),
        # 14. All information about Large Cap
        ("All information about Large Cap Fund", False, ["Large Cap", "expense", "0.86"], None, True, "all info Large Cap"),
        # 15. Fund manager ELSS
        ("Who is the fund manager of ELSS Tax Saver Fund?", False, ["Mittul", "manager"], None, True, "fund manager ELSS"),
        # 16. CAGR for a fund
        ("What is the CAGR for ICICI Prudential Large Cap Fund?", False, ["CAGR", "1Y"], None, True, "CAGR Large Cap"),
        # 17. Recommend -> refused
        ("Recommend a fund for me", True, [], None, False, "recommend refused"),
        # 18. Statement download
        ("How can I download my capital gains statement for ICICI funds?", False, ["statement", "AMC"], None, True, "statement download"),
        # 19. Answer must not contain Source: https in body
        ("What is the expense ratio of Balanced Advantage Fund?", False, ["0.86"], ["Source: https", "Last updated from sources"], True, "no source in answer body"),
        # 20. Response shape: answer + source_url + refused
        ("Exit load for Multi Asset Fund?", False, ["exit", "NIL"], None, True, "response shape"),
    ]
    passed = 0
    failed = []
    print("=" * 70)
    print("20 complex test cases (in-process handle_chat)")
    print("=" * 70)
    for i, (query, exp_ref, exp_contains, exp_not_contains, exp_icici, label) in enumerate(cases, 1):
        allow = query.strip() == ""
        ok, msg = run(
            query,
            expect_refused=exp_ref,
            expect_contains=exp_contains or [],
            expect_not_contains=exp_not_contains or [],
            expect_source_icici=exp_icici,
            allow_index_not_built=allow,
        )
        if ok:
            passed += 1
            short = (query[:52] + "…") if len(query) > 52 else query
            print(f"  [{i:2}] PASS: {label} | {short!r}")
        else:
            failed.append((i, label, msg))
            print(f"  [{i:2}] FAIL: {label} | {msg}")
    print("=" * 70)
    print(f"Result: {passed}/20 passed, {len(failed)} failed")
    if failed:
        for i, label, msg in failed:
            print(f"  Failure {i} ({label}): {msg}")
        sys.exit(1)
    print("All 20 complex tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
