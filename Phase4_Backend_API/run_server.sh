#!/bin/sh
# Run from repo root: ./Phase4_Backend_API/run_server.sh
cd "$(dirname "$0")/.." && PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --reload --host 0.0.0.0 --port 8000
