#!/usr/bin/env bash
# Fetch latest NAV for configured funds and update Phase1 funds.json.
# Run from repo root. Optionally run via cron or run_nav_scheduler for daily updates.
set -e
cd "$(dirname "$0")"
. .venv/bin/activate 2>/dev/null || true
python -m Phase1_Corpus_and_Scope.fetch_nav
