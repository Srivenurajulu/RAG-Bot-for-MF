#!/usr/bin/env python3
"""
Test: Top 5 Stock/Sector Holdings in funds.json and fast_lookup;
and that multiple questions in one query return all answers.
Run from repo root: .venv/bin/python3 tests/test_holdings_and_multi_questions.py
"""
import sys
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.chat import handle_chat
from Phase4_Backend_API.fast_lookup import fast_lookup, _load_funds

FUNDS_JSON = REPO / "Phase1_Corpus_and_Scope" / "data" / "funds.json"


def test_funds_json_has_holdings_fields():
    """funds.json should have top_5_stock_holdings and top_5_sector_holdings for at least one fund."""
    with open(FUNDS_JSON, encoding="utf-8") as f:
        funds = json.load(f)
    with_stocks = [f for f in funds if f.get("top_5_stock_holdings")]
    with_sectors = [f for f in funds if f.get("top_5_sector_holdings")]
    assert len(with_stocks) >= 1, "At least one fund should have top_5_stock_holdings"
    assert len(with_sectors) >= 1, "At least one fund should have top_5_sector_holdings"
    # ELSS should have both (from factsheet)
    elss = next((f for f in funds if "ELSS" in f.get("fund_name", "")), None)
    assert elss, "ELSS fund not found"
    assert elss.get("top_5_stock_holdings") and elss["top_5_stock_holdings"].get("display"), "ELSS should have stock holdings"
    assert elss.get("top_5_sector_holdings") and elss["top_5_sector_holdings"].get("display"), "ELSS should have sector holdings"


def test_fast_lookup_top_5_stock_holdings():
    """Query for 'ELSS fund top 5 stock holdings' returns answer from funds.json."""
    r = fast_lookup("ICICI ELSS fund top 5 stock holdings")
    assert r is not None, "fast_lookup should return for top 5 stock holdings"
    answer = (r.get("answer") or "").strip()
    assert "Top 5 Stock" in answer or "stock" in answer.lower(), f"Answer should mention stock holdings: {answer[:150]}"
    assert "ICICI Bank" in answer or "HDFC" in answer, "Answer should include at least one stock name"


def test_fast_lookup_top_5_sector_holdings():
    """Query for 'ELSS top 5 sector holdings' returns answer."""
    r = fast_lookup("ELSS fund top 5 sector holdings")
    assert r is not None
    answer = (r.get("answer") or "").strip()
    assert "Sector" in answer or "sector" in answer
    assert "Financial" in answer or "Healthcare" in answer or "Oil" in answer


def test_multiple_questions_return_all_answers():
    """When user asks for multiple things in one query, all answers should be returned."""
    # e.g. "Large Cap Fund expense ratio, benchmark and top 5 stock holdings"
    q = "ICICI Large Cap Fund expense ratio benchmark and top 5 stock holdings"
    r = fast_lookup(q)
    assert r is not None
    answer = (r.get("answer") or "").strip()
    parts = [p.strip() for p in answer.split("\n\n") if p.strip()]
    assert len(parts) >= 2, f"Expected at least 2 answer parts for multi-question; got: {parts}"
    assert any("Expense Ratio" in p or "expense" in p.lower() for p in parts)
    assert any("Benchmark" in p or "benchmark" in p.lower() for p in parts)
    assert any("Stock" in p or "stock" in p.lower() for p in parts)


def test_handle_chat_multi_question():
    """handle_chat returns all answers for a multi-part question."""
    r = handle_chat("ELSS fund expense ratio and top 5 sector holdings")
    assert r.get("answer")
    parts = [p for p in (r.get("answer") or "").split("\n\n") if p.strip()]
    assert len(parts) >= 2
    assert any("Expense" in p for p in parts)
    assert any("Sector" in p or "sector" in p.lower() for p in parts)


def test_holding_singular_and_plural_both_return_answers():
    """Both 'holding' (singular) and 'holdings' (plural) must return an answer, not the 'What would you like to know?' prompt."""
    # Singular - should get answer (data or "not available"), not the clarification prompt
    r1 = fast_lookup("Top 5 sector holding and Top 5 stock holding of Balanced Advantage fund")
    assert r1 is not None
    ans1 = (r1.get("answer") or "").strip()
    assert "What would you like to know" not in ans1, "Should return holdings answer, not prompt"
    assert "Top 5 Sector" in ans1 or "Top 5 Stock" in ans1 or "not available" in ans1
    # Plural - same
    r2 = fast_lookup("Top 5 sector holdings and Top 5 stock holdings of ELSS fund")
    assert r2 is not None
    ans2 = (r2.get("answer") or "").strip()
    assert "What would you like to know" not in ans2
    assert "•" in ans2 or "not available" in ans2


if __name__ == "__main__":
    test_funds_json_has_holdings_fields()
    test_fast_lookup_top_5_stock_holdings()
    test_fast_lookup_top_5_sector_holdings()
    test_multiple_questions_return_all_answers()
    test_handle_chat_multi_question()
    test_holding_singular_and_plural_both_return_answers()
    print("All holdings and multi-question tests passed.")
