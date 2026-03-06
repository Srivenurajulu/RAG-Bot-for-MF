#!/bin/bash
# Start backend + frontend with one command. Backend runs in background; frontend in foreground.
# Press Ctrl+C to stop both.
cd "$(dirname "$0")"
ROOT="$PWD"

if [ ! -d ".venv" ]; then
  echo "Error: .venv not found. Install dependencies first (see RUN.md)."
  exit 1
fi

# Same env as run_backend.sh
CERT_PATH="$("$ROOT/.venv/bin/python" -c "import certifi; print(certifi.where())" 2>/dev/null)"
[ -n "$CERT_PATH" ] && export SSL_CERT_FILE="$CERT_PATH" && export REQUESTS_CA_BUNDLE="$CERT_PATH" && export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$CERT_PATH"
export PYTHONWARNINGS="ignore::FutureWarning,ignore::UserWarning"
export GRPC_VERBOSITY="ERROR"
export GLOG_minloglevel="2"
export USE_LOCAL_EMBEDDINGS="${USE_LOCAL_EMBEDDINGS:-1}"

# Kill backend on exit
cleanup() {
  echo ""
  echo "Stopping backend (PID $BACKEND_PID)..."
  kill $BACKEND_PID 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# If port 8000 is already in use, try to free it
if lsof -t -i :8000 >/dev/null 2>&1; then
  echo "Port 8000 is in use. Stopping existing process..."
  lsof -t -i :8000 | xargs kill 2>/dev/null
  sleep 2
fi

echo "Starting backend at http://localhost:8000 ..."
PYTHONPATH="$ROOT" "$ROOT/.venv/bin/uvicorn" Phase4_Backend_API.app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be up
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s -o /dev/null http://localhost:8000/health 2>/dev/null; then
    echo "Backend is up."
    break
  fi
  sleep 1
done

echo "Starting frontend at http://localhost:3000"
echo "Open in browser: http://localhost:3000/Phase5_Frontend/"
echo "Press Ctrl+C to stop both backend and frontend."
echo ""
python3 -m http.server 3000
