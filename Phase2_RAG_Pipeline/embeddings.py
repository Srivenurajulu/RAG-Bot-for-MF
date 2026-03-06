"""
Phase 2 — Embeddings

Primary: Gemini embedding API (google-generativeai).
Fallback: Local ONNX MiniLM embedding function shipped with ChromaDB.

Why fallback exists:
- Gemini embedding model IDs and API versions can change over time.
- A local embedding path ensures the project runs end-to-end (index build + retrieval)
  even when Gemini embeddings are unavailable/misconfigured.
"""
import os
from pathlib import Path
from typing import List

from .config import GEMINI_EMBEDDING_MODEL, EMBED_BATCH_SIZE, GOOGLE_API_KEY_ENV


_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOCAL_CACHE_DIR = _REPO_ROOT / ".cache"


def _ensure_local_cache_env() -> None:
    """
    Ensure embedding downloads/caches go into the repo (not ~/.cache).
    This avoids permission issues in restricted environments and keeps the project self-contained.
    """
    _LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Used by many libs (including Chroma's ONNX embedding function) as a base cache location.
    os.environ.setdefault("XDG_CACHE_HOME", str(_LOCAL_CACHE_DIR))
    # Some stacks also look at these:
    os.environ.setdefault("HF_HOME", str(_LOCAL_CACHE_DIR / "hf"))


def _get_local_embedding_fn():
    """
    Return a callable embedding function that maps List[str] -> List[List[float]].
    Uses Chroma's ONNX MiniLM embedding function (downloads model once into cache).
    """
    _ensure_local_cache_env()
    from chromadb.utils import embedding_functions

    # Prefer the explicit ONNX MiniLM implementation (consistent + fast).
    if hasattr(embedding_functions, "ONNXMiniLM_L6_V2"):
        # Chroma hardcodes the default download path to Path.home()/.cache/... which may
        # be unwritable in some environments. Override it to a repo-local cache.
        try:
            embedding_functions.ONNXMiniLM_L6_V2.DOWNLOAD_PATH = _LOCAL_CACHE_DIR / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"
        except Exception:
            pass
        return embedding_functions.ONNXMiniLM_L6_V2()
    # Fallback to whatever Chroma considers default.
    return embedding_functions.DefaultEmbeddingFunction()


def _get_client():
    """Lazy init of Gemini embedding client."""
    api_key = os.environ.get(GOOGLE_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"Set {GOOGLE_API_KEY_ENV} for Gemini embeddings. "
            "Get an API key from https://aistudio.google.com/apikey"
        )
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except ImportError:
        raise ImportError("Install google-generativeai: pip install google-generativeai")


def embed_texts(texts: List[str], model: str = None) -> List[List[float]]:
    """
    Embed a list of texts using Gemini. Batches requests.
    Returns list of embedding vectors (same order as texts).
    """
    # If explicitly requested, force local embeddings.
    force_local = (os.environ.get("USE_LOCAL_EMBEDDINGS") or "").strip().lower() in ("1", "true", "yes")

    # Try Gemini first unless forced local.
    if not force_local:
        try:
            model = model or GEMINI_EMBEDDING_MODEL
            genai = _get_client()
            all_embeddings = []
            for i in range(0, len(texts), EMBED_BATCH_SIZE):
                batch = texts[i : i + EMBED_BATCH_SIZE]
                batch = [t.strip() or " " for t in batch]
                try:
                    result = genai.embed_content(
                        model=model,
                        content=batch,
                        task_type="retrieval_document",
                    )
                except Exception:
                    result = genai.embed_content(model=model, content=batch)
                # Response: single -> {"embedding": [...]}; batch -> list or {"embeddings": [[...], ...]}
                try:
                    if isinstance(result, list):
                        for item in result:
                            emb = item.get("embedding") if isinstance(item, dict) else getattr(item, "embedding", None)
                            if emb is not None:
                                all_embeddings.append(emb)
                    elif isinstance(result, dict) and "embeddings" in result:
                        all_embeddings.extend(result["embeddings"])
                    elif isinstance(result, dict) and "embedding" in result and len(batch) == 1:
                        all_embeddings.append(result["embedding"])
                    elif isinstance(result, dict) and "embedding" in result and len(batch) > 1:
                        # Some APIs return one embedding for batch -> fallback to one-by-one
                        raise ValueError("Single embedding for batch")
                    else:
                        emb = getattr(result, "embedding", None)
                        if emb is not None:
                            all_embeddings.append(emb)
                        else:
                            raise ValueError("No embeddings in result")
                except Exception:
                    for t in batch:
                        r = genai.embed_content(model=model, content=t)
                        emb = r.get("embedding") if isinstance(r, dict) else getattr(r, "embedding", None)
                        all_embeddings.append(emb if emb else [0.0] * 768)
            return all_embeddings
        except Exception:
            # Fall back to local embeddings on any Gemini failure
            pass

    # Local embedding fallback (Chroma ONNX MiniLM)
    ef = _get_local_embedding_fn()
    texts = [t.strip() or " " for t in texts]
    return ef(texts)


def embed_query(query: str, model: str = None) -> List[float]:
    """Embed a single query string. Use same model as documents for retrieval."""
    force_local = (os.environ.get("USE_LOCAL_EMBEDDINGS") or "").strip().lower() in ("1", "true", "yes")
    if not force_local:
        try:
            model = model or GEMINI_EMBEDDING_MODEL
            genai = _get_client()
            try:
                result = genai.embed_content(
                    model=model,
                    content=query.strip() or " ",
                    task_type="retrieval_query",
                )
            except Exception:
                result = genai.embed_content(model=model, content=query.strip() or " ")
            if isinstance(result, dict) and "embedding" in result:
                return result["embedding"]
            if hasattr(result, "embedding"):
                return result.embedding
        except Exception:
            pass

    ef = _get_local_embedding_fn()
    return ef([query.strip() or " "])[0]
