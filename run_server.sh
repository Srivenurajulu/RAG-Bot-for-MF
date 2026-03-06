#!/bin/bash
# One command: backend + frontend on port 8000. No separate frontend server.
# Open http://localhost:8000/ or http://localhost:8000/Phase5_Frontend/
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  echo "Error: .venv not found. Install dependencies first (see RUN.md)."
  exit 1
fi
CERT_PATH="$("$PWD/.venv/bin/python" -c "import certifi; print(certifi.where())" 2>/dev/null)"
[ -n "$CERT_PATH" ] && export SSL_CERT_FILE="$CERT_PATH" && export REQUESTS_CA_BUNDLE="$CERT_PATH" && export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$CERT_PATH"
export PYTHONWARNINGS="ignore::FutureWarning,ignore::UserWarning"
export GRPC_VERBOSITY="ERROR"
export GLOG_minloglevel="2"
export USE_LOCAL_EMBEDDINGS="${USE_LOCAL_EMBEDDINGS:-1}"
echo "Starting MF FAQ Assistant at http://localhost:8000"
echo "Open in browser: http://localhost:8000/ or http://localhost:8000/Phase5_Frontend/"
echo ""
PYTHONPATH=. .venv/bin/uvicorn Phase4_Backend_API.app:app --host 0.0.0.0 --port 8000
