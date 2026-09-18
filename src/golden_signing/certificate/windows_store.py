"""Windows certificate store listing — certutil with fully hidden console."""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from golden_signing.signing.contracts import CertificateInfo

__all__ = [
    "StoreCertificate",
    "DENY_SUBJECT_MARKERS",
    "NON_SIGNING_EKU_ONLY",
    "SIGNING_EKU_HINTS",
    "certificate_is_valid_at",
    "certificate_is_signing_capable",
    "filter_certificates_valid_at",
    "filter_signing_capable_certificates",
    "list_windows_my_certificates",
]

NON_SIGNING_EKU_ONLY = frozenset(
    {
        "1.3.6.1.5.5.7.3.1",
        "1.3.6.1.5.5.7.3.2",
        "1.3.6.1.5.5.7.3.4",
        "1.3.6.1.5.5.7.3.5",
        "1.3.6.1.5.5.7.3.6",
        "1.3.6.1.5.5.7.3.7",
        "1.3.6.1.5.5.7.3.8",
        "1.3.6.1.5.5.7.3.9",
    }
)

SIGNING_EKU_HINTS = frozenset(
    {
        "1.3.6.1.5.5.7.3.3",
        "2.5.29.37.0",
        "1.3.6.1.4.1.311.10.3.12",
        "1.3.6.1.4.1.311.10.3.1",
    }
)

DENY_SUBJECT_MARKERS = (
    "your phone",
    "microsoft account",
    "microsoft windows",
    "windows hello",
    "microsoft security",
    "adobe trust",
    "localhost",
)

_CREATE_NO_WINDOW = 0x08000000


def _hidden_startupinfo() -> Any:
    if not sys.platform.startswith("win"):
        return None
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        return si
    except Exception:  # noqa: BLE001
        return None


def _run_hidden(cmd: list[str], timeout: float = 20.0) -> str:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "check": False,
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = _CREATE_NO_WINDOW
        si = _hidden_startupinfo()
        if si is not None:
            kwargs["startupinfo"] = si
    try:
        proc = subprocess.run(cmd, **kwargs)  # noqa: S603
    except Exception:  # noqa: BLE001
        return ""
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


@dataclass
class StoreCertificate:
    subject: str
    issuer: str
    serial: str
    fingerprint_sha256: str
    not_valid_before: str
    not_valid_after: str
    has_private_key: bool
    store: str
    der: bytes
    eku_oids: tuple[str, ...] = ()
    key_usage_digital_signature: bool | None = None

    @property
    def backend(self) -> str:
        return "windows_store"


def certificate_is_signing_capable(cert: Any) -> bool:
    subject = str(getattr(cert, "subject", "") or "")
    subject_l = subject.lower()
    issuer = str(getattr(cert, "issuer", "") or "").lower()
    if any(m in subject_l or m in issuer for m in DENY_SUBJECT_MARKERS):
        return False
    backend = str(getattr(cert, "backend", "") or "")
    has_pk = getattr(cert, "has_private_key", None)
    if backend == "windows_store" and has_pk is False:
        return False
    if backend == "windows_store" and has_pk is None:
        return False
    eku = tuple(getattr(cert, "eku_oids", ()) or ())
    ds = getattr(cert, "key_usage_digital_signature", None)
    if ds is True:
        return True
    if eku:
        if any(oid in SIGNING_EKU_HINTS for oid in eku):
            return True
        if any(oid not in NON_SIGNING_EKU_ONLY for oid in eku):
            return not all(oid in NON_SIGNING_EKU_ONLY for oid in eku)
        return False
    return backend != "windows_store" or bool(has_pk)


def filter_signing_capable_certificates(certs: list[Any]) -> list[Any]:
    return [c for c in certs if certificate_is_signing_capable(c)]


def _cert_meta(der: bytes) -> tuple[Any, ...]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.x509.oid import ExtensionOID

    cert = x509.load_der_x509_certificate(der)
    eku_oids: tuple[str, ...] = ()
    try:
        ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
        eku_oids = tuple(oid.dotted_string for oid in ext.value)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        eku_oids = ()
    ds: bool | None = None
    try:
        ku = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
        ds = bool(getattr(ku.value, "digital_signature", False))
    except Exception:  # noqa: BLE001
        ds = None
    return (
        eku_oids,
        ds,
        cert.subject.rfc4514_string(),
        cert.issuer.rfc4514_string(),
        format(cert.serial_number, "X"),
        cert.not_valid_before_utc.isoformat(),
        cert.not_valid_after_utc.isoformat(),
        cert.fingerprint(hashes.SHA256()).hex(),
    )


