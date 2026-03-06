#!/bin/bash
# Serve the FAQ frontend (Phase 5). Keep this terminal open.
cd "$(dirname "$0")"
echo "Serving frontend at http://localhost:3000"
echo "Open in browser: http://localhost:3000/Phase5_Frontend/"
echo "Make sure the backend is running in another terminal (./run_backend.sh)"
echo ""
python3 -m http.server 3000
