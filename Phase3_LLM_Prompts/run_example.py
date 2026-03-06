#!/usr/bin/env python3
"""
Phase 3 — Example: classify + answer_query (factual vs advice).
Run after Phase 2 index is built; set GOOGLE_API_KEY for real LLM calls.
"""
from classifier import classify_query, get_refusal_response
from answer import answer_query

def main():
    # 1) Advice query — no RAG/LLM on context
    q_advice = "Should I buy ICICI Prudential Large Cap Fund?"
    label = classify_query(q_advice)
    print(f"Query: {q_advice}")
    print(f"Class: {label}")
    if label == "advice":
        answer_text, source_url = get_refusal_response()
        print(f"Refusal: {answer_text[:80]}...")
        print(f"URL: {source_url}\n")

    # 2) Factual query — would call RAG then answer_query in Phase 4
    q_factual = "What is the expense ratio of ICICI Prudential Large Cap Fund?"
    print(f"Query: {q_factual}")
    print(f"Class: {classify_query(q_factual)}")
    # Simulated RAG output (replace with Phase 2 get_relevant_context in real flow)
    fake_chunks = [
        "ICICI Prudential Large Cap Fund - Direct Plan - Expense ratio: 0.89% (as on date)."
    ]
    result = answer_query(
        user_query=q_factual,
        retrieved_chunks=fake_chunks,
        citation_url="https://www.icicipruamc.com/blob/.../Large-Cap-Fund.pdf",
        scrape_date="2025-01-15",
    )
    print(f"Answer: {result['answer_text'][:200]}...")
    print(f"Source: {result['source_url']}")
    print(f"Refused: {result['refused']}")

if __name__ == "__main__":
    main()
