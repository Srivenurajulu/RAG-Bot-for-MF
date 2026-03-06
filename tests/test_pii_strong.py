#!/usr/bin/env python3
"""
Test stronger PII detection: PAN, Aadhaar, partial account/folio, CIN, "my folio" phrases.
Runs in-process (no server). Run: .venv/bin/python3 tests/test_pii_strong.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Phase4_Backend_API.pii_check import contains_pii


def test_pii_rejected():
    """Queries that must be rejected as PII."""
    must_reject = [
        ("My PAN is ABCDE1234F", "PAN"),
        ("1234 5678 9012", "Aadhaar"),
        ("12345678901234", "account 10+ digits"),
        ("my folio number", "my folio"),
        ("What is my folio number?", "folio phrase"),
        ("Give me my folio", "give me my folio"),
        ("folio 12345678", "partial account folio"),
        ("account number 987654321", "partial account"),
        ("L71990GJ1994PLC019050", "CIN"),
        ("user@example.com", "email"),
        ("9876543210", "phone"),
    ]
    for text, label in must_reject:
        has_pii, reason = contains_pii(text)
        assert has_pii, f"Expected PII reject for: {label!r} in {text!r}"
    print(f"[PASS] {len(must_reject)} PII patterns rejected.")


def test_pii_allowed():
    """Queries that must NOT be rejected (no PII)."""
    must_allow = [
        "What is the expense ratio of Large Cap Fund?",
        "Minimum SIP for ELSS?",
        "How can I download my capital gains statement?",
        "List of funds",
        "my fund performance",
    ]
    for text in must_allow:
        has_pii, _ = contains_pii(text)
        assert not has_pii, f"Expected no PII for: {text!r}"
    print(f"[PASS] {len(must_allow)} non-PII queries allowed.")


def main():
    test_pii_rejected()
    test_pii_allowed()
    print("All PII tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
