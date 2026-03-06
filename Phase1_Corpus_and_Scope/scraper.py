#!/usr/bin/env python3
"""
Phase 1 — Scraper for MF FAQ corpus.
Reads sources.csv, visits each URL (HTML or PDF), extracts main text,
saves to data/raw/ with metadata and builds data/manifest.json.
Uses requests by default (no browser). Set USE_PLAYWRIGHT=1 to use Playwright.
Public pages only; polite delays; no auth; no PII.
"""

import csv
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from pypdf import PdfReader

# Paths
PHASE_DIR = Path(__file__).resolve().parent
SOURCES_CSV = PHASE_DIR / "sources.csv"
DATA_DIR = PHASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
MANIFEST_PATH = DATA_DIR / "manifest.json"

# Scraping config
DELAY_BETWEEN_REQUESTS_SEC = 1.5
PAGE_WAIT_MS = 8000
USER_AGENT = "Mozilla/5.0 (compatible; MF-FAQ-Scraper/1.0; facts-only; no auth)"


def slug_from_url(url: str, scheme_name: str, page_type: str) -> str:
    """Generate a safe filename slug from URL and metadata."""
    # Prefer readable slug: scheme + page_type, then hash of URL for uniqueness
    safe_scheme = re.sub(r"[^\w\s-]", "", scheme_name)[:40].strip().replace(" ", "_")
    safe_scheme = safe_scheme or "scheme"
    safe_type = page_type or "page"
    parsed = urlparse(url)
    path = (parsed.path or "").strip("/").replace("/", "_")
    if len(path) > 60:
        path = path[:60]
    unique = str(hash(url) % (10**8))
    return f"{safe_scheme}_{safe_type}_{unique}".lower()


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes. Returns empty string on failure."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            try:
                t = page.extract_text()
                if t:
                    parts.append(t)
            except Exception:
                continue
        return "\n\n".join(parts).strip() if parts else ""
    except Exception:
        return ""


def extract_main_text_from_html(html: str, url: str) -> str:
    """
    Extract main content from HTML: strip scripts, styles, then tags; collapse whitespace.
    """
    raw = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    raw = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", raw, flags=re.I)
    raw = re.sub(r"<nav[^>]*>[\s\S]*?</nav>", " ", raw, flags=re.I)
    raw = re.sub(r"<footer[^>]*>[\s\S]*?</footer>", " ", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:500_000]  # cap size


