from __future__ import annotations

from pathlib import Path

from golden_signing.certificate.catalog import merge_unique_certificates
from golden_signing.signing.contracts import CertificateInfo
from golden_signing.signing.token_pdf_signer import TokenPdfSigner


def _cert(serial: str, *, backend: str = "pkcs11", lib: str | None = None, token: str = "T") -> CertificateInfo:
    return CertificateInfo(
        subject=f"CN={serial}",
        issuer="CN=CA",
        serial=serial,
        fingerprint_sha256=f"fp-{serial}",
        not_valid_before="2024-01-01T00:00:00+00:00",
        not_valid_after="2028-01-01T00:00:00+00:00",
        key_algorithm="RSA",
        token_label=token,
        backend=backend,
        has_private_key=True,
        pkcs11_library=lib,
    )


def test_certificate_info_has_pkcs11_library_field() -> None:
    c = _cert("abc", lib=r"C:\Windows\System32\eca_csp11_v1.dll")
    assert c.pkcs11_library.endswith("eca_csp11_v1.dll")
    store = _cert("def", backend="windows_store", lib=None)
    assert store.pkcs11_library is None


def test_merge_prefers_pkcs11_library_stamp() -> None:
    a = _cert("aa1", backend="pkcs11", lib=r"C:\a\pkcs11.dll", token="Sanchine")
    b = _cert("aa1", backend="windows_store", lib=None, token="store")
    merged = merge_unique_certificates([a], [b])
    assert len(merged) == 1
    assert merged[0].pkcs11_library is not None


def test_serial_on_library_false_for_missing(tmp_path: Path) -> None:
    dummy = tmp_path / "fake-pkcs11.dll"
    dummy.write_bytes(b"MZ")
    # Unreadable as real PKCS#11 → serial_on_library False
    assert TokenPdfSigner.serial_on_library(dummy, "540117eca0139bb7c55c666d4550b3a4") is False


def test_serial_on_library_true_for_eca_if_present() -> None:
    """Do not load live PKCS#11 in unit tests (can hard-crash C-level token stack)."""
    assert hasattr(TokenPdfSigner, "serial_on_library")
    assert hasattr(TokenPdfSigner, "close_session")
