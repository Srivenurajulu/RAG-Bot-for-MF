#!/bin/bash
# One-time: build the RAG index (Phase 2). Requires Phase 1 data and .env with GOOGLE_API_KEY.
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  echo "Error: .venv not found. Install dependencies first (see QUICKSTART.md)."
  exit 1
fi
if [ ! -f "Phase1_Corpus_and_Scope/data/manifest.json" ] && [ ! -f "Phase1_Corpus_and_Scope/data/funds.json" ]; then
  echo "Error: Phase 1 data not found. Run Phase 1 scraper then extract structured data:"
  echo "  cd Phase1_Corpus_and_Scope && ../.venv/bin/python scraper.py && cd .."
  echo "  python -m Phase1_Corpus_and_Scope.extract_structured"
  exit 1
fi
# Use certifi's SSL bundle so Gemini/Google APIs can verify certificates (fixes CERTIFICATE_VERIFY_FAILED on macOS)
CERT_PATH="$("$PWD/.venv/bin/python" -c "import certifi; print(certifi.where())" 2>/dev/null)"
[ -n "$CERT_PATH" ] && export SSL_CERT_FILE="$CERT_PATH" && export REQUESTS_CA_BUNDLE="$CERT_PATH" && export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$CERT_PATH"
export PYTHONWARNINGS="ignore::FutureWarning,ignore::UserWarning"
export GRPC_VERBOSITY="ERROR"
export GLOG_minloglevel="2"
# Use local embeddings by default (Gemini embeddings are optional and may change model IDs over time)
export USE_LOCAL_EMBEDDINGS="${USE_LOCAL_EMBEDDINGS:-1}"
echo "Building RAG index (this may take a few minutes)..."
PYTHONPATH=. .venv/bin/python -m Phase2_RAG_Pipeline.build_index
exit_code=$?
if [ $exit_code -eq 0 ]; then
  echo "Done. You can now run ./run_backend.sh and ./run_frontend.sh"
else
  echo "Build failed (exit code $exit_code). If you see SSL certificate errors, run this script from your system terminal (e.g. outside Cursor) or ensure Python can verify HTTPS (e.g. run 'Install Certificates.command' for macOS Python)."
fi
exit $exit_code
