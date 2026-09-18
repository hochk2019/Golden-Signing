"""Assemble displayable certificates for UI (PKCS#11 + Windows store, valid-only)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from golden_signing.certificate.windows_store import (
    certificate_is_signing_capable,
    filter_certificates_valid_at,
    list_windows_my_certificates,
)
from golden_signing.signing.contracts import CertificateInfo
from golden_signing.signing.token_pdf_signer import TokenPdfSigner
from golden_signing.token.discovery import discover_pkcs11_libraries

__all__ = [
    "clear_certificate_cache",
    "collect_display_certificates",
    "merge_unique_certificates",
]

# Avoid spawning PowerShell / reloading PKCS#11 on every UI action
_CACHE: list[CertificateInfo] | None = None
_CACHE_TS: float = 0.0
_CACHE_TTL_S = 20.0


def clear_certificate_cache() -> None:
    global _CACHE, _CACHE_TS  # noqa: PLW0603
    _CACHE = None
    _CACHE_TS = 0.0


def _as_token_cert(cert: CertificateInfo) -> CertificateInfo:
    """PKCS#11 objects hold private key material on the token."""
    if cert.backend == "windows_store" or cert.has_private_key is not None:
        return cert
    return CertificateInfo(
        subject=cert.subject,
        issuer=cert.issuer,
        serial=cert.serial,
        fingerprint_sha256=cert.fingerprint_sha256,
        not_valid_before=cert.not_valid_before,
        not_valid_after=cert.not_valid_after,
        key_algorithm=cert.key_algorithm,
        key_size=cert.key_size,
        token_label=cert.token_label,
        backend=cert.backend or "pkcs11",
        has_private_key=True,
        eku_oids=cert.eku_oids,
        key_usage_digital_signature=cert.key_usage_digital_signature,
    )


def merge_unique_certificates(*groups: list[CertificateInfo]) -> list[CertificateInfo]:
    seen: set[str] = set()
    out: list[CertificateInfo] = []
    for group in groups:
        for cert in group:
            keys = {
                (cert.fingerprint_sha256 or "").lower(),
                str(cert.serial or "").lower().lstrip("0"),
            }
            keys.discard("")
            if not keys:
                keys = {f"{cert.subject}|{cert.backend}"}
            if keys & seen:
                continue
            seen |= keys
            out.append(cert)
    return out


def collect_display_certificates(
    *,
    at: datetime | None = None,
    dlls: list[Path] | None = None,
    use_cache: bool = True,
) -> list[CertificateInfo]:
    """Certificates to show in Golden Sign UI.

    - Enumerate PKCS#11 tokens + Windows Current User\\My.
    - Filter: valid at signing time + capable of signing (private key / signing EKU).
    - Cached briefly so adding files / opening dialogs does not flash PowerShell.
    """
    global _CACHE, _CACHE_TS  # noqa: PLW0603

    when = at or datetime.now(timezone.utc)
    now = time.monotonic()
    if (
        use_cache
        and dlls is None
        and _CACHE is not None
        and (now - _CACHE_TS) < _CACHE_TTL_S
    ):
        return list(filter_certificates_valid_at(_CACHE, when))

    pkcs: list[CertificateInfo] = []
    libs = dlls if dlls is not None else discover_pkcs11_libraries()
    for dll in libs:
        try:
            pkcs.extend(_as_token_cert(c) for c in TokenPdfSigner.list_certificates(dll))
        except Exception:  # noqa: BLE001
            continue
    store: list[CertificateInfo] = []
    try:
        store = list_windows_my_certificates()
    except Exception:  # noqa: BLE001
        store = []
    merged = merge_unique_certificates(pkcs, store)
    valid = filter_certificates_valid_at(merged, when)
    signing = [c for c in valid if certificate_is_signing_capable(c)]
    if dlls is None:
        _CACHE = list(merged)
        _CACHE_TS = now
    return signing
