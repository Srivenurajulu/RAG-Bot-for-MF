#!/usr/bin/env python3
"""
Fetch latest NAV for configured ICICI Prudential schemes from MFapi.in and merge into funds.json.
Run from repo root: python -m Phase1_Corpus_and_Scope.fetch_nav
Or: ./run_fetch_nav.sh from repo root.
Used by the scheduler to keep NAV up to date for the RAG bot.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

PHASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PHASE_DIR.parent
DATA_DIR = PHASE_DIR / "data"
FUNDS_JSON = DATA_DIR / "funds.json"

# Ensure we can import nav_scheme_codes
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
try:
    from Phase1_Corpus_and_Scope.nav_scheme_codes import NAV_SCHEME_CODES, NAV_API_BASE, FUND_SCHEME_PAGE_URLS
except ImportError:
    from nav_scheme_codes import NAV_SCHEME_CODES, NAV_API_BASE, FUND_SCHEME_PAGE_URLS


def fetch_nav_for_scheme(scheme_code: int) -> Optional[dict]:
    """Call MFapi.in for latest NAV. Returns {'nav': str, 'date': 'YYYY-MM-DD'} or None on failure."""
    try:
        import urllib.request
        url = f"{NAV_API_BASE}/{scheme_code}/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "MF-FAQ-NAV/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Scheme {scheme_code}: fetch failed — {e}", file=sys.stderr)
        return None
    d = data.get("data")
    if not d or not isinstance(d, list):
        print(f"  Scheme {scheme_code}: no data array", file=sys.stderr)
        return None
    # Latest is first: API returns the most recent published NAV. Date is from AMFI/AMC
    # (so it can be yesterday or last business day if today's NAV not yet published or if market was closed).
    first = d[0]
    nav_str = first.get("nav")
    date_str = first.get("date")  # DD-MM-YYYY from API
    if not nav_str:
        return None
    try:
        nav_float = float(nav_str)
    except (TypeError, ValueError):
        return None
    # Normalize date to YYYY-MM-DD
    as_of = date_str
    if date_str and len(date_str) == 10 and date_str[2] == "-":
        parts = date_str.split("-")
        if len(parts) == 3:
            as_of = f"{parts[2]}-{parts[1]}-{parts[0]}"
    return {"nav": nav_str, "nav_float": nav_float, "date": as_of or date_str}


def run():
    if not FUNDS_JSON.exists():
        print("funds.json not found. Run Phase 1 scraper and extract_structured first.", file=sys.stderr)
        sys.exit(1)
    with open(FUNDS_JSON, "r", encoding="utf-8") as f:
        funds = json.load(f)
    if not isinstance(funds, list):
        print("funds.json must be a JSON array.", file=sys.stderr)
        sys.exit(1)
    name_to_index = {f.get("fund_name"): i for i, f in enumerate(funds) if f.get("fund_name")}
    updated = 0
    for fund_name, scheme_code in NAV_SCHEME_CODES.items():
        idx = name_to_index.get(fund_name)
        if idx is None:
            print(f"  Skip {fund_name}: not in funds.json", file=sys.stderr)
            continue
        rec = fetch_nav_for_scheme(scheme_code)
        if not rec:
            continue
        nav_val = rec["nav_float"]
        nav_date = rec.get("date", "")
        try:
            dt = datetime.strptime(nav_date, "%Y-%m-%d")
            display_date = dt.strftime("%d %b %Y")
        except Exception:
            display_date = nav_date
        funds[idx]["nav"] = {
            "value": nav_val,
            "date": nav_date,
            "display": f"Rs. {nav_val:.4f} (as of {display_date})",
        }
        scheme_page = FUND_SCHEME_PAGE_URLS.get(fund_name, "")
        if scheme_page:
            funds[idx]["scheme_page_url"] = scheme_page
        updated += 1
        print(f"  {fund_name}: Rs. {nav_val:.4f} ({nav_date})")
    with open(FUNDS_JSON, "w", encoding="utf-8") as f:
        json.dump(funds, f, indent=2, ensure_ascii=False)
    print(f"Updated NAV for {updated} schemes in {FUNDS_JSON}")
    print("(NAV date is from MFapi.in — latest published by AMC; may be last business day if market was closed or today's NAV not yet published.)")


if __name__ == "__main__":
    run()
