"""Certificate discovery / validity / signing-capability unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from golden_signing.certificate.catalog import merge_unique_certificates
from golden_signing.certificate.windows_store import (
    certificate_is_signing_capable,
    certificate_is_valid_at,
    filter_certificates_valid_at,
    filter_signing_capable_certificates,
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
    has_private_key: bool | None = None,
    eku: tuple[str, ...] = (),
    ds: bool | None = None,
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
        has_private_key=has_private_key,
        eku_oids=eku,
        key_usage_digital_signature=ds,
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


def test_hide_store_certs_without_private_key() -> None:
    store_no_pk = _cert(
        "CN=CÔNG TY ABC",
        "2024-01-01",
        "2028-01-01",
        backend="windows_store",
        has_private_key=False,
        eku=("1.3.6.1.4.1.311.10.3.12",),
    )
    assert not certificate_is_signing_capable(store_no_pk)


def test_hide_secure_email_only_store_cert() -> None:
    email_only = _cert(
        "CN=CÔNG TY TNHH HANYANG",
        "2024-01-01",
        "2028-01-01",
        backend="windows_store",
        has_private_key=True,
        eku=("1.3.6.1.5.5.7.3.4",),  # emailProtection only
    )
    assert not certificate_is_signing_capable(email_only)


def test_keep_document_signing_store_cert() -> None:
    doc = _cert(
        "CN=CÔNG TY TNHH JAEYOUNG VINA",
        "2024-01-01",
        "2028-01-01",
        backend="windows_store",
        has_private_key=True,
        eku=("1.3.6.1.4.1.311.10.3.12",),
    )
    assert certificate_is_signing_capable(doc)


def test_hide_microsoft_your_phone_subject() -> None:
    noise = _cert(
        "CN=Microsoft Your Phone",
        "2024-01-01",
        "2028-01-01",
        backend="windows_store",
        has_private_key=True,
        eku=("1.3.6.1.5.5.7.3.2",),
    )
    assert not certificate_is_signing_capable(noise)


def test_keep_pkcs11_token_cert() -> None:
    token = _cert(
        "CN=CÔNG TY TNHH X",
        "2024-01-01",
        "2028-01-01",
        backend="pkcs11",
        has_private_key=True,
    )
    assert certificate_is_signing_capable(token)


def test_filter_signing_capable_list() -> None:
    items = [
        _cert("CN=Good", "2024-01-01", "2028-01-01", backend="pkcs11", has_private_key=True, serial="1"),
        _cert(
            "CN=Email",
            "2024-01-01",
            "2028-01-01",
            backend="windows_store",
            has_private_key=True,
            eku=("1.3.6.1.5.5.7.3.4",),
            serial="2",
        ),
        _cert(
            "CN=NoKey",
            "2024-01-01",
            "2028-01-01",
            backend="windows_store",
            has_private_key=False,
            serial="3",
        ),
    ]
    kept = filter_signing_capable_certificates(items)
    assert [c.serial for c in kept] == ["1"]


def test_digital_signature_key_usage_keeps_store_cert() -> None:
    cert = _cert(
        "CN=CTY",
        "2024-01-01",
        "2028-01-01",
        backend="windows_store",
        has_private_key=True,
        ds=True,
    )
    assert certificate_is_signing_capable(cert)


def test_discovery_reads_env_path(tmp_path: Path) -> None:
    dll = tmp_path / "fake-pkcs11.dll"
    dll.write_bytes(b"MZ")
    found = discover_pkcs11_libraries(env={ENV_PKCS11: str(dll)})
    assert dll in found or dll.resolve() in found


def test_discovery_includes_ca2_dll_name_in_defaults() -> None:
    import golden_signing.token.discovery as disc

    assert "CA2_csp11.dll" in disc._SYSTEM32_NAMES
    assert any("csp11" in n.lower() for n in disc._SYSTEM32_NAMES)
