#!/usr/bin/env python3
"""
Test RAG bot: POST /chat with sample queries and assert reasonable responses.
Run from repo root. Backend must be running: ./run_backend.sh

  python tests/test_rag_chat.py           # fast only (health, PII)
  python tests/test_rag_chat.py --slow   # include RAG/LLM chat tests (can take 1–2 min)
"""
import argparse
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

BASE_URL = os.environ.get("FAQ_API_URL", "http://localhost:8000")
CHAT_TIMEOUT = 90  # RAG + Gemini can be slow


def chat(query: str) -> dict:
    """POST /chat and return parsed JSON or raise."""
    r = requests.post(
        f"{BASE_URL}/chat",
        json={"query": query},
        timeout=CHAT_TIMEOUT,
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()
    return r.json()


def test_health():
    """GET /health should return status ok."""
    r = requests.get(f"{BASE_URL}/health", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "ok", data
    print("[PASS] GET /health -> ok")


def test_pii_rejected():
    """Query containing PII should get 400."""
    r = requests.post(
        f"{BASE_URL}/chat",
        json={"query": "My PAN is ABCDE1234F"},
        timeout=10,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 400, f"Expected 400 for PII, got {r.status_code}"
    print("[PASS] PII query rejected with 400.")


def test_factual_queries():
    """Factual questions should return an answer and a source_url (or index-not-built message)."""
    queries = [
        "What is the expense ratio of ICICI Prudential Large Cap Fund?",
        "What is the exit load for ICICI Prudential Balanced Advantage Fund?",
        "Minimum SIP for ICICI Prudential ELSS Tax Saver Fund?",
        "What is the lock-in period for ELSS schemes?",
        "What is the benchmark for ICICI Prudential NASDAQ 100 Index Fund?",
        "How can I download my statement for ICICI Prudential funds?",
    ]
    for q in queries:
        out = chat(q)
        assert "answer" in out and "source_url" in out and "refused" in out
        assert isinstance(out["answer"], str)
        assert isinstance(out["refused"], bool)
        assert out["refused"] is False, f"Expected factual answer for: {q!r}"
        assert len(out["answer"].strip()) > 0, f"Empty answer for: {q!r}"
        print(f"[PASS] Factual: {q[:50]}... -> answer length {len(out['answer'])}")
    print("[PASS] All factual queries returned non-refused answers.")


def test_advice_refused():
    """Advice-style query should be refused with refused=True."""
    out = chat("Should I invest in ICICI Prudential Large Cap Fund?")
    assert out.get("refused") is True
    assert "answer" in out and len(out["answer"]) > 0
    print("[PASS] Advice query refused.")


def main():
    parser = argparse.ArgumentParser(description="Test RAG bot API")
    parser.add_argument("--slow", action="store_true", help="Run RAG/LLM chat tests (slower)")
    args = parser.parse_args()
    slow = args.slow

    print("RAG bot tests (backend at", BASE_URL, ")")
    print("-" * 50)
    test_health()
    test_pii_rejected()
    if slow:
        print("Running slow RAG/LLM tests...")
        test_factual_queries()
        test_advice_refused()
    else:
        print("Skipping RAG/LLM tests (use --slow to run them).")
    print("-" * 50)
    print("All tests passed.")


if __name__ == "__main__":
    main()
