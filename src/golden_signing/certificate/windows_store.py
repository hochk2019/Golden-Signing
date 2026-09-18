"""Windows certificate store listing + validity helpers (discovery only)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from golden_signing.signing.contracts import CertificateInfo

__all__ = [
    "StoreCertificate",
    "list_windows_my_certificates",
    "certificate_is_valid_at",
    "filter_certificates_valid_at",
]


@dataclass
class StoreCertificate:
    """Certificate from Windows CurrentUser/LocalMachine My store."""

    subject: str
    issuer: str
    serial: str
    fingerprint_sha256: str
    not_valid_before: str
    not_valid_after: str
    has_private_key: bool
    store: str
    der: bytes

    @property
    def backend(self) -> str:
        return "windows_store"


def _parse_certutil_store(store: str, user: bool) -> list[StoreCertificate]:
    """Parse `certutil -store` output; tolerant of Vietnamese/English Windows."""
    import subprocess

    cmd = ["certutil", "-store"]
    if user:
        cmd += ["-user"]
    cmd += ["My"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return []
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return _parse_certutil_text(text, store_name=store)


def _parse_certutil_text(text: str, *, store_name: str) -> list[StoreCertificate]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    out: list[StoreCertificate] = []
    # certutil blocks often: "Serial Number: ..", "Subject: ..", "Issuer: ..", "NotBefore: ..", "NotAfter: ..", "Hash", "Key Container", hex dump
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        raw = line.strip()
        low = raw.lower()
        if low.startswith("serial number") or low.startswith("serial"):
            if current.get("der_hex") or current.get("subject"):
                blocks.append(current)
                current = {}
            current["serial"] = raw.split(":", 1)[-1].strip() if ":" in raw else raw
        elif low.startswith("subject"):
            current["subject"] = raw.split(":", 1)[-1].strip() if ":" in raw else ""
        elif low.startswith("issuer"):
            current["issuer"] = raw.split(":", 1)[-1].strip() if ":" in raw else ""
        elif low.startswith("notbefore") or low.startswith("not before"):
            current["not_before"] = raw.split(":", 1)[-1].strip() if ":" in raw else ""
        elif low.startswith("notafter") or low.startswith("not after"):
            current["not_after"] = raw.split(":", 1)[-1].strip() if ":" in raw else ""
        elif "private key" in low or "key container" in low or "csp" in low:
            current["has_key"] = "yes" if any(
                x in low for x in ("private key", "key container", "csp")
            ) else current.get("has_key", "")
        # hex dump lines (certutil prints spaced hex)
        hex_line = raw.replace(" ", "")
        if len(hex_line) >= 32 and all(c in "0123456789abcdefABCDEF" for c in hex_line):
            current["der_hex"] = current.get("der_hex", "") + hex_line
    if current:
        blocks.append(current)

    for b in blocks:
        der_hex = b.get("der_hex") or ""
        if len(der_hex) < 40:
            continue
        try:
            der = bytes.fromhex(der_hex)
            cert = x509.load_der_x509_certificate(der)
        except Exception:  # noqa: BLE001
            continue
        out.append(
            StoreCertificate(
                subject=cert.subject.rfc4514_string(),
                issuer=cert.issuer.rfc4514_string(),
                serial=format(cert.serial_number, "X"),
                fingerprint_sha256=cert.fingerprint(hashes.SHA256()).hex(),
                not_valid_before=cert.not_valid_before_utc.isoformat(),
                not_valid_after=cert.not_valid_after_utc.isoformat(),
                has_private_key=bool(b.get("has_key")),
                store=store_name,
                der=der,
            )
        )
    return out


def _parse_certutil_store_via_powershell(store_path: str) -> list[StoreCertificate]:
    """Enumerate store certs with .NET X509Store (more reliable than certutil text)."""
    import json
    import subprocess

    script = f"""
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store('{store_path}','CurrentUser')
$store.Open('ReadOnly')
$list = @()
foreach ($c in $store.Certificates) {{
  $list += @{{
    subject = $c.Subject
    issuer = $c.Issuer
    serial = $c.SerialNumber
    not_before = $c.NotBefore.ToUniversalTime().ToString('o')
    not_after = $c.NotAfter.ToUniversalTime().ToString('o')
    has_private_key = [bool]$c.HasPrivateKey
    der_b64 = [Convert]::ToBase64String($c.RawData)
  }}
}}
$store.Close()
ConvertTo-Json -InputObject $list -Compress
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return []
    payload = (proc.stdout or "").strip()
    if not payload:
        return []
    try:
        items = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if isinstance(items, dict):
        items = [items]
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    out: list[StoreCertificate] = []
    for item in items:
        try:
            der = __import__("base64").b64decode(item.get("der_b64") or "")
            cert = x509.load_der_x509_certificate(der)
        except Exception:  # noqa: BLE001
            continue
        out.append(
            StoreCertificate(
                subject=cert.subject.rfc4514_string(),
                issuer=cert.issuer.rfc4514_string(),
                serial=format(cert.serial_number, "X"),
                fingerprint_sha256=cert.fingerprint(hashes.SHA256()).hex(),
                not_valid_before=cert.not_valid_before_utc.isoformat(),
                not_valid_after=cert.not_valid_after_utc.isoformat(),
                has_private_key=bool(item.get("has_private_key")),
                store=store_path,
                der=der,
            )
        )
    return out


def list_windows_my_certificates() -> list[CertificateInfo]:
    """List Personal (My) certificates visible to the current Windows user."""
    found: list[StoreCertificate] = []
    found.extend(_parse_certutil_store_via_powershell("My"))
    if not found:
        found.extend(_parse_certutil_store("My", user=True))
    out: list[CertificateInfo] = []
    seen: set[str] = set()
    for c in found:
        fp = c.fingerprint_sha256
        if fp in seen:
            continue
        seen.add(fp)
        out.append(
            CertificateInfo(
                subject=c.subject,
                issuer=c.issuer,
                serial=c.serial.lower(),
                fingerprint_sha256=fp,
                not_valid_before=c.not_valid_before,
                not_valid_after=c.not_valid_after,
                key_algorithm="",
                key_size=None,
                token_label="Windows cert store" + (" (có private key)" if c.has_private_key else ""),
                backend="windows_store",
            )
        )
    return out


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    # asn1crypto / cryptography string forms
    for fmt in (
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%d%H%M%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(text.replace("Z", "+0000") if fmt.endswith("%z") else text, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def certificate_is_valid_at(cert: Any, at: datetime | None = None) -> bool:
    """True when cert validity window covers `at` (default: now, UTC)."""
    when = at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    nb = _parse_iso_datetime(getattr(cert, "not_valid_before", None))
    na = _parse_iso_datetime(getattr(cert, "not_valid_after", None))
    if nb is not None and when < nb:
        return False
    if na is not None and when > na:
        return False
    return True


def filter_certificates_valid_at(certs: list[Any], at: datetime | None = None) -> list[Any]:
    """Keep only certificates valid at signing time `at`."""
    return [c for c in certs if certificate_is_valid_at(c, at)]
