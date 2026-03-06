#!/bin/bash
# Run Phase 1 (scrape data) then Phase 2 (build RAG index). Use this to get real search results.
# Run this script from the project folder in your own terminal (not in Cursor's sandbox).
set -e
cd "$(dirname "$0")"
ROOT="$PWD"

if [ ! -d ".venv" ]; then
  echo "Error: .venv not found. Install dependencies first (see QUICKSTART.md)."
  exit 1
fi

# Phase 1: scrape (skip only if user passed --skip-scrape)
if [ "$1" = "--skip-scrape" ]; then
  echo "Skipping Phase 1 (--skip-scrape)."
else
  echo "========== Phase 1: Scraping data (this may take 2–5 minutes) =========="
  cd Phase1_Corpus_and_Scope
  "$ROOT/.venv/bin/python" scraper.py
  cd "$ROOT"
  echo "Phase 1 done."
fi
echo ""

echo "========== Phase 1b: Extracting structured fund data (funds.json) =========="
PYTHONPATH="$ROOT" "$ROOT/.venv/bin/python" -m Phase1_Corpus_and_Scope.extract_structured 2>/dev/null || true
if [ -f "Phase1_Corpus_and_Scope/data/funds.json" ]; then
  echo "Structured funds written. RAG will use these for answers."
else
  echo "No funds.json (optional). RAG will use raw scraped docs."
fi
echo ""

echo "========== Phase 2: Building RAG index (uses your API key; may take a few minutes) =========="
CERT_PATH="$("$ROOT/.venv/bin/python" -c "import certifi; print(certifi.where())" 2>/dev/null)"
[ -n "$CERT_PATH" ] && export SSL_CERT_FILE="$CERT_PATH" && export REQUESTS_CA_BUNDLE="$CERT_PATH" && export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$CERT_PATH"
export PYTHONWARNINGS="ignore::FutureWarning,ignore::UserWarning"
export GRPC_VERBOSITY="ERROR"
export GLOG_minloglevel="2"
PYTHONPATH="$ROOT" "$ROOT/.venv/bin/python" -m Phase2_RAG_Pipeline.build_index
echo ""
echo "Done. Run ./run_backend.sh and ./run_frontend.sh — search will now return results."
