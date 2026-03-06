#!/usr/bin/env python3
"""
20 mixed test cases (other AMCs + general MF questions + out-of-scope).

Backend must be running (recommended): ./run_server.sh

Run:
  python tests/test_misc_20.py
"""

import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

BASE_URL = os.environ.get("FAQ_API_URL", "http://localhost:8000")


def chat(query: str) -> dict:
    r = requests.post(f"{BASE_URL}/chat", json={"query": query}, timeout=60)
    r.raise_for_status()
    return r.json()


def main() -> None:
    queries = [
        # Other AMCs (should be fast, no RAG/LLM required)
        "What is the expense ratio of SBI Bluechip Fund?",
        "Exit load for HDFC Mid-Cap Opportunities Fund?",
        "Minimum SIP for Axis Small Cap Fund?",
        "NAV of Nippon India Small Cap Fund?",
        "Give details about Kotak Emerging Equity Fund",
        "Compare SBI and HDFC mutual funds",
        # General mutual fund education (should respond; may use RAG/LLM, but must not crash)
        "What is NAV in mutual funds?",
        "What does expense ratio mean?",
        "What is an exit load?",
        "What is ELSS and its lock-in period?",
        "What is SIP and how does it work?",
        "What is CAGR?",
        "What is a benchmark index in mutual funds?",
        "What is a riskometer in mutual funds?",
        # In-scope ICICI queries that should be handled via fast_lookup even without RAG
        "List all funds",
        "How can I download my mutual fund statement?",
        "NAV for ELSS fund",
        "Benchmark for ICICI Prudential NASDAQ 100 Index Fund",
        # Out-of-scope
        "What's the weather in Hyderabad today?",
        "Write a recipe for paneer butter masala",
    ]

    assert len(queries) == 20

    failures = 0
    for q in queries:
        out = chat(q)
        ans = (out.get("answer") or "").strip()
        if not ans:
            failures += 1
            print(f"[FAIL] Empty answer: {q!r} -> {out}")
            continue
        print(f"[PASS] {q!r} -> {len(ans)} chars; refused={out.get('refused')}")

    if failures:
        raise SystemExit(f"{failures} failures")
    print("All 20 misc test cases passed.")


if __name__ == "__main__":
    main()

