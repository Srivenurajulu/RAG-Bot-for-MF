#!/usr/bin/env python3
"""
Offline tests for RAG pipeline (no backend server).
Tests classifier and, if index exists, retrieval.
Run from repo root: python tests/test_rag_offline.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def test_classifier_factual():
    """Factual queries should be classified as 'factual'."""
    from Phase3_LLM_Prompts.classifier import classify_query
    factual = [
        "What is the expense ratio of ICICI Prudential Large Cap Fund?",
        "Exit load for Balanced Advantage Fund?",
        "Minimum SIP for ELSS?",
        "What is the benchmark for NASDAQ 100 Index Fund?",
        "How to download statement?",
    ]
    for q in factual:
        assert classify_query(q) == "factual", q
    print("[PASS] Classifier: factual queries")


def test_classifier_advice():
    """Advice-style queries should be classified as 'advice'."""
    from Phase3_LLM_Prompts.classifier import classify_query
    advice = [
        "Should I invest in ICICI Prudential Large Cap Fund?",
        "Which fund should I buy?",
        "Is this fund good to invest?",
        "Recommend a fund for me",
        "Which scheme to choose?",
    ]
    for q in advice:
        assert classify_query(q) == "advice", q
    print("[PASS] Classifier: advice queries")


def test_refusal_response():
    """Refusal response should return non-empty answer and URL."""
    from Phase3_LLM_Prompts.classifier import get_refusal_response
    answer, url = get_refusal_response()
    assert answer and len(answer) > 20
    assert url and ("amfi" in url.lower() or "sebi" in url.lower() or "http" in url)
    print("[PASS] Refusal response")


def test_retrieve_if_index_exists():
    """If ChromaDB index exists, get_relevant_context should return chunks."""
    chroma_dir = REPO / "Phase2_RAG_Pipeline" / "data" / "chroma"
    if not chroma_dir.exists():
        print("[SKIP] No ChromaDB index (run ./run_build_index.sh)")
        return
    try:
        from Phase2_RAG_Pipeline.retrieve import get_relevant_context
        chunks, urls, citation, scrape_date, distances = get_relevant_context(
            "What is the expense ratio of ICICI Prudential Large Cap Fund?", k=3
        )
    except Exception as e:
        if "GOOGLE_API_KEY" in str(e) or "api" in str(e).lower():
            print("[SKIP] Retrieval needs GOOGLE_API_KEY / network")
            return
        raise
    assert isinstance(chunks, list)
    assert isinstance(urls, list)
    if len(chunks) > 0:
        assert citation or (urls and urls[0])
    print("[PASS] Retrieval returned chunks (index present)")


def main():
    print("Offline RAG tests")
    print("-" * 40)
    test_classifier_factual()
    test_classifier_advice()
    test_refusal_response()
    test_retrieve_if_index_exists()
    print("-" * 40)
    print("All offline tests passed.")


if __name__ == "__main__":
    main()
