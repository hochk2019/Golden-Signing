"""Assemble displayable certificates for UI (PKCS#11 + Windows store, valid-only)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from golden_signing.certificate.windows_store import (
    filter_certificates_valid_at,
    list_windows_my_certificates,
)
from golden_signing.signing.contracts import CertificateInfo
from golden_signing.signing.token_pdf_signer import TokenPdfSigner
from golden_signing.token.discovery import discover_pkcs11_libraries

__all__ = ["collect_display_certificates", "merge_unique_certificates"]


def merge_unique_certificates(*groups: list[CertificateInfo]) -> list[CertificateInfo]:
    seen: set[str] = set()
    out: list[CertificateInfo] = []
    for group in groups:
        for cert in group:
            key = (cert.fingerprint_sha256 or "").lower()
            if not key:
                key = f"{cert.serial}|{cert.subject}|{cert.backend}"
            if key in seen:
                continue
            seen.add(key)
            out.append(cert)
    return out


def collect_display_certificates(
    *,
    at: datetime | None = None,
    dlls: list[Path] | None = None,
) -> list[CertificateInfo]:
    """Certificates to show in Golden Sign UI.

    - Enumerate PKCS#11 tokens (existing path).
    - Also list Windows Current User\\My (certmgr Personal) so CSP/store certs appear
      even when PKCS#11 middleware is missing or not discovered.
    - Filter to certificates still valid at signing time ``at`` (default now UTC).
    """
    when = at or datetime.now(timezone.utc)
    pkcs: list[CertificateInfo] = []
    libs = dlls if dlls is not None else discover_pkcs11_libraries()
    for dll in libs:
        try:
            pkcs.extend(TokenPdfSigner.list_certificates(dll))
        except Exception:  # noqa: BLE001
            continue
    store: list[CertificateInfo] = []
    try:
        store = list_windows_my_certificates()
    except Exception:  # noqa: BLE001
        store = []
    merged = merge_unique_certificates(pkcs, store)
    return filter_certificates_valid_at(merged, when)
