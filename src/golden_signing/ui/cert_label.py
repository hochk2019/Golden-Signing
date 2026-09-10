"""Certificate display helpers (compact labels)."""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "cert_detail_lines",
    "common_name_from_subject",
    "mst_from_subject",
    "short_cert_label",
]

_MST_PATTERNS = (
    re.compile(r"MST[:\s]*([0-9]{8,14})", re.IGNORECASE),
    re.compile(r"Mã số thuế[:\s]*([0-9]{8,14})", re.IGNORECASE),
    re.compile(r"OID\.0\.9\.2342\.19200300\.100\.1\.1=([0-9]{8,14})", re.IGNORECASE),
)

_CN_PATTERNS = (
    re.compile(r"CN=([^,/]+)", re.IGNORECASE),
    re.compile(r"Common Name:\s*([^,]+)", re.IGNORECASE),
)


def common_name_from_subject(subject: str) -> str:
    """Extract CN / Common Name from human_friendly or DN subject."""
    s = " ".join(str(subject or "").split())
    for pat in _CN_PATTERNS:
        m = pat.search(s)
        if m:
            return m.group(1).strip()
    # Fallback: first segment that looks like a company name
    parts = [p.strip() for p in s.split(",") if p.strip()]
    for p in parts:
        if p.upper().startswith("USER ID"):
            continue
        if p.upper().startswith("SERIALNUMBER") or p.upper().startswith("SERIAL"):
            continue
        # drop key: prefix
        if ":" in p:
            val = p.split(":", 1)[1].strip()
            if val and not val.upper().startswith("MST"):
                return val
        else:
            return p
    return s[:40] if s else "Không rõ"


def mst_from_subject(subject: str) -> str | None:
    """Extract MST / tax code from subject if present."""
    s = " ".join(str(subject or "").split())
    for pat in _MST_PATTERNS:
        m = pat.search(s)
        if m:
            return m.group(1).strip()
    return None


def short_cert_label(cert: Any) -> str:
    cn = common_name_from_subject(getattr(cert, "subject", "") or "")
    expiry_full = str(getattr(cert, "not_valid_after", "") or "")
    expiry = expiry_full[:10] if expiry_full else "?"
    token = getattr(cert, "token_label", None) or ""
    base = cn if len(cn) <= 36 else cn[:35] + "…"
    if token:
        return f"{base} · {token} · {expiry}"
    return f"{base} · {expiry}"


def cert_detail_lines(cert: Any) -> str:
    cn = common_name_from_subject(getattr(cert, "subject", "") or "")
    issuer = " ".join(str(getattr(cert, "issuer", "") or "").split())
    expiry = str(getattr(cert, "not_valid_after", ""))[:10]
    serial = getattr(cert, "serial", "") or ""
    return (
        f"Chủ thể: {cn}\n"
        f"Issuer: {issuer[:56]}\n"
        f"Hết hạn: {expiry}\n"
        f"Serial: {serial[:24]}"
    )
