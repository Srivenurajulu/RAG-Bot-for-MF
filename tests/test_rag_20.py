#!/usr/bin/env python3
"""
20 test cases for the RAG bot: fast lookup, RAG fallback, advice refusal, PII.
Runs handle_chat in-process (no server). Run from repo root: python tests/test_rag_20.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Import after path
from Phase4_Backend_API.chat import handle_chat
from Phase4_Backend_API.fast_lookup import fast_lookup, _load_funds
from Phase3_LLM_Prompts.classifier import classify_query


def run_one(query: str, expect_refused: bool = None, expect_contains: list = None, expect_source_icici: bool = False):
    """Run handle_chat(query). expect_contains: list of substrings that must appear in answer."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e}"
    answer = (out.get("answer") or "").strip()
    source = (out.get("source_url") or "").strip()
    refused = out.get("refused", False)
    if expect_refused is not None and refused != expect_refused:
        return False, f"refused={refused} expected {expect_refused}"
    if expect_contains:
        for sub in expect_contains:
            if sub not in answer and sub.lower() not in answer.lower():
                return False, f"answer missing '{sub}'"
    if expect_source_icici and "icicipruamc.com" not in source:
        return False, f"source should be icicipruamc.com, got {source[:60]}"
    if not answer:
        return False, "empty answer"
    return True, "OK"


def main():
    funds = _load_funds()
    n_funds = len(funds)
    print("=" * 60)
    print("20 test cases for RAG bot (in-process, no server)")
    print(f"funds.json: {n_funds} funds loaded")
    print("=" * 60)
    cases = [
        # (query, expect_refused, expect_contains, expect_source_icici)
        ("What is the expense ratio of ICICI Prudential Large Cap Fund?", False, ["0.86", "expense"], True),
        ("Exit load for Balanced Advantage Fund?", False, ["NIL", "exit"], True),
        ("Minimum SIP for ELSS Tax Saver Fund?", False, ["500", "SIP"], True),
        ("What is the lock-in period for ICICI Prudential ELSS Tax Saver Fund?", False, ["3 year", "ELSS"], True),
        ("Benchmark for NASDAQ 100 Index Fund?", False, ["NASDAQ", "benchmark"], True),
        ("Riskometer of Smallcap Fund?", False, ["Riskometer", "Very High"], True),
        ("How can I download my capital gains statement?", False, ["statement", "AMC"], True),
        ("Expense ratio of MidCap Fund?", False, ["1.03", "expense"], True),
        ("Minimum SIP for ICICI Prudential Energy Opportunities Fund?", False, ["5000", "SIP"], True),
        ("Should I invest in ICICI Prudential Large Cap Fund?", True, [], False),
        ("Which fund should I buy?", True, [], False),
        ("What is the expense ratio of US Bluechip Equity Fund?", False, ["1.16", "expense"], True),
        ("Minimum SIP for Multicap Fund?", False, ["250", "SIP"], True),
        ("Exit load for Multi Asset Fund?", False, ["NIL", "exit"], True),
        ("What is the benchmark for ICICI Prudential Large Cap Fund?", False, ["Nifty", "benchmark"], True),
        ("Expense ratio of ICICI Prudential Smallcap Fund?", False, ["0.77", "expense"], True),
        ("Is this fund good to invest?", True, [], False),
        ("Recommend a fund for me", True, [], False),
        ("Minimum investment for NASDAQ 100 Index Fund?", False, ["100", "SIP"], True),
        ("Riskometer for NASDAQ 100?", False, ["Riskometer", "Very High"], True),
    ]
    passed = 0
    failed = []
    for i, c in enumerate(cases, 1):
        query, exp_ref, exp_contains, exp_icici = c[0], c[1], c[2], c[3]
        ok, msg = run_one(query, expect_refused=exp_ref, expect_contains=exp_contains, expect_source_icici=exp_icici)
        if ok:
            passed += 1
            print(f"  [{i:2}] PASS: {query[:55]}...")
        else:
            failed.append((i, query[:50], msg))
            print(f"  [{i:2}] FAIL: {query[:55]}... -> {msg}")

    print("=" * 60)
    print(f"Result: {passed}/20 passed, {len(failed)} failed")
    if failed:
        print("Failures:", failed)
        sys.exit(1)
    print("All 20 tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
