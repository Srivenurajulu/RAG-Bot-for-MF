#!/usr/bin/env python3
"""
Verify RAG setup: funds.json exists, Chroma index has documents.
Run from repo root: python scripts/verify_rag_setup.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FUNDS_JSON = REPO / "Phase1_Corpus_and_Scope" / "data" / "funds.json"
CHROMA_DIR = REPO / "Phase2_RAG_Pipeline" / "data" / "chroma"
MANIFEST = REPO / "Phase1_Corpus_and_Scope" / "data" / "manifest.json"


def main():
    ok = True
    print("RAG setup check")
    print("-" * 50)

    if FUNDS_JSON.exists():
        funds = json.loads(FUNDS_JSON.read_text(encoding="utf-8"))
        print(f"[OK] funds.json exists with {len(funds)} funds")
        if funds:
            f = funds[0]
            print(f"     Example: {f.get('fund_name', '')} — expense_ratio: {f.get('expense_ratio', {}).get('display', 'N/A')}")
    else:
        print("[MISSING] funds.json — run: python -m Phase1_Corpus_and_Scope.extract_structured")
        ok = False

    if not MANIFEST.exists():
        print("[MISSING] manifest.json — run Phase 1 scraper first (./run_scrape_and_build_index.sh without --skip-scrape)")
        ok = False
    else:
        print("[OK] manifest.json exists")

    # Check Chroma (directory may exist but be empty if index was never built)
    if not CHROMA_DIR.exists():
        print("[MISSING] ChromaDB directory — run ./run_build_index.sh")
        ok = False
    elif not any(CHROMA_DIR.iterdir()):
        print("[EMPTY] ChromaDB directory is empty — run ./run_build_index.sh")
        ok = False
    else:
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
            coll = client.get_collection("mf_faq_corpus")
            n = coll.count()
            if n > 0:
                print(f"[OK] ChromaDB index has {n} documents — RAG will use your data")
            else:
                print("[EMPTY] ChromaDB collection has 0 documents — run ./run_build_index.sh")
                ok = False
        except Exception as e:
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                print("[MISSING] ChromaDB collection not found — run ./run_build_index.sh")
                ok = False
            else:
                print(f"[?] ChromaDB check failed: {e}")

    print("-" * 50)
    if ok:
        print("Setup looks good. Restart the backend if you just built the index.")
    else:
        print("Fix the items above, then run ./run_build_index.sh (in Terminal.app if you see SSL errors).")
        sys.exit(1)


if __name__ == "__main__":
    main()