def scrape_url_with_requests(
    url: str,
    scheme_name: str,
    page_type: str,
    amc: str,
) -> Tuple[str, Optional[Path], str]:
    """
    Scrape one URL using requests (no browser). PDF: fetch bytes + pypdf. HTML: fetch text + strip tags.
    Returns (extracted_text, path_to_saved_file or None, scrape_date).
    """
    import requests
    slug = slug_from_url(url, scheme_name, page_type)
    is_pdf = url.lower().rstrip("/").endswith(".pdf")
    scrape_date = time.strftime("%Y-%m-%d", time.gmtime())
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            allow_redirects=True,
        )
        if not resp.ok:
            return f"[Failed to fetch: HTTP {resp.status_code}]", None, scrape_date
        if is_pdf:
            text = extract_text_from_pdf_bytes(resp.content)
            if not text:
                text = "[PDF text extraction returned no text; file may be image-based or protected.]"
        else:
            resp.encoding = resp.apparent_encoding or "utf-8"
            text = extract_main_text_from_html(resp.text, url)
            if not text or len(text.strip()) < 50:
                text = "[Page content too short or could not be extracted.]"
    except Exception as e:
        text = f"[Scrape error: {type(e).__name__}: {str(e)[:200]}]"
        return text, None, scrape_date
    if not text:
        return text, None, scrape_date
    meta = {
        "url": url,
        "scrape_date": scrape_date,
        "page_type": page_type,
        "scheme_name": scheme_name,
        "amc": amc,
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{slug}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        f.write("\n\n---\n\n")
        f.write(text)
    return text, out_path, scrape_date


def scrape_url(
    url: str,
    scheme_name: str,
    page_type: str,
    amc: str,
    playwright_context,
) -> Tuple[str, Optional[Path], str]:
    """
    Scrape one URL. Returns (extracted_text, path_to_saved_file or None, scrape_date).
    Uses Playwright for both HTML and PDF (PDF is fetched then parsed with pypdf).
    """
    slug = slug_from_url(url, scheme_name, page_type)
    is_pdf = url.lower().rstrip("/").endswith(".pdf")

    try:
        if is_pdf:
            # Fetch PDF via Playwright request
            response = playwright_context.request.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=60_000,
            )
            if not response.ok:
                return f"[Failed to fetch PDF: HTTP {response.status}]", None, time.strftime("%Y-%m-%d", time.gmtime())
            pdf_bytes = response.body()
            text = extract_text_from_pdf_bytes(pdf_bytes)
            if not text:
                text = "[PDF text extraction returned no text; file may be image-based or protected.]"
        else:
            page = playwright_context.new_page()
            page.set_extra_http_headers({"User-Agent": USER_AGENT})
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=PAGE_WAIT_MS)
                page.wait_for_timeout(2000)  # allow dynamic content
                html = page.content()
                text = extract_main_text_from_html(html, url)
                if not text or len(text) < 100:
                    # Fallback: body text
                    body = page.query_selector("body")
                    if body:
                        text = body.inner_text()[:500_000]
            finally:
                page.close()
            if not text or len(text.strip()) < 50:
                text = "[Page content too short or could not be extracted.]"
    except Exception as e:
        text = f"[Scrape error: {type(e).__name__}: {str(e)[:200]}]"
        scrape_date = time.strftime("%Y-%m-%d", time.gmtime())
        return text, None, scrape_date

    scrape_date = time.strftime("%Y-%m-%d", time.gmtime())
    if not text:
        return text, None, scrape_date
    meta = {
        "url": url,
        "scrape_date": scrape_date,
        "page_type": page_type,
        "scheme_name": scheme_name,
        "amc": amc,
    }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{slug}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        f.write("\n\n---\n\n")
        f.write(text)
    return text, out_path, scrape_date


def load_sources(csv_path: Path) -> list[dict]:
    """Load source list from CSV."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["url"] = (row.get("url") or "").strip()
            if row["url"]:
                rows.append(row)
    return rows


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    sources = load_sources(SOURCES_CSV)
    if not sources:
        print("No URLs found in sources.csv")
        return

    use_playwright = os.environ.get("USE_PLAYWRIGHT", "").strip().lower() in ("1", "true", "yes")
    manifest = {}

    if use_playwright:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("USE_PLAYWRIGHT=1 but Playwright not installed. Falling back to requests.")
            use_playwright = False
    if not use_playwright:
        # Requests-based scraping (no browser)
        print("Using requests (no browser). Set USE_PLAYWRIGHT=1 to use Playwright for JS-heavy pages.")
        for i, row in enumerate(sources):
            url = row["url"]
            scheme_name = row.get("scheme_name", "")
            page_type = row.get("page_type", "")
            amc = row.get("amc", "")
            print(f"[{i+1}/{len(sources)}] {page_type}: {scheme_name[:50]}...")
            _, path, scrape_date = scrape_url_with_requests(url, scheme_name, page_type, amc)
            if path:
                manifest[url] = {
                    "file_path": str(path.relative_to(PHASE_DIR)),
                    "scrape_date": scrape_date,
                    "scheme_name": scheme_name,
                    "page_type": page_type,
                    "amc": amc,
                }
            time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=False,
            )
            try:
                for i, row in enumerate(sources):
                    url = row["url"]
                    scheme_name = row.get("scheme_name", "")
                    page_type = row.get("page_type", "")
                    amc = row.get("amc", "")
                    print(f"[{i+1}/{len(sources)}] {page_type}: {scheme_name[:50]}...")
                    _, path, scrape_date = scrape_url(url, scheme_name, page_type, amc, context)
                    if path:
                        manifest[url] = {
                            "file_path": str(path.relative_to(PHASE_DIR)),
                            "scrape_date": scrape_date,
                            "scheme_name": scheme_name,
                            "page_type": page_type,
                            "amc": amc,
                        }
                    time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
            finally:
                context.close()
                browser.close()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Manifest written to {MANIFEST_PATH} ({len(manifest)} entries).")
    print(f"Raw files in {RAW_DIR}.")


if __name__ == "__main__":
    main()
