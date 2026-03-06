"""
Phase 3 — answer_query: call Gemini with prompts, parse reply, enforce citation and disclaimer.
Returns { answer_text, source_url }. Handles refusals via classifier (no LLM on context).
"""
import os
import re
from typing import Any, Dict, List

from .config import GEMINI_MODEL, GOOGLE_API_KEY_ENV, DEFAULT_EDUCATION_URL, AMC_WEBSITE_URL
from .classifier import classify_query, get_refusal_response
from .prompts import SYSTEM_PROMPT, build_user_prompt

# Fallback when Gemini fails for out-of-database reply
OUT_OF_DB_FALLBACK = "Please visit the official sites to explore more on the available mutual funds."


def _get_genai():
    """Lazy init of Gemini generative model."""
    api_key = os.environ.get(GOOGLE_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"Set {GOOGLE_API_KEY_ENV} for Gemini LLM. "
            "Get an API key from https://aistudio.google.com/apikey"
        )
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except ImportError:
        raise ImportError("Install google-generativeai: pip install google-generativeai")


def _normalize_reply(
    reply: str,
    citation_url: str,
    scrape_date: str,
) -> str:
    """
    Clean the reply: remove any "Source: ..." and "Last updated from sources: ..."
    from the answer text. The API returns source_url separately for the frontend.
    """
    if not reply or not reply.strip():
        reply = "This information was not found in the provided sources."
    # Strip "Source: ..." (URL or markdown link)
    reply = re.sub(
        r"\s*Source:\s*\[?\s*https?://[^\s\]\)]+\s*\]?",
        "",
        reply,
        flags=re.IGNORECASE,
    )
    # Strip "Last updated from sources: ..."
    reply = re.sub(
        r"\s*Last updated from sources:\s*[^\n.]+",
        "",
        reply,
        flags=re.IGNORECASE,
    )
    return reply.strip()


def answer_query(
    user_query: str,
    retrieved_chunks: List[str],
    citation_url: str,
    scrape_date: str,
    model: str = None,
) -> Dict[str, Any]:
    """
    Generate a factual answer from context using Gemini, or return refusal for advice queries.
    Returns { "answer_text": str, "source_url": str, "refused": bool }.
    - For "advice" queries: return fixed refusal message + education URL; refused=True.
    - For "factual": call LLM with system + user prompt; normalize reply (one link, disclaimer).
    """
    if classify_query(user_query) == "advice":
        answer_text, source_url = get_refusal_response()
        return {"answer_text": answer_text, "source_url": source_url, "refused": True}

    # Use only corpus citation for factual answers; never AMFI (that is for advice refusals only)
    citation_url = citation_url or AMC_WEBSITE_URL
    scrape_date = scrape_date or ""
    model = model or GEMINI_MODEL
    genai = _get_genai()
    user_prompt = build_user_prompt(
        user_query=user_query,
        retrieved_chunks=retrieved_chunks or [],
        citation_url=citation_url,
        scrape_date=scrape_date,
    )
    try:
        generative_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT,
        )
        response = generative_model.generate_content(user_prompt)
        reply = response.text if response and hasattr(response, "text") else ""
        if not reply and response and hasattr(response, "candidates"):
            for c in getattr(response, "candidates", []) or []:
                if hasattr(c, "content") and c.content and hasattr(c.content, "parts"):
                    for p in c.content.parts:
                        if hasattr(p, "text"):
                            reply += p.text or ""
        reply = _normalize_reply(reply, citation_url, scrape_date)
    except Exception as e:
        reply = "This information was not found in the indexed corpus. You can check the fund factsheet on the AMC website."
    return {
        "answer_text": reply,
        "source_url": citation_url,
        "refused": False,
    }


def answer_out_of_database(user_query: str, model: str = None) -> Dict[str, Any]:
    """
    Call Gemini to reply when the user asked about a scheme not in our database.
    Asks them to visit the official sites to explore more mutual funds.
    Returns { "answer_text": str, "source_url": str, "refused": bool }.
    """
    model = model or GEMINI_MODEL
    genai = _get_genai()
    system = (
        "You are a factual mutual fund assistant. The user asked about a scheme that is not in our database. "
        "Reply in one short, polite sentence: ask them to visit the official AMC website to explore more on the available mutual funds. "
        "Do not add 'Source:' or 'Last updated' in your answer. Be concise."
    )
    user_prompt = f"User asked: {user_query}\n\nReply with one sentence directing them to the official site to explore more mutual funds."
    try:
        generative_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
        )
        response = generative_model.generate_content(user_prompt)
        reply = response.text if response and hasattr(response, "text") else ""
        if not reply and response and hasattr(response, "candidates"):
            for c in getattr(response, "candidates", []) or []:
                if hasattr(c, "content") and c.content and hasattr(c.content, "parts"):
                    for p in c.content.parts:
                        if hasattr(p, "text"):
                            reply += p.text or ""
        reply = _normalize_reply(reply or "", AMC_WEBSITE_URL, "")
        if not reply or len(reply) < 10:
            reply = OUT_OF_DB_FALLBACK
    except Exception:
        reply = OUT_OF_DB_FALLBACK
    return {
        "answer_text": reply,
        "source_url": AMC_WEBSITE_URL,
        "refused": False,
    }


def polish_fast_answer(user_query: str, raw_answer: str, model: str = None):
    """
    Optional Gemini step: rewrite a template-based (fast_lookup / all_info) answer
    in a friendlier, more natural way. Keeps all facts and numbers unchanged.
    Returns polished string, or None on failure (caller should keep original).
    """
    if not raw_answer or not (raw_answer or "").strip():
        return None
    model = model or GEMINI_MODEL
    try:
        genai = _get_genai()
        system = (
            "You are a helpful mutual fund assistant. Rewrite the following factual answer "
            "in a friendly, concise way. Keep all numbers, percentages, fund names, and facts exactly the same. "
            "Do not add sources, disclaimers, or investment advice. Output only the rewritten answer, no preamble."
        )
        user_prompt = (
            f"User question: {user_query}\n\n"
            f"Current answer:\n{raw_answer}\n\n"
            "Rewrite the answer in a natural, friendly way while keeping every fact unchanged."
        )
        generative_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
        )
        response = generative_model.generate_content(user_prompt)
        reply = response.text if response and hasattr(response, "text") else ""
        if not reply and response and hasattr(response, "candidates"):
            for c in getattr(response, "candidates", []) or []:
                if hasattr(c, "content") and c.content and hasattr(c.content, "parts"):
                    for p in c.content.parts:
                        if hasattr(p, "text"):
                            reply += p.text or ""
        reply = (reply or "").strip()
        return reply if reply and len(reply) > 10 else None
    except Exception:
        return None