def _parse_certutil_text(text: str) -> list[bytes]:
    """Extract DER blobs (hex dumps) from certutil -store output."""
    ders: list[bytes] = []
    current_hex: list[str] = []

    def _flush() -> None:
        nonlocal current_hex
        if not current_hex:
            return
        joined = "".join(current_hex)
        if len(joined) >= 40 and len(joined) % 2 == 0:
            try:
                der = bytes.fromhex(joined)
                if len(der) > 32:
                    ders.append(der)
            except ValueError:
                pass
        current_hex = []

    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        low = raw.lower()
        if low.startswith("serial number") or low.startswith("subject"):
            # new cert block often starts here — flush previous dump only on serial
            if low.startswith("serial number"):
                _flush()
            continue
        # hex lines from certutil: groups of hex pairs
        hex_part = re.sub(r"[^0-9A-Fa-f]", "", raw)
        # certutil hex dump lines typically have many hex chars and some spaces
        if len(raw) >= 20 and re.search(r"[0-9A-Fa-f]{8,}", raw) and " " in raw:
            # remove offsets like "0000  " at start
            body = re.sub(r"^[0-9A-Fa-f]{2,8}\s+", "", raw)
            hs = re.sub(r"[^0-9A-Fa-f]", "", body)
            if len(hs) >= 16:
                current_hex.append(hs)
        elif re.fullmatch(r"[0-9A-Fa-f\s]+", raw) and len(hex_part) >= 16:
            current_hex.append(hex_part)
    _flush()
    return ders


def _parse_certutil_metadata(text: str) -> list[StoreCertificate]:
    """Parse certutil -store -user My metadata blocks (no DER hex on many systems)."""
    blocks = re.split(r"={3,}\s*Certificate\s+\d+\s*={3,}", text)
    out: list[StoreCertificate] = []
    for block in blocks[1:] if len(blocks) > 1 else []:
        def field(label: str) -> str:
            m = re.search(rf"{label}:\s*(.+)", block, re.I)
            return m.group(1).strip() if m else ""

        serial = field("Serial Number")
        subject = field("Subject")
        issuer = field("Issuer")
        not_before = field("NotBefore")
        not_after = field("NotAfter")
        if not serial and not subject:
            continue
        has_pk = bool(
            re.search(r"Key Container\s*=", block)
            or re.search(r"Provider\s*=", block)
            or re.search(r"Private key", block, re.I)
        )
        # Normalize dates to ISO if possible
        def _iso(raw: str) -> str:
            raw = raw.strip()
            for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M"):
                try:
                    # Vietnamese AM/PM may be CH/SA
                    t = raw.replace(" CH", " PM").replace(" SA", " AM")
                    return datetime.strptime(t, fmt).replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    continue
            return raw

        fp = hashlib.sha256(f"{serial}|{subject}|{not_after}".encode()).hexdigest()
        out.append(
            StoreCertificate(
                subject=subject,
                issuer=issuer,
                serial=serial.replace(" ", ""),
                fingerprint_sha256=fp,
                not_valid_before=_iso(not_before),
                not_valid_after=_iso(not_after),
                has_private_key=has_pk,
                store="My",
                der=b"",
                eku_oids=(),
                key_usage_digital_signature=None,
            )
        )
    return out


def _list_my_via_certutil() -> list[StoreCertificate]:
    text = _run_hidden(["certutil.exe", "-store", "-user", "My"], timeout=25.0)
    if not text.strip():
        return []
    ders = _parse_certutil_text(text)
    out: list[StoreCertificate] = []
    for der in ders:
        try:
            (
                eku,
                ds,
                subject,
                issuer,
                serial,
                nb,
                na,
                fp,
            ) = _cert_meta(der)
        except Exception:  # noqa: BLE001
            continue
        out.append(
            StoreCertificate(
                subject=subject,
                issuer=issuer,
                serial=serial,
                fingerprint_sha256=fp,
                not_valid_before=nb,
                not_valid_after=na,
                has_private_key=True,
                store="My",
                der=der,
                eku_oids=eku,
                key_usage_digital_signature=ds,
            )
        )
    if not out:
        out = _parse_certutil_metadata(text)
    return out


def list_windows_my_certificates() -> list[CertificateInfo]:
    try:
        found = _list_my_via_certutil()
    except Exception:  # noqa: BLE001
        found = []
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
                token_label="Windows cert store"
                + (" (có private key)" if c.has_private_key else " (không private key)"),
                backend="windows_store",
                has_private_key=c.has_private_key,
                eku_oids=c.eku_oids,
                key_usage_digital_signature=c.key_usage_digital_signature,
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
    return [c for c in certs if certificate_is_valid_at(c, at)]
