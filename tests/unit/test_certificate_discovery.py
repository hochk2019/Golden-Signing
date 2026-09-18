"""Certificate discovery / validity filter unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from golden_signing.certificate.catalog import merge_unique_certificates
from golden_signing.certificate.windows_store import (
    certificate_is_valid_at,
    filter_certificates_valid_at,
)
from golden_signing.signing.contracts import CertificateInfo
from golden_signing.token.discovery import ENV_PKCS11, discover_pkcs11_libraries


def _cert(
    subject: str,
    nb: str,
    na: str,
    *,
    serial: str = "ABC",
    backend: str = "pkcs11",
    fp: str = "",
) -> CertificateInfo:
    return CertificateInfo(
        subject=subject,
        issuer="CN=Test CA",
        serial=serial,
        fingerprint_sha256=fp or f"fp-{subject}",
        not_valid_before=nb,
        not_valid_after=na,
        key_algorithm="RSA",
        key_size=2048,
        token_label="TEST",
        backend=backend,
    )


def test_certificate_valid_at_window() -> None:
    cert = _cert("CN=Ok", "2024-01-01 00:00:00", "2027-01-01 00:00:00")
    assert certificate_is_valid_at(cert, datetime(2026, 9, 18, tzinfo=timezone.utc))
    assert not certificate_is_valid_at(cert, datetime(2023, 1, 1, tzinfo=timezone.utc))
    assert not certificate_is_valid_at(cert, datetime(2028, 1, 1, tzinfo=timezone.utc))


def test_filter_certificates_valid_at_signing_date() -> None:
    valid = _cert("CN=Valid", "2025-01-01", "2028-01-01", serial="1")
    expired = _cert("CN=Expired", "2020-01-01", "2022-01-01", serial="2")
    future = _cert("CN=Future", "2030-01-01", "2031-01-01", serial="3")
    at = datetime(2026, 9, 18, tzinfo=timezone.utc)
    kept = filter_certificates_valid_at([valid, expired, future], at)
    assert [c.serial for c in kept] == ["1"]


def test_merge_unique_prefers_first() -> None:
    a = _cert("CN=A", "2024-01-01", "2028-01-01", serial="1", backend="pkcs11", fp="same")
    b = _cert("CN=B", "2024-01-01", "2028-01-01", serial="1", backend="windows_store", fp="same")
    merged = merge_unique_certificates([a], [b])
    assert len(merged) == 1
    assert merged[0].backend == "pkcs11"


def test_discovery_reads_env_path(tmp_path: Path) -> None:
    dll = tmp_path / "fake-pkcs11.dll"
    dll.write_bytes(b"MZ")
    found = discover_pkcs11_libraries(env={ENV_PKCS11: str(dll)})
    assert dll in found or dll.resolve() in found


def test_discovery_includes_ca2_dll_name_in_defaults() -> None:
    # Source of truth: default System32 candidate list mentions CA2 middleware
    import golden_signing.token.discovery as disc

    assert "CA2_csp11.dll" in disc._SYSTEM32_NAMES
    assert any("csp11" in n.lower() for n in disc._SYSTEM32_NAMES)
