#!/usr/bin/env python3
"""
50 additional complex test cases for the RAG Bot (no overlap with test_complex_20).
Runs handle_chat in-process. Use --show-answers to print each question and bot answer.
Run: .venv/bin/python3 tests/test_complex_50.py [--show-answers]
"""
import argparse
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
    """Run handle_chat(query). Return (passed: bool, message: str, out: dict)."""
    try:
        out = handle_chat(query)
    except Exception as e:
        return False, f"Exception: {e!r}", {}
    answer = (out.get("answer") or "").strip()
    source = (out.get("source_url") or "").strip()
    refused = out.get("refused", False)

    if expect_refused is not None and refused != expect_refused:
        return False, f"refused={refused} expected {expect_refused}", out
    if not answer and not allow_index_not_built:
        return False, "empty answer", out
    if expect_contains:
        for sub in expect_contains:
            if sub not in answer and sub.lower() not in answer.lower():
                return False, f"answer missing '{sub}'", out
    if expect_not_contains:
        for sub in expect_not_contains:
            if sub in answer or sub.lower() in answer.lower():
                return False, f"answer must not contain '{sub}'", out
    if expect_source_icici and "icicipruamc.com" not in source:
        return False, f"source_url should contain icicipruamc.com", out
    if not source and not allow_index_not_built:
        return False, "empty source_url", out
    if "Last updated from sources:" in answer or "Source: https://" in answer:
        return False, "answer body must not contain Source: https or Last updated from sources", out
    return True, "OK", out


# 50 NEW test cases (none from test_complex_20)
CASES = [
    # (query, expect_refused, expect_contains, expect_not_contains, expect_source_icici, allow_index_not_built, label)
    ("What is the exit load for MidCap Fund?", False, ["exit", "1"], None, True, False, "exit load MidCap"),
    ("Tell me the minimum SIP for Balanced Advantage Fund", False, ["250", "SIP"], None, True, False, "min SIP Balanced Advantage"),
    ("Lock-in period for ELSS?", False, ["3", "ELSS"], None, True, False, "lock-in ELSS short"),
    ("Riskometer of Large Cap Fund?", False, ["Riskometer", "Very High"], None, True, False, "riskometer Large Cap"),
    ("Benchmark for ELSS Tax Saver?", False, ["Nifty", "benchmark"], None, True, False, "benchmark ELSS"),
    ("Fund manager of Large Cap Fund?", False, ["manager", "Anish"], None, True, False, "fund manager Large Cap"),
    ("CAGR 3 year for ELSS?", False, ["CAGR", "16"], None, True, False, "CAGR 3y ELSS"),
    ("Is there information about Multicap Fund?", False, ["Multicap", "expense"], None, True, False, "is there info Multicap"),
    ("Do you have info about Energy Opportunities Fund?", False, ["Energy", "expense"], None, True, False, "have info Energy"),
    ("Which schemes do you have?", False, ["schemes", "ICICI"], None, True, False, "which schemes"),
    ("List of funds", False, ["schemes", "ICICI"], None, True, False, "list of funds"),
    ("Everything you have on MidCap Fund", False, ["MidCap", "expense", "1.03"], None, True, False, "everything MidCap"),
    ("Full details of NASDAQ 100 Index Fund", False, ["NASDAQ", "expense"], None, True, False, "full details NASDAQ"),
    ("Details about Smallcap Fund", False, ["Smallcap", "expense"], None, True, False, "details Smallcap"),
    ("What is the expense ratio of Multi Asset Fund?", False, ["0.64", "expense"], None, True, False, "expense ratio Multi Asset"),
    ("Exit load for ELSS Tax Saver?", False, ["exit", "NIL"], None, True, False, "exit load ELSS"),
    ("Minimum investment for Multicap?", False, ["250", "SIP"], None, True, False, "min investment Multicap"),
    ("What is the risk level of Balanced Advantage Fund?", False, ["risk", "Very High"], None, True, False, "risk level Balanced Advantage"),
    ("Who manages the MidCap Fund?", False, ["Lalit", "manager"], None, True, False, "who manages MidCap"),
    ("1 year return for Large Cap Fund?", False, ["CAGR", "11"], None, True, False, "1y return Large Cap"),
    ("Should we invest in ELSS?", True, ["facts-only"], None, False, False, "advice should we invest"),
    ("Is this scheme good to buy?", True, [], None, False, False, "advice good to buy"),
    ("Compare returns of Large Cap and ELSS", True, [], None, False, False, "advice compare returns"),
    ("Help me choose a fund", True, ["facts-only"], None, False, False, "advice help choose"),
    ("Which is better Large Cap or MidCap?", True, [], None, False, False, "advice which better"),
    ("Do you have information about HDFC Balanced Fund?", False, ["don't have", "official"], None, True, False, "have info unknown HDFC"),
    ("What is the benchmark for Energy Opportunities Fund?", False, ["Nifty Energy", "benchmark"], None, True, False, "benchmark Energy"),
    ("Expense ratio of US Bluechip Equity Fund?", False, ["1.16", "expense"], None, True, False, "expense US Bluechip"),
    ("Minimum SIP for Smallcap Fund?", False, ["5000", "SIP"], None, True, False, "min SIP Smallcap"),
    ("How to download statement for ELSS?", False, ["statement", "AMC"], None, True, False, "statement ELSS"),
    ("Account statement download", False, ["statement"], None, True, False, "account statement"),
    ("Tell me all the information you have on Balanced Advantage Fund", False, ["Balanced Advantage", "0.86"], None, True, False, "all info Balanced Advantage"),
    ("All the information about Multi Asset Fund", False, ["Multi Asset", "0.64"], None, True, False, "all info Multi Asset"),
    ("Complete details of US Bluechip Equity Fund", False, ["US Bluechip", "expense"], None, True, False, "complete details US Bluechip"),
    ("What funds does the bot have information on?", False, ["schemes", "ICICI"], None, True, False, "bot have info on"),
    ("Information on which funds", False, ["schemes", "ICICI"], None, True, False, "information on which funds"),
    ("Do you have any information about ICICI Prudential Large Cap Fund?", False, ["Large Cap", "expense"], None, True, False, "any info Large Cap"),
    ("Have you got information about Smallcap Fund?", False, ["Smallcap", "expense"], None, True, False, "have you got info Smallcap"),
    ("Do you have information about SBI Bluechip Fund?", False, ["don't have", "official"], None, True, False, "have info unknown SBI"),
    ("What is the total expense ratio of MidCap Fund?", False, ["1.03", "expense"], None, True, False, "total expense ratio MidCap"),
    ("Min sip for NASDAQ 100?", False, ["100", "SIP"], None, True, False, "min sip NASDAQ"),
    ("ELSS lock in", False, ["3", "ELSS"], None, True, False, "ELSS lock in"),
    ("Risk meter for Multi Asset Fund?", False, ["risk", "Very High"], None, True, False, "risk meter Multi Asset"),
    ("Benchmark index for Large Cap?", False, ["Nifty 100", "benchmark"], None, True, False, "benchmark index Large Cap"),
    ("Fund managers of Multicap Fund?", False, ["Lalit", "manager"], None, True, False, "fund managers Multicap"),
    ("Since inception return for ELSS?", False, ["CAGR", "inception"], None, True, False, "since inception ELSS"),
    ("Capital gains statement download for ICICI funds?", False, ["statement", "AMC"], None, True, False, "capital gains statement"),
    ("Recommend me a scheme", True, [], None, False, False, "advice recommend scheme"),
    ("Worth investing in this fund?", True, [], None, False, False, "advice worth investing"),
    ("What do you know about ELSS Tax Saver Fund?", False, ["ELSS", "expense"], None, True, False, "what do you know ELSS"),
]

