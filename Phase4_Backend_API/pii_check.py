"""
Phase 4 — PII detection: reject PAN, Aadhaar, account numbers, OTPs, email, phone,
partial account/folio numbers, CIN, and "my folio" / "my number" style patterns.
Return 400 with a generic message; no logging or storage of PII.
"""
import re
from typing import Tuple

# PAN: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
# Aadhaar: 12 digits, optional spaces/dashes
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?-?\s?\d{4}\s?-?\s?\d{4}\b")
# Generic account number: long digit string (e.g. 10+ digits)
ACCOUNT_PATTERN = re.compile(r"\b\d{10,}\b")
# OTP: 4–8 digit codes often mentioned as "OTP" or "one time"
OTP_PATTERN = re.compile(r"\b(?:otp|one\s*time\s*password)\s*[:\s]*\d{4,8}\b", re.IGNORECASE)
# Email
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
# Indian phone: 10 digits, optional +91
PHONE_PATTERN = re.compile(r"\b(?:\+91[\s-]*)?[6-9]\d{9}\b")

# Partial account/folio: 6–9 digits after "account", "folio", "account number", "folio number"
PARTIAL_ACCOUNT_PATTERN = re.compile(
    r"\b(?:account|folio|fund\s*folio)\s*(?:number\s*)?[#:=\s]*\d{6,9}\b|\b(?:account\s+number|folio\s+number)\s*[#:=\s]*\d{6,9}\b|\b\d{6,9}\s*(?:account|folio)\b",
    re.IGNORECASE,
)
# CIN (Corporate Identification Number): 21 chars = 1 letter + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits
CIN_PATTERN = re.compile(r"\b[A-Z][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b", re.IGNORECASE)
# Phrases that suggest user may paste folio/account/number — reject to avoid PII
FOLIO_PHRASE_PATTERN = re.compile(
    r"\b(?:my\s+folio|folio\s+number|my\s+account\s+number|my\s+number|my\s+fund\s+number|give\s+me\s+my\s+folio)\b",
    re.IGNORECASE,
)


def contains_pii(text: str) -> Tuple[bool, str]:
    """
    Returns (True, reason) if text appears to contain PII; else (False, "").
    Used to reject request before any processing or logging.
    """
    if not text or not isinstance(text, str):
        return (False, "")
    t = text.strip()
    if PAN_PATTERN.search(t):
        return (True, "personal information")
    if AADHAAR_PATTERN.search(t):
        return (True, "personal information")
    if ACCOUNT_PATTERN.search(t):
        return (True, "personal information")
    if OTP_PATTERN.search(t):
        return (True, "personal information")
    if EMAIL_PATTERN.search(t):
        return (True, "personal information")
    if PHONE_PATTERN.search(t):
        return (True, "personal information")
    if PARTIAL_ACCOUNT_PATTERN.search(t):
        return (True, "personal information")
    if CIN_PATTERN.search(t):
        return (True, "personal information")
    if FOLIO_PHRASE_PATTERN.search(t):
        return (True, "personal information")
    return (False, "")
