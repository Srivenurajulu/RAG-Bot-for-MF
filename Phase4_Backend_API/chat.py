"""
Phase 4 — Chat orchestration: PII check → classify → RAG (Phase 2) → answer (Phase 3).
Returns { "answer", "source_url", "refused" }. No logging or storage of PII.
"""
import sys
from pathlib import Path
from typing import Optional

# Ensure repo root is on path for Phase 2 and Phase 3 imports
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from Phase2_RAG_Pipeline.retrieve import get_relevant_context
from Phase3_LLM_Prompts.classifier import classify_query, get_refusal_response, is_out_of_scope, get_out_of_scope_response
from Phase3_LLM_Prompts.answer import answer_query, polish_fast_answer
from Phase3_LLM_Prompts.config import AMC_WEBSITE_URL, USE_GEMINI_POLISH_FAST_ANSWERS

from .fast_lookup import (
    fast_lookup,
    query_looks_like_followup,
    all_info_for_fund_if_asked,
    reply_unknown_fund_if_asked,
    list_funds_if_asked,
    other_amc_query_fast_reply,
    kim_sid_download_reply,
    icici_unknown_fund_instant_reply,
)


def handle_chat(query: str, context_fund: Optional[str] = None) -> dict:
    """
    Orchestrate: classify → advice refusal; else try fast lookup from funds.json; else RAG → answer_query.
    context_fund: when the user sends a follow-up (e.g. "Expense ratio") after we said "We have info on X",
    pass X here so we answer from funds.json instantly instead of calling RAG/Gemini.
    Returns { "answer", "source_url", "refused", "audit_path", "context_fund" (optional) }.
    """
    query = (query or "").strip()
    if not query:
        answer, url = get_refusal_response()
        return {"answer": answer, "source_url": url, "refused": True, "audit_path": "empty_refused"}

    # 1) Unrelated / general questions first (e.g. passport, weather, recipe, recommend podcasts)
    if is_out_of_scope(query):
        answer, _ = get_out_of_scope_response()
        return {"answer": answer, "source_url": "", "refused": False, "audit_path": "out_of_scope"}

    # 2) Advice → refusal + education link; skip RAG and LLM
    if classify_query(query) == "advice":
        answer, source_url = get_refusal_response()
        return {"answer": answer, "source_url": source_url, "refused": True, "audit_path": "advice_refused"}

    # 3) Other-AMC queries (e.g. "SBI mutual fund") → instant reply; no RAG/Gemini (avoids timeout)
    other_amc = other_amc_query_fast_reply(query)
    if other_amc is not None:
        other_amc["audit_path"] = "other_amc"
        return other_amc

    # 1d) KIM / SID — point to ICICI official downloads page
    kim_sid = kim_sid_download_reply(query)
    if kim_sid is not None:
        kim_sid["audit_path"] = "kim_sid_downloads"
        return kim_sid

    # 2a) "Do you have information/details about [X]?" → instant yes/no or "we don't have that scheme" (no RAG)
    unknown_fund_reply = reply_unknown_fund_if_asked(query)
    if unknown_fund_reply is not None:
        unknown_fund_reply["audit_path"] = "reply_unknown_fund"
        return unknown_fund_reply

    # 2b) "List all the information you have on [fund]" → full summary
    all_info = all_info_for_fund_if_asked(query)
    if all_info is not None:
        all_info["audit_path"] = "all_info"
        if USE_GEMINI_POLISH_FAST_ANSWERS:
            polished = polish_fast_answer(query, all_info.get("answer", ""))
            if polished:
                all_info["answer"] = polished
        return all_info

    # 2c) "What funds do you have?" / "List of schemes" → instant list
    list_reply = list_funds_if_asked(query)
    if list_reply is not None:
        list_reply["audit_path"] = "list_funds"
        return list_reply

    # 2d) Fast path: answer directly from funds.json (scraped data, no API call)
    # Always try the user's query first so a new fund name wins over previous context.
    # Only use context_fund when the query looks like a follow-up (e.g. "expense ratio", "benchmark").
    fast = fast_lookup(query)
    if fast is not None:
        fast["audit_path"] = "fast_lookup"
        if USE_GEMINI_POLISH_FAST_ANSWERS:
            polished = polish_fast_answer(query, fast.get("answer", ""))
            if polished:
                fast["answer"] = polished
        return fast
    ctx = (context_fund or "").strip()
    if ctx and query_looks_like_followup(query):
        combined = f"{ctx} {query}".strip()
        fast = fast_lookup(combined)
        if fast is not None:
            fast["audit_path"] = "fast_lookup"
            if USE_GEMINI_POLISH_FAST_ANSWERS:
                polished = polish_fast_answer(query, fast.get("answer", ""))
                if polished:
                    fast["answer"] = polished
            return fast

    # 2e) User entered an ICICI fund name we don't have → instant reply (no RAG, no timeout)
    icici_unknown = icici_unknown_fund_instant_reply(query)
    if icici_unknown is not None:
        icici_unknown["audit_path"] = "icici_unknown_fund"
        return icici_unknown

    # 3) RAG retrieval (Phase 2)
    index_not_built = False
    distances = []
    try:
        chunk_texts, source_urls, chosen_citation_url, scrape_date, distances = get_relevant_context(query, k=3)
        if not chunk_texts and not source_urls:
            index_not_built = True
    except Exception as e:
        err = str(e).lower()
        if "does not exist" in err or "not found" in err or "no collection" in err:
            index_not_built = True
        chunk_texts = []
        chosen_citation_url = ""
        scrape_date = ""
        distances = []

    if index_not_built:
        return {
            "answer": "The FAQ index has not been built yet, so no answers can be found. From the project folder run: ./run_build_index.sh (you need Phase 1 data first: run the Phase 1 scraper, then extract structured data). Until then you can check fund details on the AMC website.",
            "source_url": AMC_WEBSITE_URL,
            "refused": False,
            "audit_path": "index_not_built",
        }

    # 3b) No good match from RAG (e.g. user asked about a scheme not in our database)
    NO_MATCH_DISTANCE_THRESHOLD = 1.15
    if distances and min(distances) > NO_MATCH_DISTANCE_THRESHOLD:
        return {
            "answer": "We don't have that scheme in our data. Please visit the official site to explore more mutual funds.",
            "source_url": AMC_WEBSITE_URL,
            "refused": False,
            "audit_path": "rag_no_match",
        }

    # 4) LLM answer (Phase 3) — works with empty chunks / no context
    result = answer_query(
        user_query=query,
        retrieved_chunks=chunk_texts,
        citation_url=chosen_citation_url,
        scrape_date=scrape_date,
    )
    return {
        "answer": result["answer_text"],
        "source_url": result["source_url"],
        "refused": result["refused"],
        "audit_path": "rag_answer",
    }
