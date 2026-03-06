#!/bin/bash
# Start the FAQ backend (Phase 4). Keep this terminal open.
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  echo "Error: .venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r Phase4_Backend_API/requirements.txt -r Phase2_RAG_Pipeline/requirements.txt -r Phase3_LLM_Prompts/requirements.txt"
  exit 1
fi
# Use certifi's SSL bundle so Gemini/Google APIs can verify certificates (fixes CERTIFICATE_VERIFY_FAILED on macOS)
CERT_PATH="$("$PWD/.venv/bin/python" -c "import certifi; print(certifi.where())" 2>/dev/null)"
[ -n "$CERT_PATH" ] && export SSL_CERT_FILE="$CERT_PATH" && export REQUESTS_CA_BUNDLE="$CERT_PATH" && export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$CERT_PATH"
# Reduce warning noise (Python 3.9 EOL, deprecated package messages)
export PYTHONWARNINGS="ignore::FutureWarning,ignore::UserWarning"
# Reduce gRPC log noise
export GRPC_VERBOSITY="ERROR"
export GLOG_minloglevel="2"
# Use local embeddings by default for retrieval
export USE_LOCAL_EMBEDDINGS="${USE_LOCAL_EMBEDDINGS:-1}"
echo "Starting backend at http://localhost:8000 ..."
echo "Leave this terminal open. In another terminal run: ./run_frontend.sh"
echo ""
PYTHONPATH=. .venv/bin/uvicorn Phase4_Backend_API.app:app --reload --host 0.0.0.0 --port 8000
