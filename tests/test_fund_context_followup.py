#!/usr/bin/env python3
"""
Test: When a fund is already in context, single-field follow-up queries (e.g. "Bench mark",
"expense ratio", "riskometer") should be answered from funds.json using that fund — no
"What would you like to know?" and no RAG/Gemini timeout.
Run from repo root: .venv/bin/python3 tests/test_fund_context_followup.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.chat import handle_chat

CONTEXT_FUND = "ICICI Prudential ELSS Tax Saver Fund"

# (query, substring that must appear in answer to pass)
FOLLOWUP_CASES = [
    ("Bench mark", "Benchmark"),
    ("benchmark", "Benchmark"),
    ("Bench mark?", "Benchmark"),
    ("expense ratio", "Expense Ratio"),
    ("Expense ratio", "Expense Ratio"),
    ("riskometer", "Riskometer"),
    ("Risk meter", "Riskometer"),
    ("lock in", "Lock"),
    ("lock-in", "Lock"),
    ("fund manager", "Manager"),
    ("minimum sip", "Minimum"),
    ("exit load", "Exit"),
    ("CAGR", "CAGR"),
    ("benchmark and riskometer", "Benchmark"),
    ("benchmark and riskometer", "Riskometer"),
]


def test_first_message_returns_context_fund():
    """First message 'ICICI ELSS fund' should return context_fund so frontend can send it next."""
    out = handle_chat("ICICI ELSS fund")
    assert out.get("context_fund") == CONTEXT_FUND, f"Expected context_fund={CONTEXT_FUND!r}, got {out.get('context_fund')!r}"
    assert "What would you like to know" in (out.get("answer") or ""), "Expected prompt asking what they want"
    return True


def test_followups_with_context():
    """Each follow-up with context_fund should return a direct answer, not 'What would you like to know?'."""
    failures = []
    for query, must_contain in FOLLOWUP_CASES:
        out = handle_chat(query, context_fund=CONTEXT_FUND)
        answer = (out.get("answer") or "").strip()
        if "What would you like to know" in answer and must_contain.lower() not in answer.lower():
            failures.append((query, f"Got prompt instead of answer; answer snippet: {answer[:80]}"))
        elif must_contain not in answer and must_contain.lower() not in answer.lower():
            failures.append((query, f"Answer should contain {must_contain!r}; got: {answer[:100]}"))
    if failures:
        raise AssertionError("Follow-up failures:\n" + "\n".join(f"  {q}: {msg}" for q, msg in failures))
    return True


def test_no_context_bench_mark_alone():
    """Without context, 'Bench mark' alone may not find a fund; with context it must return benchmark."""
    out_with_ctx = handle_chat("Bench mark", context_fund=CONTEXT_FUND)
    answer = (out_with_ctx.get("answer") or "")
    assert "Benchmark" in answer or "benchmark" in answer.lower(), f"With context expected benchmark answer: {answer[:120]}"
    assert "What would you like to know" not in answer, "With context should not reply with prompt"
    return True


def test_unrelated_query_treated_as_new():
    """Unrelated queries must not be treated as follow-ups; they go to RAG as new queries."""
    from Phase4_Backend_API.fast_lookup import query_looks_like_followup
    assert query_looks_like_followup("Whats the weather") is False
    assert query_looks_like_followup("Why are you hallucinating") is False
    assert query_looks_like_followup("What is the capital of India") is False
    # So handle_chat will not use context_fund for these — they fall through to RAG
    return True


def test_switch_fund_query_first():
    """When user types a different fund (e.g. 'ICICI Mid cap' or 'ICICI Balanced Advantage fund'),
    the bot must answer about that fund, not the previous context_fund."""
    # User was in ELSS context; now asks about other funds — must get the new fund, not ELSS
    cases = [
        ("ICICI Mid cap", "MidCap", "ELSS"),
        ("ICICI Balanced Advantage fund", "Balanced Advantage", "ELSS"),
        ("ICICI Balanced Advantage fund expense ratio", "Balanced Advantage", "1.08"),  # ELSS is 1.08; Balanced Advantage is 0.86
    ]
    for query, must_contain, must_not_be_elss_answer in cases:
        out = handle_chat(query, context_fund="ICICI Prudential ELSS Tax Saver Fund")
        answer = (out.get("answer") or "").strip()
        if must_contain not in answer:
            raise AssertionError(f"Query {query!r}: expected answer to contain {must_contain!r}, got: {answer[:120]}")
        # Ensure we didn't return ELSS when user asked for another fund
        if "ICICI Prudential ELSS Tax Saver Fund" in answer and must_contain.lower() != "elss":
            # ELSS in answer is OK only if we're answering about ELSS (e.g. expense ratio 1.08 for ELSS)
            if "Balanced Advantage" in query and "ELSS" in answer:
                raise AssertionError(f"Query {query!r}: user asked for Balanced Advantage but got ELSS: {answer[:120]}")
        if "Expense Ratio is 1.08" in answer and "Balanced Advantage" in query:
            raise AssertionError(f"Query {query!r}: expected Balanced Advantage expense ratio (0.86), not ELSS (1.08)")
    return True


if __name__ == "__main__":
    test_first_message_returns_context_fund()
    test_followups_with_context()
    test_no_context_bench_mark_alone()
    test_unrelated_query_treated_as_new()
    test_switch_fund_query_first()
    print("All fund-context follow-up scenarios passed.")
