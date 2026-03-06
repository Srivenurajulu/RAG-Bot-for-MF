#!/bin/bash
# Stop whatever is running on port 8000 (the backend).
PID=$(lsof -t -i :8000 2>/dev/null)
if [ -z "$PID" ]; then
  echo "Nothing is running on port 8000."
  exit 0
fi
kill "$PID" 2>/dev/null && echo "Stopped process $PID on port 8000." || echo "Could not stop process $PID. Try: kill $PID"
exit 0