assert len(CASES) == 50, f"Expected 50 cases, got {len(CASES)}"


def main():
    parser = argparse.ArgumentParser(description="50 complex test cases")
    parser.add_argument("--show-answers", action="store_true", help="Print each question and bot answer")
    parser.add_argument("--write-qa", action="store_true", help="Write tests/COMPLEX_50_QA.md with all Q&A")
    args = parser.parse_args()
    show = args.show_answers
    write_qa = args.write_qa

    passed = 0
    failed = []
    results = []  # (label, query, full_answer, passed, msg)

    print("=" * 72)
    print("50 additional complex test cases (in-process handle_chat)")
    print("=" * 72)

    for i, row in enumerate(CASES, 1):
        query, exp_ref, exp_contains, exp_not_contains, exp_icici, allow_idx, label = row
        ok, msg, out = run(
            query,
            expect_refused=exp_ref,
            expect_contains=exp_contains or [],
            expect_not_contains=exp_not_contains or [],
            expect_source_icici=exp_icici,
            allow_index_not_built=allow_idx,
        )
        full_answer = (out.get("answer") or "")
        answer = full_answer[:200]
        if ok:
            passed += 1
            status = "PASS"
        else:
            failed.append((i, label, msg))
            status = "FAIL"
        short_q = (query[:48] + "…") if len(query) > 48 else query
        print(f"  [{i:2}] {status}: {label} | {short_q!r}")
        results.append((label, query, full_answer, ok, msg))

        if show:
            print(f"       Q: {query}")
            print(f"       A: {full_answer[:350]}{'…' if len(full_answer) > 350 else ''}")
            if not ok:
                print(f"       FAIL: {msg}")
            print()

    print("=" * 72)
    print(f"Result: {passed}/50 passed, {len(failed)} failed")

    if failed:
        print("\n--- Failed cases (question and bot answer) ---")
        for i, label, msg in failed:
            for r in results:
                if r[0] == label and not r[3]:
                    print(f"\n[{i}] {label}")
                    print(f"  Q: {r[1]}")
                    print(f"  A: {r[2]}…")
                    print(f"  Reason: {r[4]}")
                    break
        sys.exit(1)

    if write_qa and not failed:
        qa_path = REPO / "tests" / "COMPLEX_50_QA.md"
        lines = ["# 50 Additional Test Cases — Questions and Bot Answers", "", "| # | Question | Bot Answer |", "|---|----------|------------|"]
        for i, (label, query, full_answer, ok, _) in enumerate(results, 1):
            a_esc = full_answer.replace("|", " ").replace("\n", " ").strip()[:300]
            q_esc = query.replace("|", " ").strip()
            lines.append(f"| {i} | {q_esc} | {a_esc}… |")
        qa_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote {qa_path}")

    if show and not failed:
        print("\n--- All Q&A (first 250 chars of answer) ---")
        for label, query, full_ans, ok, _ in results:
            print(f"\n{label}")
            print(f"  Q: {query}")
            print(f"  A: {full_ans[:250]}…")

    print("All 50 tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
