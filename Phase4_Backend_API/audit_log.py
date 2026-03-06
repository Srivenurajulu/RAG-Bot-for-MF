"""
Phase 4 — Audit trail: log query type (path), timestamp, request_id, latency. No query text or PII.
For compliance and debugging. One JSON line per request.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_AUDIT_DIR = Path(__file__).resolve().parent / "logs"
_AUDIT_FILE = _AUDIT_DIR / "audit.log"


def _ensure_dir():
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def log_request(
    path: str,
    request_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
    method: str = "POST",
    http_path: str = "/chat",
) -> None:
    """
    Append one structured audit line. No PII or query text.
    path: audit_path (e.g. fast_lookup, rag_answer, pii_rejected).
    """
    try:
        _ensure_dir()
        entry = {
            "t": datetime.now(timezone.utc).isoformat(),
            "path": path,
            "method": method,
            "http_path": http_path,
        }
        if request_id is not None:
            entry["request_id"] = request_id
        if latency_ms is not None:
            entry["latency_ms"] = round(latency_ms, 2)
        with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # do not fail the request if logging fails
